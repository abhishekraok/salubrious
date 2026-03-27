"""Tests for authentication and user accounts."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///file::memory:?cache=shared"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _register(name="Alice", email="alice@test.com", password="pass1234"):
    return client.post("/api/auth/register", json={"name": name, "email": email, "password": password})


def _login(email="alice@test.com", password="pass1234"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestAuthConfig:
    def test_config_returns_oauth_disabled(self):
        resp = client.get("/api/auth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["oauth_enabled"] is False
        assert data["google_client_id"] is None


class TestRegistration:
    def test_register_success(self):
        resp = _register()
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["name"] == "Alice"
        assert data["user"]["email"] == "alice@test.com"
        assert "token" in data

    def test_register_duplicate_email(self):
        _register()
        resp = _register()
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_register_creates_settings_and_policy(self):
        resp = _register()
        token = resp.json()["token"]
        # Should have settings
        resp = client.get("/api/settings", headers=_auth_header(token))
        assert resp.status_code == 200
        # Should have policy
        resp = client.get("/api/policy", headers=_auth_header(token))
        assert resp.status_code == 200


class TestLogin:
    def test_login_success(self):
        _register()
        resp = _login()
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "alice@test.com"
        assert "token" in data

    def test_login_wrong_password(self):
        _register()
        resp = _login(password="wrong")
        assert resp.status_code == 401

    def test_login_unknown_email(self):
        resp = _login(email="nobody@test.com")
        assert resp.status_code == 401


class TestAuthRequired:
    def test_unauthenticated_returns_401(self):
        resp = client.get("/api/accounts")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self):
        resp = client.get("/api/accounts", headers=_auth_header("bad-token"))
        assert resp.status_code == 401

    def test_authenticated_works(self):
        token = _register().json()["token"]
        resp = client.get("/api/accounts", headers=_auth_header(token))
        assert resp.status_code == 200


class TestDataIsolation:
    def test_users_see_only_their_data(self):
        # Register two users
        token_a = _register("Alice", "alice@test.com", "pass1234").json()["token"]
        token_b = _register("Bob", "bob@test.com", "pass1234").json()["token"]

        # Alice creates an account
        client.post("/api/accounts", json={
            "institution_name": "Vanguard",
            "account_name": "Alice Taxable",
            "account_type": "taxable",
        }, headers=_auth_header(token_a))

        # Alice sees her account
        resp = client.get("/api/accounts", headers=_auth_header(token_a))
        assert len(resp.json()) == 1
        assert resp.json()[0]["account_name"] == "Alice Taxable"

        # Bob sees nothing
        resp = client.get("/api/accounts", headers=_auth_header(token_b))
        assert len(resp.json()) == 0


class TestMe:
    def test_me_returns_current_user(self):
        token = _register("Alice", "alice@test.com", "pass1234").json()["token"]
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Alice"


class TestProfileExportImport:
    def test_export_returns_json(self):
        token = _register().json()["token"]
        resp = client.get("/api/profile/export", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
        assert data["user"]["name"] == "Alice"
        assert data["settings"] is not None
        assert data["policy"] is not None

    def test_import_restores_data(self):
        # Register user A, create some data
        token_a = _register("Alice", "alice@test.com", "pass1234").json()["token"]
        client.post("/api/accounts", json={
            "institution_name": "Vanguard",
            "account_name": "My Brokerage",
            "account_type": "taxable",
        }, headers=_auth_header(token_a))

        # Export user A's profile
        export = client.get("/api/profile/export", headers=_auth_header(token_a))
        export_data = export.json()

        # Register user B
        token_b = _register("Bob", "bob@test.com", "pass1234").json()["token"]

        # Import into user B
        import io
        file_content = json.dumps(export_data).encode("utf-8")
        resp = client.post(
            "/api/profile/import",
            headers=_auth_header(token_b),
            files={"file": ("profile.json", io.BytesIO(file_content), "application/json")},
        )
        assert resp.status_code == 200
        summary = resp.json()["imported"]
        assert summary["accounts"] == 1

        # User B should now have an account
        resp = client.get("/api/accounts", headers=_auth_header(token_b))
        assert len(resp.json()) == 1
        assert resp.json()[0]["account_name"] == "My Brokerage"

    def test_import_replaces_existing_data(self):
        token = _register().json()["token"]

        # Create an account
        client.post("/api/accounts", json={
            "institution_name": "Old Bank",
            "account_name": "Old Account",
            "account_type": "taxable",
        }, headers=_auth_header(token))

        # Export
        export_data = client.get("/api/profile/export", headers=_auth_header(token)).json()

        # Modify export data
        export_data["accounts"][0]["account_name"] = "Imported Account"

        # Import (should replace)
        import io
        resp = client.post(
            "/api/profile/import",
            headers=_auth_header(token),
            files={"file": ("profile.json", io.BytesIO(json.dumps(export_data).encode()), "application/json")},
        )
        assert resp.status_code == 200

        # Should have the imported account, not the old one
        resp = client.get("/api/accounts", headers=_auth_header(token))
        accounts = resp.json()
        assert len(accounts) == 1
        assert accounts[0]["account_name"] == "Imported Account"

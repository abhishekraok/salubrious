from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "salubrious.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Add columns that may be missing from older databases."""
    inspector = inspect(engine)
    if "user_profiles" not in inspector.get_table_names():
        return  # Fresh DB; create_all will handle everything

    existing = {col["name"] for col in inspector.get_columns("user_profiles")}
    migrations = [
        ("email", "VARCHAR(255)"),
        ("password_hash", "VARCHAR(255)"),
        ("google_id", "VARCHAR(255)"),
        ("avatar_url", "VARCHAR(500)"),
    ]

    with engine.begin() as conn:
        for col_name, col_type in migrations:
            if col_name not in existing:
                conn.execute(text(
                    f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}"
                ))

        # Give existing users without credentials a default login
        # so they can access their data after the auth migration
        rows = conn.execute(text(
            "SELECT id FROM user_profiles WHERE email IS NULL"
        )).fetchall()
        if rows:
            from passlib.hash import bcrypt
            default_hash = bcrypt.hash("changeme")
            for (uid,) in rows:
                conn.execute(text(
                    "UPDATE user_profiles SET email = :email, password_hash = :pw WHERE id = :uid"
                ), {"email": f"user{uid}@local", "pw": default_hash, "uid": uid})

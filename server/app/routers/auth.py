from fastapi import APIRouter, Depends, HTTPException
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..auth_config import (
    GOOGLE_CLIENT_ID,
    create_access_token,
    is_oauth_enabled,
)
from ..database import get_db
from ..models import InvestmentPolicy, UserProfile, UserSettings
from ..schemas import (
    AuthConfigOut,
    AuthResponse,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    UserProfileOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _init_user_data(user: UserProfile, db: Session) -> None:
    """Create default settings and policy for a new user."""
    settings = UserSettings(user_id=user.id)
    db.add(settings)
    policy = InvestmentPolicy(user_id=user.id, name="My Investment Policy")
    db.add(policy)
    db.commit()


@router.get("/config", response_model=AuthConfigOut)
def get_auth_config():
    return AuthConfigOut(
        oauth_enabled=is_oauth_enabled(),
        google_client_id=GOOGLE_CLIENT_ID if is_oauth_enabled() else None,
    )


@router.post("/register", response_model=AuthResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if is_oauth_enabled():
        raise HTTPException(status_code=400, detail="Registration disabled when OAuth is enabled")

    existing = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = UserProfile(
        name=data.name,
        email=data.email,
        password_hash=bcrypt.hash(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _init_user_data(user, db)

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=UserProfileOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    if is_oauth_enabled():
        raise HTTPException(status_code=400, detail="Password login disabled when OAuth is enabled")

    user = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    if not user or not user.password_hash or not bcrypt.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=UserProfileOut.model_validate(user))


@router.post("/google", response_model=AuthResponse)
async def google_auth(data: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not is_oauth_enabled():
        raise HTTPException(status_code=400, detail="OAuth is not configured")

    import httpx

    # Verify the ID token with Google
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={data.id_token}"
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        token_info = resp.json()

    if token_info.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token audience mismatch")

    google_id = token_info["sub"]
    email = token_info.get("email", "")
    name = token_info.get("name", email.split("@")[0])
    avatar_url = token_info.get("picture")

    # Find or create user
    user = db.query(UserProfile).filter(UserProfile.google_id == google_id).first()
    if not user:
        # Check if email already exists (link accounts)
        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if user:
            user.google_id = google_id
            if avatar_url:
                user.avatar_url = avatar_url
            db.commit()
        else:
            user = UserProfile(
                name=name,
                email=email,
                google_id=google_id,
                avatar_url=avatar_url,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            _init_user_data(user, db)
    else:
        # Update avatar on each login
        if avatar_url:
            user.avatar_url = avatar_url
            db.commit()

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=UserProfileOut.model_validate(user))


@router.get("/me", response_model=UserProfileOut)
def get_me(user: UserProfile = Depends(get_current_user)):
    return user

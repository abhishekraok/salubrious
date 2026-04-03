"""Google OAuth login, logout, and session check."""

import os

from fastapi import APIRouter, Depends, HTTPException, Response
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import COOKIE_NAME, create_token, get_current_user
from ..database import get_db
from ..models import UserProfile, UserSettings
from ..schemas import UserProfileOut

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: str


@router.post("/google", response_model=UserProfileOut)
def google_login(body: GoogleLoginRequest, response: Response, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    try:
        idinfo = id_token.verify_oauth2_token(
            body.credential, GoogleRequest(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_id = idinfo["sub"]
    email = idinfo.get("email", "")
    name = idinfo.get("name", email)

    user = db.query(UserProfile).filter(UserProfile.google_id == google_id).first()
    if not user:
        user = UserProfile(google_id=google_id, email=email, name=name)
        db.add(user)
        db.flush()
        db.add(UserSettings(user_id=user.id))
        db.commit()
        db.refresh(user)
    else:
        if user.email != email or user.name != name:
            user.email = email
            user.name = name
            db.commit()
            db.refresh(user)

    token = create_token(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # set True in production with HTTPS
        max_age=30 * 24 * 3600,
    )
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=UserProfileOut)
def me(user: UserProfile = Depends(get_current_user)):
    return user

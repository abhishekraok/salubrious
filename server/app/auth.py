from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .auth_config import verify_access_token
from .database import get_db
from .models import UserProfile


def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserProfile:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[7:]
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user

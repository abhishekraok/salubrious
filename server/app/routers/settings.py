from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UserProfile, UserSettings
from ..schemas import UserProfileOut, UserProfileUpdate, UserSettingsOut, UserSettingsUpdate

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/user", response_model=UserProfileOut)
def get_user(db: Session = Depends(get_db)):
    return db.query(UserProfile).first()


@router.put("/user", response_model=UserProfileOut)
def update_user(data: UserProfileUpdate, db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.get("/settings", response_model=UserSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    return db.query(UserSettings).filter(UserSettings.user_id == user.id).first()


@router.put("/settings", response_model=UserSettingsOut)
def update_settings(data: UserSettingsUpdate, db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(settings, k, v)
    db.commit()
    db.refresh(settings)
    return settings

"""Review and journal entry endpoints."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import InvestmentPolicy, JournalEntry, ReviewEntry, UserProfile
from ..schemas import (
    JournalEntryCreate,
    JournalEntryOut,
    ReviewEntryCreate,
    ReviewEntryOut,
)

router = APIRouter(prefix="/api", tags=["review"])


@router.get("/reviews", response_model=list[ReviewEntryOut])
def list_reviews(db: Session = Depends(get_db), user: UserProfile = Depends(get_current_user)):
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    return db.query(ReviewEntry).filter(ReviewEntry.policy_id == policy.id).order_by(ReviewEntry.review_date.desc()).all()


@router.post("/reviews", response_model=ReviewEntryOut)
def create_review(data: ReviewEntryCreate, db: Session = Depends(get_db), user: UserProfile = Depends(get_current_user)):
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    entry = ReviewEntry(
        policy_id=policy.id,
        review_date=data.review_date or date.today(),
        summary=data.summary,
        life_change_flag=data.life_change_flag,
        allocation_changed_flag=data.allocation_changed_flag,
        notes=data.notes,
    )
    db.add(entry)
    # Update policy review dates
    policy.last_review_date = entry.review_date
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/journal", response_model=list[JournalEntryOut])
def list_journal(db: Session = Depends(get_db), user: UserProfile = Depends(get_current_user)):
    return db.query(JournalEntry).filter(JournalEntry.user_id == user.id).order_by(JournalEntry.entry_date.desc()).all()


@router.post("/journal", response_model=JournalEntryOut)
def create_journal(data: JournalEntryCreate, db: Session = Depends(get_db), user: UserProfile = Depends(get_current_user)):
    entry = JournalEntry(
        user_id=user.id,
        entry_date=data.entry_date or date.today(),
        action_type=data.action_type,
        reason_category=data.reason_category,
        explanation=data.explanation,
        confidence_score=data.confidence_score,
        follow_up_date=data.follow_up_date,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

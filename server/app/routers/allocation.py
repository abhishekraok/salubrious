"""Allocation computation and rebalance suggestions."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..engines.allocation import compute_allocation
from ..engines.rebalance import suggest_rebalance
from ..models import Account, Holding, InvestmentPolicy, PortfolioSleeve, UserProfile

router = APIRouter(prefix="/api/allocation", tags=["allocation"])


def _get_allocation(db: Session, user: UserProfile):
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    sleeves = db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).all()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()
    return compute_allocation(holdings, sleeves), policy


@router.get("/current")
def get_current_allocation(db: Session = Depends(get_db), user: UserProfile = Depends(get_current_user)):
    allocation, _ = _get_allocation(db, user)
    return asdict(allocation)


@router.get("/suggested-actions")
def get_suggested_actions(
    pending_cash: float = Query(0.0),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(get_current_user),
):
    allocation, policy = _get_allocation(db, user)
    suggestion = suggest_rebalance(
        allocation,
        pending_cash=pending_cash,
        avoid_taxable_sales=policy.avoid_taxable_sales,
    )
    return asdict(suggestion)

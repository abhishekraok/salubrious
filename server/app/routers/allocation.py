"""Allocation computation and rebalance suggestions."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.allocation import compute_allocation
from ..engines.breakdown import compute_breakdown
from ..engines.rebalance import suggest_category_rebalance, suggest_rebalance
from ..models import Account, Holding, InvestmentPolicy, PortfolioSleeve, UserProfile

router = APIRouter(prefix="/api/allocation", tags=["allocation"])


def _get_data(db: Session):
    user = db.query(UserProfile).first()
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    sleeves = db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).all()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()
    allocation = compute_allocation(holdings, sleeves)
    return allocation, policy, sleeves, holdings


@router.get("/current")
def get_current_allocation(db: Session = Depends(get_db)):
    allocation, *_ = _get_data(db)
    return asdict(allocation)


@router.get("/suggested-actions")
def get_suggested_actions(
    pending_cash: float = Query(0.0),
    db: Session = Depends(get_db),
):
    allocation, policy, sleeves, holdings = _get_data(db)

    if getattr(policy, "targeting_mode", "fund") == "category":
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown,
            sleeves=sleeves,
            holdings=holdings,
            policy=policy,
            pending_cash=pending_cash,
            avoid_taxable_sales=policy.avoid_taxable_sales,
        )
    else:
        suggestion = suggest_rebalance(
            allocation,
            pending_cash=pending_cash,
            avoid_taxable_sales=policy.avoid_taxable_sales,
        )
    return asdict(suggestion)

"""Today page recommendation endpoint."""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.allocation import compute_allocation
from ..engines.breakdown import compute_breakdown
from ..engines.rebalance import suggest_rebalance
from ..engines.recommendation import compute_today
from ..engines.spending import compute_spending_runway
from ..models import Account, Holding, InvestmentPolicy, PortfolioSleeve, UserProfile

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])


@router.get("/today")
def get_today(db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    sleeves = db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).all()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()

    allocation = compute_allocation(holdings, sleeves)
    rebalance = suggest_rebalance(allocation, avoid_taxable_sales=policy.avoid_taxable_sales)
    runway = compute_spending_runway(holdings, sleeves, policy)

    breakdown = None
    if getattr(policy, "targeting_mode", "fund") == "category":
        breakdown = compute_breakdown(holdings, sleeves, policy)

    today = compute_today(allocation, runway, policy, rebalance, breakdown=breakdown)

    return asdict(today)

"""Spending runway and scenario endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.spending import compute_spending_guidance, compute_spending_runway, run_scenario
from ..models import Account, Holding, InvestmentPolicy, PortfolioSleeve, UserProfile

router = APIRouter(prefix="/api/spending", tags=["spending"])


class ScenarioRequest(BaseModel):
    spending_delta: float = 0.0
    portfolio_shock_percent: float = 0.0
    runway_target_change: float = 0.0


def _get_runway(db: Session):
    user = db.query(UserProfile).first()
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    sleeves = db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).all()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()
    return compute_spending_runway(holdings, sleeves, policy), policy


@router.get("/runway")
def get_runway(db: Session = Depends(get_db)):
    runway, _ = _get_runway(db)
    return asdict(runway)


@router.get("/guidance")
def get_guidance(db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()
    guidance = compute_spending_guidance(holdings, policy)
    return asdict(guidance)


@router.post("/scenario")
def post_scenario(req: ScenarioRequest, db: Session = Depends(get_db)):
    runway, policy = _get_runway(db)
    result = run_scenario(
        runway,
        baseline_spending=policy.baseline_annual_spending,
        spending_delta=req.spending_delta,
        portfolio_shock_percent=req.portfolio_shock_percent,
        runway_target_years=policy.safe_asset_runway_years_target + req.runway_target_change,
    )
    return asdict(result)

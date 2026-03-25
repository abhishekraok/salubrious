"""Spending runway and scenario endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.monte_carlo import SimulationParams, run_simulation
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


@router.get("/simulation")
def get_simulation(db: Session = Depends(get_db)):
    """Run Monte Carlo simulation of wealth trajectory."""
    user = db.query(UserProfile).first()
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    sleeves = db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).all()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()

    total_portfolio = sum(h.market_value for h in holdings)
    equity_value = sum(
        h.market_value for h in holdings
        if any(s.ticker == h.ticker and s.asset_class == "equity" for s in sleeves)
    )
    equity_fraction = equity_value / total_portfolio if total_portfolio > 0 else 0.6

    params = SimulationParams(
        current_portfolio=total_portfolio,
        annual_spending=policy.baseline_annual_spending or 0,
        years_remaining=policy.expected_years_remaining or 50,
        years_earning=policy.expected_years_earning or 0,
        after_tax_salary=policy.expected_after_tax_salary or 0,
        equity_fraction=equity_fraction,
        withdrawal_rate_pct=policy.withdrawal_rate_pct,
    )
    result = run_simulation(params)
    return asdict(result)


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

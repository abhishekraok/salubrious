"""Spending runway and guidance calculator."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Holding, InvestmentPolicy, PortfolioSleeve


@dataclass
class SpendingRunway:
    safe_asset_total: float
    cash_like_total: float
    baseline_runway_years: float
    comfortable_runway_years: float
    emergency_runway_years: float
    cash_runway_years: float
    funded_status: str  # 'secure', 'watch', 'constrained'
    above_minimum_reserve_by: float


@dataclass
class ScenarioResult:
    description: str
    adjusted_runway_years: float
    adjusted_funded_status: str
    impact_summary: str


def compute_spending_runway(
    holdings: list[Holding],
    sleeves: list[PortfolioSleeve],
    policy: InvestmentPolicy,
) -> SpendingRunway:
    """Compute spending runway from holdings, sleeve tags, and policy."""
    # Build ticker -> flags from sleeves
    safe_tickers = {s.ticker for s in sleeves if s.is_safe_asset}
    cash_tickers = {s.ticker for s in sleeves if s.is_cash_like}

    # Sum values
    value_by_ticker: dict[str, float] = {}
    for h in holdings:
        value_by_ticker[h.ticker] = value_by_ticker.get(h.ticker, 0) + h.market_value

    safe_total = sum(v for t, v in value_by_ticker.items() if t in safe_tickers)
    cash_total = sum(v for t, v in value_by_ticker.items() if t in cash_tickers)

    baseline = policy.baseline_annual_spending or 1  # avoid division by zero
    comfortable = policy.comfortable_annual_spending or baseline
    emergency = policy.emergency_annual_spending or baseline

    baseline_years = safe_total / baseline
    comfortable_years = safe_total / comfortable
    emergency_years = safe_total / emergency
    cash_years = cash_total / baseline

    target_years = policy.safe_asset_runway_years_target
    above_reserve = cash_total - policy.minimum_cash_reserve

    if baseline_years >= target_years:
        funded_status = "secure"
    elif baseline_years >= target_years * 0.75:
        funded_status = "watch"
    else:
        funded_status = "constrained"

    return SpendingRunway(
        safe_asset_total=round(safe_total, 2),
        cash_like_total=round(cash_total, 2),
        baseline_runway_years=round(baseline_years, 1),
        comfortable_runway_years=round(comfortable_years, 1),
        emergency_runway_years=round(emergency_years, 1),
        cash_runway_years=round(cash_years, 1),
        funded_status=funded_status,
        above_minimum_reserve_by=round(above_reserve, 2),
    )


@dataclass
class SpendingGuidance:
    total_portfolio_value: float
    withdrawal_rate_pct: float
    recommended_annual_spending: float
    current_baseline_spending: float
    spending_status: str  # 'low', 'appropriate', 'high'
    future_earnings_present_value: float
    effective_wealth: float  # portfolio + PV of future earnings
    effective_recommended_spending: float  # based on effective wealth
    years_remaining: int | None
    years_earning: int | None
    after_tax_salary: float | None


def compute_spending_guidance(
    holdings: list[Holding],
    policy: InvestmentPolicy,
) -> SpendingGuidance:
    """Compute recommended spending using variable percentage withdrawal with guardrails.

    Uses the policy's withdrawal_rate_pct (default 3.5%) applied to total portfolio.
    Incorporates future earnings as present value (discounted at 3% real) to compute
    effective wealth and a more nuanced recommendation.
    """
    total_value = sum(h.market_value for h in holdings)
    rate = policy.withdrawal_rate_pct / 100.0

    # Base recommendation: withdrawal rate * portfolio
    base_recommended = total_value * rate

    # Present value of future earnings (discounted at 3% real rate)
    discount_rate = 0.03
    pv_earnings = 0.0
    years_earning = policy.expected_years_earning
    salary = policy.expected_after_tax_salary
    if years_earning and salary and salary > 0:
        # PV of annuity: salary * (1 - (1+r)^-n) / r
        if discount_rate > 0:
            pv_earnings = salary * (1 - (1 + discount_rate) ** -years_earning) / discount_rate
        else:
            pv_earnings = salary * years_earning

    effective_wealth = total_value + pv_earnings

    # Recommended: withdrawal rate applied to effective wealth.
    # During accumulation, effective wealth includes PV of future earnings,
    # so recommended spending accounts for lifetime resources, not just portfolio.
    effective_recommended = effective_wealth * rate

    if pv_earnings > 0:
        recommended = effective_recommended
    else:
        recommended = base_recommended

    # Determine status relative to current baseline spending
    baseline = policy.baseline_annual_spending or 0
    if baseline <= 0:
        status = "appropriate"
    elif baseline < recommended * 0.85:
        status = "low"
    elif baseline > recommended * 1.15:
        status = "high"
    else:
        status = "appropriate"

    return SpendingGuidance(
        total_portfolio_value=round(total_value, 2),
        withdrawal_rate_pct=policy.withdrawal_rate_pct,
        recommended_annual_spending=round(recommended, 0),
        current_baseline_spending=round(baseline, 0),
        spending_status=status,
        future_earnings_present_value=round(pv_earnings, 0),
        effective_wealth=round(effective_wealth, 0),
        effective_recommended_spending=round(effective_recommended, 0),
        years_remaining=policy.expected_years_remaining,
        years_earning=policy.expected_years_earning,
        after_tax_salary=policy.expected_after_tax_salary,
    )


def run_scenario(
    runway: SpendingRunway,
    baseline_spending: float,
    spending_delta: float = 0.0,
    portfolio_shock_percent: float = 0.0,
    runway_target_years: float = 4.0,
) -> ScenarioResult:
    """Run a simple what-if scenario on the spending runway."""
    adjusted_safe = runway.safe_asset_total * (1 + portfolio_shock_percent / 100)
    adjusted_spending = baseline_spending + spending_delta

    if adjusted_spending <= 0:
        return ScenarioResult(
            description="Invalid: spending must be positive.",
            adjusted_runway_years=0,
            adjusted_funded_status="constrained",
            impact_summary="Cannot compute with zero or negative spending.",
        )

    adjusted_years = adjusted_safe / adjusted_spending

    if adjusted_years >= runway_target_years:
        status = "secure"
    elif adjusted_years >= runway_target_years * 0.75:
        status = "watch"
    else:
        status = "constrained"

    parts = []
    if spending_delta != 0:
        parts.append(f"spending {'increases' if spending_delta > 0 else 'decreases'} by ${abs(spending_delta):,.0f}/year")
    if portfolio_shock_percent != 0:
        parts.append(f"safe assets {'drop' if portfolio_shock_percent < 0 else 'increase'} by {abs(portfolio_shock_percent):.0f}%")

    description = "If " + " and ".join(parts) + ":" if parts else "Current state:"

    return ScenarioResult(
        description=description,
        adjusted_runway_years=round(adjusted_years, 1),
        adjusted_funded_status=status,
        impact_summary=f"Safe assets would cover {adjusted_years:.1f} years of spending.",
    )

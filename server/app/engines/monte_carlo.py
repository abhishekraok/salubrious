"""Monte Carlo simulation for spending sustainability.

Simulates portfolio wealth trajectories over the user's remaining lifetime,
accounting for annual spending, future earnings, and stochastic market returns.
Produces percentile bands for wealth trajectory and ruin probability.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SimulationParams:
    current_portfolio: float
    annual_spending: float
    years_remaining: int
    years_earning: int = 0
    after_tax_salary: float = 0.0
    equity_fraction: float = 0.67  # used to blend return distribution
    withdrawal_rate_pct: float = 3.5
    n_simulations: int = 2000
    seed: int | None = 42


@dataclass
class SimulationResult:
    # Per-year percentile bands for wealth (years_remaining + 1 points including year 0)
    years: list[int]
    p5: list[float]
    p25: list[float]
    p50: list[float]
    p75: list[float]
    p95: list[float]
    ruin_probability: float  # fraction of simulations that hit zero
    ruin_by_year: list[float]  # cumulative ruin probability at each year
    # Spending corridor: floor and ceiling based on guardrails
    spending_floor: float
    spending_recommended: float
    spending_ceiling: float


# Historical real return parameters (approximate)
# Equities: ~7% real mean, ~16% std dev
# Bonds: ~2% real mean, ~6% std dev
EQUITY_MEAN = 0.07
EQUITY_STD = 0.16
BOND_MEAN = 0.02
BOND_STD = 0.06
CORRELATION = 0.0  # simplified: equity-bond correlation ~0


def run_simulation(params: SimulationParams) -> SimulationResult:
    """Run Monte Carlo simulation of portfolio wealth over time.

    Uses a blended return distribution based on equity/bond allocation.
    Each year: portfolio = portfolio * (1 + return) - spending + salary (if still earning).
    Portfolio is floored at 0 (can't go negative).
    """
    rng = np.random.default_rng(params.seed)

    n = params.n_simulations
    years = params.years_remaining

    # Blended return distribution
    eq = params.equity_fraction
    blended_mean = eq * EQUITY_MEAN + (1 - eq) * BOND_MEAN
    # Variance of blend (assuming zero correlation for simplicity)
    blended_std = np.sqrt(eq**2 * EQUITY_STD**2 + (1 - eq)**2 * BOND_STD**2)

    # Generate all returns at once: (n_simulations, years)
    returns = rng.normal(blended_mean, blended_std, size=(n, years))

    # Simulate wealth trajectories
    # wealth_matrix: (n_simulations, years+1) — includes year 0
    wealth = np.zeros((n, years + 1))
    wealth[:, 0] = params.current_portfolio

    spending = params.annual_spending

    for t in range(years):
        # Market return
        wealth[:, t + 1] = wealth[:, t] * (1 + returns[:, t])

        # Subtract spending
        wealth[:, t + 1] -= spending

        # Add salary if still earning
        if t < params.years_earning:
            wealth[:, t + 1] += params.after_tax_salary

        # Floor at zero
        np.maximum(wealth[:, t + 1], 0, out=wealth[:, t + 1])

    # Compute percentiles at each year
    p5 = np.percentile(wealth, 5, axis=0).tolist()
    p25 = np.percentile(wealth, 25, axis=0).tolist()
    p50 = np.percentile(wealth, 50, axis=0).tolist()
    p75 = np.percentile(wealth, 75, axis=0).tolist()
    p95 = np.percentile(wealth, 95, axis=0).tolist()

    # Ruin: any simulation where wealth hits 0
    ever_ruined = np.any(wealth[:, 1:] <= 0, axis=1)
    ruin_probability = float(np.mean(ever_ruined))

    # Cumulative ruin by year
    cumulative_ruin = np.zeros(years + 1)
    for t in range(1, years + 1):
        cumulative_ruin[t] = float(np.mean(np.any(wealth[:, 1:t + 1] <= 0, axis=1)))

    # Spending corridor (guardrails: ±20% of recommended)
    recommended = params.current_portfolio * (params.withdrawal_rate_pct / 100.0)
    floor_spending = recommended * 0.80
    ceiling_spending = recommended * 1.20

    return SimulationResult(
        years=list(range(years + 1)),
        p5=[round(v, 0) for v in p5],
        p25=[round(v, 0) for v in p25],
        p50=[round(v, 0) for v in p50],
        p75=[round(v, 0) for v in p75],
        p95=[round(v, 0) for v in p95],
        ruin_probability=round(ruin_probability, 4),
        ruin_by_year=[round(v, 4) for v in cumulative_ruin.tolist()],
        spending_floor=round(floor_spending, 0),
        spending_recommended=round(recommended, 0),
        spending_ceiling=round(ceiling_spending, 0),
    )

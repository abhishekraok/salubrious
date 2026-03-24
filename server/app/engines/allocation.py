"""Allocation calculator: maps holdings to sleeves, computes drift."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Holding, PortfolioSleeve
from .bands import classify_drift, compute_bands


@dataclass
class SleeveAllocation:
    ticker: str
    label: str
    current_value: float
    current_percent: float
    target_percent: float
    drift_pp: float
    soft_band: float
    hard_band: float
    status: str  # 'ok', 'watch', 'action_needed'
    is_safe_asset: bool = False
    is_cash_like: bool = False


@dataclass
class AllocationResult:
    total_value: float
    sleeves: list[SleeveAllocation] = field(default_factory=list)
    sleeves_outside_soft: int = 0
    sleeves_outside_hard: int = 0


def compute_allocation(
    holdings: list[Holding],
    sleeves: list[PortfolioSleeve],
) -> AllocationResult:
    """Compute current allocation vs target for all sleeves."""

    # Sum market value by ticker across all accounts
    value_by_ticker: dict[str, float] = {}
    for h in holdings:
        value_by_ticker[h.ticker] = value_by_ticker.get(h.ticker, 0) + h.market_value

    total_value = sum(value_by_ticker.values())

    if total_value == 0:
        return AllocationResult(total_value=0)

    result_sleeves: list[SleeveAllocation] = []
    outside_soft = 0
    outside_hard = 0

    for sleeve in sleeves:
        current_value = value_by_ticker.get(sleeve.ticker, 0.0)
        current_percent = (current_value / total_value) * 100
        drift_pp = current_percent - sleeve.target_percent
        soft, hard = compute_bands(sleeve.target_percent)
        status = classify_drift(drift_pp, soft, hard)

        if status == "watch":
            outside_soft += 1
        elif status == "action_needed":
            outside_soft += 1
            outside_hard += 1

        result_sleeves.append(SleeveAllocation(
            ticker=sleeve.ticker,
            label=sleeve.label,
            current_value=current_value,
            current_percent=round(current_percent, 2),
            target_percent=sleeve.target_percent,
            drift_pp=round(drift_pp, 2),
            soft_band=soft,
            hard_band=hard,
            status=status,
            is_safe_asset=sleeve.is_safe_asset,
            is_cash_like=sleeve.is_cash_like,
        ))

    return AllocationResult(
        total_value=round(total_value, 2),
        sleeves=sorted(result_sleeves, key=lambda s: s.ticker),
        sleeves_outside_soft=outside_soft,
        sleeves_outside_hard=outside_hard,
    )

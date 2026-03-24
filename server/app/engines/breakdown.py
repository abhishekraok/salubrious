"""Portfolio breakdown engine: aggregate by asset class, region, factors.

Targets come from category-level targets on the policy (if set),
with current values always computed from actual holdings + sleeve metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..models import Holding, InvestmentPolicy, PortfolioSleeve


@dataclass
class BreakdownEntry:
    label: str
    current_pct: float
    target_pct: float


@dataclass
class PortfolioBreakdown:
    asset_type: list[BreakdownEntry] = field(default_factory=list)
    region: list[BreakdownEntry] = field(default_factory=list)
    factor_value: list[BreakdownEntry] = field(default_factory=list)
    factor_size: list[BreakdownEntry] = field(default_factory=list)


def _normalize(d: dict[str, float]) -> dict[str, float]:
    """Normalize values to sum to 100%."""
    total = sum(d.values())
    if total == 0:
        return d
    return {k: v / total * 100 for k, v in d.items()}


def compute_breakdown(
    holdings: list[Holding],
    sleeves: list[PortfolioSleeve],
    policy: Optional[InvestmentPolicy] = None,
) -> PortfolioBreakdown:
    value_by_ticker: dict[str, float] = {}
    for h in holdings:
        value_by_ticker[h.ticker] = value_by_ticker.get(h.ticker, 0) + h.market_value

    total_value = sum(value_by_ticker.values())

    if total_value == 0 and not sleeves:
        return PortfolioBreakdown()

    # Use category targets only when mode is "category"
    use_cat = policy is not None and getattr(policy, "targeting_mode", "fund") == "category"
    cat_equity = policy.target_equity_pct if use_cat and policy.target_equity_pct is not None else None
    cat_intl = policy.target_international_pct if use_cat and policy.target_international_pct is not None else None
    cat_value = policy.target_value_tilted_pct if use_cat and policy.target_value_tilted_pct is not None else None
    cat_small = policy.target_small_cap_pct if use_cat and policy.target_small_cap_pct is not None else None

    # --- Asset type: Safe vs Equity ---
    asset_type_current: dict[str, float] = {"Equities": 0, "Safe Assets": 0}
    for sleeve in sleeves:
        bucket = "Safe Assets" if sleeve.is_safe_asset else "Equities"
        cur_val = value_by_ticker.get(sleeve.ticker, 0.0)
        cur_pct = (cur_val / total_value * 100) if total_value else 0
        asset_type_current[bucket] += cur_pct

    if cat_equity is not None:
        asset_type_target = {"Equities": cat_equity, "Safe Assets": 100 - cat_equity}
    else:
        asset_type_target: dict[str, float] = {"Equities": 0, "Safe Assets": 0}
        for sleeve in sleeves:
            bucket = "Safe Assets" if sleeve.is_safe_asset else "Equities"
            asset_type_target[bucket] += sleeve.target_percent

    # --- Equity-only for region and factor breakdowns ---
    equity_sleeves = [s for s in sleeves if not s.is_safe_asset]
    equity_total_value = sum(value_by_ticker.get(s.ticker, 0.0) for s in equity_sleeves)

    # --- Region (equity only, US vs International) ---
    us_current = 0.0
    intl_current = 0.0
    for sleeve in equity_sleeves:
        cur_val = value_by_ticker.get(sleeve.ticker, 0.0)
        cur_pct = (cur_val / equity_total_value * 100) if equity_total_value else 0
        us_current += cur_pct * sleeve.region_us_pct / 100
        intl_current += cur_pct * (sleeve.region_developed_pct + sleeve.region_emerging_pct) / 100

    region_current = {"US": us_current, "International": intl_current}

    if cat_intl is not None:
        region_target = {"US": 100 - cat_intl, "International": cat_intl}
    else:
        us_tgt = 0.0
        intl_tgt = 0.0
        for sleeve in equity_sleeves:
            us_tgt += sleeve.target_percent * sleeve.region_us_pct / 100
            intl_tgt += sleeve.target_percent * (sleeve.region_developed_pct + sleeve.region_emerging_pct) / 100
        total_tgt = us_tgt + intl_tgt
        if total_tgt > 0:
            region_target = {"US": us_tgt / total_tgt * 100, "International": intl_tgt / total_tgt * 100}
        else:
            region_target: dict[str, float] = {"US": 0, "International": 0}

    # --- Factor: Value (equity only, normalized to 100%) ---
    fv_current: dict[str, float] = {}
    for sleeve in equity_sleeves:
        label = (sleeve.factor_value or "blend").capitalize()
        cur_val = value_by_ticker.get(sleeve.ticker, 0.0)
        cur_pct = (cur_val / equity_total_value * 100) if equity_total_value else 0
        fv_current[label] = fv_current.get(label, 0) + cur_pct

    if cat_value is not None:
        fv_target = {"Tilted": cat_value, "Blend": 100 - cat_value}
    else:
        fv_target: dict[str, float] = {}
        for sleeve in equity_sleeves:
            label = (sleeve.factor_value or "blend").capitalize()
            fv_target[label] = fv_target.get(label, 0) + sleeve.target_percent
        fv_target = _normalize(fv_target)

    # --- Factor: Size (equity only, Small vs Other) ---
    small_current = 0.0
    other_current = 0.0
    for sleeve in equity_sleeves:
        cur_val = value_by_ticker.get(sleeve.ticker, 0.0)
        cur_pct = (cur_val / equity_total_value * 100) if equity_total_value else 0
        if (sleeve.factor_size or "").lower() == "small":
            small_current += cur_pct
        else:
            other_current += cur_pct

    fs_current = {"Small Cap": small_current, "Other": other_current}

    if cat_small is not None:
        fs_target = {"Small Cap": cat_small, "Other": 100 - cat_small}
    else:
        small_tgt = 0.0
        other_tgt = 0.0
        for sleeve in equity_sleeves:
            if (sleeve.factor_size or "").lower() == "small":
                small_tgt += sleeve.target_percent
            else:
                other_tgt += sleeve.target_percent
        total_tgt = small_tgt + other_tgt
        if total_tgt > 0:
            fs_target = {"Small Cap": small_tgt / total_tgt * 100, "Other": other_tgt / total_tgt * 100}
        else:
            fs_target: dict[str, float] = {"Small Cap": 0, "Other": 0}

    def to_entries(current: dict[str, float], target: dict[str, float]) -> list[BreakdownEntry]:
        all_keys = sorted(set(current) | set(target))
        return [
            BreakdownEntry(
                label=k,
                current_pct=round(current.get(k, 0), 1),
                target_pct=round(target.get(k, 0), 1),
            )
            for k in all_keys
        ]

    return PortfolioBreakdown(
        asset_type=to_entries(asset_type_current, asset_type_target),
        region=to_entries(region_current, region_target),
        factor_value=to_entries(fv_current, fv_target),
        factor_size=to_entries(fs_current, fs_target),
    )

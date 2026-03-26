"""Shared test fixtures for engine tests.

Uses simple namespace objects to simulate SQLAlchemy ORM models without
needing a database connection.
"""
from types import SimpleNamespace


def make_holding(ticker: str, market_value: float) -> SimpleNamespace:
    return SimpleNamespace(ticker=ticker, market_value=market_value)


def make_sleeve(
    ticker: str,
    label: str,
    target_percent: float,
    is_safe_asset: bool = False,
    is_cash_like: bool = False,
    region_us_pct: float = 100.0,
    region_developed_pct: float = 0.0,
    region_emerging_pct: float = 0.0,
    factor_value: str | None = None,
    factor_size: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        ticker=ticker,
        label=label,
        target_percent=target_percent,
        is_safe_asset=is_safe_asset,
        is_cash_like=is_cash_like,
        region_us_pct=region_us_pct,
        region_developed_pct=region_developed_pct,
        region_emerging_pct=region_emerging_pct,
        factor_value=factor_value,
        factor_size=factor_size,
    )


def make_policy(
    baseline_annual_spending: float = 50_000.0,
    comfortable_annual_spending: float = 60_000.0,
    emergency_annual_spending: float = 40_000.0,
    safe_asset_runway_years_target: float = 4.0,
    minimum_cash_reserve: float = 10_000.0,
    targeting_mode: str = "fund",
    target_equity_pct: float | None = None,
    target_international_pct: float | None = None,
    target_value_tilted_pct: float | None = None,
    target_small_cap_pct: float | None = None,
    next_review_date=None,
    last_review_date=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        baseline_annual_spending=baseline_annual_spending,
        comfortable_annual_spending=comfortable_annual_spending,
        emergency_annual_spending=emergency_annual_spending,
        safe_asset_runway_years_target=safe_asset_runway_years_target,
        minimum_cash_reserve=minimum_cash_reserve,
        targeting_mode=targeting_mode,
        target_equity_pct=target_equity_pct,
        target_international_pct=target_international_pct,
        target_value_tilted_pct=target_value_tilted_pct,
        target_small_cap_pct=target_small_cap_pct,
        next_review_date=next_review_date,
        last_review_date=last_review_date,
    )

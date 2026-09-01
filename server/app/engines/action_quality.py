"""Evaluate historical allocation decisions against a benchmark.

The engine intentionally answers a narrow counterfactual question: how did the
security bought perform over the same observable window as the benchmark?  It
does not attempt to infer whether a transaction caused a portfolio outcome.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import math
from typing import Iterable, Mapping, TypeAlias


DateLike: TypeAlias = date | datetime | str
PriceSeries: TypeAlias = Mapping[DateLike, float]
PriceHistory: TypeAlias = Mapping[str, PriceSeries]

DEFAULT_BENCHMARK = "VFFVX"
DEFAULT_HORIZON_DAYS = 365
DEFAULT_DEADBAND_PCT_POINTS = 2.0

# Automatic dividends and cash movements are deliberately absent.  Callers can
# opt into additional canonical action types when they represent real allocation
# choices in their source data.
DEFAULT_SCORABLE_ACTION_TYPES = frozenset({"buy", "purchase", "exchange_in"})

SUMMARY_INTERPRETATION = (
    "Notional-weighted comparison with the benchmark. Overlapping action "
    "counterfactuals are descriptive, not additive or causal."
)


@dataclass(frozen=True)
class AllocationAction:
    """A normalized transaction that may represent an allocation decision."""

    action_id: str
    action_date: DateLike
    action_type: str
    ticker: str | None
    notional: float


@dataclass(frozen=True)
class ActionQuality:
    """JSON-ready score for one action."""

    action_id: str
    action_date: str
    action_type: str
    ticker: str | None
    notional: float
    benchmark_ticker: str
    score_status: str  # scored, excluded, missing_prices, duplicate
    reason: str | None
    maturity: str | None  # mature, developing
    outcome: str | None  # ahead, similar, behind
    entry_date: str | None
    evaluation_date: str | None
    horizon_date: str | None
    observed_days: int | None
    chosen_return_pct: float | None
    benchmark_return_pct: float | None
    advantage_pct_points: float | None
    opportunity_cost: float | None


@dataclass(frozen=True)
class ActionQualitySummary:
    """Notional-weighted descriptive summary of independently scored actions."""

    benchmark_ticker: str
    horizon_days: int
    deadband_pct_points: float
    total_actions: int
    scored_actions: int
    mature_actions: int
    developing_actions: int
    ahead_actions: int
    similar_actions: int
    behind_actions: int
    excluded_actions: int
    missing_price_actions: int
    duplicate_actions: int
    scored_notional: float
    weighted_advantage_pct_points: float | None
    weighted_outcome: str | None
    interpretation: str = SUMMARY_INTERPRETATION


@dataclass(frozen=True)
class ActionQualityReport:
    """Collection returned by :func:`score_actions`."""

    actions: list[ActionQuality]
    summary: ActionQualitySummary

    def to_dict(self) -> dict[str, object]:
        """Return a structure containing only JSON-serializable primitives."""

        return asdict(self)


def score_action(
    action: AllocationAction,
    prices_by_ticker: PriceHistory,
    *,
    benchmark_ticker: str = DEFAULT_BENCHMARK,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    as_of: DateLike | None = None,
    deadband_pct_points: float = DEFAULT_DEADBAND_PCT_POINTS,
    scorable_action_types: Iterable[str] = DEFAULT_SCORABLE_ACTION_TYPES,
) -> ActionQuality:
    """Score one buy-like action using adjusted-close total returns.

    Entry is the first date on or after the action date for which both the
    selected security and benchmark have a valid adjusted close.  Evaluation is
    the last such common date no later than the aligned entry plus ``horizon_days``
    or ``as_of``, whichever comes first.
    """

    _validate_options(horizon_days, deadband_pct_points)
    benchmark = benchmark_ticker.strip().upper()
    action_type = _normalize_action_type(action.action_type)
    ticker = action.ticker.strip().upper() if action.ticker and action.ticker.strip() else None
    notional = _normalize_notional(action.notional)

    try:
        action_date = _coerce_date(action.action_date)
    except (TypeError, ValueError):
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="excluded",
            reason="invalid_action_date",
        )

    allowed_types = {_normalize_action_type(value) for value in scorable_action_types}
    if action_type not in allowed_types:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="excluded",
            reason="action_type_not_scorable",
            action_date=action_date,
        )
    if not ticker:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=None,
            notional=notional,
            score_status="missing_prices",
            reason="missing_ticker",
            action_date=action_date,
        )
    if notional <= 0:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="excluded",
            reason="invalid_notional",
            action_date=action_date,
        )

    normalized_history = {
        str(symbol).strip().upper(): _normalize_series(series)
        for symbol, series in prices_by_ticker.items()
    }
    chosen_prices = normalized_history.get(ticker, {})
    benchmark_prices = normalized_history.get(benchmark, {})
    if not chosen_prices:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="missing_prices",
            reason="missing_security_prices",
            action_date=action_date,
        )
    if not benchmark_prices:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="missing_prices",
            reason="missing_benchmark_prices",
            action_date=action_date,
        )

    common_dates = sorted(chosen_prices.keys() & benchmark_prices.keys())
    if not common_dates:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="missing_prices",
            reason="no_common_price_dates",
            action_date=action_date,
        )

    as_of_date = _coerce_date(as_of) if as_of is not None else common_dates[-1]
    entry_candidates = [day for day in common_dates if action_date <= day <= as_of_date]
    if not entry_candidates:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="missing_prices",
            reason="no_common_price_on_or_after_action_date",
            action_date=action_date,
        )

    entry_date = entry_candidates[0]
    horizon_date = entry_date + timedelta(days=horizon_days)
    cutoff_date = min(horizon_date, as_of_date)
    evaluation_candidates = [
        day for day in common_dates if entry_date <= day <= cutoff_date
    ]
    if not evaluation_candidates:
        return _unscored(
            action,
            benchmark=benchmark,
            action_type=action_type,
            ticker=ticker,
            notional=notional,
            score_status="missing_prices",
            reason="no_common_evaluation_price",
            action_date=action_date,
        )

    evaluation_date = evaluation_candidates[-1]
    chosen_return = (chosen_prices[evaluation_date] / chosen_prices[entry_date] - 1) * 100
    benchmark_return = (
        benchmark_prices[evaluation_date] / benchmark_prices[entry_date] - 1
    ) * 100
    # Stabilize exact deadband boundaries against binary floating-point noise.
    advantage = round(chosen_return - benchmark_return, 10)
    outcome = _outcome(advantage, deadband_pct_points)
    opportunity_cost = max(0.0, -advantage / 100 * notional)

    return ActionQuality(
        action_id=action.action_id,
        action_date=action_date.isoformat(),
        action_type=action_type,
        ticker=ticker,
        notional=round(notional, 2),
        benchmark_ticker=benchmark,
        score_status="scored",
        reason=None,
        maturity="mature" if as_of_date >= horizon_date else "developing",
        outcome=outcome,
        entry_date=entry_date.isoformat(),
        evaluation_date=evaluation_date.isoformat(),
        horizon_date=horizon_date.isoformat(),
        observed_days=(evaluation_date - entry_date).days,
        chosen_return_pct=round(chosen_return, 4),
        benchmark_return_pct=round(benchmark_return, 4),
        advantage_pct_points=round(advantage, 4),
        opportunity_cost=round(opportunity_cost, 2),
    )


def score_actions(
    actions: Iterable[AllocationAction],
    prices_by_ticker: PriceHistory,
    *,
    benchmark_ticker: str = DEFAULT_BENCHMARK,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    as_of: DateLike | None = None,
    deadband_pct_points: float = DEFAULT_DEADBAND_PCT_POINTS,
    scorable_action_types: Iterable[str] = DEFAULT_SCORABLE_ACTION_TYPES,
) -> ActionQualityReport:
    """Score actions once per non-empty action id and return a weighted summary."""

    _validate_options(horizon_days, deadband_pct_points)
    benchmark = benchmark_ticker.strip().upper()
    results: list[ActionQuality] = []
    seen_ids: set[str] = set()

    for action in actions:
        identity = action.action_id.strip()
        if identity and identity in seen_ids:
            results.append(
                _unscored(
                    action,
                    benchmark=benchmark,
                    action_type=_normalize_action_type(action.action_type),
                    ticker=(
                        action.ticker.strip().upper()
                        if action.ticker and action.ticker.strip()
                        else None
                    ),
                    notional=_normalize_notional(action.notional),
                    score_status="duplicate",
                    reason="duplicate_action_id",
                )
            )
            continue
        if identity:
            seen_ids.add(identity)

        results.append(
            score_action(
                action,
                prices_by_ticker,
                benchmark_ticker=benchmark,
                horizon_days=horizon_days,
                as_of=as_of,
                deadband_pct_points=deadband_pct_points,
                scorable_action_types=scorable_action_types,
            )
        )

    return ActionQualityReport(
        actions=results,
        summary=summarize_action_quality(
            results,
            benchmark_ticker=benchmark,
            horizon_days=horizon_days,
            deadband_pct_points=deadband_pct_points,
        ),
    )


def summarize_action_quality(
    actions: Iterable[ActionQuality],
    *,
    benchmark_ticker: str = DEFAULT_BENCHMARK,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    deadband_pct_points: float = DEFAULT_DEADBAND_PCT_POINTS,
) -> ActionQualitySummary:
    """Build a notional-weighted summary without summing counterfactual losses."""

    _validate_options(horizon_days, deadband_pct_points)
    results = list(actions)
    scored = [result for result in results if result.score_status == "scored"]
    scored_notional = sum(result.notional for result in scored)

    if scored and scored_notional > 0:
        weighted_advantage = sum(
            result.notional * (result.advantage_pct_points or 0.0)
            for result in scored
        ) / scored_notional
        weighted_outcome = _outcome(weighted_advantage, deadband_pct_points)
        weighted_advantage_value: float | None = round(weighted_advantage, 4)
    else:
        weighted_advantage_value = None
        weighted_outcome = None

    return ActionQualitySummary(
        benchmark_ticker=benchmark_ticker.strip().upper(),
        horizon_days=horizon_days,
        deadband_pct_points=deadband_pct_points,
        total_actions=len(results),
        scored_actions=len(scored),
        mature_actions=sum(result.maturity == "mature" for result in scored),
        developing_actions=sum(result.maturity == "developing" for result in scored),
        ahead_actions=sum(result.outcome == "ahead" for result in scored),
        similar_actions=sum(result.outcome == "similar" for result in scored),
        behind_actions=sum(result.outcome == "behind" for result in scored),
        excluded_actions=sum(result.score_status == "excluded" for result in results),
        missing_price_actions=sum(
            result.score_status == "missing_prices" for result in results
        ),
        duplicate_actions=sum(result.score_status == "duplicate" for result in results),
        scored_notional=round(scored_notional, 2),
        weighted_advantage_pct_points=weighted_advantage_value,
        weighted_outcome=weighted_outcome,
    )


def _unscored(
    action: AllocationAction,
    *,
    benchmark: str,
    action_type: str,
    ticker: str | None,
    notional: float,
    score_status: str,
    reason: str,
    action_date: date | None = None,
) -> ActionQuality:
    if action_date is None:
        try:
            action_date_text = _coerce_date(action.action_date).isoformat()
        except (TypeError, ValueError):
            action_date_text = str(action.action_date)
    else:
        action_date_text = action_date.isoformat()

    return ActionQuality(
        action_id=action.action_id,
        action_date=action_date_text,
        action_type=action_type,
        ticker=ticker,
        notional=round(notional, 2),
        benchmark_ticker=benchmark,
        score_status=score_status,
        reason=reason,
        maturity=None,
        outcome=None,
        entry_date=None,
        evaluation_date=None,
        horizon_date=None,
        observed_days=None,
        chosen_return_pct=None,
        benchmark_return_pct=None,
        advantage_pct_points=None,
        opportunity_cost=None,
    )


def _normalize_series(series: PriceSeries) -> dict[date, float]:
    normalized: dict[date, float] = {}
    for raw_date, raw_price in series.items():
        try:
            day = _coerce_date(raw_date)
            price = float(raw_price)
        except (TypeError, ValueError):
            continue
        if price > 0 and math.isfinite(price):
            normalized[day] = price
    return normalized


def _coerce_date(value: DateLike) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return date.fromisoformat(text)
        except ValueError:
            return datetime.fromisoformat(text).date()
    raise TypeError(f"Unsupported date value: {value!r}")


def _normalize_action_type(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_notional(value: float) -> float:
    try:
        notional = abs(float(value))
    except (TypeError, ValueError):
        return 0.0
    return notional if math.isfinite(notional) else 0.0


def _outcome(advantage_pct_points: float, deadband_pct_points: float) -> str:
    if advantage_pct_points > deadband_pct_points:
        return "ahead"
    if advantage_pct_points < -deadband_pct_points:
        return "behind"
    return "similar"


def _validate_options(horizon_days: int, deadband_pct_points: float) -> None:
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if deadband_pct_points < 0:
        raise ValueError("deadband_pct_points cannot be negative")

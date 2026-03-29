"""Rebalance suggestion engine (MVP simplified)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..models import Holding, InvestmentPolicy, PortfolioSleeve
from .allocation import AllocationResult
from .bands import classify_drift, compute_bands
from .breakdown import PortfolioBreakdown, compute_breakdown


@dataclass
class ActionItem:
    action: str  # 'buy', 'sell', 'exchange'
    ticker: str
    amount: float
    source_ticker: str | None = None
    rationale: str = ""


@dataclass
class RebalanceSuggestion:
    headline: str
    action_items: list[ActionItem] = field(default_factory=list)
    rationale: str = ""
    urgency: str = "none"  # 'none', 'low', 'medium', 'high'


def suggest_rebalance(
    allocation: AllocationResult,
    pending_cash: float = 0.0,
    avoid_taxable_sales: bool = True,
) -> RebalanceSuggestion:
    """Generate minimum-action rebalance suggestion.

    Algorithm (MVP):
    1. Find overweight sleeves outside band.
    2. Find underweight sleeves outside band.
    3. If pending cash can resolve underweights, direct cash there.
    4. Else if cash-like sleeve is overweight, suggest exchange.
    5. Else suggest minimum transfer between most-over and most-under.
    """
    if not allocation.sleeves:
        return RebalanceSuggestion(headline="No holdings to rebalance")

    # No action needed
    if allocation.sleeves_outside_soft == 0:
        return RebalanceSuggestion(
            headline="No action needed",
            rationale="All sleeves are within tolerance bands.",
            urgency="none",
        )

    overweight = [s for s in allocation.sleeves if s.drift_pp > s.soft_band]
    underweight = [s for s in allocation.sleeves if s.drift_pp < -s.soft_band]

    # Sort by magnitude of drift
    overweight.sort(key=lambda s: s.drift_pp, reverse=True)
    underweight.sort(key=lambda s: s.drift_pp)

    has_hard_breach = allocation.sleeves_outside_hard > 0
    urgency = "high" if has_hard_breach else "low"

    action_items: list[ActionItem] = []

    # Calculate total underweight dollar amount needed
    total_underweight_dollars = sum(
        abs(s.drift_pp) / 100 * allocation.total_value for s in underweight
    )

    # Strategy 1: Use pending cash to fill underweight
    if pending_cash > 0 and underweight:
        remaining_cash = pending_cash
        for s in underweight:
            needed = abs(s.drift_pp) / 100 * allocation.total_value
            deploy = min(needed, remaining_cash)
            if deploy > 0:
                action_items.append(ActionItem(
                    action="buy",
                    ticker=s.ticker,
                    amount=round(deploy, 2),
                    rationale=f"{s.ticker} is {abs(s.drift_pp):.1f}pp below target.",
                ))
                remaining_cash -= deploy
            if remaining_cash <= 0:
                break

        if action_items:
            return RebalanceSuggestion(
                headline=f"Direct ${pending_cash:,.0f} contribution to underweight sleeves",
                action_items=action_items,
                rationale="New contributions can restore balance without selling.",
                urgency=urgency,
            )

    # Strategy 2: Exchange from overweight cash-like to underweight
    cash_like_over = [s for s in overweight if s.is_cash_like]
    if cash_like_over and underweight:
        source = cash_like_over[0]
        target = underweight[0]
        available = source.drift_pp / 100 * allocation.total_value
        needed = abs(target.drift_pp) / 100 * allocation.total_value
        amount = round(min(available, needed), 2)

        action_items.append(ActionItem(
            action="exchange",
            ticker=target.ticker,
            amount=amount,
            source_ticker=source.ticker,
            rationale=(
                f"{source.ticker} is {source.drift_pp:.1f}pp above target and "
                f"{target.ticker} is {abs(target.drift_pp):.1f}pp below target. "
                f"A transfer restores allocation without taxable equity sales."
            ),
        ))

        return RebalanceSuggestion(
            headline=f"Exchange ${amount:,.0f} from {source.ticker} to {target.ticker}",
            action_items=action_items,
            rationale=action_items[0].rationale,
            urgency=urgency,
        )

    # Strategy 3: Exchange from most overweight to most underweight
    if overweight and underweight:
        source = overweight[0]
        target = underweight[0]

        if avoid_taxable_sales and not source.is_cash_like and not source.is_safe_asset:
            return RebalanceSuggestion(
                headline="Rebalance suggested but requires taxable sale",
                rationale=(
                    f"{source.ticker} is {source.drift_pp:.1f}pp overweight and "
                    f"{target.ticker} is {abs(target.drift_pp):.1f}pp underweight. "
                    f"Rebalancing would require selling {source.ticker} in a taxable account. "
                    f"Consider waiting for new contributions or a scheduled review."
                ),
                urgency="low",
            )

        available = source.drift_pp / 100 * allocation.total_value
        needed = abs(target.drift_pp) / 100 * allocation.total_value
        amount = round(min(available, needed), 2)

        action_items.append(ActionItem(
            action="exchange",
            ticker=target.ticker,
            amount=amount,
            source_ticker=source.ticker,
            rationale=(
                f"{source.ticker} is {source.drift_pp:.1f}pp above target and "
                f"{target.ticker} is {abs(target.drift_pp):.1f}pp below target."
            ),
        ))

        return RebalanceSuggestion(
            headline=f"Exchange ${amount:,.0f} from {source.ticker} to {target.ticker}",
            action_items=action_items,
            rationale=action_items[0].rationale,
            urgency=urgency,
        )

    # Only overweight with nothing underweight (rare)
    return RebalanceSuggestion(
        headline="Portfolio drift detected",
        rationale="Some sleeves are outside bands but no clear rebalance action is available. Review at next scheduled date.",
        urgency="low",
    )


# ---------------------------------------------------------------------------
# Category-mode rebalance: map category drift to concrete fund-level trades
# ---------------------------------------------------------------------------


@dataclass
class _CategoryDrift:
    """A single drifted category dimension with fund groupings."""
    dimension: str          # e.g. "Asset Type", "Region"
    label_over: str         # label of the overweight side (e.g. "Equities")
    label_under: str        # label of the underweight side (e.g. "Safe Assets")
    drift_pp: float         # abs drift of the overweight entry
    status: str             # 'watch' or 'action_needed'
    sell_tickers: list[str] # candidate tickers to sell (overweight side)
    buy_tickers: list[str]  # candidate tickers to buy (underweight side)
    dollar_amount: float    # $ needed to restore balance


def _category_drifts(
    breakdown: PortfolioBreakdown,
    sleeves: list[PortfolioSleeve],
    value_by_ticker: dict[str, float],
    total_value: float,
) -> list[_CategoryDrift]:
    """Identify drifted categories and map them to candidate fund groups."""

    equity_sleeves = [s for s in sleeves if not s.is_safe_asset]
    safe_sleeves = [s for s in sleeves if s.is_safe_asset]
    equity_total = sum(value_by_ticker.get(s.ticker, 0.0) for s in equity_sleeves)

    drifts: list[_CategoryDrift] = []

    # Helper: find entries with drift outside bands in a breakdown dimension
    def _check(entries: list) -> tuple[Optional[object], Optional[object], float, str]:
        """Return (over_entry, under_entry, abs_drift, status) for worst-drifted pair."""
        over_entry = None
        under_entry = None
        worst_abs = 0.0
        worst_status = "ok"
        for e in entries:
            if e.target_pct == 0:
                continue
            drift = e.current_pct - e.target_pct
            soft, hard = compute_bands(e.target_pct)
            st = classify_drift(drift, soft, hard)
            if st == "ok":
                continue
            if drift > 0 and abs(drift) > worst_abs:
                over_entry = e
                worst_abs = abs(drift)
                worst_status = st
            elif drift < 0:
                under_entry = e
        # If we only found one side, look for the complement
        if over_entry and not under_entry:
            for e in entries:
                if e is not over_entry:
                    under_entry = e
                    break
        if under_entry and not over_entry:
            for e in entries:
                if e is not under_entry and (e.current_pct - e.target_pct) > 0:
                    over_entry = e
                    worst_abs = abs(e.current_pct - e.target_pct)
                    soft, hard = compute_bands(e.target_pct)
                    worst_status = classify_drift(e.current_pct - e.target_pct, soft, hard)
                    break
        return over_entry, under_entry, worst_abs, worst_status

    # --- 1. Asset Type: Equity vs Safe ---
    over_e, under_e, drift_abs, status = _check(breakdown.asset_type)
    if over_e and under_e and status != "ok":
        if over_e.label == "Equities":
            sell_candidates = [s.ticker for s in equity_sleeves]
            buy_candidates = [s.ticker for s in safe_sleeves]
        else:
            sell_candidates = [s.ticker for s in safe_sleeves]
            buy_candidates = [s.ticker for s in equity_sleeves]
        dollar_amt = drift_abs / 100 * total_value
        drifts.append(_CategoryDrift(
            dimension="Asset Type", label_over=over_e.label, label_under=under_e.label,
            drift_pp=drift_abs, status=status,
            sell_tickers=sell_candidates, buy_tickers=buy_candidates,
            dollar_amount=round(dollar_amt, 2),
        ))

    # --- 2. Region: US vs International (within equities) ---
    over_e, under_e, drift_abs, status = _check(breakdown.region)
    if over_e and under_e and status != "ok":
        # Rank equity funds by their international-ness
        us_heavy = sorted(equity_sleeves, key=lambda s: s.region_us_pct, reverse=True)
        intl_heavy = sorted(equity_sleeves, key=lambda s: s.region_developed_pct + s.region_emerging_pct, reverse=True)
        if over_e.label == "International":
            sell_candidates = [s.ticker for s in intl_heavy if (s.region_developed_pct + s.region_emerging_pct) > 50]
            buy_candidates = [s.ticker for s in us_heavy if s.region_us_pct > 50]
        else:
            sell_candidates = [s.ticker for s in us_heavy if s.region_us_pct > 50]
            buy_candidates = [s.ticker for s in intl_heavy if (s.region_developed_pct + s.region_emerging_pct) > 50]
        if not sell_candidates:
            sell_candidates = [s.ticker for s in (intl_heavy if over_e.label == "International" else us_heavy)]
        if not buy_candidates:
            buy_candidates = [s.ticker for s in (us_heavy if over_e.label == "International" else intl_heavy)]
        # Skip if sell and buy are the same set (no distinct fund exists for this dimension)
        buy_only = [t for t in buy_candidates if t not in sell_candidates]
        if buy_only:
            buy_candidates = buy_only
            dollar_amt = drift_abs / 100 * equity_total
            drifts.append(_CategoryDrift(
                dimension="Region", label_over=over_e.label, label_under=under_e.label,
                drift_pp=drift_abs, status=status,
                sell_tickers=sell_candidates, buy_tickers=buy_candidates,
                dollar_amount=round(dollar_amt, 2),
            ))

    # --- 3. Value Factor: Tilted vs Blend (within equities) ---
    over_e, under_e, drift_abs, status = _check(breakdown.factor_value)
    if over_e and under_e and status != "ok":
        tilted = [s for s in equity_sleeves if (s.factor_value or "").lower() == "tilted"]
        blend = [s for s in equity_sleeves if (s.factor_value or "").lower() != "tilted"]
        if over_e.label == "Tilted":
            sell_candidates = [s.ticker for s in tilted]
            buy_candidates = [s.ticker for s in blend]
        else:
            sell_candidates = [s.ticker for s in blend]
            buy_candidates = [s.ticker for s in tilted]
        dollar_amt = drift_abs / 100 * equity_total
        drifts.append(_CategoryDrift(
            dimension="Value Factor", label_over=over_e.label, label_under=under_e.label,
            drift_pp=drift_abs, status=status,
            sell_tickers=sell_candidates, buy_tickers=buy_candidates,
            dollar_amount=round(dollar_amt, 2),
        ))

    # --- 4. Size Factor: Small Cap vs Other (within value-tilted) ---
    over_e, under_e, drift_abs, status = _check(breakdown.factor_size)
    if over_e and under_e and status != "ok":
        tilted = [s for s in equity_sleeves if (s.factor_value or "").lower() == "tilted"]
        tilted_total = sum(value_by_ticker.get(s.ticker, 0.0) for s in tilted)
        small = [s for s in tilted if (s.factor_size or "").lower() == "small"]
        other = [s for s in tilted if (s.factor_size or "").lower() != "small"]
        if over_e.label == "Small Cap":
            sell_candidates = [s.ticker for s in small]
            buy_candidates = [s.ticker for s in other]
        else:
            sell_candidates = [s.ticker for s in other]
            buy_candidates = [s.ticker for s in small]
        dollar_amt = drift_abs / 100 * tilted_total if tilted_total else 0
        drifts.append(_CategoryDrift(
            dimension="Size Factor", label_over=over_e.label, label_under=under_e.label,
            drift_pp=drift_abs, status=status,
            sell_tickers=sell_candidates, buy_tickers=buy_candidates,
            dollar_amount=round(dollar_amt, 2),
        ))

    # Sort by severity: action_needed first, then by drift magnitude
    drifts.sort(key=lambda d: (0 if d.status == "action_needed" else 1, -d.drift_pp))
    return drifts


def suggest_category_rebalance(
    breakdown: PortfolioBreakdown,
    sleeves: list[PortfolioSleeve],
    holdings: list[Holding],
    policy: InvestmentPolicy,
    pending_cash: float = 0.0,
    avoid_taxable_sales: bool = True,
) -> RebalanceSuggestion:
    """Generate minimum-trade rebalance suggestions for category-mode portfolios.

    Works top-down through category dimensions (asset type → region → value → size),
    picking one trade per drifted dimension. Skips dimensions that become resolved
    after earlier trades. Optimizes for fewest trades by preferring funds that
    address multiple drift dimensions simultaneously.
    """
    value_by_ticker: dict[str, float] = {}
    for h in holdings:
        value_by_ticker[h.ticker] = value_by_ticker.get(h.ticker, 0.0) + h.market_value
    total_value = sum(value_by_ticker.values())

    if total_value == 0:
        return RebalanceSuggestion(headline="No holdings to rebalance")

    drifts = _category_drifts(breakdown, sleeves, value_by_ticker, total_value)

    if not drifts:
        return RebalanceSuggestion(
            headline="No action needed",
            rationale="All category allocations are within tolerance bands.",
            urgency="none",
        )

    has_hard = any(d.status == "action_needed" for d in drifts)
    urgency = "high" if has_hard else "low"

    action_items: list[ActionItem] = []
    # Track virtual balance changes to avoid redundant trades
    virtual_values = dict(value_by_ticker)
    sleeve_map = {s.ticker: s for s in sleeves}
    used_trades: set[tuple[str, str]] = set()  # (sell_ticker, buy_ticker)

    # Strategy 1: Use pending cash for underweight categories
    if pending_cash > 0:
        remaining_cash = pending_cash
        for drift in drifts:
            if remaining_cash <= 0:
                break
            # Buy the largest underweight fund in the buy group
            # Prefer buy candidates that aren't also sell candidates
            buy_candidates = [t for t in drift.buy_tickers if t not in drift.sell_tickers] or drift.buy_tickers
            buy_ticker = _pick_best_fund(buy_candidates, virtual_values, prefer="smallest")
            if not buy_ticker:
                continue
            deploy = min(drift.dollar_amount, remaining_cash)
            if deploy > 0:
                action_items.append(ActionItem(
                    action="buy",
                    ticker=buy_ticker,
                    amount=round(deploy, 2),
                    rationale=f"{drift.label_under} is underweight by {drift.drift_pp:.1f}pp. "
                              f"Direct contribution to {buy_ticker}.",
                ))
                virtual_values[buy_ticker] = virtual_values.get(buy_ticker, 0) + deploy
                remaining_cash -= deploy

        if action_items:
            return RebalanceSuggestion(
                headline=f"Direct ${pending_cash:,.0f} contribution to underweight categories",
                action_items=action_items,
                rationale="New contributions can restore category balance without selling.",
                urgency=urgency,
            )

    # Strategy 2: Generate exchange trades, one per drifted category
    for drift in drifts:
        if drift.dollar_amount <= 0:
            continue

        # Re-check if this category is still drifted after previous trades
        new_breakdown = compute_breakdown(
            _virtual_holdings(virtual_values), sleeves, policy,
        )
        new_drifts = _category_drifts(new_breakdown, sleeves, virtual_values, sum(virtual_values.values()))
        still_drifted = any(d.dimension == drift.dimension for d in new_drifts)
        if not still_drifted:
            continue

        # Pick best sell fund (largest holding in overweight group)
        sell_ticker = _pick_best_fund(drift.sell_tickers, virtual_values, prefer="largest")
        buy_ticker = _pick_best_fund(drift.buy_tickers, virtual_values, prefer="smallest")

        if not sell_ticker or not buy_ticker or sell_ticker == buy_ticker:
            continue
        if (sell_ticker, buy_ticker) in used_trades:
            continue

        sell_sleeve = sleeve_map.get(sell_ticker)
        # Check taxable sale constraint
        if (avoid_taxable_sales and sell_sleeve
                and not sell_sleeve.is_cash_like and not sell_sleeve.is_safe_asset):
            action_items.append(ActionItem(
                action="exchange",
                ticker=buy_ticker,
                amount=0,
                source_ticker=sell_ticker,
                rationale=f"{drift.label_over} ({drift.dimension}) is {drift.drift_pp:.1f}pp overweight. "
                          f"Selling {sell_ticker} would be a taxable event — consider using new contributions instead.",
            ))
            continue

        available = virtual_values.get(sell_ticker, 0)
        # Refresh the drift amount from current virtual state
        for nd in new_drifts:
            if nd.dimension == drift.dimension:
                drift_amount = nd.dollar_amount
                break
        else:
            drift_amount = drift.dollar_amount

        amount = round(min(available, drift_amount), 2)
        if amount <= 0:
            continue

        action_items.append(ActionItem(
            action="exchange",
            ticker=buy_ticker,
            amount=amount,
            source_ticker=sell_ticker,
            rationale=f"{drift.label_over} ({drift.dimension}) is {drift.drift_pp:.1f}pp overweight. "
                      f"Exchange from {sell_ticker} to {buy_ticker}.",
        ))
        virtual_values[sell_ticker] = virtual_values.get(sell_ticker, 0) - amount
        virtual_values[buy_ticker] = virtual_values.get(buy_ticker, 0) + amount
        used_trades.add((sell_ticker, buy_ticker))

    # Filter out zero-amount taxable-warning items if we have real trades
    real_trades = [a for a in action_items if a.amount > 0]
    warnings = [a for a in action_items if a.amount == 0]

    if real_trades:
        # Consolidate: merge trades with same sell/buy pair
        consolidated: dict[tuple[str, str], ActionItem] = {}
        for item in real_trades:
            key = (item.source_ticker or "", item.ticker)
            if key in consolidated:
                consolidated[key].amount = round(consolidated[key].amount + item.amount, 2)
            else:
                consolidated[key] = ActionItem(
                    action=item.action,
                    ticker=item.ticker,
                    amount=item.amount,
                    source_ticker=item.source_ticker,
                    rationale=item.rationale,
                )
        final_items = list(consolidated.values())
        trade_descs = []
        for item in final_items:
            if item.source_ticker:
                trade_descs.append(f"${item.amount:,.0f} {item.source_ticker} → {item.ticker}")
            else:
                trade_descs.append(f"Buy ${item.amount:,.0f} {item.ticker}")
        headline = f"{len(final_items)} trade{'s' if len(final_items) != 1 else ''} to restore target: " + ", ".join(trade_descs)
        if len(headline) > 120:
            headline = f"{len(final_items)} trade{'s' if len(final_items) != 1 else ''} suggested to restore category targets"
        return RebalanceSuggestion(
            headline=headline,
            action_items=final_items,
            rationale=f"Category drift detected in {len(drifts)} dimension{'s' if len(drifts) != 1 else ''}. "
                      f"These trades use the minimum number of exchanges to restore targets.",
            urgency=urgency,
        )

    if warnings:
        return RebalanceSuggestion(
            headline="Rebalance suggested but requires taxable sales",
            action_items=[],
            rationale=warnings[0].rationale,
            urgency="low",
        )

    return RebalanceSuggestion(
        headline="Category drift detected",
        rationale="Some categories are outside bands but no clear trade is available. "
                  "Consider directing new contributions to underweight categories.",
        urgency="low",
    )


def _pick_best_fund(
    tickers: list[str],
    values: dict[str, float],
    prefer: str = "largest",
) -> Optional[str]:
    """Pick the best fund from candidates. 'largest' picks the biggest holding,
    'smallest' picks the smallest (to concentrate new money)."""
    if not tickers:
        return None
    candidates = [(t, values.get(t, 0.0)) for t in tickers]
    if prefer == "largest":
        candidates.sort(key=lambda x: x[1], reverse=True)
    else:
        candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


class _VirtualHolding:
    """Lightweight holding stand-in that avoids SQLAlchemy instrumentation."""
    __slots__ = ("ticker", "market_value", "quantity", "price", "as_of_date", "id", "account_id")

    def __init__(self, ticker: str, market_value: float):
        self.ticker = ticker
        self.market_value = market_value
        self.quantity = 0
        self.price = 0
        self.as_of_date = None
        self.id = 0
        self.account_id = 0


def _virtual_holdings(values: dict[str, float]) -> list:
    """Create lightweight Holding-like objects from a virtual value dict."""
    return [_VirtualHolding(t, v) for t, v in values.items() if v > 0]

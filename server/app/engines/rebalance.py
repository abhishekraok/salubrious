"""Rebalance suggestion engine (MVP simplified)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .allocation import AllocationResult


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

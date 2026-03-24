"""Top-level recommendation engine for the Today page."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import InvestmentPolicy
from .allocation import AllocationResult
from .rebalance import RebalanceSuggestion
from .spending import SpendingRunway


@dataclass
class SummaryCard:
    label: str
    value: str
    status: str  # 'calm', 'watch', 'action'


@dataclass
class TodayRecommendation:
    headline: str
    explanation: str
    status: str  # 'calm', 'watch', 'action'
    summary_cards: list[SummaryCard] = field(default_factory=list)
    active_issues: list[str] = field(default_factory=list)


def compute_today(
    allocation: AllocationResult,
    runway: SpendingRunway,
    policy: InvestmentPolicy,
    rebalance: RebalanceSuggestion,
) -> TodayRecommendation:
    """Determine the single top recommendation for the Today page.

    Priority ordering:
    1. Spending runway below target
    2. Rebalance required (hard band breach)
    3. Annual review due / overdue
    4. Rebalance with contributions only (soft band breach)
    5. No action needed (default calm state)
    """
    issues: list[str] = []
    headline = "No action needed"
    explanation = "All allocation sleeves are within tolerance bands. Everything is within policy."
    status = "calm"

    # Check spending runway
    runway_below = runway.baseline_runway_years < policy.safe_asset_runway_years_target
    if runway_below:
        issues.append(
            f"Spending runway is {runway.baseline_runway_years:.1f} years, "
            f"below target of {policy.safe_asset_runway_years_target:.0f} years."
        )

    # Check hard band breaches
    if allocation.sleeves_outside_hard > 0:
        breached = [s for s in allocation.sleeves if s.status == "action_needed"]
        names = ", ".join(s.ticker for s in breached)
        issues.append(f"Hard band breached for: {names}.")

    # Check review overdue
    review_overdue = False
    if policy.next_review_date and policy.next_review_date <= date.today():
        review_overdue = True
        issues.append("Scheduled review is overdue.")

    # Check soft band breaches
    if allocation.sleeves_outside_soft > 0 and allocation.sleeves_outside_hard == 0:
        drifted = [s for s in allocation.sleeves if s.status == "watch"]
        names = ", ".join(s.ticker for s in drifted)
        issues.append(f"Soft band drift for: {names}.")

    # Determine headline by priority
    if runway_below:
        headline = "Spending runway below target"
        explanation = (
            f"Safe assets cover {runway.baseline_runway_years:.1f} years of baseline spending, "
            f"below your target of {policy.safe_asset_runway_years_target:.0f} years."
        )
        status = "action"
    elif allocation.sleeves_outside_hard > 0:
        headline = "Rebalance required"
        explanation = rebalance.rationale or "One or more sleeves are outside hard tolerance bands."
        status = "action"
    elif review_overdue:
        headline = "Annual review due"
        explanation = f"Your scheduled review date ({policy.next_review_date}) has passed."
        status = "watch"
    elif allocation.sleeves_outside_soft > 0:
        headline = "Mild drift detected"
        explanation = rebalance.rationale or "Some sleeves are outside soft bands. Consider directing new contributions."
        status = "watch"

    # Build summary cards
    # Portfolio status
    if allocation.sleeves_outside_hard > 0:
        portfolio_status = ("Action needed", "action")
    elif allocation.sleeves_outside_soft > 0:
        portfolio_status = ("Watch", "watch")
    else:
        portfolio_status = ("On plan", "calm")

    # Spending runway
    if runway_below:
        runway_status = "action"
    elif runway.funded_status == "watch":
        runway_status = "watch"
    else:
        runway_status = "calm"

    # Review
    if review_overdue:
        review_card_status = "action"
    else:
        review_card_status = "calm"

    next_review_str = str(policy.next_review_date) if policy.next_review_date else "Not set"

    cards = [
        SummaryCard("Portfolio Status", portfolio_status[0], portfolio_status[1]),
        SummaryCard("Spending Runway", f"{runway.baseline_runway_years:.1f} years", runway_status),
        SummaryCard("Safe Assets", f"${runway.safe_asset_total:,.0f}", runway_status),
        SummaryCard("Next Review", next_review_str, review_card_status),
    ]

    return TodayRecommendation(
        headline=headline,
        explanation=explanation,
        status=status,
        summary_cards=cards,
        active_issues=issues,
    )

"""Top-level recommendation engine for the Today page."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..models import InvestmentPolicy
from .allocation import AllocationResult
from .bands import classify_drift, compute_bands
from .breakdown import PortfolioBreakdown
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


def _check_category_drift(
    breakdown: PortfolioBreakdown,
) -> tuple[int, int, list[str], str]:
    """Check category-level drift for category-mode portfolios.

    Returns (outside_soft, outside_hard, issue_strings, rationale).
    Reports at most one issue per category group (the most-drifted entry).
    """
    outside_soft = 0
    outside_hard = 0
    issues: list[str] = []
    rationale_parts: list[str] = []

    category_groups = [
        ("Asset Type", breakdown.asset_type),
        ("Region", breakdown.region),
        ("Value Factor", breakdown.factor_value),
        ("Size Factor", breakdown.factor_size),
    ]

    for group_name, entries in category_groups:
        if not entries or all(e.target_pct == 0 for e in entries):
            continue

        worst_status = "ok"
        worst_entry = None
        worst_drift = 0.0

        for entry in entries:
            if entry.target_pct == 0:
                continue
            drift = entry.current_pct - entry.target_pct
            soft, hard = compute_bands(entry.target_pct)
            status = classify_drift(drift, soft, hard)
            if status == "action_needed" or (
                status == "watch" and worst_status not in ("action_needed",)
            ):
                if abs(drift) > abs(worst_drift):
                    worst_status = status
                    worst_entry = entry
                    worst_drift = drift

        if worst_entry is not None and worst_status != "ok":
            direction = "above" if worst_drift > 0 else "below"
            issues.append(
                f"{worst_entry.label} ({group_name}) is {abs(worst_drift):.1f}pp {direction} target "
                f"({worst_entry.current_pct:.1f}% actual vs {worst_entry.target_pct:.1f}% target)."
            )
            rationale_parts.append(
                f"{worst_entry.label} is {abs(worst_drift):.1f}pp {direction} target"
            )
            outside_soft += 1
            if worst_status == "action_needed":
                outside_hard += 1

    rationale = "; ".join(rationale_parts) + "." if rationale_parts else ""
    return outside_soft, outside_hard, issues, rationale


def compute_today(
    allocation: AllocationResult,
    runway: SpendingRunway,
    policy: InvestmentPolicy,
    rebalance: RebalanceSuggestion,
    breakdown: Optional[PortfolioBreakdown] = None,
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

    # Determine whether to use category-level or sleeve-level drift analysis
    use_category = (
        getattr(policy, "targeting_mode", "fund") == "category"
        and breakdown is not None
    )

    if use_category:
        eff_outside_soft, eff_outside_hard, drift_issues, drift_rationale = (
            _check_category_drift(breakdown)  # type: ignore[arg-type]
        )
    else:
        eff_outside_soft = allocation.sleeves_outside_soft
        eff_outside_hard = allocation.sleeves_outside_hard
        drift_rationale = rebalance.rationale
        drift_issues = []

    # Check spending runway
    runway_below = runway.baseline_runway_years < policy.safe_asset_runway_years_target
    if runway_below:
        issues.append(
            f"Spending runway is {runway.baseline_runway_years:.1f} years, "
            f"below target of {policy.safe_asset_runway_years_target:.0f} years."
        )

    # Check band breaches
    if use_category:
        issues.extend(drift_issues)
    else:
        if eff_outside_hard > 0:
            breached = [s for s in allocation.sleeves if s.status == "action_needed"]
            names = ", ".join(s.ticker for s in breached)
            issues.append(f"Hard band breached for: {names}.")
        elif eff_outside_soft > 0:
            drifted = [s for s in allocation.sleeves if s.status == "watch"]
            names = ", ".join(s.ticker for s in drifted)
            issues.append(f"Soft band drift for: {names}.")

    # Check review overdue
    review_overdue = False
    if policy.next_review_date and policy.next_review_date <= date.today():
        review_overdue = True
        issues.append("Scheduled review is overdue.")

    # Determine headline by priority
    if runway_below:
        headline = "Spending runway below target"
        explanation = (
            f"Safe assets cover {runway.baseline_runway_years:.1f} years of baseline spending, "
            f"below your target of {policy.safe_asset_runway_years_target:.0f} years."
        )
        status = "action"
    elif eff_outside_hard > 0:
        headline = "Rebalance required"
        explanation = drift_rationale or "One or more categories are outside hard tolerance bands."
        status = "action"
    elif review_overdue:
        headline = "Annual review due"
        explanation = f"Your scheduled review date ({policy.next_review_date}) has passed."
        status = "watch"
    elif eff_outside_soft > 0:
        headline = "Mild drift detected"
        explanation = drift_rationale or "Some categories are outside soft bands. Consider directing new contributions."
        status = "watch"

    # Build summary cards
    # Portfolio status
    if eff_outside_hard > 0:
        portfolio_status = ("Action needed", "action")
    elif eff_outside_soft > 0:
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

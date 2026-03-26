"""Tests for the recommendation engine (Today page)."""
from datetime import date, timedelta

import pytest
from app.engines.allocation import AllocationResult, SleeveAllocation
from app.engines.bands import classify_drift
from app.engines.recommendation import compute_today
from app.engines.rebalance import RebalanceSuggestion
from app.engines.spending import SpendingRunway
from tests.conftest import make_policy


def _make_ok_allocation() -> AllocationResult:
    sleeve = SleeveAllocation(
        ticker="VTI",
        label="US Stocks",
        current_value=100_000.0,
        current_percent=100.0,
        target_percent=100.0,
        drift_pp=0.0,
        soft_band=7.5,
        hard_band=15.0,
        status="ok",
    )
    return AllocationResult(
        total_value=100_000.0,
        sleeves=[sleeve],
        sleeves_outside_soft=0,
        sleeves_outside_hard=0,
    )


def _make_allocation_with_hard_breach() -> AllocationResult:
    sleeve = SleeveAllocation(
        ticker="VTI",
        label="US Stocks",
        current_value=100_000.0,
        current_percent=60.0,
        target_percent=40.0,
        drift_pp=20.0,
        soft_band=2.0,
        hard_band=5.0,
        status="action_needed",
    )
    return AllocationResult(
        total_value=100_000.0,
        sleeves=[sleeve],
        sleeves_outside_soft=1,
        sleeves_outside_hard=1,
    )


def _make_allocation_with_soft_breach() -> AllocationResult:
    sleeve = SleeveAllocation(
        ticker="VTI",
        label="US Stocks",
        current_value=100_000.0,
        current_percent=63.0,
        target_percent=60.0,
        drift_pp=3.0,
        soft_band=2.0,
        hard_band=5.0,
        status="watch",
    )
    return AllocationResult(
        total_value=100_000.0,
        sleeves=[sleeve],
        sleeves_outside_soft=1,
        sleeves_outside_hard=0,
    )


def _make_secure_runway(years: float = 5.0) -> SpendingRunway:
    return SpendingRunway(
        safe_asset_total=250_000.0,
        cash_like_total=50_000.0,
        baseline_runway_years=years,
        comfortable_runway_years=years * 0.8,
        emergency_runway_years=years * 1.25,
        cash_runway_years=1.0,
        funded_status="secure",
        above_minimum_reserve_by=40_000.0,
    )


def _make_constrained_runway(years: float = 2.0) -> SpendingRunway:
    return SpendingRunway(
        safe_asset_total=100_000.0,
        cash_like_total=10_000.0,
        baseline_runway_years=years,
        comfortable_runway_years=years * 0.8,
        emergency_runway_years=years * 1.25,
        cash_runway_years=0.2,
        funded_status="constrained",
        above_minimum_reserve_by=0.0,
    )


def _make_calm_rebalance() -> RebalanceSuggestion:
    return RebalanceSuggestion(
        headline="No action needed",
        rationale="All within bands.",
        urgency="none",
    )


def _make_action_rebalance() -> RebalanceSuggestion:
    return RebalanceSuggestion(
        headline="Rebalance required",
        rationale="VTI is 20pp overweight.",
        urgency="high",
    )


class TestComputeTodayCalm:
    def test_all_calm_returns_calm_status(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() + timedelta(days=30),
        )
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        assert result.status == "calm"
        assert result.headline == "No action needed"
        assert result.active_issues == []

    def test_calm_summary_cards_present(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() + timedelta(days=30),
        )
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        labels = [c.label for c in result.summary_cards]
        assert "Portfolio Status" in labels
        assert "Spending Runway" in labels
        assert "Next Review" in labels


class TestComputeTodaySpendingPriority:
    def test_low_runway_triggers_action(self):
        # Runway below target (2 years < 4 year target)
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() + timedelta(days=30),
        )
        result = compute_today(
            _make_ok_allocation(),
            _make_constrained_runway(years=2.0),
            policy,
            _make_calm_rebalance(),
        )
        assert result.status == "action"
        assert "runway" in result.headline.lower()

    def test_spending_issue_in_active_issues(self):
        policy = make_policy(safe_asset_runway_years_target=4.0)
        result = compute_today(
            _make_ok_allocation(),
            _make_constrained_runway(years=2.0),
            policy,
            _make_calm_rebalance(),
        )
        assert any("runway" in issue.lower() for issue in result.active_issues)

    def test_spending_takes_priority_over_hard_breach(self):
        # Both spending and hard breach; spending should win
        policy = make_policy(safe_asset_runway_years_target=4.0)
        result = compute_today(
            _make_allocation_with_hard_breach(),
            _make_constrained_runway(years=2.0),
            policy,
            _make_action_rebalance(),
        )
        assert "runway" in result.headline.lower()


class TestComputeTodayHardBreach:
    def test_hard_breach_triggers_action(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() + timedelta(days=30),
        )
        result = compute_today(
            _make_allocation_with_hard_breach(),
            _make_secure_runway(),
            policy,
            _make_action_rebalance(),
        )
        assert result.status == "action"
        assert "rebalance" in result.headline.lower()

    def test_hard_breach_in_active_issues(self):
        policy = make_policy(safe_asset_runway_years_target=4.0)
        result = compute_today(
            _make_allocation_with_hard_breach(),
            _make_secure_runway(),
            policy,
            _make_action_rebalance(),
        )
        assert any("hard band" in issue.lower() for issue in result.active_issues)

    def test_hard_breach_explanation_uses_rebalance_rationale(self):
        policy = make_policy(safe_asset_runway_years_target=4.0)
        rebalance = _make_action_rebalance()
        result = compute_today(
            _make_allocation_with_hard_breach(),
            _make_secure_runway(),
            policy,
            rebalance,
        )
        assert result.explanation == rebalance.rationale


class TestComputeTodayReviewOverdue:
    def test_overdue_review_triggers_watch(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() - timedelta(days=1),
        )
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        assert result.status == "watch"
        assert "review" in result.headline.lower()

    def test_overdue_review_in_active_issues(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() - timedelta(days=1),
        )
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        assert any("review" in issue.lower() for issue in result.active_issues)

    def test_future_review_date_not_overdue(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() + timedelta(days=1),
        )
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        assert result.status == "calm"

    def test_none_review_date_not_overdue(self):
        policy = make_policy(safe_asset_runway_years_target=4.0, next_review_date=None)
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        assert result.status == "calm"


class TestComputeTodaySoftBreach:
    def test_soft_breach_only_triggers_watch(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() + timedelta(days=30),
        )
        result = compute_today(
            _make_allocation_with_soft_breach(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        assert result.status == "watch"
        assert "drift" in result.headline.lower()

    def test_soft_breach_in_active_issues(self):
        policy = make_policy(safe_asset_runway_years_target=4.0)
        result = compute_today(
            _make_allocation_with_soft_breach(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        assert any("soft band" in issue.lower() for issue in result.active_issues)

    def test_hard_breach_takes_priority_over_soft(self):
        # When hard breach exists, soft-only check should not fire
        policy = make_policy(safe_asset_runway_years_target=4.0)
        result = compute_today(
            _make_allocation_with_hard_breach(),
            _make_secure_runway(),
            policy,
            _make_action_rebalance(),
        )
        # Headline should be rebalance, not drift
        assert "rebalance" in result.headline.lower()
        assert "drift" not in result.headline.lower()


class TestComputeTodaySummaryCards:
    def test_portfolio_card_on_plan_when_calm(self):
        policy = make_policy(safe_asset_runway_years_target=4.0)
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        portfolio_card = next(c for c in result.summary_cards if c.label == "Portfolio Status")
        assert portfolio_card.status == "calm"
        assert portfolio_card.value == "On plan"

    def test_portfolio_card_action_when_hard_breach(self):
        policy = make_policy(safe_asset_runway_years_target=4.0)
        result = compute_today(
            _make_allocation_with_hard_breach(),
            _make_secure_runway(),
            policy,
            _make_action_rebalance(),
        )
        portfolio_card = next(c for c in result.summary_cards if c.label == "Portfolio Status")
        assert portfolio_card.status == "action"

    def test_spending_card_shows_runway_years(self):
        policy = make_policy(safe_asset_runway_years_target=4.0)
        runway = _make_secure_runway(years=5.0)
        result = compute_today(
            _make_ok_allocation(),
            runway,
            policy,
            _make_calm_rebalance(),
        )
        spending_card = next(c for c in result.summary_cards if c.label == "Spending Runway")
        assert "5.0" in spending_card.value

    def test_review_card_action_when_overdue(self):
        policy = make_policy(
            safe_asset_runway_years_target=4.0,
            next_review_date=date.today() - timedelta(days=10),
        )
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        review_card = next(c for c in result.summary_cards if c.label == "Next Review")
        assert review_card.status == "action"

    def test_review_card_not_set_shows_not_set(self):
        policy = make_policy(safe_asset_runway_years_target=4.0, next_review_date=None)
        result = compute_today(
            _make_ok_allocation(),
            _make_secure_runway(),
            policy,
            _make_calm_rebalance(),
        )
        review_card = next(c for c in result.summary_cards if c.label == "Next Review")
        assert review_card.value == "Not set"

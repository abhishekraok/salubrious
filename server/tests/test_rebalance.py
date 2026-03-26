"""Tests for the rebalance suggestion engine."""
import pytest
from app.engines.allocation import AllocationResult, SleeveAllocation
from app.engines.rebalance import suggest_rebalance


def _make_sleeve_alloc(
    ticker: str,
    current_percent: float,
    target_percent: float,
    soft_band: float,
    hard_band: float,
    is_safe_asset: bool = False,
    is_cash_like: bool = False,
) -> SleeveAllocation:
    drift_pp = round(current_percent - target_percent, 2)
    from app.engines.bands import classify_drift
    status = classify_drift(drift_pp, soft_band, hard_band)
    return SleeveAllocation(
        ticker=ticker,
        label=ticker,
        current_value=current_percent * 1_000.0,  # $100k portfolio scaled
        current_percent=current_percent,
        target_percent=target_percent,
        drift_pp=drift_pp,
        soft_band=soft_band,
        hard_band=hard_band,
        status=status,
        is_safe_asset=is_safe_asset,
        is_cash_like=is_cash_like,
    )


def _make_result(sleeves: list[SleeveAllocation], total: float = 100_000.0) -> AllocationResult:
    outside_soft = sum(1 for s in sleeves if s.status in ("watch", "action_needed"))
    outside_hard = sum(1 for s in sleeves if s.status == "action_needed")
    return AllocationResult(
        total_value=total,
        sleeves=sleeves,
        sleeves_outside_soft=outside_soft,
        sleeves_outside_hard=outside_hard,
    )


class TestSuggestRebalanceNoAction:
    def test_no_sleeves_returns_no_holdings_message(self):
        result = _make_result([])
        suggestion = suggest_rebalance(result)
        assert suggestion.headline == "No holdings to rebalance"

    def test_all_within_bands_returns_no_action(self):
        sleeves = [
            _make_sleeve_alloc("VTI", 60.0, 60.0, 7.5, 15.0),
            _make_sleeve_alloc("BND", 40.0, 40.0, 2.0, 4.0),
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result)
        assert suggestion.headline == "No action needed"
        assert suggestion.urgency == "none"
        assert suggestion.action_items == []


class TestSuggestRebalancePendingCash:
    def test_pending_cash_directed_to_underweight(self):
        # BND is 5pp underweight
        sleeves = [
            _make_sleeve_alloc("VTI", 65.0, 60.0, 7.5, 15.0),  # ok (drift=5 < soft=7.5)
            _make_sleeve_alloc("BND", 35.0, 40.0, 2.0, 4.0),   # action (drift=-5 > hard=4)
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, pending_cash=5_000.0)
        assert len(suggestion.action_items) == 1
        item = suggestion.action_items[0]
        assert item.action == "buy"
        assert item.ticker == "BND"
        assert item.amount == pytest.approx(5_000.0)

    def test_pending_cash_split_across_multiple_underweights(self):
        sleeves = [
            _make_sleeve_alloc("VTI", 70.0, 60.0, 7.5, 15.0),   # ok
            _make_sleeve_alloc("BND", 15.0, 20.0, 2.0, 5.0),    # action (drift=-5)
            _make_sleeve_alloc("VXUS", 15.0, 20.0, 2.0, 5.0),   # action (drift=-5)
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, pending_cash=8_000.0)
        assert len(suggestion.action_items) >= 1
        total_deployed = sum(i.amount for i in suggestion.action_items)
        assert total_deployed <= 8_000.0

    def test_pending_cash_urgency_high_when_hard_breach(self):
        sleeves = [
            _make_sleeve_alloc("VTI", 60.0, 40.0, 2.0, 5.0),  # action_needed (drift=20)
            _make_sleeve_alloc("BND", 40.0, 60.0, 7.5, 15.0), # action_needed (drift=-20)
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, pending_cash=10_000.0)
        assert suggestion.urgency == "high"


class TestSuggestRebalanceCashLikeExchange:
    def test_cash_like_overweight_exchanges_to_underweight(self):
        sleeves = [
            _make_sleeve_alloc("SGOV", 25.0, 15.0, 2.0, 3.75, is_cash_like=True),  # overweight
            _make_sleeve_alloc("VTI", 75.0, 85.0, 7.5, 15.0),  # underweight
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, pending_cash=0.0)
        assert len(suggestion.action_items) == 1
        item = suggestion.action_items[0]
        assert item.action == "exchange"
        assert item.source_ticker == "SGOV"
        assert item.ticker == "VTI"
        assert item.amount > 0

    def test_cash_like_exchange_amount_capped_by_underweight_need(self):
        # SGOV has 10pp excess = $10k; VTI needs only 5pp = $5k
        sleeves = [
            _make_sleeve_alloc("SGOV", 30.0, 20.0, 2.0, 5.0, is_cash_like=True),
            _make_sleeve_alloc("VTI", 70.0, 80.0, 7.5, 15.0),
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result)
        item = suggestion.action_items[0]
        # Amount should be min(available=10k, needed=10k)
        assert item.amount == pytest.approx(min(10_000.0, 10_000.0))


class TestSuggestRebalanceStrategy3:
    def test_avoid_taxable_sale_returns_soft_message(self):
        # Overweight equity (not cash-like, not safe asset) with avoid_taxable_sales=True
        sleeves = [
            _make_sleeve_alloc("VTI", 70.0, 60.0, 7.5, 15.0),  # overweight: ok (drift=10 > soft=7.5) -> watch
            _make_sleeve_alloc("BND", 30.0, 40.0, 2.0, 4.0),   # underweight: action_needed
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, avoid_taxable_sales=True)
        assert "taxable" in suggestion.headline.lower() or "taxable" in suggestion.rationale.lower()

    def test_allow_taxable_sale_returns_exchange(self):
        sleeves = [
            _make_sleeve_alloc("VTI", 70.0, 60.0, 7.5, 15.0),
            _make_sleeve_alloc("BND", 30.0, 40.0, 2.0, 4.0),
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, avoid_taxable_sales=False)
        assert suggestion.action_items
        assert suggestion.action_items[0].action == "exchange"

    def test_safe_asset_overweight_can_sell_even_with_avoid_taxable(self):
        # Safe assets are not equity; avoid_taxable_sales should not block selling them
        sleeves = [
            _make_sleeve_alloc("BND", 50.0, 30.0, 2.0, 7.5, is_safe_asset=True),
            _make_sleeve_alloc("VTI", 50.0, 70.0, 7.5, 15.0),
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, avoid_taxable_sales=True)
        # BND is_safe_asset so strategy 3 proceeds without taxable sale warning
        assert suggestion.action_items


class TestSuggestRebalanceUrgency:
    def test_soft_breach_only_urgency_low(self):
        sleeves = [
            _make_sleeve_alloc("VTI", 63.0, 60.0, 7.5, 15.0),  # ok
            _make_sleeve_alloc("BND", 37.0, 40.0, 2.0, 4.0),   # watch (drift=-3, soft=2)
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result)
        assert suggestion.urgency == "low"

    def test_hard_breach_urgency_high(self):
        # Need both overweight and underweight with hard breach so strategy 3 fires
        sleeves = [
            _make_sleeve_alloc("VTI", 60.0, 40.0, 2.0, 5.0),   # action_needed (drift=+20)
            _make_sleeve_alloc("BND", 40.0, 60.0, 7.5, 15.0),  # action_needed (drift=-20)
        ]
        result = _make_result(sleeves)
        suggestion = suggest_rebalance(result, avoid_taxable_sales=False)
        assert suggestion.urgency == "high"

"""Tests for the allocation engine."""
import pytest
from app.engines.allocation import AllocationResult, compute_allocation
from tests.conftest import make_holding, make_sleeve


class TestComputeAllocation:
    def test_empty_holdings_returns_zero_total(self):
        sleeves = [make_sleeve("VTI", "US Stocks", 60.0)]
        result = compute_allocation([], sleeves)
        assert result.total_value == 0
        assert result.sleeves == []
        assert result.sleeves_outside_soft == 0
        assert result.sleeves_outside_hard == 0

    def test_single_sleeve_on_target(self):
        holdings = [make_holding("VTI", 100_000.0)]
        sleeves = [make_sleeve("VTI", "US Stocks", 100.0)]
        result = compute_allocation(holdings, sleeves)
        assert result.total_value == 100_000.0
        assert len(result.sleeves) == 1
        s = result.sleeves[0]
        assert s.ticker == "VTI"
        assert s.current_percent == 100.0
        assert s.drift_pp == 0.0
        assert s.status == "ok"
        assert result.sleeves_outside_soft == 0
        assert result.sleeves_outside_hard == 0

    def test_two_sleeves_balanced(self):
        holdings = [make_holding("VTI", 60_000.0), make_holding("BND", 40_000.0)]
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0),
            make_sleeve("BND", "Bonds", 40.0),
        ]
        result = compute_allocation(holdings, sleeves)
        assert result.total_value == 100_000.0
        by_ticker = {s.ticker: s for s in result.sleeves}
        assert by_ticker["VTI"].drift_pp == pytest.approx(0.0)
        assert by_ticker["BND"].drift_pp == pytest.approx(0.0)
        assert result.sleeves_outside_soft == 0

    def test_drift_detected_watch(self):
        # VTI at 65% vs 60% target -> drift = +5pp
        # bands for 60% target: hard=max(2, 15)=15, soft=7.5
        # 5pp < 7.5 soft -> ok
        # Let's use a target where 5pp drift triggers watch
        # target=20: hard=max(2, 5)=5, soft=2.5; drift of 3 -> watch
        holdings = [make_holding("VTI", 23_000.0), make_holding("BND", 77_000.0)]
        sleeves = [
            make_sleeve("VTI", "US Stocks", 20.0),
            make_sleeve("BND", "Bonds", 80.0),
        ]
        result = compute_allocation(holdings, sleeves)
        by_ticker = {s.ticker: s for s in result.sleeves}
        vti = by_ticker["VTI"]
        assert vti.current_percent == pytest.approx(23.0)
        assert vti.drift_pp == pytest.approx(3.0)
        assert vti.status == "watch"
        assert result.sleeves_outside_soft == 1
        assert result.sleeves_outside_hard == 0

    def test_drift_detected_action_needed(self):
        # target=20: hard=5, soft=2.5; drift of 10 -> action_needed
        holdings = [make_holding("VTI", 30_000.0), make_holding("BND", 70_000.0)]
        sleeves = [
            make_sleeve("VTI", "US Stocks", 20.0),
            make_sleeve("BND", "Bonds", 80.0),
        ]
        result = compute_allocation(holdings, sleeves)
        by_ticker = {s.ticker: s for s in result.sleeves}
        vti = by_ticker["VTI"]
        assert vti.drift_pp == pytest.approx(10.0)
        assert vti.status == "action_needed"
        assert result.sleeves_outside_soft == 1
        assert result.sleeves_outside_hard == 1

    def test_holdings_aggregated_across_accounts(self):
        # Same ticker held in two accounts should be summed
        holdings = [
            make_holding("VTI", 30_000.0),
            make_holding("VTI", 30_000.0),
            make_holding("BND", 40_000.0),
        ]
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0),
            make_sleeve("BND", "Bonds", 40.0),
        ]
        result = compute_allocation(holdings, sleeves)
        by_ticker = {s.ticker: s for s in result.sleeves}
        assert by_ticker["VTI"].current_value == pytest.approx(60_000.0)
        assert by_ticker["VTI"].drift_pp == pytest.approx(0.0)

    def test_sleeve_not_held_shows_zero(self):
        holdings = [make_holding("VTI", 100_000.0)]
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0),
            make_sleeve("BND", "Bonds", 40.0),
        ]
        result = compute_allocation(holdings, sleeves)
        by_ticker = {s.ticker: s for s in result.sleeves}
        bnd = by_ticker["BND"]
        assert bnd.current_value == 0.0
        assert bnd.current_percent == 0.0
        assert bnd.drift_pp == pytest.approx(-40.0)

    def test_results_sorted_by_ticker(self):
        holdings = [make_holding("VTI", 60_000.0), make_holding("BND", 40_000.0)]
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0),
            make_sleeve("BND", "Bonds", 40.0),
        ]
        result = compute_allocation(holdings, sleeves)
        tickers = [s.ticker for s in result.sleeves]
        assert tickers == sorted(tickers)

    def test_safe_asset_and_cash_like_flags_propagated(self):
        holdings = [make_holding("SGOV", 100_000.0)]
        sleeves = [make_sleeve("SGOV", "T-Bills", 100.0, is_safe_asset=True, is_cash_like=True)]
        result = compute_allocation(holdings, sleeves)
        s = result.sleeves[0]
        assert s.is_safe_asset is True
        assert s.is_cash_like is True

    def test_multiple_breaches_counted(self):
        # Three sleeves each with action_needed drift
        holdings = [
            make_holding("A", 50_000.0),
            make_holding("B", 30_000.0),
            make_holding("C", 20_000.0),
        ]
        # Targets: A=20, B=50, C=30 -> big drifts for A and B
        sleeves = [
            make_sleeve("A", "Fund A", 20.0),
            make_sleeve("B", "Fund B", 50.0),
            make_sleeve("C", "Fund C", 30.0),
        ]
        result = compute_allocation(holdings, sleeves)
        # A: current=50%, target=20%, drift=+30% -> action_needed (hard=5)
        # B: current=30%, target=50%, drift=-20% -> action_needed (hard=12.5)
        # C: current=20%, target=30%, drift=-10% -> action_needed (hard=7.5)
        assert result.sleeves_outside_hard == 3

"""Tests for the portfolio breakdown engine."""
import pytest
from app.engines.breakdown import compute_breakdown
from tests.conftest import make_holding, make_policy, make_sleeve


def _find(entries, label):
    for e in entries:
        if e.label == label:
            return e
    return None


class TestComputeBreakdownEmpty:
    def test_empty_holdings_and_sleeves_returns_empty(self):
        result = compute_breakdown([], [], policy=None)
        assert result.asset_type == []
        assert result.region == []

    def test_zero_value_sleeves_returns_zero_percents(self):
        sleeves = [make_sleeve("VTI", "US Stocks", 60.0)]
        result = compute_breakdown([], sleeves, policy=None)
        entry = _find(result.asset_type, "Equities")
        assert entry is not None
        assert entry.current_pct == 0.0


class TestComputeBreakdownAssetType:
    def test_all_equity_fund_mode(self):
        sleeves = [make_sleeve("VTI", "US Stocks", 100.0)]
        holdings = [make_holding("VTI", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        equities = _find(result.asset_type, "Equities")
        safe = _find(result.asset_type, "Safe Assets")
        assert equities.current_pct == pytest.approx(100.0)
        assert safe.current_pct == pytest.approx(0.0)

    def test_mixed_equity_and_safe_assets(self):
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0, is_safe_asset=False),
            make_sleeve("BND", "Bonds", 40.0, is_safe_asset=True),
        ]
        holdings = [make_holding("VTI", 60_000.0), make_holding("BND", 40_000.0)]
        result = compute_breakdown(holdings, sleeves)
        equities = _find(result.asset_type, "Equities")
        safe = _find(result.asset_type, "Safe Assets")
        assert equities.current_pct == pytest.approx(60.0)
        assert safe.current_pct == pytest.approx(40.0)

    def test_target_from_sleeve_weights_fund_mode(self):
        sleeves = [
            make_sleeve("VTI", "US Stocks", 70.0, is_safe_asset=False),
            make_sleeve("BND", "Bonds", 30.0, is_safe_asset=True),
        ]
        holdings = [make_holding("VTI", 70_000.0), make_holding("BND", 30_000.0)]
        result = compute_breakdown(holdings, sleeves)
        equities = _find(result.asset_type, "Equities")
        assert equities.target_pct == pytest.approx(70.0)

    def test_target_from_category_mode(self):
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0),
            make_sleeve("BND", "Bonds", 40.0, is_safe_asset=True),
        ]
        holdings = [make_holding("VTI", 60_000.0), make_holding("BND", 40_000.0)]
        policy = make_policy(targeting_mode="category", target_equity_pct=75.0)
        result = compute_breakdown(holdings, sleeves, policy=policy)
        equities = _find(result.asset_type, "Equities")
        safe = _find(result.asset_type, "Safe Assets")
        assert equities.target_pct == pytest.approx(75.0)
        assert safe.target_pct == pytest.approx(25.0)


class TestComputeBreakdownRegion:
    def test_all_us_equity(self):
        sleeves = [
            make_sleeve("VTI", "US Stocks", 100.0, region_us_pct=100.0)
        ]
        holdings = [make_holding("VTI", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        us = _find(result.region, "US")
        intl = _find(result.region, "International")
        assert us.current_pct == pytest.approx(100.0)
        assert intl.current_pct == pytest.approx(0.0)

    def test_mixed_us_and_international(self):
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0, region_us_pct=100.0),
            make_sleeve("VXUS", "Intl Stocks", 40.0, region_us_pct=0.0,
                        region_developed_pct=80.0, region_emerging_pct=20.0),
        ]
        holdings = [make_holding("VTI", 60_000.0), make_holding("VXUS", 40_000.0)]
        result = compute_breakdown(holdings, sleeves)
        us = _find(result.region, "US")
        intl = _find(result.region, "International")
        # VTI: 60% weight, 100% US -> 60% of equity is US
        # VXUS: 40% weight, 100% international -> 40% of equity is intl
        assert us.current_pct == pytest.approx(60.0)
        assert intl.current_pct == pytest.approx(40.0)

    def test_region_target_from_category_mode(self):
        sleeves = [
            make_sleeve("VTI", "US Stocks", 60.0, region_us_pct=100.0),
            make_sleeve("VXUS", "Intl", 40.0, region_us_pct=0.0,
                        region_developed_pct=100.0, region_emerging_pct=0.0),
        ]
        holdings = [make_holding("VTI", 60_000.0), make_holding("VXUS", 40_000.0)]
        policy = make_policy(targeting_mode="category", target_international_pct=30.0)
        result = compute_breakdown(holdings, sleeves, policy=policy)
        intl = _find(result.region, "International")
        us = _find(result.region, "US")
        assert intl.target_pct == pytest.approx(30.0)
        assert us.target_pct == pytest.approx(70.0)

    def test_no_equity_sleeves_empty_region(self):
        sleeves = [make_sleeve("BND", "Bonds", 100.0, is_safe_asset=True)]
        holdings = [make_holding("BND", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        # No equity sleeves -> region has US=0/International=0
        us = _find(result.region, "US")
        intl = _find(result.region, "International")
        if us:
            assert us.current_pct == pytest.approx(0.0)
        if intl:
            assert intl.current_pct == pytest.approx(0.0)


class TestComputeBreakdownFactorValue:
    def test_all_blend_value(self):
        sleeves = [
            make_sleeve("VTI", "US Total", 100.0, factor_value="blend"),
        ]
        holdings = [make_holding("VTI", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        blend = _find(result.factor_value, "Blend")
        assert blend is not None
        assert blend.current_pct == pytest.approx(100.0)

    def test_mixed_value_and_blend(self):
        sleeves = [
            make_sleeve("VTV", "Value", 40.0, factor_value="tilted"),
            make_sleeve("VTI", "Blend", 60.0, factor_value="blend"),
        ]
        holdings = [make_holding("VTV", 40_000.0), make_holding("VTI", 60_000.0)]
        result = compute_breakdown(holdings, sleeves)
        tilted = _find(result.factor_value, "Tilted")
        blend = _find(result.factor_value, "Blend")
        assert tilted.current_pct == pytest.approx(40.0)
        assert blend.current_pct == pytest.approx(60.0)

    def test_none_factor_value_defaults_to_blend(self):
        sleeves = [make_sleeve("VTI", "US", 100.0, factor_value=None)]
        holdings = [make_holding("VTI", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        blend = _find(result.factor_value, "Blend")
        assert blend is not None
        assert blend.current_pct == pytest.approx(100.0)

    def test_category_mode_value_target(self):
        sleeves = [
            make_sleeve("VTV", "Value", 40.0, factor_value="tilted"),
            make_sleeve("VTI", "Blend", 60.0, factor_value="blend"),
        ]
        holdings = [make_holding("VTV", 40_000.0), make_holding("VTI", 60_000.0)]
        policy = make_policy(targeting_mode="category", target_value_tilted_pct=35.0)
        result = compute_breakdown(holdings, sleeves, policy=policy)
        tilted = _find(result.factor_value, "Tilted")
        assert tilted.target_pct == pytest.approx(35.0)


class TestComputeBreakdownFactorSize:
    """Size breakdown is now relative to value-tilted equities only."""

    def test_all_other_size_within_tilted(self):
        # A tilted large-cap sleeve: 100% "Other" within tilted
        sleeves = [make_sleeve("AVLV", "US LCV", 100.0, factor_value="tilted", factor_size="large")]
        holdings = [make_holding("AVLV", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        other = _find(result.factor_size, "Other")
        small = _find(result.factor_size, "Small Cap")
        assert other.current_pct == pytest.approx(100.0)
        assert small.current_pct == pytest.approx(0.0)

    def test_non_tilted_excluded_from_size(self):
        # Blend sleeves are excluded; size breakdown is empty (0/0)
        sleeves = [make_sleeve("VTI", "US", 100.0, factor_value="blend", factor_size="large")]
        holdings = [make_holding("VTI", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        other = _find(result.factor_size, "Other")
        small = _find(result.factor_size, "Small Cap")
        assert other.current_pct == pytest.approx(0.0)
        assert small.current_pct == pytest.approx(0.0)

    def test_small_cap_as_pct_of_tilted(self):
        sleeves = [
            make_sleeve("AVUV", "Small Value", 30.0, factor_value="tilted", factor_size="small"),
            make_sleeve("AVLV", "Large Value", 20.0, factor_value="tilted", factor_size="large"),
            make_sleeve("VTI", "Total", 50.0, factor_value="blend", factor_size="large"),
        ]
        holdings = [
            make_holding("AVUV", 30_000.0),
            make_holding("AVLV", 20_000.0),
            make_holding("VTI", 50_000.0),
        ]
        result = compute_breakdown(holdings, sleeves)
        small = _find(result.factor_size, "Small Cap")
        other = _find(result.factor_size, "Other")
        # 30K small / 50K tilted total = 60%, 20K large / 50K = 40%
        assert small.current_pct == pytest.approx(60.0)
        assert other.current_pct == pytest.approx(40.0)

    def test_category_mode_small_cap_target(self):
        sleeves = [
            make_sleeve("AVUV", "Small", 30.0, factor_value="tilted", factor_size="small"),
            make_sleeve("AVLV", "Large", 70.0, factor_value="tilted", factor_size="large"),
        ]
        holdings = [make_holding("AVUV", 30_000.0), make_holding("AVLV", 70_000.0)]
        policy = make_policy(targeting_mode="category", target_small_cap_pct=25.0)
        result = compute_breakdown(holdings, sleeves, policy=policy)
        small = _find(result.factor_size, "Small Cap")
        assert small.target_pct == pytest.approx(25.0)

    def test_none_factor_size_tilted_treated_as_other(self):
        sleeves = [make_sleeve("VTV", "US Value", 100.0, factor_value="tilted", factor_size=None)]
        holdings = [make_holding("VTV", 100_000.0)]
        result = compute_breakdown(holdings, sleeves)
        other = _find(result.factor_size, "Other")
        assert other is not None
        assert other.current_pct == pytest.approx(100.0)

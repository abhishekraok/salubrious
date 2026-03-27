"""Tests for the spending runway engine."""
import pytest
from app.engines.spending import compute_spending_runway, run_scenario
from tests.conftest import make_holding, make_policy, make_sleeve


def _make_basic_setup():
    """200k safe assets (bonds + t-bills), 300k total, 50k baseline spending."""
    sleeves = [
        make_sleeve("VTI", "US Stocks", 60.0, is_safe_asset=False),
        make_sleeve("BND", "Bonds", 30.0, is_safe_asset=True),
        make_sleeve("SGOV", "T-Bills", 10.0, is_safe_asset=True, is_cash_like=True),
    ]
    holdings = [
        make_holding("VTI", 100_000.0),
        make_holding("BND", 75_000.0),
        make_holding("SGOV", 25_000.0),
    ]
    policy = make_policy(
        baseline_annual_spending=50_000.0,
        comfortable_annual_spending=60_000.0,
        emergency_annual_spending=40_000.0,
        safe_asset_runway_years_target=4.0,
        minimum_cash_reserve=10_000.0,
    )
    return holdings, sleeves, policy


class TestComputeSpendingRunway:
    def test_safe_asset_total_correct(self):
        holdings, sleeves, policy = _make_basic_setup()
        result = compute_spending_runway(holdings, sleeves, policy)
        # BND=75k + SGOV=25k = 100k safe assets
        assert result.safe_asset_total == pytest.approx(100_000.0)

    def test_cash_like_total_correct(self):
        holdings, sleeves, policy = _make_basic_setup()
        result = compute_spending_runway(holdings, sleeves, policy)
        # Only SGOV is cash_like
        assert result.cash_like_total == pytest.approx(25_000.0)

    def test_baseline_runway_years(self):
        holdings, sleeves, policy = _make_basic_setup()
        result = compute_spending_runway(holdings, sleeves, policy)
        # 100k / 50k = 2.0 years
        assert result.baseline_runway_years == pytest.approx(2.0)

    def test_comfortable_runway_years(self):
        holdings, sleeves, policy = _make_basic_setup()
        result = compute_spending_runway(holdings, sleeves, policy)
        # 100k / 60k ≈ 1.667 years, rounded to 1dp = 1.7
        assert result.comfortable_runway_years == pytest.approx(1.7, abs=0.05)

    def test_emergency_runway_years(self):
        holdings, sleeves, policy = _make_basic_setup()
        result = compute_spending_runway(holdings, sleeves, policy)
        # 100k / 40k = 2.5 years
        assert result.emergency_runway_years == pytest.approx(2.5)

    def test_cash_runway_years(self):
        holdings, sleeves, policy = _make_basic_setup()
        result = compute_spending_runway(holdings, sleeves, policy)
        # 25k / 50k = 0.5 years
        assert result.cash_runway_years == pytest.approx(0.5)

    def test_funded_status_secure(self):
        sleeves = [make_sleeve("BND", "Bonds", 100.0, is_safe_asset=True)]
        holdings = [make_holding("BND", 250_000.0)]
        policy = make_policy(
            baseline_annual_spending=50_000.0,
            safe_asset_runway_years_target=4.0,
        )
        result = compute_spending_runway(holdings, sleeves, policy)
        # 250k / 50k = 5 years >= 4 target -> secure
        assert result.funded_status == "secure"

    def test_funded_status_watch(self):
        sleeves = [make_sleeve("BND", "Bonds", 100.0, is_safe_asset=True)]
        holdings = [make_holding("BND", 160_000.0)]
        policy = make_policy(
            baseline_annual_spending=50_000.0,
            safe_asset_runway_years_target=4.0,
        )
        result = compute_spending_runway(holdings, sleeves, policy)
        # 160k / 50k = 3.2 years; >= 4*0.75=3.0 -> watch
        assert result.funded_status == "watch"

    def test_funded_status_constrained(self):
        sleeves = [make_sleeve("BND", "Bonds", 100.0, is_safe_asset=True)]
        holdings = [make_holding("BND", 100_000.0)]
        policy = make_policy(
            baseline_annual_spending=50_000.0,
            safe_asset_runway_years_target=4.0,
        )
        result = compute_spending_runway(holdings, sleeves, policy)
        # 100k / 50k = 2.0 years; < 3.0 -> constrained
        assert result.funded_status == "constrained"

    def test_above_minimum_reserve(self):
        holdings, sleeves, policy = _make_basic_setup()
        result = compute_spending_runway(holdings, sleeves, policy)
        # 25k cash - 10k reserve = 15k above
        assert result.above_minimum_reserve_by == pytest.approx(15_000.0)

    def test_no_safe_assets_returns_zero_runway(self):
        sleeves = [make_sleeve("VTI", "US Stocks", 100.0)]
        holdings = [make_holding("VTI", 100_000.0)]
        policy = make_policy(baseline_annual_spending=50_000.0)
        result = compute_spending_runway(holdings, sleeves, policy)
        assert result.safe_asset_total == 0.0
        assert result.baseline_runway_years == 0.0

    def test_zero_baseline_spending_defaults_to_one(self):
        # Edge case: policy with zero spending should not divide by zero
        sleeves = [make_sleeve("BND", "Bonds", 100.0, is_safe_asset=True)]
        holdings = [make_holding("BND", 100_000.0)]
        policy = make_policy(
            baseline_annual_spending=0.0,
            comfortable_annual_spending=0.0,
            emergency_annual_spending=0.0,
        )
        result = compute_spending_runway(holdings, sleeves, policy)
        # defaults baseline to 1, so runway = 100_000
        assert result.baseline_runway_years == pytest.approx(100_000.0)

    def test_holdings_aggregated_across_accounts(self):
        sleeves = [make_sleeve("BND", "Bonds", 100.0, is_safe_asset=True)]
        holdings = [make_holding("BND", 50_000.0), make_holding("BND", 50_000.0)]
        policy = make_policy(baseline_annual_spending=50_000.0)
        result = compute_spending_runway(holdings, sleeves, policy)
        assert result.safe_asset_total == pytest.approx(100_000.0)
        assert result.baseline_runway_years == pytest.approx(2.0)


class TestRunScenario:
    def _make_runway(self, safe_total=200_000.0):
        from app.engines.spending import SpendingRunway
        return SpendingRunway(
            safe_asset_total=safe_total,
            cash_like_total=50_000.0,
            baseline_runway_years=4.0,
            comfortable_runway_years=3.3,
            emergency_runway_years=5.0,
            cash_runway_years=1.0,
            funded_status="secure",
            above_minimum_reserve_by=40_000.0,
        )

    def test_no_change_scenario(self):
        runway = self._make_runway()
        result = run_scenario(runway, baseline_spending=50_000.0)
        # 200k / 50k = 4.0 years
        assert result.adjusted_runway_years == pytest.approx(4.0)
        assert result.adjusted_funded_status == "secure"

    def test_spending_increase_reduces_runway(self):
        runway = self._make_runway()
        result = run_scenario(runway, baseline_spending=50_000.0, spending_delta=10_000.0)
        # 200k / 60k ≈ 3.333 years, rounded to 1dp = 3.3; >= 4*0.75=3 -> watch
        assert result.adjusted_runway_years == pytest.approx(3.3, abs=0.05)
        assert result.adjusted_funded_status == "watch"

    def test_portfolio_shock_reduces_runway(self):
        runway = self._make_runway()
        result = run_scenario(runway, baseline_spending=50_000.0, portfolio_shock_percent=-50.0)
        # 200k * 0.5 / 50k = 2.0 years -> constrained (< 3.0)
        assert result.adjusted_runway_years == pytest.approx(2.0)
        assert result.adjusted_funded_status == "constrained"

    def test_portfolio_increase_improves_runway(self):
        runway = self._make_runway(safe_total=100_000.0)
        result = run_scenario(runway, baseline_spending=50_000.0, portfolio_shock_percent=100.0)
        # 100k * 2 / 50k = 4.0 years -> secure
        assert result.adjusted_runway_years == pytest.approx(4.0)
        assert result.adjusted_funded_status == "secure"

    def test_combined_spending_and_shock(self):
        runway = self._make_runway()
        result = run_scenario(
            runway,
            baseline_spending=50_000.0,
            spending_delta=10_000.0,
            portfolio_shock_percent=-25.0,
        )
        # 200k * 0.75 / 60k = 2.5 years -> constrained
        assert result.adjusted_runway_years == pytest.approx(2.5)
        assert result.adjusted_funded_status == "constrained"

    def test_invalid_spending_zero_returns_error(self):
        runway = self._make_runway()
        result = run_scenario(runway, baseline_spending=50_000.0, spending_delta=-50_000.0)
        assert result.adjusted_funded_status == "constrained"
        assert result.adjusted_runway_years == 0

    def test_invalid_spending_negative_returns_error(self):
        runway = self._make_runway()
        result = run_scenario(runway, baseline_spending=50_000.0, spending_delta=-100_000.0)
        assert result.adjusted_funded_status == "constrained"

    def test_description_includes_spending_change(self):
        runway = self._make_runway()
        result = run_scenario(runway, baseline_spending=50_000.0, spending_delta=5_000.0)
        assert "spending" in result.description.lower()
        assert "increases" in result.description.lower()

    def test_description_includes_shock(self):
        runway = self._make_runway()
        result = run_scenario(runway, baseline_spending=50_000.0, portfolio_shock_percent=-30.0)
        assert "safe assets" in result.description.lower()
        assert "drop" in result.description.lower()

    def test_custom_runway_target(self):
        runway = self._make_runway()
        # With target=2 years, 4 years runway -> secure
        result = run_scenario(runway, baseline_spending=50_000.0, runway_target_years=2.0)
        assert result.adjusted_funded_status == "secure"

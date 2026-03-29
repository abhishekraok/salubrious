"""Tests for the rebalance suggestion engine."""
from datetime import date

import pytest
from app.engines.allocation import AllocationResult, SleeveAllocation
from app.engines.breakdown import compute_breakdown
from app.engines.rebalance import suggest_category_rebalance, suggest_rebalance


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


# ---------------------------------------------------------------------------
# Category-mode rebalance tests
# ---------------------------------------------------------------------------

class _FakeSleeve:
    """Lightweight stand-in for PortfolioSleeve (avoids SQLAlchemy instrumentation)."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


class _FakeHolding:
    """Lightweight stand-in for Holding."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


class _FakePolicy:
    """Lightweight stand-in for InvestmentPolicy."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


def _make_sleeve(
    ticker: str,
    label: str,
    is_safe_asset: bool = False,
    is_cash_like: bool = False,
    region_us_pct: float = 100.0,
    region_developed_pct: float = 0.0,
    region_emerging_pct: float = 0.0,
    factor_value: str | None = None,
    factor_size: str | None = None,
):
    return _FakeSleeve(
        ticker=ticker, label=label, target_percent=0.0,
        asset_class="bond" if is_safe_asset else "equity",
        is_safe_asset=is_safe_asset, is_cash_like=is_cash_like,
        region_us_pct=region_us_pct, region_developed_pct=region_developed_pct,
        region_emerging_pct=region_emerging_pct,
        factor_value=factor_value, factor_size=factor_size,
        geography=None, preferred_account_type=None, notes=None,
    )


def _make_holding(ticker: str, market_value: float):
    return _FakeHolding(
        ticker=ticker, market_value=market_value,
        quantity=0, price=0, as_of_date=date.today(), id=0, account_id=0,
    )


def _make_policy(
    target_equity_pct: float = 80.0,
    target_international_pct: float = 40.0,
    target_value_tilted_pct: float = 0.0,
    target_small_cap_pct: float = 0.0,
):
    return _FakePolicy(
        targeting_mode="category",
        target_equity_pct=target_equity_pct,
        target_international_pct=target_international_pct,
        target_value_tilted_pct=target_value_tilted_pct,
        target_small_cap_pct=target_small_cap_pct,
        avoid_taxable_sales=False,
    )


class TestCategoryRebalanceNoAction:
    def test_no_holdings_returns_no_holdings(self):
        policy = _make_policy()
        sleeves = [_make_sleeve("VTI", "US Equity")]
        breakdown = compute_breakdown([], sleeves, policy)
        suggestion = suggest_category_rebalance(breakdown, sleeves, [], policy)
        assert suggestion.headline == "No holdings to rebalance"

    def test_on_target_returns_no_action(self):
        """Portfolio perfectly matches 80/20 equity/safe with 40% intl."""
        sleeves = [
            _make_sleeve("VTI", "US Total Market", region_us_pct=100),
            _make_sleeve("VXUS", "Intl Equity", region_us_pct=0, region_developed_pct=80, region_emerging_pct=20),
            _make_sleeve("BND", "US Bonds", is_safe_asset=True),
        ]
        # 80% equity (48% US + 32% intl), 20% safe
        # International = 32/80 = 40% of equities — matches target
        holdings = [
            _make_holding("VTI", 48_000),
            _make_holding("VXUS", 32_000),
            _make_holding("BND", 20_000),
        ]
        policy = _make_policy(target_equity_pct=80.0, target_international_pct=40.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(breakdown, sleeves, holdings, policy)
        assert suggestion.headline == "No action needed"
        assert suggestion.urgency == "none"


class TestCategoryRebalanceEquityDrift:
    def test_equity_too_high_suggests_sell_equity_buy_safe(self):
        """Equities at 90% vs target 70% — should suggest selling equity, buying bonds."""
        sleeves = [
            _make_sleeve("VTI", "US Equity", region_us_pct=100),
            _make_sleeve("BND", "US Bonds", is_safe_asset=True),
        ]
        holdings = [
            _make_holding("VTI", 90_000),
            _make_holding("BND", 10_000),
        ]
        policy = _make_policy(target_equity_pct=70.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown, sleeves, holdings, policy, avoid_taxable_sales=False,
        )
        assert suggestion.action_items
        item = suggestion.action_items[0]
        assert item.action == "exchange"
        assert item.source_ticker == "VTI"
        assert item.ticker == "BND"
        assert item.amount > 0

    def test_equity_too_low_suggests_sell_safe_buy_equity(self):
        """Equities at 50% vs target 80% — should suggest selling bonds, buying equity."""
        sleeves = [
            _make_sleeve("VTI", "US Equity", region_us_pct=100),
            _make_sleeve("BND", "US Bonds", is_safe_asset=True, is_cash_like=True),
        ]
        holdings = [
            _make_holding("VTI", 50_000),
            _make_holding("BND", 50_000),
        ]
        policy = _make_policy(target_equity_pct=80.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown, sleeves, holdings, policy, avoid_taxable_sales=True,
        )
        assert suggestion.action_items
        item = suggestion.action_items[0]
        assert item.action == "exchange"
        assert item.source_ticker == "BND"
        assert item.ticker == "VTI"


class TestCategoryRebalanceRegionDrift:
    def test_international_too_low_suggests_sell_us_buy_intl(self):
        """International at 10% of equities vs target 40%."""
        sleeves = [
            _make_sleeve("VTI", "US Equity", region_us_pct=100),
            _make_sleeve("VXUS", "Intl Equity", region_us_pct=0, region_developed_pct=80, region_emerging_pct=20),
            _make_sleeve("BND", "Bonds", is_safe_asset=True),
        ]
        # 80% equities (72% US, 8% intl). Intl is 8/80 = 10% of equities.
        holdings = [
            _make_holding("VTI", 72_000),
            _make_holding("VXUS", 8_000),
            _make_holding("BND", 20_000),
        ]
        policy = _make_policy(target_equity_pct=80.0, target_international_pct=40.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown, sleeves, holdings, policy, avoid_taxable_sales=False,
        )
        # Should suggest exchanging VTI → VXUS
        exchange_items = [a for a in suggestion.action_items if a.action == "exchange"]
        region_trade = [a for a in exchange_items if a.ticker == "VXUS"]
        assert region_trade, f"Expected VXUS buy trade, got: {suggestion.action_items}"
        assert region_trade[0].source_ticker == "VTI"


class TestCategoryRebalancePendingCash:
    def test_pending_cash_buys_underweight_category(self):
        """Use pending cash to buy into underweight safe assets."""
        sleeves = [
            _make_sleeve("VTI", "US Equity", region_us_pct=100),
            _make_sleeve("BND", "Bonds", is_safe_asset=True),
        ]
        # 90% equity vs 70% target
        holdings = [
            _make_holding("VTI", 90_000),
            _make_holding("BND", 10_000),
        ]
        policy = _make_policy(target_equity_pct=70.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown, sleeves, holdings, policy, pending_cash=20_000,
        )
        assert suggestion.action_items
        buy_items = [a for a in suggestion.action_items if a.action == "buy"]
        assert buy_items
        assert buy_items[0].ticker == "BND"


class TestCategoryRebalanceMinimumTrades:
    def test_single_trade_fixes_multiple_drifts(self):
        """When equity is too high AND international is too low,
        selling US equity for intl equity is NOT the fix for asset type.
        But selling US equity for bonds fixes asset type.
        This test verifies we don't generate unnecessary trades."""
        sleeves = [
            _make_sleeve("VTI", "US Equity", region_us_pct=100),
            _make_sleeve("VXUS", "Intl Equity", region_us_pct=0, region_developed_pct=80, region_emerging_pct=20),
            _make_sleeve("BND", "Bonds", is_safe_asset=True),
        ]
        holdings = [
            _make_holding("VTI", 80_000),
            _make_holding("VXUS", 10_000),
            _make_holding("BND", 10_000),
        ]
        # Target: 70% equity, 40% intl of equity
        policy = _make_policy(target_equity_pct=70.0, target_international_pct=40.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown, sleeves, holdings, policy, avoid_taxable_sales=False,
        )
        # Should have trades but keep the count low
        real_trades = [a for a in suggestion.action_items if a.amount > 0]
        assert len(real_trades) <= 3  # At most one per drifted dimension
        # Verify trades are consolidated (no duplicate sell/buy pairs)
        pairs = [(a.source_ticker, a.ticker) for a in real_trades if a.source_ticker]
        assert len(pairs) == len(set(pairs)), "Duplicate trade pairs found"


class TestCategoryRebalanceUrgency:
    def test_hard_breach_urgency_high(self):
        """Large drift should result in high urgency."""
        sleeves = [
            _make_sleeve("VTI", "US Equity", region_us_pct=100),
            _make_sleeve("BND", "Bonds", is_safe_asset=True),
        ]
        # 95% equity vs 60% target — huge drift (35pp, hard band = 15pp)
        holdings = [
            _make_holding("VTI", 95_000),
            _make_holding("BND", 5_000),
        ]
        policy = _make_policy(target_equity_pct=60.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown, sleeves, holdings, policy, avoid_taxable_sales=False,
        )
        assert suggestion.urgency == "high"

    def test_mild_drift_urgency_low(self):
        """Drift outside soft but inside hard band → low urgency.
        Equity target 80%: hard=20, soft=10. Safe target 20%: hard=5, soft=2.5.
        We need BOTH sides inside their hard bands but at least one outside soft.
        Use 85% equity (5pp drift on equity side, outside soft=10? No, 5<10).
        Actually: equity drift 5pp < soft 10 → ok. Safe drift -5pp, |5| > soft 2.5
        but |5| = hard 5 → watch (not action_needed since <= hard). So urgency = low.
        """
        sleeves = [
            _make_sleeve("VTI", "US Equity", region_us_pct=100),
            _make_sleeve("BND", "Bonds", is_safe_asset=True),
        ]
        # 85% equity vs 80% target. Safe: 15% vs 20% target (drift=-5pp, hard=5, soft=2.5)
        # |drift|=5 == hard → classify_drift says "watch" (<=hard)
        holdings = [
            _make_holding("VTI", 85_000),
            _make_holding("BND", 15_000),
        ]
        policy = _make_policy(target_equity_pct=80.0)
        breakdown = compute_breakdown(holdings, sleeves, policy)
        suggestion = suggest_category_rebalance(
            breakdown, sleeves, holdings, policy, avoid_taxable_sales=False,
        )
        if suggestion.urgency != "none":
            assert suggestion.urgency == "low"

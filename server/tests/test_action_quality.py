"""Tests for benchmark-relative historical action scoring."""

import json

import pytest

from app.engines.action_quality import (
    AllocationAction,
    score_action,
    score_actions,
)


def make_action(
    action_id: str = "a-1",
    *,
    action_date: str = "2024-01-02",
    action_type: str = "buy",
    ticker: str = "CHOSEN",
    notional: float = 1_000.0,
) -> AllocationAction:
    return AllocationAction(
        action_id=action_id,
        action_date=action_date,
        action_type=action_type,
        ticker=ticker,
        notional=notional,
    )


def price_history(
    chosen: dict[str, float],
    benchmark: dict[str, float],
) -> dict[str, dict[str, float]]:
    return {"CHOSEN": chosen, "VFFVX": benchmark}


def test_weekend_action_aligns_to_first_common_trading_date():
    prices = price_history(
        {
            "2024-01-05": 90.0,
            "2024-01-08": 100.0,
            "2025-01-06": 110.0,
            "2025-01-08": 111.0,
        },
        {
            "2024-01-05": 95.0,
            "2024-01-08": 100.0,
            "2025-01-06": 105.0,
            "2025-01-08": 106.0,
        },
    )

    result = score_action(
        make_action(action_date="2024-01-06"),
        prices,
        as_of="2025-01-08",
    )

    assert result.entry_date == "2024-01-08"
    # The 365-day horizon is 2025-01-07, so the last common date is Jan 6.
    assert result.evaluation_date == "2025-01-06"
    assert result.maturity == "mature"
    assert result.chosen_return_pct == pytest.approx(10.0)
    assert result.benchmark_return_pct == pytest.approx(5.0)


def test_buy_advantage_sign_and_opportunity_cost():
    prices = price_history(
        {"2024-01-02": 100.0, "2025-01-01": 90.0},
        {"2024-01-02": 100.0, "2025-01-01": 110.0},
    )

    result = score_action(make_action(notional=1_000.0), prices, as_of="2025-01-02")

    assert result.chosen_return_pct == pytest.approx(-10.0)
    assert result.benchmark_return_pct == pytest.approx(10.0)
    assert result.advantage_pct_points == pytest.approx(-20.0)
    assert result.opportunity_cost == pytest.approx(200.0)
    assert result.outcome == "behind"


@pytest.mark.parametrize(
    ("chosen_end", "expected_outcome"),
    [(105.0, "similar"), (105.01, "ahead"), (100.99, "behind")],
)
def test_two_point_deadband_is_inclusive(chosen_end: float, expected_outcome: str):
    prices = price_history(
        {"2024-01-02": 100.0, "2025-01-01": chosen_end},
        {"2024-01-02": 100.0, "2025-01-01": 103.0},
    )

    result = score_action(make_action(), prices, as_of="2025-01-02")

    assert result.outcome == expected_outcome


def test_action_before_full_horizon_is_developing():
    prices = price_history(
        {"2025-01-02": 100.0, "2025-06-30": 108.0},
        {"2025-01-02": 100.0, "2025-06-30": 104.0},
    )

    result = score_action(make_action(action_date="2025-01-02"), prices, as_of="2025-06-30")

    assert result.maturity == "developing"
    assert result.horizon_date == "2026-01-02"
    assert result.evaluation_date == "2025-06-30"
    assert result.observed_days == 179


def test_missing_security_prices_are_marked_without_metrics():
    result = score_action(
        make_action(ticker="MISSING"),
        {"VFFVX": {"2024-01-02": 100.0, "2025-01-01": 110.0}},
        as_of="2025-01-02",
    )

    assert result.score_status == "missing_prices"
    assert result.reason == "missing_security_prices"
    assert result.outcome is None
    assert result.opportunity_cost is None


def test_non_buy_action_is_explicitly_excluded():
    result = score_action(
        make_action(action_type="sell"),
        price_history(
            {"2024-01-02": 100.0, "2025-01-01": 110.0},
            {"2024-01-02": 100.0, "2025-01-01": 105.0},
        ),
        as_of="2025-01-02",
    )

    assert result.score_status == "excluded"
    assert result.reason == "action_type_not_scorable"
    assert result.maturity is None


def test_duplicate_action_ids_are_not_scored_or_weighted_twice():
    action = make_action(action_id="same-id", notional=2_000.0)
    prices = price_history(
        {"2024-01-02": 100.0, "2025-01-01": 110.0},
        {"2024-01-02": 100.0, "2025-01-01": 105.0},
    )

    report = score_actions([action, action], prices, as_of="2025-01-02")

    assert report.actions[0].score_status == "scored"
    assert report.actions[1].score_status == "duplicate"
    assert report.actions[1].reason == "duplicate_action_id"
    assert report.summary.scored_actions == 1
    assert report.summary.duplicate_actions == 1
    assert report.summary.scored_notional == pytest.approx(2_000.0)


def test_summary_uses_notional_weighted_advantage_and_is_json_ready():
    actions = [
        make_action("small", ticker="SMALL", notional=100.0),
        make_action("large", ticker="LARGE", notional=900.0),
    ]
    prices = {
        "SMALL": {"2024-01-02": 100.0, "2025-01-01": 120.0},
        "LARGE": {"2024-01-02": 100.0, "2025-01-01": 100.0},
        "VFFVX": {"2024-01-02": 100.0, "2025-01-01": 110.0},
    }

    report = score_actions(actions, prices, as_of="2025-01-02")

    # 10pp at weight 10%, -10pp at weight 90% => -8pp.
    assert report.summary.weighted_advantage_pct_points == pytest.approx(-8.0)
    assert report.summary.weighted_outcome == "behind"
    assert "not additive or causal" in report.summary.interpretation
    json.dumps(report.to_dict())

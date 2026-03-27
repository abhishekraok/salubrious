"""Tests for the tolerance band engine."""
import pytest
from app.engines.bands import classify_drift, compute_bands


class TestComputeBands:
    def test_small_target_hits_floor(self):
        # 25% of 4 = 1.0, which is below the 2pp floor
        soft, hard = compute_bands(4.0)
        assert hard == 2.0
        assert soft == 1.0

    def test_large_target_uses_relative_rule(self):
        # 25% of 40 = 10.0 > floor; soft = 5.0
        soft, hard = compute_bands(40.0)
        assert hard == 10.0
        assert soft == 5.0

    def test_boundary_target_at_floor_crossover(self):
        # 25% of 8 = 2.0, exactly at floor; soft = 1.0
        soft, hard = compute_bands(8.0)
        assert hard == 2.0
        assert soft == 1.0

    def test_target_just_above_crossover(self):
        # 25% of 12 = 3.0 > 2 floor
        soft, hard = compute_bands(12.0)
        assert hard == 3.0
        assert soft == 1.5

    def test_zero_target_uses_floor(self):
        soft, hard = compute_bands(0.0)
        assert hard == 2.0
        assert soft == 1.0

    def test_returns_rounded_values(self):
        # 25% of 7 = 1.75, floor wins at 2.0; soft = 1.0
        soft, hard = compute_bands(7.0)
        assert isinstance(soft, float)
        assert isinstance(hard, float)
        # Rounding to 1 decimal place
        assert soft == round(soft, 1)
        assert hard == round(hard, 1)


class TestClassifyDrift:
    def test_no_drift_is_ok(self):
        assert classify_drift(0.0, soft=1.0, hard=2.0) == "ok"

    def test_within_soft_band_is_ok(self):
        assert classify_drift(0.9, soft=1.0, hard=2.0) == "ok"
        assert classify_drift(-0.9, soft=1.0, hard=2.0) == "ok"

    def test_at_soft_boundary_is_ok(self):
        assert classify_drift(1.0, soft=1.0, hard=2.0) == "ok"

    def test_just_over_soft_is_watch(self):
        assert classify_drift(1.1, soft=1.0, hard=2.0) == "watch"
        assert classify_drift(-1.1, soft=1.0, hard=2.0) == "watch"

    def test_at_hard_boundary_is_watch(self):
        assert classify_drift(2.0, soft=1.0, hard=2.0) == "watch"

    def test_just_over_hard_is_action_needed(self):
        assert classify_drift(2.1, soft=1.0, hard=2.0) == "action_needed"
        assert classify_drift(-2.1, soft=1.0, hard=2.0) == "action_needed"

    def test_large_drift_is_action_needed(self):
        assert classify_drift(15.0, soft=1.0, hard=2.0) == "action_needed"

    def test_negative_drift_symmetry(self):
        # Drift in both directions should be classified equally
        for drift in [0.5, 1.5, 3.0]:
            assert classify_drift(drift, 1.0, 2.0) == classify_drift(-drift, 1.0, 2.0)

import math
import pytest
import numpy as np
from banking_risk.irrbb.constants import EBA_BUCKET_MIDPOINTS, POST_SHOCK_FLOOR_INTERCEPT, POST_SHOCK_FLOOR_SLOPE
from banking_risk.irrbb.scenarios import (
    Flattener,
    Parallel_Down,
    Parallel_Up,
    Scenario_Set,
    Short_Rate_Down,
    Short_Rate_Up,
    Steepener,
)

_MIDS = np.array(EBA_BUCKET_MIDPOINTS)
_FLAT = np.full(len(_MIDS), 0.03)   # 3% flat base curve


# ── Parallel scenarios ────────────────────────────────────────────────────────

def test_parallel_up_uniform_shift():
    shocked = Parallel_Up(200).shock(_FLAT, _MIDS)
    assert np.allclose(shocked, _FLAT + 0.02)


def test_parallel_down_uniform_shift():
    shocked = Parallel_Down(-200).shock(_FLAT, _MIDS)
    floor = POST_SHOCK_FLOOR_INTERCEPT + POST_SHOCK_FLOOR_SLOPE * _MIDS
    expected = np.maximum(_FLAT - 0.02, floor)
    assert np.allclose(shocked, expected)


def test_parallel_down_applies_floor():
    # Very low base rates: floor should bind
    low_base = np.full(len(_MIDS), 0.001)
    shocked = Parallel_Down(-200).shock(low_base, _MIDS)
    floor = POST_SHOCK_FLOOR_INTERCEPT + POST_SHOCK_FLOOR_SLOPE * _MIDS
    assert np.all(shocked >= floor - 1e-10)


def test_parallel_up_ignores_maturities():
    maturities_a = np.array([1.0, 2.0, 5.0])
    maturities_b = np.array([3.0, 7.0, 10.0])
    base = np.array([0.03, 0.03, 0.03])
    assert np.allclose(
        Parallel_Up(100).shock(base, maturities_a),
        Parallel_Up(100).shock(base, maturities_b),
    )


# ── Short-rate scenarios ──────────────────────────────────────────────────────

def test_short_rate_up_fades_at_20y():
    maturities = np.array([0.0, 10.0, 20.0, 30.0])
    base = np.full(4, 0.03)
    shocked = Short_Rate_Up(250).shock(base, maturities)
    assert shocked[0] > shocked[1] > shocked[2]   # fades toward 20Y
    assert shocked[2] == pytest.approx(base[2])    # zero weight at 20Y
    assert shocked[3] == pytest.approx(base[3])    # beyond 20Y unchanged


def test_short_rate_down_applies_floor():
    maturities = np.array([0.0, 1.0, 5.0])
    base = np.full(3, 0.001)
    shocked = Short_Rate_Down(-250).shock(base, maturities)
    floor = POST_SHOCK_FLOOR_INTERCEPT + POST_SHOCK_FLOOR_SLOPE * maturities
    assert np.all(shocked >= floor - 1e-10)


# ── Non-parallel shape ────────────────────────────────────────────────────────

def test_steepener_short_down_long_up():
    maturities = np.array([0.5, 25.0])
    base = np.full(2, 0.03)
    shocked = Steepener(250, 100).shock(base, maturities)
    assert shocked[0] < base[0]   # short end moves down
    assert shocked[1] > base[1]   # long end moves up


def test_flattener_short_up_long_down():
    maturities = np.array([0.5, 25.0])
    base = np.full(2, 0.03)
    shocked = Flattener(250, 100).shock(base, maturities)
    assert shocked[0] > base[0]   # short end moves up
    assert shocked[1] < base[1]   # long end moves down


# ── Scenario_Set ─────────────────────────────────────────────────────────────

def test_scenario_set_has_six_scenarios():
    assert len(Scenario_Set("EUR")) == 6


def test_scenario_set_unknown_currency():
    with pytest.raises(ValueError):
        Scenario_Set("XYZ")


def test_scenario_set_getitem():
    ss = Scenario_Set("EUR")
    assert ss["parallel_up"].name == "parallel_up"


def test_scenario_set_getitem_missing():
    ss = Scenario_Set("EUR")
    with pytest.raises(KeyError):
        ss["nonexistent"]


def test_scenario_set_names():
    ss = Scenario_Set("EUR")
    names = {s.name for s in ss}
    assert names == {"parallel_up", "parallel_down", "short_rate_up",
                     "short_rate_down", "steepener", "flattener"}


# ── Grid properties ───────────────────────────────────────────────────────────

def test_combined_contains_all_midpoints():
    ss = Scenario_Set("EUR")
    for m in ss.midpoints:
        assert np.any(np.isclose(ss.combined, m))


def test_midpoint_idx_indexes_correctly():
    ss = Scenario_Set("EUR")
    for i, idx in enumerate(ss.midpoint_idx):
        assert ss.combined[idx] == pytest.approx(ss.midpoints[i])


def test_combined_sorted():
    ss = Scenario_Set("EUR")
    assert np.all(np.diff(ss.combined) > 0)


def test_custom_grid_injected():
    custom = np.linspace(0.5, 10.0, 50)
    ss = Scenario_Set("EUR", grid=custom)
    assert np.allclose(ss.grid, custom)

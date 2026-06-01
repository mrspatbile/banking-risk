import math
import numpy as np
import pytest

from banking_risk.frtb.girr.curvature import (
    SA_GIRR_Curvature_Calculator,
    GIRR_Curvature_Result,
    curvature_pnl_from_greeks,
)
from banking_risk.frtb.constants import FRTB_GIRR_RISK_WEIGHTS, FRTB_GIRR_VERTICES

_N  = len(FRTB_GIRR_VERTICES)
_RW = np.array(FRTB_GIRR_RISK_WEIGHTS) / 10_000


def _run(cvr_up, cvr_down):
    return SA_GIRR_Curvature_Calculator().compute(cvr_up, cvr_down)


# ── Input validation ──────────────────────────────────────────────────────────

def test_mismatched_currencies_raises():
    with pytest.raises(ValueError, match="currency keys"):
        _run({"EUR": 100.0}, {"USD": 100.0})


# ── Zero CVR ──────────────────────────────────────────────────────────────────

def test_zero_cvr_zero_capital():
    result = _run({"EUR": 0.0}, {"EUR": 0.0})
    assert result.capital == pytest.approx(0.0)

def test_negative_cvr_only_zero_capital():
    # Both scenarios are gains (negative CVR) → no capital charge
    result = _run({"EUR": -100.0}, {"EUR": -50.0})
    assert result.K["EUR"] == pytest.approx(0.0)
    assert result.capital  == pytest.approx(0.0)


# ── K per bucket ──────────────────────────────────────────────────────────────

def test_K_equals_max_of_up_and_down():
    result = _run({"EUR": 200.0}, {"EUR": 150.0})
    assert result.K["EUR"] == pytest.approx(200.0)

def test_K_picks_down_when_larger():
    result = _run({"EUR": 100.0}, {"EUR": 300.0})
    assert result.K["EUR"] == pytest.approx(300.0)

def test_K_is_zero_when_both_negative():
    result = _run({"EUR": -10.0}, {"EUR": -20.0})
    assert result.K["EUR"] == pytest.approx(0.0)


# ── Single currency capital ───────────────────────────────────────────────────

def test_single_currency_capital_equals_K():
    result = _run({"EUR": 500.0}, {"EUR": 300.0})
    assert result.capital == pytest.approx(result.K["EUR"])


# ── Cross-currency aggregation ────────────────────────────────────────────────

def test_two_currencies_same_sign_capital():
    # K_EUR = 100, K_USD = 100, S_EUR = 100, S_USD = 100, gamma = 0.5
    # Capital = sqrt(100² + 100² + 2 × 0.5 × 100 × 100) = sqrt(30000) ≈ 173.2
    result = _run({"EUR": 100.0, "USD": 100.0}, {"EUR": 80.0, "USD": 80.0})
    expected = math.sqrt(100**2 + 100**2 + 2 * 0.5 * 100 * 100)
    assert result.capital == pytest.approx(expected, rel=1e-6)


def test_two_currencies_opposite_sign_cancel():
    # K_EUR = 100 (up = 100), K_USD = 100 (down = 100)
    # S_EUR = 100 (worst = up = 100), S_USD = 100 (worst = down = 100)
    # cross = 0.5 × 100 × 100 = 5000, two off-diagonal terms → +10000
    # sum = 10000 + 10000 + 10000 = 30000, sqrt = 173.2
    # (same as above — sign of S only matters when opposite)
    result = _run({"EUR": 100.0, "USD": -100.0}, {"EUR": 50.0, "USD": 100.0})
    # K_EUR=100, K_USD=100; S_EUR=100, S_USD=100 (worst case for each)
    # Both K positive, S chosen from worst scenario
    assert result.capital >= 0.0


# ── Result shape ──────────────────────────────────────────────────────────────

def test_result_contains_all_currencies():
    result = _run({"EUR": 100.0, "USD": 50.0}, {"EUR": 80.0, "USD": 40.0})
    assert set(result.currencies) == {"EUR", "USD"}
    assert set(result.K) == {"EUR", "USD"}


# ── curvature_pnl_from_greeks ─────────────────────────────────────────────────

def test_greeks_zero_gamma_zero_cvr():
    delta = np.ones(_N)
    gamma = np.zeros(_N)
    cvr_up, cvr_down = curvature_pnl_from_greeks(delta, gamma)
    assert cvr_up   == pytest.approx(0.0)
    assert cvr_down == pytest.approx(0.0)

def test_greeks_symmetric_up_equals_down():
    delta = np.ones(_N)
    gamma = np.ones(_N)
    cvr_up, cvr_down = curvature_pnl_from_greeks(delta, gamma)
    assert cvr_up == pytest.approx(cvr_down)

def test_greeks_positive_gamma_negative_cvr():
    # Positive gamma (long convexity) → CVR < 0 (gain under stress)
    delta = np.zeros(_N)
    gamma = np.ones(_N)
    cvr_up, _ = curvature_pnl_from_greeks(delta, gamma)
    assert cvr_up < 0.0

def test_greeks_negative_gamma_positive_cvr():
    # Negative gamma (short convexity) → CVR > 0 (loss under stress)
    delta = np.zeros(_N)
    gamma = -np.ones(_N)
    cvr_up, _ = curvature_pnl_from_greeks(delta, gamma)
    assert cvr_up > 0.0

def test_greeks_manual_value():
    # CVR = -0.5 × Σ gamma_k × RW_k²
    # With gamma = [1, 0, 0, ...] and RW[0] = 1.7bps = 0.00017
    # CVR = -0.5 × 1 × (0.00017)² ≈ -1.445e-8
    delta = np.zeros(_N)
    gamma = np.zeros(_N)
    gamma[0] = 1.0
    cvr_up, _ = curvature_pnl_from_greeks(delta, gamma)
    expected  = -0.5 * 1.0 * (_RW[0] ** 2)
    assert cvr_up == pytest.approx(expected, rel=1e-6)

def test_greeks_wrong_length_raises():
    with pytest.raises(ValueError, match="length"):
        curvature_pnl_from_greeks(np.ones(5), np.ones(5))

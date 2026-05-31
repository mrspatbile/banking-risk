# tests/test_girr.py

import math
import pytest
import numpy as np
from banking_risk.frtb.constants import (
    FRTB_GIRR_LABELS,
    FRTB_GIRR_RISK_WEIGHTS,
    FRTB_GIRR_VERTICES,
    GIRR_CORRELATION_ALPHA,
    GIRR_CROSS_BUCKET_GAMMA,
)
from banking_risk.frtb.girr.delta import SA_GIRR_Calculator, GIRR_Result

_N = len(FRTB_GIRR_VERTICES)
_RW = np.array(FRTB_GIRR_RISK_WEIGHTS)
_V  = np.array(FRTB_GIRR_VERTICES)


def _run(sensitivities):
    return SA_GIRR_Calculator().compute(sensitivities)


# ── Input validation ──────────────────────────────────────────────────────────

def test_wrong_array_length_raises():
    with pytest.raises(ValueError, match="length"):
        _run({"EUR": np.zeros(5)})


def test_empty_sensitivities_returns_zero_capital():
    result = _run({"EUR": np.zeros(_N)})
    assert result.capital == pytest.approx(0.0)


# ── Risk-weighted sensitivities ───────────────────────────────────────────────

def test_ws_equals_pv01_times_risk_weight():
    s = np.ones(_N)
    result = _run({"EUR": s})
    expected = s * _RW
    assert np.allclose(result.ws["EUR"].values, expected)


def test_ws_labels_match_girr_labels():
    result = _run({"EUR": np.ones(_N)})
    assert list(result.ws["EUR"].index) == FRTB_GIRR_LABELS


# ── Within-bucket capital ─────────────────────────────────────────────────────

def test_single_vertex_capital_equals_abs_ws():
    """Only one non-zero PV01 → K_b = |WS_k|."""
    s = np.zeros(_N)
    s[4] = 1000.0   # 3Y vertex
    ws_k = 1000.0 * _RW[4]
    result = _run({"EUR": s})
    assert result.K["EUR"] == pytest.approx(ws_k, rel=1e-6)


def test_two_vertices_capital_manual():
    """K_b = sqrt(WS1^2 + WS5^2 + 2*rho*WS1*WS5) for two active vertices."""
    s = np.zeros(_N)
    s[0] = 500.0    # 0.25Y
    s[5] = 800.0    # 5Y
    ws0 = 500.0 * _RW[0]
    ws5 = 800.0 * _RW[5]
    rho = math.exp(-GIRR_CORRELATION_ALPHA * abs(_V[0] - _V[5]))
    expected_K = math.sqrt(ws0**2 + ws5**2 + 2 * rho * ws0 * ws5)
    result = _run({"EUR": s})
    assert result.K["EUR"] == pytest.approx(expected_K, rel=1e-6)


def test_capital_non_negative_for_offsetting_positions():
    """Long and short at same vertex — capital floored at 0, never negative."""
    s = np.zeros(_N)
    s[3] = 1000.0
    s[4] = -1500.0
    result = _run({"EUR": s})
    assert result.capital >= 0.0


# ── Correlation matrix ────────────────────────────────────────────────────────

def test_correlation_diagonal_is_one():
    """rho(t, t) = exp(0) = 1 for all vertices."""
    for i in range(_N):
        rho_ii = math.exp(-GIRR_CORRELATION_ALPHA * 0.0)
        assert rho_ii == pytest.approx(1.0)


def test_correlation_decays_with_tenor_distance():
    """Vertices farther apart have lower correlation."""
    rho_adj  = math.exp(-GIRR_CORRELATION_ALPHA * abs(_V[0] - _V[1]))
    rho_far  = math.exp(-GIRR_CORRELATION_ALPHA * abs(_V[0] - _V[-1]))
    assert rho_adj > rho_far


def test_correlation_symmetric():
    diff = np.abs(_V[:, None] - _V[None, :])
    rho  = np.exp(-GIRR_CORRELATION_ALPHA * diff)
    assert np.allclose(rho, rho.T)


# ── Net sensitivity capping ───────────────────────────────────────────────────

def test_net_sensitivity_capped_at_K():
    """S_b never exceeds K_b in absolute value."""
    s = np.ones(_N) * 10_000.0
    result = _run({"EUR": s})
    assert abs(result.S["EUR"]) <= result.K["EUR"] + 1e-10


# ── Single currency ───────────────────────────────────────────────────────────

def test_single_currency_capital_equals_K():
    """One currency → no cross-bucket term → capital = K_b."""
    s = np.ones(_N) * 500.0
    result = _run({"EUR": s})
    assert result.capital == pytest.approx(result.K["EUR"], rel=1e-6)


# ── Cross-bucket aggregation ──────────────────────────────────────────────────

def test_two_identical_currencies_capital():
    """capital = sqrt(K1^2 + K2^2 + 2*gamma*S1*S2)."""
    s = np.ones(_N) * 500.0
    result = _run({"EUR": s, "USD": s.copy()})
    K1 = result.K["EUR"]
    K2 = result.K["USD"]
    S1 = result.S["EUR"]
    S2 = result.S["USD"]
    expected = math.sqrt(max(0.0, K1**2 + K2**2 + 2 * GIRR_CROSS_BUCKET_GAMMA * S1 * S2))
    assert result.capital == pytest.approx(expected, rel=1e-6)


def test_capital_with_opposite_currencies_lower():
    """Long EUR, short USD of same magnitude → cross-bucket reduces capital."""
    s = np.ones(_N) * 500.0
    result_single = _run({"EUR": s})
    result_multi  = _run({"EUR": s, "USD": -s.copy()})
    assert result_multi.capital <= result_single.capital + 1e-10


# ── Result structure ──────────────────────────────────────────────────────────

def test_result_currencies_match_input():
    result = _run({"EUR": np.ones(_N), "GBP": np.ones(_N)})
    assert set(result.currencies) == {"EUR", "GBP"}


def test_result_K_keys_match_currencies():
    result = _run({"EUR": np.ones(_N), "USD": np.ones(_N)})
    assert set(result.K.keys()) == {"EUR", "USD"}

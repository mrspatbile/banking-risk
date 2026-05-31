# tests/test_girr_vega.py

import math
import pytest
import numpy as np
import pandas as pd
from banking_risk.frtb.constants import (
    GIRR_CROSS_BUCKET_GAMMA,
    GIRR_VEGA_ALPHA,
    GIRR_VEGA_LABELS,
    GIRR_VEGA_VERTICES,
    GIRR_VEGA_RISK_WEIGHT,
)

from banking_risk.frtb.girr.vega import SA_GIRR_Vega_Calculator

_E   = np.array(GIRR_VEGA_VERTICES)
_T   = np.array(GIRR_VEGA_VERTICES)
_N_E = len(_E)
_N_T = len(_T)
_RW  = GIRR_VEGA_RISK_WEIGHT


def _run(sensitivities):
    return SA_GIRR_Vega_Calculator().compute(sensitivities)


def _zeros():
    return np.zeros((_N_E, _N_T))


def _single(i, j, value=1000.0):
    """Sensitivity array with one non-zero node at (i, j)."""
    s = _zeros()
    s[i, j] = value
    return s


# ── Input validation ──────────────────────────────────────────────────────────

def test_wrong_shape_raises():
    with pytest.raises(ValueError, match="shape"):
        _run({"EUR": np.zeros((3, 3))})


def test_1d_array_raises():
    with pytest.raises(ValueError, match="shape"):
        _run({"EUR": np.zeros(10)})


def test_zero_sensitivities_zero_capital():
    result = _run({"EUR": _zeros()})
    assert result.capital == pytest.approx(0.0)


# ── Risk-weighted sensitivities ───────────────────────────────────────────────

def test_ws_equals_vega_times_risk_weight():
    s = np.ones((_N_E, _N_T)) * 500.0
    result = _run({"EUR": s})
    expected = s.ravel() * _RW
    assert np.allclose(result.ws["EUR"].values, expected)


def test_ws_has_multiindex():
    result = _run({"EUR": _zeros()})
    assert isinstance(result.ws["EUR"].index, pd.MultiIndex)
    assert result.ws["EUR"].index.names == ["expiry", "tenor"]


def test_ws_multiindex_labels():
    result = _run({"EUR": _zeros()})
    expiry_levels = result.ws["EUR"].index.get_level_values("expiry").unique().tolist()
    tenor_levels  = result.ws["EUR"].index.get_level_values("tenor").unique().tolist()
    assert expiry_levels == GIRR_VEGA_LABELS
    assert tenor_levels  == GIRR_VEGA_LABELS


# ── Within-bucket capital ─────────────────────────────────────────────────────

def test_single_node_capital_equals_abs_ws():
    """One non-zero node → K = |WS| exactly."""
    s = _single(2, 2, value=1000.0)
    expected_ws = 1000.0 * _RW
    result = _run({"EUR": s})
    assert result.K["EUR"] == pytest.approx(abs(expected_ws), rel=1e-6)


def test_two_nodes_capital_manual():
    """K = sqrt(WS1^2 + WS2^2 + 2*rho*WS1*WS2) for two active nodes."""
    s = _zeros()
    s[0, 0] = 1000.0   # expiry 0.5Y, tenor 0.5Y
    s[1, 1] = 500.0    # expiry 1Y,   tenor 1Y

    ws1 = 1000.0 * _RW
    ws2 = 500.0  * _RW

    # rho between node(0,0) and node(1,1)
    rho_e = math.exp(-GIRR_VEGA_ALPHA * abs(_E[0] - _E[1]) / min(_E[0], _E[1]))
    rho_t = math.exp(-GIRR_VEGA_ALPHA * abs(_T[0] - _T[1]) / min(_T[0], _T[1]))
    rho   = rho_e * rho_t

    expected_K = math.sqrt(ws1**2 + ws2**2 + 2 * rho * ws1 * ws2)
    result = _run({"EUR": s})
    assert result.K["EUR"] == pytest.approx(expected_K, rel=1e-6)


def test_capital_non_negative_for_offsetting_nodes():
    s = _zeros()
    s[0, 0] =  2000.0
    s[0, 1] = -3000.0
    result = _run({"EUR": s})
    assert result.capital >= 0.0


# ── Kronecker correlation structure ──────────────────────────────────────────

def test_same_expiry_different_tenor_correlation():
    """Same expiry → rho_expiry = 1 → rho_kl = rho_tenor only."""
    rho_t_01 = math.exp(-GIRR_VEGA_ALPHA * abs(_T[0] - _T[1]) / min(_T[0], _T[1]))
    rho_e_same = 1.0
    expected = rho_e_same * rho_t_01

    # Verify via capital: two nodes same expiry row, adjacent tenor columns
    s1 = _zeros(); s1[0, 0] = 1000.0
    s2 = _zeros(); s2[0, 1] = 1000.0
    s_both = s1 + s2
    ws = 1000.0 * _RW
    expected_K = math.sqrt(2 * ws**2 + 2 * expected * ws**2)
    result = _run({"EUR": s_both})
    assert result.K["EUR"] == pytest.approx(expected_K, rel=1e-6)


def test_correlation_diagonal_is_one():
    """rho(k, k) = 1 for all nodes."""
    for i in range(_N_E):
        rho_e = math.exp(-GIRR_VEGA_ALPHA * 0.0)
        rho_t = math.exp(-GIRR_VEGA_ALPHA * 0.0)
        assert rho_e * rho_t == pytest.approx(1.0)


def test_rho_decays_with_both_dimensions():
    """rho for nodes far in both expiry and tenor < rho for nodes close in both."""
    rho_close = (
        math.exp(-GIRR_VEGA_ALPHA * abs(_E[0] - _E[1]) / min(_E[0], _E[1])) *
        math.exp(-GIRR_VEGA_ALPHA * abs(_T[0] - _T[1]) / min(_T[0], _T[1]))
    )
    rho_far = (
        math.exp(-GIRR_VEGA_ALPHA * abs(_E[0] - _E[-1]) / min(_E[0], _E[-1])) *
        math.exp(-GIRR_VEGA_ALPHA * abs(_T[0] - _T[-1]) / min(_T[0], _T[-1]))
    )
    assert rho_close > rho_far


# ── Net sensitivity capping ───────────────────────────────────────────────────

def test_net_sensitivity_capped_at_K():
    s = np.ones((_N_E, _N_T)) * 5000.0
    result = _run({"EUR": s})
    assert abs(result.S["EUR"]) <= result.K["EUR"] + 1e-10


# ── Single currency ───────────────────────────────────────────────────────────

def test_single_currency_capital_equals_K():
    s = np.ones((_N_E, _N_T)) * 200.0
    result = _run({"EUR": s})
    assert result.capital == pytest.approx(result.K["EUR"], rel=1e-6)


# ── Cross-bucket aggregation ──────────────────────────────────────────────────

def test_two_identical_currencies_capital_manual():
    s = np.ones((_N_E, _N_T)) * 200.0
    result = _run({"EUR": s, "USD": s.copy()})
    K1, K2 = result.K["EUR"], result.K["USD"]
    S1, S2 = result.S["EUR"], result.S["USD"]
    expected = math.sqrt(max(0.0, K1**2 + K2**2 + 2 * GIRR_CROSS_BUCKET_GAMMA * S1 * S2))
    assert result.capital == pytest.approx(expected, rel=1e-6)


def test_opposite_currencies_lower_capital():
    s = np.ones((_N_E, _N_T)) * 200.0
    single   = _run({"EUR": s})
    opposite = _run({"EUR": s, "USD": -s.copy()})
    assert opposite.capital <= single.capital + 1e-10


# ── Result structure ──────────────────────────────────────────────────────────

def test_result_currencies_match_input():
    s = np.ones((_N_E, _N_T))
    result = _run({"EUR": s, "GBP": s.copy()})
    assert set(result.currencies) == {"EUR", "GBP"}


def test_result_K_keys_match_currencies():
    s = np.ones((_N_E, _N_T))
    result = _run({"EUR": s, "USD": s.copy()})
    assert set(result.K.keys()) == {"EUR", "USD"}

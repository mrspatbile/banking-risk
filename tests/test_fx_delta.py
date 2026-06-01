import math
import numpy as np
import pytest
from banking_risk.frtb.fx.delta import SA_FX_Delta_Calculator
from banking_risk.frtb.constants import FX_RISK_WEIGHT, FX_CORRELATION_RHO

_CALC = SA_FX_Delta_Calculator()


def test_zero_sensitivity_zero_capital():
    result = _CALC.compute({"EURUSD": 0.0})
    assert result.capital == pytest.approx(0.0)


def test_single_pair_capital_equals_rw_times_sensitivity():
    result = _CALC.compute({"EURUSD": 100.0})
    assert result.capital == pytest.approx(abs(100.0 * FX_RISK_WEIGHT), rel=1e-9)


def test_ws_equals_sensitivity_times_rw():
    result = _CALC.compute({"EURUSD": 200.0})
    assert result.ws["EURUSD"] == pytest.approx(200.0 * FX_RISK_WEIGHT, rel=1e-9)


def test_two_pairs_same_sign_capital():
    # K = RW × sqrt(s1² + s2² + 2×ρ×s1×s2) — both positive, so cross-term adds
    s1, s2 = 100.0, 100.0
    result = _CALC.compute({"EURUSD": s1, "GBPUSD": s2})
    ws1 = s1 * FX_RISK_WEIGHT
    ws2 = s2 * FX_RISK_WEIGHT
    expected = math.sqrt(ws1**2 + ws2**2 + 2 * FX_CORRELATION_RHO * ws1 * ws2)
    assert result.capital == pytest.approx(expected, rel=1e-6)


def test_two_pairs_opposite_sign_partial_cancel():
    s1, s2 = 100.0, -100.0
    result = _CALC.compute({"EURUSD": s1, "GBPUSD": s2})
    ws1 = s1 * FX_RISK_WEIGHT
    ws2 = s2 * FX_RISK_WEIGHT
    expected = math.sqrt(ws1**2 + ws2**2 + 2 * FX_CORRELATION_RHO * ws1 * ws2)
    assert result.capital == pytest.approx(expected, rel=1e-6)


def test_empty_input_zero_capital():
    result = _CALC.compute({})
    assert result.capital == pytest.approx(0.0)
    assert result.pairs == []


def test_capital_scales_with_magnitude():
    r1 = _CALC.compute({"EURUSD": 100.0})
    r2 = _CALC.compute({"EURUSD": 200.0})
    assert r2.capital == pytest.approx(2 * r1.capital, rel=1e-9)


def test_pairs_sorted():
    result = _CALC.compute({"USDJPY": 10.0, "EURUSD": 20.0})
    assert result.pairs == sorted(result.pairs)


def test_to_table_has_ws_column():
    result = _CALC.compute({"EURUSD": 100.0})
    table  = result.to_table()
    assert "ws" in table.columns

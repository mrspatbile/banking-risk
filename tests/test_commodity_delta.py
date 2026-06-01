import numpy as np
import pytest
from banking_risk.frtb.commodity.delta import SA_Commodity_Delta_Calculator
from banking_risk.frtb.constants import COMMODITY_RISK_WEIGHTS, COMMODITY_RHO_INTRA

_CALC = SA_Commodity_Delta_Calculator()
_N    = 7  # commodity tenor vertices


def _sens(bucket: int, val: float = 1.0) -> dict[int, np.ndarray]:
    return {bucket: np.full(_N, val)}


def test_zero_sensitivity_zero_capital():
    result = _CALC.compute({1: np.zeros(_N)})
    assert result.capital == pytest.approx(0.0)


def test_capital_positive_for_nonzero():
    result = _CALC.compute(_sens(2, 100.0))
    assert result.capital > 0.0


def test_K_scales_with_risk_weight():
    # Bucket 2 (oil, RW=35%) vs bucket 7 (precious metals, RW=20%)
    r2 = _CALC.compute(_sens(2, 100.0))
    r7 = _CALC.compute(_sens(7, 100.0))
    assert r2.K[2] > r7.K[7]


def test_single_bucket_capital_equals_K():
    result = _CALC.compute(_sens(5, 80.0))
    assert result.capital == pytest.approx(result.K[5], rel=1e-9)


def test_equicorrelation_formula():
    # K_b = sqrt((1-ρ) Σ WS² + ρ (Σ WS)²)
    b  = 2                          # oil: RW=35%, ρ=0.95
    rw = COMMODITY_RISK_WEIGHTS[1]  # 0.35
    rh = COMMODITY_RHO_INTRA[1]     # 0.95
    s  = np.ones(_N) * 100.0
    ws = s * rw
    expected = float(np.sqrt((1 - rh) * (ws ** 2).sum() + rh * ws.sum() ** 2))
    result = _CALC.compute({b: s})
    assert result.K[b] == pytest.approx(expected, rel=1e-6)


def test_cross_bucket_increases_capital():
    r1 = _CALC.compute(_sens(1, 100.0))
    r2 = _CALC.compute(_sens(5, 100.0))
    r12 = _CALC.compute({1: np.full(_N, 100.0), 5: np.full(_N, 100.0)})
    import math
    naive = math.sqrt(r1.K[1]**2 + r2.K[5]**2)
    assert r12.capital >= naive


def test_invalid_bucket_raises():
    with pytest.raises(ValueError):
        _CALC.compute({12: np.zeros(_N)})


def test_wrong_array_length_raises():
    with pytest.raises(ValueError):
        _CALC.compute({1: np.zeros(5)})


def test_to_table_has_expected_structure():
    result = _CALC.compute(_sens(1, 10.0))
    table  = result.to_table()
    assert "K" in table.columns
    assert "desc" in table.columns

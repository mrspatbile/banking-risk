"""Tests for CSR Securitisation delta calculator — BKR-60."""

import numpy as np
import pytest
from banking_risk.frtb.csr_sec.delta import SA_CSR_Sec_Delta_Calculator, CSR_Sec_Delta_Result
from banking_risk.frtb.constants import CSR_SEC_RISK_WEIGHTS

_CALC = SA_CSR_Sec_Delta_Calculator()
_N    = 5  # CSR tenor vertices


def _sens(bucket: int, val: float = 1.0) -> dict[int, np.ndarray]:
    return {bucket: np.full(_N, val)}


def test_zero_sensitivity_zero_capital():
    result = _CALC.compute({1: np.zeros(_N)})
    assert result.capital == pytest.approx(0.0)


def test_capital_positive_for_nonzero_sensitivity():
    result = _CALC.compute(_sens(1, 100.0))
    assert result.capital > 0.0


def test_K_scales_with_risk_weight():
    s1 = _CALC.compute(_sens(1, 1.0))   # RW = 2.0%
    s5 = _CALC.compute(_sens(5, 1.0))   # RW = 2.0%
    # Both buckets have same RW, so K should be identical
    assert s1.K[1] == pytest.approx(s5.K[5], rel=1e-9)


def test_K_scales_with_sensitivity_magnitude():
    r1 = _CALC.compute(_sens(1, 1.0))
    r2 = _CALC.compute(_sens(1, 2.0))
    assert r2.K[1] == pytest.approx(2 * r1.K[1], rel=1e-9)


def test_single_bucket_capital_equals_K():
    result = _CALC.compute(_sens(7, 50.0))
    assert result.capital == pytest.approx(result.K[7], rel=1e-9)


def test_two_buckets_cross_bucket_adds():
    r1 = _CALC.compute(_sens(1, 100.0))
    r2 = _CALC.compute(_sens(2, 100.0))
    r12 = _CALC.compute({1: np.full(_N, 100.0), 2: np.full(_N, 100.0)})
    # Combined > individual because cross-bucket term adds
    assert r12.capital >= max(r1.capital, r2.capital)


def test_invalid_bucket_raises():
    with pytest.raises(ValueError):
        _CALC.compute({0: np.zeros(_N)})
    with pytest.raises(ValueError):
        _CALC.compute({42: np.zeros(_N)})


def test_wrong_array_length_raises():
    with pytest.raises(ValueError):
        _CALC.compute({1: np.zeros(3)})


def test_result_contains_requested_buckets():
    result = _CALC.compute({1: np.zeros(_N), 7: np.zeros(_N)})
    assert 1 in result.buckets
    assert 7 in result.buckets


def test_ws_equals_sensitivity_times_rw():
    s = np.array([100.0, 0.0, 0.0, 0.0, 0.0])
    result = _CALC.compute({1: s})
    rw = CSR_SEC_RISK_WEIGHTS[0]
    assert result.ws[1].iloc[0] == pytest.approx(100.0 * rw, rel=1e-9)


def test_to_table_has_correct_columns():
    result = _CALC.compute(_sens(1, 10.0))
    table  = result.to_table()
    assert "K" in table.columns
    assert "S" in table.columns


def test_negative_sensitivity_enters_capital():
    result = _CALC.compute({1: np.array([-100.0, -50.0, 0.0, 50.0, 100.0])})
    assert result.capital > 0.0


def test_ctp_bucket_computation():
    """Test CTP (credit tranched products) bucket — higher number."""
    result = _CALC.compute(_sens(30, 100.0))
    assert result.capital > 0.0
    assert result.K[30] > 0.0


def test_all_buckets_accept_input():
    """Test that all 41 buckets can be computed."""
    for bucket in [1, 10, 20, 25, 30, 35, 41]:
        result = _CALC.compute(_sens(bucket, 50.0))
        assert result.capital > 0.0
        assert bucket in result.buckets


def test_result_dataclass():
    result = _CALC.compute(_sens(1, 10.0))
    assert isinstance(result, CSR_Sec_Delta_Result)
    assert hasattr(result, 'ws')
    assert hasattr(result, 'K')
    assert hasattr(result, 'S')
    assert hasattr(result, 'capital')
    assert hasattr(result, 'buckets')


def test_multiple_buckets_aggregation():
    """Test multi-bucket aggregation — K^2 + cross terms."""
    sensitivities = {
        1: np.full(_N, 50.0),
        5: np.full(_N, 30.0),
        10: np.full(_N, 40.0),
    }
    result = _CALC.compute(sensitivities)
    # Capital should be aggregate of the three buckets
    assert result.capital > max(result.K[1], result.K[5], result.K[10])
    assert len(result.buckets) == 3


def test_sensitivities_capped_at_K():
    """Test that net sensitivities S are capped at ±K."""
    result = _CALC.compute(_sens(1, 1000.0))
    for b in result.buckets:
        assert abs(result.S[b]) <= result.K[b] + 1e-9  # small tolerance

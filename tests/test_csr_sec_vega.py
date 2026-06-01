"""Tests for CSR Securitisation vega calculator — BKR-60."""

import numpy as np
import pytest
from banking_risk.frtb.csr_sec.vega import SA_CSR_Sec_Vega_Calculator, CSR_Sec_Vega_Result


_CALC = SA_CSR_Sec_Vega_Calculator()
_N_E  = 5  # vega expiry vertices
_N_T  = 5  # CSR tenor vertices


def _vega_grid(bucket: int, val: float = 1.0) -> dict[int, np.ndarray]:
    return {bucket: np.full((_N_E, _N_T), val)}


def test_zero_vega_zero_capital():
    result = _CALC.compute({1: np.zeros((_N_E, _N_T))})
    assert result.capital == pytest.approx(0.0)


def test_capital_positive_for_nonzero_vega():
    result = _CALC.compute(_vega_grid(1, 100.0))
    assert result.capital > 0.0


def test_single_bucket_capital_equals_K():
    result = _CALC.compute(_vega_grid(1, 50.0))
    assert result.capital == pytest.approx(result.K[1], rel=1e-9)


def test_invalid_shape_raises():
    with pytest.raises(ValueError):
        _CALC.compute({1: np.zeros((3, 3))})
    with pytest.raises(ValueError):
        _CALC.compute({1: np.zeros(_N_E)})


def test_negative_vega_enters_capital():
    grid = np.ones((_N_E, _N_T))
    grid[0, 0] = -100.0
    result = _CALC.compute({1: grid})
    assert result.capital > 0.0


def test_vega_K_scales_with_magnitude():
    r1 = _CALC.compute(_vega_grid(1, 10.0))
    r2 = _CALC.compute(_vega_grid(1, 20.0))
    assert r2.K[1] == pytest.approx(2 * r1.K[1], rel=1e-9)


def test_two_buckets_cross_bucket_adds():
    r1 = _CALC.compute(_vega_grid(1, 50.0))
    r2 = _CALC.compute(_vega_grid(5, 50.0))
    r12 = _CALC.compute({
        1: np.full((_N_E, _N_T), 50.0),
        5: np.full((_N_E, _N_T), 50.0),
    })
    # Combined > individual because cross-bucket term adds
    assert r12.capital >= max(r1.capital, r2.capital)


def test_result_dataclass():
    result = _CALC.compute(_vega_grid(1, 10.0))
    assert isinstance(result, CSR_Sec_Vega_Result)
    assert hasattr(result, 'ws')
    assert hasattr(result, 'K')
    assert hasattr(result, 'S')
    assert hasattr(result, 'capital')
    assert hasattr(result, 'buckets')


def test_to_table_has_correct_columns():
    result = _CALC.compute(_vega_grid(1, 10.0))
    table = result.to_table()
    assert "K" in table.columns
    assert "S" in table.columns


def test_ctp_bucket_vega():
    """Test CTP bucket vega — higher bucket number."""
    result = _CALC.compute(_vega_grid(30, 100.0))
    assert result.capital > 0.0
    assert result.K[30] > 0.0


def test_all_bucket_types():
    """Test different bucket types: non-CTP and CTP."""
    for bucket in [1, 10, 25, 26, 35, 41]:
        result = _CALC.compute(_vega_grid(bucket, 50.0))
        assert result.capital > 0.0
        assert bucket in result.buckets


def test_vega_sensitivities_capped():
    """Test that net vega sensitivities S are capped at ±K."""
    result = _CALC.compute(_vega_grid(1, 1000.0))
    for b in result.buckets:
        assert abs(result.S[b]) <= result.K[b] + 1e-9


def test_multiindex_ws():
    """Test that ws Series has MultiIndex for expiry × tenor."""
    result = _CALC.compute(_vega_grid(1, 100.0))
    ws_series = result.ws[1]
    assert isinstance(ws_series.index, type(ws_series.index))
    # Should have (expiry, tenor) multi-level index
    assert ws_series.index.nlevels == 2

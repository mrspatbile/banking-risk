"""Tests for CSR Securitisation curvature calculator — BKR-60."""

import numpy as np
import pytest
from banking_risk.frtb.csr_sec.curvature import (
    SA_CSR_Sec_Curvature_Calculator,
    CSR_Sec_Curvature_Result,
    curvature_pnl_from_greeks,
)


_CALC = SA_CSR_Sec_Curvature_Calculator()


def test_zero_cvr_zero_capital():
    result = _CALC.compute({1: 0.0}, {1: 0.0})
    assert result.capital == pytest.approx(0.0)


def test_positive_cvr_enters_capital():
    result = _CALC.compute({1: 100.0}, {1: -50.0})
    assert result.capital > 0.0


def test_capital_from_worst_of_up_down():
    """Capital uses max(CVR^+, CVR^-, 0)."""
    result = _CALC.compute({1: 100.0}, {1: -80.0})
    # Max is 100, so K[1] = 100
    assert result.K[1] == pytest.approx(100.0, rel=1e-9)


def test_mismatched_keys_raises():
    with pytest.raises(ValueError):
        _CALC.compute({1: 50.0, 2: 50.0}, {1: 50.0})


def test_single_bucket_capital_equals_K():
    result = _CALC.compute({1: 50.0}, {1: 40.0})
    assert result.capital == pytest.approx(result.K[1], rel=1e-9)


def test_two_buckets_cross_bucket_adds():
    r1 = _CALC.compute({1: 50.0}, {1: 40.0})
    r2 = _CALC.compute({2: 50.0}, {2: 40.0})
    r12 = _CALC.compute({1: 50.0, 2: 50.0}, {1: 40.0, 2: 40.0})
    # Combined should be > individual (cross-bucket adds)
    assert r12.capital >= max(r1.capital, r2.capital)


def test_result_dataclass():
    result = _CALC.compute({1: 30.0}, {1: 20.0})
    assert isinstance(result, CSR_Sec_Curvature_Result)
    assert hasattr(result, 'cvr_up')
    assert hasattr(result, 'cvr_down')
    assert hasattr(result, 'K')
    assert hasattr(result, 'S')
    assert hasattr(result, 'capital')
    assert hasattr(result, 'buckets')


def test_to_table():
    result = _CALC.compute({1: 30.0, 5: 50.0}, {1: 20.0, 5: 40.0})
    table = result.to_table()
    assert "cvr_up" in table.columns
    assert "cvr_down" in table.columns
    assert "K" in table.columns


def test_multiple_buckets():
    sensitivities = {1: 30.0, 5: 50.0, 10: 40.0}
    result = _CALC.compute(sensitivities, sensitivities)
    assert len(result.buckets) == 3
    assert result.capital > 0.0


def test_ctp_bucket_curvature():
    """Test CTP bucket curvature — bucket 30 (CTP bespoke senior)."""
    result = _CALC.compute({30: 100.0}, {30: 80.0})
    assert result.capital > 0.0
    assert result.K[30] == pytest.approx(100.0, rel=1e-9)


def test_all_bucket_types():
    """Test non-CTP and CTP buckets."""
    for bucket in [1, 10, 25, 26, 35, 41]:
        result = _CALC.compute({bucket: 50.0}, {bucket: 40.0})
        assert result.capital > 0.0
        assert bucket in result.buckets


def test_curvature_pnl_from_greeks_basic():
    """Test the standalone curvature P&L approximation."""
    delta = np.zeros(5)
    gamma = np.ones(5)
    cvr_up, cvr_dn = curvature_pnl_from_greeks(delta, gamma, bucket=1)
    # Bucket 1 has RW = 0.020
    # CVR ≈ -0.5 * sum(gamma * RW^2) = -0.5 * 5 * 0.020^2 = -0.001
    expected = -0.5 * 5 * (0.020 ** 2)
    assert cvr_up == pytest.approx(expected, rel=1e-9)
    assert cvr_dn == pytest.approx(expected, rel=1e-9)


def test_curvature_pnl_override_rw():
    """Test curvature P&L with risk weight override."""
    delta = np.zeros(5)
    gamma = np.ones(5)
    cvr_up, cvr_dn = curvature_pnl_from_greeks(
        delta, gamma, bucket=1, risk_weight=0.050
    )
    expected = -0.5 * 5 * (0.050 ** 2)
    assert cvr_up == pytest.approx(expected, rel=1e-9)


def test_curvature_pnl_gamma_scale():
    """Test that curvature scales linearly with gamma."""
    delta = np.zeros(5)
    gamma1 = np.ones(5)
    gamma2 = np.ones(5) * 2.0

    cvr1_up, _ = curvature_pnl_from_greeks(delta, gamma1, bucket=1)
    cvr2_up, _ = curvature_pnl_from_greeks(delta, gamma2, bucket=1)

    assert cvr2_up == pytest.approx(2 * cvr1_up, rel=1e-9)


def test_curvature_pnl_invalid_lengths():
    """Test that invalid array lengths raise."""
    with pytest.raises(ValueError):
        curvature_pnl_from_greeks(np.zeros(3), np.ones(5), bucket=1)
    with pytest.raises(ValueError):
        curvature_pnl_from_greeks(np.zeros(5), np.ones(3), bucket=1)

"""Tests for Standardised Measurement Approach (SMA) — BKR-63."""

import pytest
from banking_risk.operational_risk.sma import SMA_Calculator, BI_Components


def test_sma_bucket_1():
    bi_comps = BI_Components(ildc=200_000_000.0, sc=50_000_000.0, fc=30_000_000.0)
    # BI = 280M, bucket 1 (≤ 1B), alpha = 12%
    calc = SMA_Calculator()
    result = calc.compute(bi_comps, loss_component=0)

    assert result.bi == pytest.approx(280_000_000.0)
    assert result.bi_bucket == 1
    assert result.alpha == 0.12
    assert result.bic == pytest.approx(33_600_000.0)
    assert result.ilm == pytest.approx(1.0)  # No loss data
    assert result.capital == pytest.approx(33_600_000.0)


def test_sma_bucket_2():
    bi_comps = BI_Components(ildc=5_000_000_000.0, sc=2_000_000_000.0, fc=1_000_000_000.0)
    # BI = 8B, bucket 2 (1–30B), alpha = 15%
    calc = SMA_Calculator()
    result = calc.compute(bi_comps, loss_component=0)

    assert result.bi == pytest.approx(8_000_000_000.0)
    assert result.bi_bucket == 2
    assert result.alpha == 0.15
    assert result.bic == pytest.approx(1_200_000_000.0)


def test_sma_bucket_3():
    bi_comps = BI_Components(ildc=50_000_000_000.0, sc=20_000_000_000.0, fc=10_000_000_000.0)
    # BI = 80B, bucket 3 (> 30B), alpha = 18%
    calc = SMA_Calculator()
    result = calc.compute(bi_comps, loss_component=0)

    assert result.bi == pytest.approx(80_000_000_000.0)
    assert result.bi_bucket == 3
    assert result.alpha == 0.18


def test_sma_with_loss_component():
    bi_comps = BI_Components(ildc=500_000_000.0, sc=100_000_000.0, fc=50_000_000.0)
    # BI = 650M, alpha = 12%, BIC = 78M
    # With high loss component relative to BIC
    calc = SMA_Calculator()
    result = calc.compute(bi_comps, loss_component=500_000_000.0)  # Very high losses

    assert result.bic == pytest.approx(78_000_000.0)
    assert result.ilm > 1.0  # High losses should increase multiplier
    assert result.capital > 78_000_000.0

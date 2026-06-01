"""Tests for leverage ratio — BKR-66."""

import pytest
from banking_risk.capital.leverage_ratio import (
    Leverage_Ratio_Calculator, Leverage_Exposure
)


def test_leverage_ratio_compliant():
    exposure = Leverage_Exposure(
        on_balance_sheet=1_000_000_000.0,
        derivative_exposure=50_000_000.0,
        sft_exposure=0.0,
        off_balance_sheet=100_000_000.0,
    )
    calc = Leverage_Ratio_Calculator()
    result = calc.compute(
        tier1_capital=50_000_000.0,
        exposure=exposure,
        gsii_buffer=0.0,
    )

    total_exposure = 1_000_000_000 + 50_000_000 + 100_000_000
    expected_ratio = 50_000_000 / total_exposure
    assert result.leverage_ratio == pytest.approx(expected_ratio)
    assert result.is_compliant
    assert result.minimum_required == pytest.approx(0.03)


def test_leverage_ratio_non_compliant():
    exposure = Leverage_Exposure(
        on_balance_sheet=2_000_000_000.0,
        derivative_exposure=100_000_000.0,
        sft_exposure=0.0,
        off_balance_sheet=200_000_000.0,
    )
    calc = Leverage_Ratio_Calculator()
    result = calc.compute(
        tier1_capital=50_000_000.0,
        exposure=exposure,
    )

    # Leverage = 50M / 2300M ≈ 2.17% < 3%
    assert not result.is_compliant
    assert result.headroom_bps < 0


def test_leverage_ratio_with_gsii():
    exposure = Leverage_Exposure(
        on_balance_sheet=1_000_000_000.0,
    )
    calc = Leverage_Ratio_Calculator()
    result = calc.compute(
        tier1_capital=50_000_000.0,
        exposure=exposure,
        gsii_buffer=0.035,  # 3.5% G-SII buffer
    )

    # Minimum = 3% + 50% × 3.5% = 3% + 1.75% = 4.75%
    assert result.minimum_required == pytest.approx(0.03 + 0.5 * 0.035)


def test_leverage_ratio_zero_exposure():
    exposure = Leverage_Exposure(on_balance_sheet=0.0)
    calc = Leverage_Ratio_Calculator()
    result = calc.compute(
        tier1_capital=50_000_000.0,
        exposure=exposure,
    )

    assert result.leverage_ratio == pytest.approx(0.0)
    assert not result.is_compliant

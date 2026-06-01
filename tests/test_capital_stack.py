"""Tests for regulatory capital stack and MDA — BKR-64."""

import pytest
from banking_risk.capital.stack import Capital_Stack_Builder


def test_capital_stack_fully_compliant():
    stack = Capital_Stack_Builder.from_components(
        cet1=100_000_000.0,  # Higher capital
        tier1=120_000_000.0,
        tier2=80_000_000.0,
        frtb_rwa=500_000_000.0,
        credit_rwa=300_000_000.0,
        oprisk_rwa=100_000_000.0,
    )

    assert stack.total_rwa == pytest.approx(900_000_000.0)
    assert stack.total_capital == pytest.approx(300_000_000.0)
    assert stack.cet1_ratio == pytest.approx(100_000_000 / 900_000_000)
    assert not stack.is_under_mda  # 11.1% CET1 > 7.25% MDA


def test_capital_stack_mda_breach():
    stack = Capital_Stack_Builder.from_components(
        cet1=30_000_000.0,  # Low
        tier1=40_000_000.0,
        tier2=20_000_000.0,
        frtb_rwa=500_000_000.0,
        credit_rwa=300_000_000.0,
        oprisk_rwa=100_000_000.0,
        ccb=0.025,
        ccyb=0.0,
    )

    # CET1 ratio = 30M / 900M = 3.33%
    # MDA = 4.5% + 2.5% = 7%, so in breach
    assert stack.is_under_mda
    assert stack.mda_headroom_bps < 0


def test_capital_stack_gsii_surcharge():
    stack = Capital_Stack_Builder.from_components(
        cet1=100_000_000.0,
        tier1=120_000_000.0,
        tier2=80_000_000.0,
        frtb_rwa=500_000_000.0,
        credit_rwa=300_000_000.0,
        oprisk_rwa=100_000_000.0,
        ccb=0.025,
        ccyb=0.01,
        gsii_buffer=0.035,  # 3.5% G-SII
    )

    # MDA = 4.5% (min) + 2.5% (CCB) + 1.0% (CCyB) + 1.75% (50% of 3.5% GSII) = 9.75%
    expected_mda = 0.045 + 0.025 + 0.01 + (0.035 * 0.5)
    assert stack.mda_trigger == pytest.approx(expected_mda)


def test_capital_stack_zero_rwa():
    stack = Capital_Stack_Builder.from_components(
        cet1=10_000_000.0,
        tier1=10_000_000.0,
        tier2=5_000_000.0,
        frtb_rwa=0.0,
        credit_rwa=0.0,
        oprisk_rwa=0.0,
    )

    assert stack.total_rwa == pytest.approx(0.0)
    assert stack.cet1_ratio == pytest.approx(0.0)

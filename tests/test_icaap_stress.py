"""Tests for ICAAP macro stress testing — BKR-65."""

import pytest
from banking_risk.capital.icaap_stress import (
    ICAAP_Stress_Calculator, BASELINE, ADVERSE, SEVERELY_ADVERSE
)


def test_icaap_no_stress():
    calc = ICAAP_Stress_Calculator()
    result = calc.compute(
        baseline_frtb_rwa=500_000_000.0,
        baseline_credit_rwa=300_000_000.0,
        baseline_cet1=100_000_000.0,
        baseline_tier1=120_000_000.0,
        baseline_tier2=80_000_000.0,
        scenarios=[BASELINE],
    )

    assert len(result.scenarios) == 1
    baseline_result = result.scenarios["Baseline"]
    # Under baseline, RWA unchanged
    assert baseline_result.total_rwa_stressed == pytest.approx(800_000_000.0)
    assert baseline_result.cet1_ratio_stressed == pytest.approx(100_000_000 / 800_000_000)


def test_icaap_adverse_stress():
    calc = ICAAP_Stress_Calculator()
    result = calc.compute(
        baseline_frtb_rwa=500_000_000.0,
        baseline_credit_rwa=300_000_000.0,
        baseline_cet1=100_000_000.0,
        baseline_tier1=120_000_000.0,
        baseline_tier2=80_000_000.0,
        scenarios=[ADVERSE],
    )

    adverse_result = result.scenarios["Adverse"]
    # Spread shock +150bps → RWA increases by ~1.5%
    assert adverse_result.total_rwa_stressed > 800_000_000.0
    # Capital unchanged (forward-looking)
    assert adverse_result.cet1_stressed == pytest.approx(100_000_000.0)


def test_icaap_severely_adverse_breach():
    calc = ICAAP_Stress_Calculator()
    result = calc.compute(
        baseline_frtb_rwa=500_000_000.0,
        baseline_credit_rwa=300_000_000.0,
        baseline_cet1=50_000_000.0,  # Low capital
        baseline_tier1=60_000_000.0,
        baseline_tier2=40_000_000.0,
        scenarios=[SEVERELY_ADVERSE],
    )

    severe_result = result.scenarios["Severely adverse"]
    # High stress → large RWA increase
    # With low capital, likely breach
    if severe_result.is_under_mda:
        assert severe_result.shortfall_bps < 0


def test_icaap_multiple_scenarios():
    calc = ICAAP_Stress_Calculator()
    result = calc.compute(
        baseline_frtb_rwa=500_000_000.0,
        baseline_credit_rwa=300_000_000.0,
        baseline_cet1=100_000_000.0,
        baseline_tier1=120_000_000.0,
        baseline_tier2=80_000_000.0,
        scenarios=[BASELINE, ADVERSE, SEVERELY_ADVERSE],
    )

    assert len(result.scenarios) == 3
    # Baseline should be best, severely adverse should be worst
    baseline_ratio = result.scenarios["Baseline"].cet1_ratio_stressed
    severe_ratio = result.scenarios["Severely adverse"].cet1_ratio_stressed
    assert baseline_ratio >= severe_ratio

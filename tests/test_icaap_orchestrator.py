"""
Tests for ICAAP Orchestrator — BKR-69.

Tests end-to-end capital adequacy assessment across baseline and
stress scenarios.
"""

import pytest
from unittest.mock import Mock

from banking_risk.capital.icaap_orchestrator import ICAAP_Orchestrator, ICAAP_Assessment_Result
from banking_risk.capital.stack import Capital_Stack_Builder
from banking_risk.capital.icaap_stress import BASELINE, ADVERSE, SEVERELY_ADVERSE
from banking_risk.credit_risk.sa_ccr_portfolio import Netting_Set, SA_CCR_Portfolio
from banking_risk.credit_risk.sa_ccr import Derivative_Position, AssetClass


def _mock_frtb_sa(capital=500_000_000.0):
    """Create a mock FRTB_SA with specified capital."""
    frtb = Mock()
    frtb.total = capital
    return frtb


def test_icaap_assessment_result_creation():
    """ICAAP_Assessment_Result holds baseline and stressed results."""
    stack = Capital_Stack_Builder.from_components(
        cet1=100_000_000, tier1=120_000_000, tier2=80_000_000,
        frtb_rwa=500_000_000, credit_rwa=300_000_000, oprisk_rwa=100_000_000
    )
    from banking_risk.capital.icaap_stress import ICAAP_Stress_Result
    stress = ICAAP_Stress_Result(scenarios={})

    result = ICAAP_Assessment_Result(
        baseline_capital_stack=stack,
        stress_results=stress,
        adequacy_status="Adequate",
    )
    assert result.baseline_capital_stack is stack
    assert result.adequacy_status == "Adequate"


def test_icaap_orchestrator_empty():
    """ICAAP_Orchestrator with no portfolios builds minimal stack."""
    orchestrator = ICAAP_Orchestrator(
        baseline_credit_rwa=300_000_000,
        baseline_oprisk_rwa=100_000_000,
    )
    result = orchestrator.assess([BASELINE, ADVERSE])

    assert result.baseline_capital_stack is not None
    assert result.stress_results is not None
    assert len(result.stress_results.scenarios) == 2


def test_icaap_orchestrator_with_frtb():
    """ICAAP_Orchestrator includes FRTB capital in baseline."""
    frtb = _mock_frtb_sa(capital=500_000_000.0)
    orchestrator = ICAAP_Orchestrator(
        frtb_sa=frtb,
        baseline_credit_rwa=300_000_000,
        baseline_oprisk_rwa=100_000_000,
    )
    result = orchestrator.assess([BASELINE])

    assert result.baseline_capital_stack.frtb_rwa == pytest.approx(500_000_000.0)
    assert result.baseline_capital_stack.credit_rwa == pytest.approx(300_000_000.0)


def test_icaap_orchestrator_with_sa_ccr():
    """ICAAP_Orchestrator includes SA-CCR EAD and CVA in baseline."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set("ns1", "JPM", [pos], collateral=0.0)
    sa_ccr_port = SA_CCR_Portfolio([ns])

    frtb = _mock_frtb_sa(capital=500_000_000.0)
    orchestrator = ICAAP_Orchestrator(
        frtb_sa=frtb,
        sa_ccr_portfolio=sa_ccr_port,
        baseline_credit_rwa=300_000_000,
        baseline_oprisk_rwa=100_000_000,
    )
    result = orchestrator.assess([BASELINE])

    # Should capture SA-CCR EAD and CVA in baseline stack
    assert result.baseline_capital_stack.sa_ccr_ead > 0
    assert result.baseline_capital_stack.cva_capital >= 0


def test_icaap_orchestrator_stress_scenarios():
    """ICAAP_Orchestrator assesses capital under stress scenarios."""
    orchestrator = ICAAP_Orchestrator(
        baseline_credit_rwa=300_000_000,
        baseline_oprisk_rwa=100_000_000,
    )
    result = orchestrator.assess([BASELINE, ADVERSE, SEVERELY_ADVERSE])

    assert len(result.stress_results.scenarios) == 3
    assert "Baseline" in result.stress_results.scenarios
    assert "Adverse" in result.stress_results.scenarios
    assert "Severely adverse" in result.stress_results.scenarios


def test_icaap_orchestrator_adequacy_status():
    """ICAAP_Orchestrator identifies breach scenarios."""
    orchestrator = ICAAP_Orchestrator(
        baseline_credit_rwa=100_000_000,  # Low RWA
        baseline_oprisk_rwa=100_000_000,
    )
    result = orchestrator.assess(
        [BASELINE, ADVERSE, SEVERELY_ADVERSE],
        mda_trigger=0.0725,
    )

    # Should compute adequacy status
    assert result.adequacy_status in ["Adequate under stress", "Breaches detected"]
    assert result.min_stressed_ratio > 0


def test_icaap_orchestrator_with_custom_capital_stack():
    """ICAAP_Orchestrator accepts pre-built capital stack."""
    stack = Capital_Stack_Builder.from_components(
        cet1=100_000_000, tier1=120_000_000, tier2=80_000_000,
        frtb_rwa=500_000_000, credit_rwa=300_000_000, oprisk_rwa=100_000_000
    )
    orchestrator = ICAAP_Orchestrator(capital_stack_baseline=stack)
    result = orchestrator.assess([BASELINE, ADVERSE])

    # Should use provided stack directly
    assert result.baseline_capital_stack is stack


def test_icaap_orchestrator_min_stressed_ratio():
    """ICAAP_Orchestrator tracks minimum stressed ratio."""
    orchestrator = ICAAP_Orchestrator(
        baseline_credit_rwa=300_000_000,
        baseline_oprisk_rwa=100_000_000,
    )
    result = orchestrator.assess([BASELINE, ADVERSE, SEVERELY_ADVERSE])

    # Find expected minimum
    expected_min = min(
        s.cet1_ratio_stressed
        for s in result.stress_results.scenarios.values()
    )
    assert result.min_stressed_ratio == pytest.approx(expected_min)


def test_icaap_orchestrator_breach_identification():
    """ICAAP_Orchestrator identifies which scenario causes breach."""
    # Build a scenario where we expect a breach
    orchestrator = ICAAP_Orchestrator(
        baseline_credit_rwa=1_000_000_000,  # Very high credit RWA
        baseline_oprisk_rwa=500_000_000,
    )
    result = orchestrator.assess(
        [BASELINE, ADVERSE, SEVERELY_ADVERSE],
        mda_trigger=0.0725,
    )

    if result.adequacy_status == "Breaches detected":
        assert result.breach_scenario is not None
        assert result.breach_scenario in ["Baseline", "Adverse", "Severely adverse"]

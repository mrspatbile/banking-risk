"""
ICAAP Orchestrator — BKR-69.

End-to-end orchestration of capital computation across multiple scenarios
for the Internal Capital Adequacy Assessment Process.

Orchestrates:
  1. Baseline capital stack from trading portfolio (FRTB), counterparty credit risk (SA-CCR/CVA)
  2. Credit risk IRB/SA
  3. Operational risk (fixed or SMA)
  4. Macro stress scenarios (adverse, severely adverse)
  5. Capital adequacy assessment and MDA trigger evaluation

Usage
-----
    from banking_risk.capital.icaap_orchestrator import ICAAP_Orchestrator
    from banking_risk.capital.icaap_stress import BASELINE, ADVERSE, SEVERELY_ADVERSE

    orchestrator = ICAAP_Orchestrator(
        frtb_sa=frtb,
        sa_ccr_portfolio=sa_ccr_port,
        baseline_credit_rwa=300_000_000,
        baseline_oprisk_rwa=100_000_000,
        capital_stack_baseline=stack_baseline,
    )

    results = orchestrator.assess(scenarios=[BASELINE, ADVERSE, SEVERELY_ADVERSE])
    print(results.adequacy_status)

References
----------
EBA/GL/2018/04 : ICAAP and ILAAP guidelines
CRR3 Art. 325 : FRTB SA
CRR3 Art. 274–276 : SA-CCR
CRR3 Art. 383a : BA-CVA
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any

import numpy as np

from banking_risk.frtb.sa import FRTB_SA
from banking_risk.credit_risk.sa_ccr_portfolio import SA_CCR_Portfolio
from banking_risk.credit_risk.cva_aggregator import CVA_Aggregator
from banking_risk.capital.stack import Capital_Stack, Capital_Stack_Builder
from banking_risk.capital.icaap_stress import (
    ICAAP_Stress_Calculator,
    ICAAP_Stress_Result,
    Scenario,
    BASELINE,
    ADVERSE,
    SEVERELY_ADVERSE,
)


@dataclass
class ICAAP_Assessment_Result:
    """End-to-end ICAAP assessment output.

    Attributes
    ----------
    baseline_capital_stack : Capital_Stack
        Baseline capital ratios under normal conditions.
    stress_results : ICAAP_Stress_Result
        Stressed capital adequacy under macro scenarios.
    adequacy_status : str
        Summary: 'Adequate' or 'Breaches detected'.
    min_stressed_ratio : float
        Minimum CET1 ratio across all stress scenarios.
    breach_scenario : Optional[str]
        Name of scenario with lowest CET1 ratio (if any breach).
    """

    baseline_capital_stack : Capital_Stack
    stress_results : ICAAP_Stress_Result
    adequacy_status : str = "Adequate"
    min_stressed_ratio : float = 0.0
    breach_scenario : Optional[str] = None


class ICAAP_Orchestrator:
    """Orchestrate end-to-end capital adequacy assessment.

    Coordinates:
      - FRTB SA capital from trading portfolio
      - SA-CCR EAD and CVA capital from derivative positions
      - Credit risk RWA (IRB/SA)
      - Operational risk RWA (SMA)
      - Capital stack assembly
      - Macro stress scenario assessment

    Parameters
    ----------
    frtb_sa : FRTB_SA
        Trading book FRTB SA orchestrator (or None).
    sa_ccr_portfolio : SA_CCR_Portfolio, optional
        Derivative portfolio for SA-CCR EAD and CVA capital.
    baseline_credit_rwa : float
        Credit risk RWA under normal conditions.
    baseline_oprisk_rwa : float
        Operational risk RWA (SMA or standardised).
    capital_stack_baseline : Capital_Stack, optional
        Pre-computed baseline capital stack. If not provided, one is
        assembled from FRTB_SA and credit/oprisk RWA.
    """

    def __init__(
        self,
        frtb_sa: Optional[FRTB_SA] = None,
        sa_ccr_portfolio: Optional[SA_CCR_Portfolio] = None,
        baseline_credit_rwa: float = 0.0,
        baseline_oprisk_rwa: float = 0.0,
        capital_stack_baseline: Optional[Capital_Stack] = None,
    ) -> None:
        self._frtb_sa = frtb_sa
        self._sa_ccr_portfolio = sa_ccr_portfolio
        self._baseline_credit_rwa = baseline_credit_rwa
        self._baseline_oprisk_rwa = baseline_oprisk_rwa
        self._capital_stack_baseline = capital_stack_baseline

    def assess(
        self,
        scenarios: list[Scenario],
        mda_trigger: float = 0.0725,
    ) -> ICAAP_Assessment_Result:
        """Run end-to-end ICAAP assessment.

        Parameters
        ----------
        scenarios : list[Scenario]
            Macro stress scenarios to apply (e.g., baseline, adverse, severe).
        mda_trigger : float
            MDA trigger level (default 7.25% = 4.5% min + 2.5% CCB).

        Returns
        -------
        ICAAP_Assessment_Result
            Baseline capital, stressed ratios, and adequacy status.
        """
        # Build baseline capital stack if not provided
        if self._capital_stack_baseline is None:
            baseline_stack = self._build_baseline_capital_stack()
        else:
            baseline_stack = self._capital_stack_baseline

        # Compute stressed capital under each scenario
        calc = ICAAP_Stress_Calculator()
        stress_result = calc.compute(
            baseline_frtb_rwa=baseline_stack.frtb_rwa,
            baseline_credit_rwa=baseline_stack.credit_rwa,
            baseline_cet1=baseline_stack.cet1,
            baseline_tier1=baseline_stack.tier1,
            baseline_tier2=baseline_stack.tier2,
            scenarios=scenarios,
            mda_trigger=mda_trigger,
        )

        # Identify the most restrictive scenario
        min_ratio = min(
            s.cet1_ratio_stressed
            for s in stress_result.scenarios.values()
        )
        breach_scenario = None
        any_breach = False
        for name, s in stress_result.scenarios.items():
            if s.cet1_ratio_stressed < mda_trigger:
                any_breach = True
                if s.cet1_ratio_stressed == min_ratio:
                    breach_scenario = name

        adequacy = "Breaches detected" if any_breach else "Adequate under stress"

        return ICAAP_Assessment_Result(
            baseline_capital_stack=baseline_stack,
            stress_results=stress_result,
            adequacy_status=adequacy,
            min_stressed_ratio=min_ratio,
            breach_scenario=breach_scenario,
        )

    def _build_baseline_capital_stack(self) -> Capital_Stack:
        """Assemble baseline capital stack from components.

        Returns
        -------
        Capital_Stack
        """
        # FRTB RWA from trading portfolio
        frtb_rwa = self._frtb_sa.total if self._frtb_sa else 0.0

        # CVA and SA-CCR EAD
        cva_capital = 0.0
        sa_ccr_ead = 0.0
        if self._sa_ccr_portfolio:
            cva_agg = CVA_Aggregator(self._sa_ccr_portfolio)
            cva_capital = cva_agg.cva_capital()
            sa_ccr_ead = self._sa_ccr_portfolio.total_ead

        # Capital amounts: assume 10% CET1, 11.5% Tier 1, 14.5% Total
        # These are conservative but typical baseline assumptions
        total_rwa = frtb_rwa + self._baseline_credit_rwa + self._baseline_oprisk_rwa
        if total_rwa > 0:
            cet1 = total_rwa * 0.10
            tier1 = total_rwa * 0.115
            tier2 = total_rwa * 0.030  # Residual to reach 14.5%
        else:
            cet1 = tier1 = tier2 = 0.0

        return Capital_Stack_Builder.from_components(
            cet1=cet1,
            tier1=tier1,
            tier2=tier2,
            frtb_rwa=frtb_rwa,
            credit_rwa=self._baseline_credit_rwa,
            oprisk_rwa=self._baseline_oprisk_rwa,
            sa_ccr_ead=sa_ccr_ead,
            cva_capital=cva_capital,
            ccb=0.025,
            ccyb=0.0,
            gsii_buffer=0.0,
        )

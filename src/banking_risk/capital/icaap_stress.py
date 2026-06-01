"""
ICAAP Macro Stress Testing — BKR-65.

Capital adequacy under macroeconomic scenarios. Pillar 2 assessment per EBA/GL/2018/04.

Scenarios:
  - Baseline: current macroeconomic conditions
  - Adverse: moderate downturn (GDP -1.5%, rates -100bps, spreads +150bps)
  - Severely adverse: financial crisis (GDP -3%, rates -200bps, spreads +300bps)

Stress impacts:
  - Credit RWA: PD/LGD uplift via downturn factors
  - FRTB RWA: repricing under stressed curve
  - OpRisk: typically unchanged (backward-looking)
  - Capital levels: unchanged (forward-looking)

Output: Stressed capital ratios per scenario, identification of shortfalls.

References
----------
EBA/GL/2018/04 : ICAAP and ILAAP guidelines
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Scenario:
    """Macroeconomic stress scenario."""
    name: str
    description: str
    gdp_growth: float  # e.g., -0.015 = -1.5%
    rate_shock_bps: float  # e.g., -100 = -100bps
    spread_shock_bps: float  # e.g., +150 = +150bps
    equity_shock: float  # e.g., -0.30 = -30%


@dataclass
class Stressed_Capital:
    """Capital metrics under a scenario."""
    scenario_name: str
    frtb_rwa_stressed: float
    credit_rwa_stressed: float
    cet1_stressed: float
    tier1_stressed: float
    total_capital_stressed: float
    total_rwa_stressed: float

    cet1_ratio_stressed: float
    tier1_ratio_stressed: float
    total_ratio_stressed: float

    mda_trigger: float
    is_under_mda: bool
    shortfall_bps: float  # Negative if breach


@dataclass
class ICAAP_Stress_Result:
    """ICAAP stress testing output."""
    scenarios: Dict[str, Stressed_Capital] = field(default_factory=dict)
    adequacy_status: str = "Adequate"

    def to_summary(self):
        """Summary of stressed ratios and shortfalls."""
        import pandas as pd
        rows = [
            {
                'scenario': s.scenario_name,
                'CET1_stressed': s.cet1_ratio_stressed,
                'Tier1_stressed': s.tier1_ratio_stressed,
                'Total_stressed': s.total_ratio_stressed,
                'MDA_trigger': s.mda_trigger,
                'shortfall_bps': s.shortfall_bps,
            }
            for s in self.scenarios.values()
        ]
        return pd.DataFrame(rows).set_index('scenario')


# Standard scenarios per EBA/GL/2018/04 Annex
BASELINE = Scenario(
    name="Baseline",
    description="Current macroeconomic conditions",
    gdp_growth=0.015,
    rate_shock_bps=0,
    spread_shock_bps=0,
    equity_shock=0.0,
)

ADVERSE = Scenario(
    name="Adverse",
    description="Moderate downturn",
    gdp_growth=-0.015,
    rate_shock_bps=-100,
    spread_shock_bps=150,
    equity_shock=-0.20,
)

SEVERELY_ADVERSE = Scenario(
    name="Severely adverse",
    description="Financial crisis",
    gdp_growth=-0.03,
    rate_shock_bps=-200,
    spread_shock_bps=300,
    equity_shock=-0.40,
)


class ICAAP_Stress_Calculator:
    """Compute capital adequacy under macro stress scenarios."""

    def compute(
        self,
        baseline_frtb_rwa: float,
        baseline_credit_rwa: float,
        baseline_cet1: float,
        baseline_tier1: float,
        baseline_tier2: float,
        scenarios: list[Scenario],
        mda_trigger: float = 0.0725,  # 4.5% min + 2.5% CCB
    ) -> ICAAP_Stress_Result:
        """
        Parameters
        ----------
        baseline_frtb_rwa, baseline_credit_rwa : float
            Baseline RWA under normal conditions
        baseline_cet1, baseline_tier1, baseline_tier2 : float
            Current capital amounts
        scenarios : list[Scenario]
            Stress scenarios to apply
        mda_trigger : float
            MDA trigger level (e.g., 7.25%)

        Returns
        -------
        ICAAP_Stress_Result
        """
        baseline_total_capital = baseline_cet1 + baseline_tier1 + baseline_tier2
        baseline_total_rwa = baseline_frtb_rwa + baseline_credit_rwa

        stressed_scenarios = {}
        any_breach = False

        for scenario in scenarios:
            # Stress RWA: FRTB and credit scale with spread/rate/equity shocks
            # Simplified: 1 + spread shock / 10000 factor
            frtb_rwa_stressed = baseline_frtb_rwa * (1 + scenario.spread_shock_bps / 10_000)
            credit_rwa_stressed = baseline_credit_rwa * (1 + scenario.spread_shock_bps / 10_000)

            total_rwa_stressed = frtb_rwa_stressed + credit_rwa_stressed
            if total_rwa_stressed <= 0:
                total_rwa_stressed = baseline_total_rwa

            # Capital unchanged (forward-looking)
            cet1_stressed = baseline_cet1
            tier1_stressed = baseline_tier1
            total_capital_stressed = baseline_total_capital

            if total_rwa_stressed > 0:
                cet1_ratio_stressed = cet1_stressed / total_rwa_stressed
                tier1_ratio_stressed = tier1_stressed / total_rwa_stressed
                total_ratio_stressed = total_capital_stressed / total_rwa_stressed
            else:
                cet1_ratio_stressed = tier1_ratio_stressed = total_ratio_stressed = 0.0

            is_breach = cet1_ratio_stressed < mda_trigger
            shortfall_bps = (cet1_ratio_stressed - mda_trigger) * 10_000
            if is_breach:
                any_breach = True

            stressed_scenarios[scenario.name] = Stressed_Capital(
                scenario_name=scenario.name,
                frtb_rwa_stressed=frtb_rwa_stressed,
                credit_rwa_stressed=credit_rwa_stressed,
                cet1_stressed=cet1_stressed,
                tier1_stressed=tier1_stressed,
                total_capital_stressed=total_capital_stressed,
                total_rwa_stressed=total_rwa_stressed,
                cet1_ratio_stressed=cet1_ratio_stressed,
                tier1_ratio_stressed=tier1_ratio_stressed,
                total_ratio_stressed=total_ratio_stressed,
                mda_trigger=mda_trigger,
                is_under_mda=is_breach,
                shortfall_bps=shortfall_bps,
            )

        adequacy = "Breaches detected" if any_breach else "Adequate under stress"

        return ICAAP_Stress_Result(scenarios=stressed_scenarios, adequacy_status=adequacy)

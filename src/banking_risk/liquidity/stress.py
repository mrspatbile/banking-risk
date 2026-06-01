"""
Liquidity Stress Testing — idiosyncratic and market-wide scenarios.

Applies stressed outflow rates and HQLA haircuts to a base LCR computation
and estimates the survival period under each scenario.

Standard scenarios (EBA/GL/2018/02 internal liquidity stress testing):
  - Idiosyncratic: 3-notch credit rating downgrade, deposit run, loss of
    secured funding access.
  - Market-wide: general market dislocation, increased haircuts, broad
    outflow acceleration.
  - Combined: worst of both (Basel III combined scenario).

Survival period = HQLA_stressed / daily_net_outflows_stressed
where daily_net_outflows_stressed = net_outflows_30d / 30.

References
----------
EBA/GL/2018/02   : Internal liquidity stress testing guidelines
BCBS (2013)      : LCR and liquidity risk monitoring tools
"""

from dataclasses import dataclass, field

import numpy as np

from banking_risk.liquidity.lcr import (
    HQLA_Asset,
    Cash_Outflow,
    Cash_Inflow,
    SA_LCR_Calculator,
    LCR_Result,
)


# ── Stress scenario definition ────────────────────────────────────────────────

@dataclass
class Stress_Scenario:
    """Multipliers and add-ons applied on top of the base LCR calculation.

    Parameters
    ----------
    name : str
    hqla_haircut_addon : float
        Additional haircut applied to all HQLA assets (decimal).
        E.g. 0.05 adds 5 percentage points to every asset haircut.
    outflow_multiplier : float
        All outflow amounts are multiplied by this factor.
        E.g. 1.30 = 30% additional outflow acceleration.
    inflow_multiplier : float
        All inflow amounts are multiplied by this factor (≤ 1.0 to
        model reduced collection).
    """

    name               : str
    hqla_haircut_addon : float = 0.0
    outflow_multiplier : float = 1.0
    inflow_multiplier  : float = 1.0


# Pre-built standard scenarios ─────────────────────────────────────────────────

IDIOSYNCRATIC_SCENARIO = Stress_Scenario(
    name="idiosyncratic",
    hqla_haircut_addon=0.0,     # HQLA values unchanged (own credit issue)
    outflow_multiplier=1.30,    # +30% outflows (deposit run, facility draws)
    inflow_multiplier=0.80,     # −20% inflows (wholesale counterparties cut lines)
)

MARKET_WIDE_SCENARIO = Stress_Scenario(
    name="market_wide",
    hqla_haircut_addon=0.05,    # +5pp haircut on all HQLA (market illiquidity)
    outflow_multiplier=1.15,    # +15% outflows (market dislocation)
    inflow_multiplier=0.90,     # −10% inflows
)

COMBINED_SCENARIO = Stress_Scenario(
    name="combined",
    hqla_haircut_addon=0.05,
    outflow_multiplier=1.45,    # worst of both — EBA/GL/2018/02
    inflow_multiplier=0.75,
)


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class Stress_Result:
    """Stressed LCR metrics for one scenario.

    Attributes
    ----------
    scenario : str
    hqla_stressed : float
    net_outflows_stressed : float
    lcr_stressed : float
    passes : bool
    survival_days : float
        HQLA_stressed / (net_outflows_stressed / 30).
        How many days the bank can sustain the stress before exhausting HQLA.
    base_lcr : float
        LCR under the unstressed base calculation.
    """

    scenario              : str
    hqla_stressed         : float
    net_outflows_stressed : float
    lcr_stressed          : float
    passes                : bool
    survival_days         : float
    base_lcr              : float


# ── Calculator ────────────────────────────────────────────────────────────────

class Liquidity_Stress_Calculator:
    """Apply stress scenarios to a base LCR input set.

    Parameters
    ----------
    scenarios : list[Stress_Scenario], optional
        Defaults to the three standard scenarios (idiosyncratic, market-wide,
        combined).
    """

    def __init__(
        self,
        scenarios: list[Stress_Scenario] | None = None,
    ) -> None:
        self._scenarios = scenarios or [
            IDIOSYNCRATIC_SCENARIO,
            MARKET_WIDE_SCENARIO,
            COMBINED_SCENARIO,
        ]

    def compute(
        self,
        hqla_assets : list[HQLA_Asset],
        outflows    : list[Cash_Outflow],
        inflows     : list[Cash_Inflow],
    ) -> list[Stress_Result]:
        """Run all scenarios and return one Stress_Result per scenario.

        Parameters
        ----------
        hqla_assets, outflows, inflows
            Same inputs as SA_LCR_Calculator.compute().
        """
        calc     = SA_LCR_Calculator()
        base_lcr = calc.compute(hqla_assets, outflows, inflows)

        results = []
        for scenario in self._scenarios:
            stressed = _apply_scenario(hqla_assets, outflows, inflows, scenario)
            stressed_result = calc.compute(*stressed)

            daily_net = stressed_result.net_outflows / 30.0
            survival  = stressed_result.hqla / daily_net if daily_net > 0.0 else float("inf")

            results.append(
                Stress_Result(
                    scenario=scenario.name,
                    hqla_stressed=stressed_result.hqla,
                    net_outflows_stressed=stressed_result.net_outflows,
                    lcr_stressed=stressed_result.lcr,
                    passes=stressed_result.passes,
                    survival_days=survival,
                    base_lcr=base_lcr.lcr,
                )
            )
        return results


# ── Private helper ────────────────────────────────────────────────────────────

def _apply_scenario(
    hqla_assets : list[HQLA_Asset],
    outflows    : list[Cash_Outflow],
    inflows     : list[Cash_Inflow],
    scenario    : Stress_Scenario,
) -> tuple[list[HQLA_Asset], list[Cash_Outflow], list[Cash_Inflow]]:
    """Return copies of inputs with scenario multipliers applied."""
    from dataclasses import replace

    stressed_assets = [
        replace(a, additional_haircut=a.additional_haircut + scenario.hqla_haircut_addon)
        for a in hqla_assets
    ]

    stressed_outflows = []
    for o in outflows:
        if o.outflow_type is not None:
            from banking_risk.liquidity.lcr import OUTFLOW_RATES
            base_rate = OUTFLOW_RATES[o.outflow_type]
        else:
            base_rate = o.rate or 0.0
        stressed_outflows.append(
            Cash_Outflow(
                name=o.name,
                balance=o.balance,
                outflow_type=None,
                rate=min(1.0, base_rate * scenario.outflow_multiplier),
            )
        )

    stressed_inflows = []
    for i in inflows:
        if i.inflow_type is not None:
            from banking_risk.liquidity.lcr import INFLOW_RATES
            base_rate = INFLOW_RATES[i.inflow_type]
        else:
            base_rate = i.rate or 0.0
        stressed_inflows.append(
            Cash_Inflow(
                name=i.name,
                balance=i.balance,
                inflow_type=None,
                rate=min(1.0, base_rate * scenario.inflow_multiplier),
            )
        )

    return stressed_assets, stressed_outflows, stressed_inflows

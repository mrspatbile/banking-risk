"""
ILAAP — Internal Liquidity Adequacy Assessment Process.

Aggregates all liquidity risk metrics into a single management summary
suitable for the ILAAP document and supervisory reporting.

The ILAAP must demonstrate that the institution:
  - Holds sufficient HQLA to meet the LCR minimum at all times
  - Maintains stable funding matching the asset structure (NSFR)
  - Can survive a range of stress scenarios over the survival horizon
  - Has robust EWI monitoring and a functioning Contingency Funding Plan

This module is an aggregator: it takes results from the other liquidity
modules and produces a structured summary. No calculations are performed
here beyond formatting and status classification.

References
----------
EBA/GL/2021/01   : Guidelines on ILAAP and ICAAP information collected
                   for SREP purposes
EBA/GL/2018/02   : Internal liquidity stress testing
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from banking_risk.liquidity.lcr    import LCR_Result
from banking_risk.liquidity.nsfr   import NSFR_Result
from banking_risk.liquidity.stress import Stress_Result
from banking_risk.liquidity.ewi    import EWI_Dashboard, EWI_Status


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class ILAAP_Report:
    """Aggregated ILAAP summary report.

    Attributes
    ----------
    lcr_result : LCR_Result | None
    nsfr_result : NSFR_Result | None
    stress_results : list[Stress_Result]
    ewi_dashboard : EWI_Dashboard | None
    summary : pd.DataFrame
        One-page key metrics table: metric, value, threshold, status.
    adequacy_status : str
        'adequate' if all regulatory minimums are met and no red EWI;
        'concerns' if amber EWI or stress scenarios show sub-100% LCR;
        'inadequate' if any regulatory minimum is breached or red EWI.
    """

    lcr_result     : LCR_Result | None
    nsfr_result    : NSFR_Result | None
    stress_results : list[Stress_Result]
    ewi_dashboard  : EWI_Dashboard | None
    summary        : pd.DataFrame
    adequacy_status: str


# ── Aggregator ────────────────────────────────────────────────────────────────

class ILAAP_Aggregator:
    """Compile an ILAAP_Report from individual liquidity risk results.

    All parameters are optional so partial assessments are supported.

    Parameters
    ----------
    lcr_result : LCR_Result | None
    nsfr_result : NSFR_Result | None
    stress_results : list[Stress_Result]
    ewi_dashboard : EWI_Dashboard | None
    """

    def compile(
        self,
        lcr_result    : LCR_Result | None         = None,
        nsfr_result   : NSFR_Result | None        = None,
        stress_results: list[Stress_Result]        = (),
        ewi_dashboard : EWI_Dashboard | None      = None,
    ) -> ILAAP_Report:

        rows: list[dict[str, Any]] = []

        # ── LCR row ───────────────────────────────────────────────────────────
        if lcr_result is not None:
            rows.append(
                {
                    "metric"    : "LCR",
                    "value"     : f"{lcr_result.lcr:.1%}",
                    "threshold" : "≥ 100%",
                    "status"    : "PASS" if lcr_result.passes else "FAIL",
                    "detail"    : (
                        f"HQLA {lcr_result.hqla:,.0f} / "
                        f"Net outflows {lcr_result.net_outflows:,.0f}"
                    ),
                }
            )

        # ── NSFR row ──────────────────────────────────────────────────────────
        if nsfr_result is not None:
            rows.append(
                {
                    "metric"    : "NSFR",
                    "value"     : f"{nsfr_result.nsfr:.1%}",
                    "threshold" : "≥ 100%",
                    "status"    : "PASS" if nsfr_result.passes else "FAIL",
                    "detail"    : (
                        f"ASF {nsfr_result.available_stable_funding:,.0f} / "
                        f"RSF {nsfr_result.required_stable_funding:,.0f}"
                    ),
                }
            )

        # ── Stress rows — failures are "WARN" (concerns, not regulatory breach) ──
        for sr in stress_results:
            rows.append(
                {
                    "metric"    : f"LCR stressed ({sr.scenario})",
                    "value"     : f"{sr.lcr_stressed:.1%}",
                    "threshold" : "≥ 100%",
                    "status"    : "PASS" if sr.passes else "WARN",
                    "detail"    : f"Survival {sr.survival_days:.0f} days",
                }
            )

        # ── EWI summary row ───────────────────────────────────────────────────
        if ewi_dashboard is not None:
            rows.append(
                {
                    "metric"    : "EWI dashboard",
                    "value"     : ewi_dashboard.overall_status.value.upper(),
                    "threshold" : "GREEN",
                    "status"    : (
                        "PASS" if ewi_dashboard.overall_status == EWI_Status.GREEN
                        else ("WARN" if ewi_dashboard.overall_status == EWI_Status.AMBER
                              else "FAIL")
                    ),
                    "detail"    : (
                        f"{ewi_dashboard.red_count} red, "
                        f"{ewi_dashboard.amber_count} amber, "
                        f"{ewi_dashboard.green_count} green"
                    ),
                }
            )

        summary = pd.DataFrame(rows)

        # ── Overall adequacy ──────────────────────────────────────────────────
        fails  = summary["status"].eq("FAIL").any() if not summary.empty else False
        warns  = summary["status"].eq("WARN").any() if not summary.empty else False
        stress_fails = any(not sr.passes for sr in stress_results)

        if fails or (ewi_dashboard and ewi_dashboard.overall_status == EWI_Status.RED):
            adequacy = "inadequate"
        elif warns or stress_fails or (ewi_dashboard and ewi_dashboard.overall_status == EWI_Status.AMBER):
            adequacy = "concerns"
        else:
            adequacy = "adequate"

        return ILAAP_Report(
            lcr_result=lcr_result,
            nsfr_result=nsfr_result,
            stress_results=list(stress_results),
            ewi_dashboard=ewi_dashboard,
            summary=summary,
            adequacy_status=adequacy,
        )

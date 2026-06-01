"""
Credit Spread Risk in the Banking Book (CSRBB) — EBA/GL/2022/14.

Captures the risk that the economic value of banking book positions
changes due to credit spread movements not driven by the institution's
own credit standing or general interest rate risk.

Unlike FRTB CSR (trading book with a prescriptive SA formula), CSRBB has
no regulatory capital formula. This module implements the standard internal
management metrics: CS01 (spread sensitivity) and scenario stress P&L
under parallel spread shocks.

Methodology
-----------
Base PV (zero-coupon approximation):
    PV_i = notional_i × exp(−(r_f + s_i) × T_i)

CS01 (spread duration × notional × 1bp):
    CS01_i = notional_i × T_i × exp(−(r_f + s_i) × T_i) × 10⁻⁴

Stress P&L (closed-form revaluation):
    ΔPV_i(Δs) = notional_i × [exp(−(r_f + s_i + Δs/10000) × T_i)
                              − exp(−(r_f + s_i) × T_i)]

References
----------
EBA/GL/2022/14 §§ 3–5    : CSRBB identification and scope
EBA/GL/2022/14 Annex I   : CSRBB reporting templates
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ── Default stress scenarios ──────────────────────────────────────────────────
# Parallel spread shocks in basis points. Widening (+) reduces PV of
# long positions; tightening (−) increases PV.

CSRBB_STRESS_SCENARIOS: dict[str, float] = {
    "spread_widen_100bp":  100.0,
    "spread_tighten_50bp":  -50.0,
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Spread_Position:
    """A single banking-book position with credit spread exposure.

    Parameters
    ----------
    name : str
        Unique identifier.
    currency : str
        ISO 4217 code.
    notional : float
        Face / book value in currency units.
    maturity_years : float
        Remaining time to maturity in years.
    z_spread : float
        Current Z-spread (OAS) in decimal (e.g. 0.0150 = 150 bps).
    rating : str | None
        External or internal credit rating used for bucket reporting.
    coupon : float
        Annual coupon rate in decimal. Retained for a future full-repricing
        path; not used in the current zero-coupon approximation.
    """

    name           : str
    currency       : str
    notional       : float
    maturity_years : float
    z_spread       : float
    rating         : str | None = None
    coupon         : float      = 0.0


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class CSRBB_Result:
    """Output of SA_CSRBB_Calculator.compute().

    Attributes
    ----------
    detail : pd.DataFrame
        Per-position: notional, maturity_years, z_spread_bps, pv, cs01.
        Index = position name.
    total_cs01 : float
        Sum of all CS01s (currency units per 1bp).
    cs01_by_rating : dict[str, float]
        CS01 aggregated by rating bucket. Empty when no position carries
        a rating.
    stress_pnl : dict[str, float]
        Scenario name → total portfolio PV change (currency units).
        Positive means portfolio gains value; negative means it loses.
    """

    detail         : pd.DataFrame
    total_cs01     : float
    cs01_by_rating : dict[str, float]
    stress_pnl     : dict[str, float]


# ── Calculator ────────────────────────────────────────────────────────────────

class SA_CSRBB_Calculator:
    """CSRBB spread sensitivity and scenario stress calculator.

    Parameters
    ----------
    scenarios : dict[str, float], optional
        Scenario name → spread shock in bps. Defaults to
        CSRBB_STRESS_SCENARIOS (+100 bp / −50 bp).
    risk_free_rate : float, optional
        Flat risk-free discounting rate in decimal used for the base-PV
        approximation. Default 0.03 (3 %).
    """

    def __init__(
        self,
        scenarios      : dict[str, float] | None = None,
        risk_free_rate : float = 0.03,
    ) -> None:
        self._scenarios = scenarios if scenarios is not None else CSRBB_STRESS_SCENARIOS
        self._rf        = risk_free_rate

    def compute(self, positions: list[Spread_Position]) -> CSRBB_Result:
        """Compute CS01 and stress P&L for a list of spread positions.

        Parameters
        ----------
        positions : list[Spread_Position]

        Returns
        -------
        CSRBB_Result
        """
        if not positions:
            return CSRBB_Result(
                detail=pd.DataFrame(
                    columns=["currency", "notional", "maturity_years",
                             "z_spread_bps", "rating", "pv", "cs01"]
                ),
                total_cs01=0.0,
                cs01_by_rating={},
                stress_pnl={s: 0.0 for s in self._scenarios},
            )

        rows = []
        for pos in positions:
            disc = np.exp(-(self._rf + pos.z_spread) * pos.maturity_years)
            pv   = pos.notional * disc
            cs01 = pos.notional * pos.maturity_years * disc * 1e-4
            rows.append(
                {
                    "name"          : pos.name,
                    "currency"      : pos.currency,
                    "notional"      : pos.notional,
                    "maturity_years": pos.maturity_years,
                    "z_spread_bps"  : round(pos.z_spread * 1e4, 4),
                    "rating"        : pos.rating,
                    "pv"            : pv,
                    "cs01"          : cs01,
                }
            )

        detail     = pd.DataFrame(rows).set_index("name")
        total_cs01 = float(detail["cs01"].sum())

        cs01_by_rating: dict[str, float] = {}
        if detail["rating"].notna().any():
            for rating, grp in detail.dropna(subset=["rating"]).groupby("rating"):
                cs01_by_rating[str(rating)] = float(grp["cs01"].sum())

        stress_pnl: dict[str, float] = {}
        for scenario, shock_bps in self._scenarios.items():
            shock = shock_bps * 1e-4
            delta = 0.0
            for pos in positions:
                base_pv    = pos.notional * np.exp(
                    -(self._rf + pos.z_spread) * pos.maturity_years
                )
                shocked_pv = pos.notional * np.exp(
                    -(self._rf + pos.z_spread + shock) * pos.maturity_years
                )
                delta += shocked_pv - base_pv
            stress_pnl[scenario] = delta

        return CSRBB_Result(
            detail=detail,
            total_cs01=total_cs01,
            cs01_by_rating=cs01_by_rating,
            stress_pnl=stress_pnl,
        )

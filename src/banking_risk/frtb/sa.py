"""
FRTB_SA — single entry point for the FRTB Standardised Approach.

Orchestrates all risk-class calculators, aggregates capital at both levels,
and exposes per-class drill-down results alongside a top-level summary.

Usage
-----
    frtb = FRTB_SA(portfolio, curve)

    # Per risk class × per measure
    frtb.girr.delta.to_table()
    frtb.girr.vega.to_table()
    frtb.girr.curvature.to_table()
    frtb.girr.capital                  # delta + vega + curvature

    frtb.csr.delta.to_table()
    frtb.equity.delta.to_table()
    frtb.fx.delta.to_table()
    frtb.commodity.delta.to_table()

    # Summary
    frtb.total                         # single FRTB SA capital number
    frtb.to_table()                    # risk class × (delta/vega/curvature/total)
    frtb.plot()                        # stacked bar + pie

References
----------
CRR3 Art. 325bb : SA capital requirement = Σ risk class charges
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from banking_risk.shared.curves import Zero_Curve
from banking_risk.frtb.portfolio import Trading_Portfolio
from banking_risk.frtb.vertex_mapping import GIRR_VEGA_VERTICES

# ── GIRR calculators ──────────────────────────────────────────────────────────
from banking_risk.frtb.girr.delta     import SA_GIRR_Calculator
from banking_risk.frtb.girr.vega      import SA_GIRR_Vega_Calculator
from banking_risk.frtb.girr.curvature import SA_GIRR_Curvature_Calculator

# ── CSR calculators ───────────────────────────────────────────────────────────
from banking_risk.frtb.csr.delta     import SA_CSR_Delta_Calculator
from banking_risk.frtb.csr.vega      import SA_CSR_Vega_Calculator
from banking_risk.frtb.csr.curvature import SA_CSR_Curvature_Calculator

# ── Equity calculators ────────────────────────────────────────────────────────
from banking_risk.frtb.equity.delta     import SA_Equity_Delta_Calculator
from banking_risk.frtb.equity.vega      import SA_Equity_Vega_Calculator
from banking_risk.frtb.equity.curvature import SA_Equity_Curvature_Calculator

# ── FX calculators ────────────────────────────────────────────────────────────
from banking_risk.frtb.fx.delta     import SA_FX_Delta_Calculator
from banking_risk.frtb.fx.vega      import SA_FX_Vega_Calculator
from banking_risk.frtb.fx.curvature import SA_FX_Curvature_Calculator

# ── Commodity calculator ──────────────────────────────────────────────────────
from banking_risk.frtb.commodity.delta import SA_Commodity_Delta_Calculator

# ── Aggregation dataclasses ───────────────────────────────────────────────────
from banking_risk.frtb.aggregator import Risk_Class_Capital, FRTB_SA_Result


# ── Risk class view ───────────────────────────────────────────────────────────

@dataclass
class Risk_Class_View:
    """Holds the three result objects for one risk class.

    Attributes
    ----------
    delta : result object | None
        Output of the relevant SA_*_Delta_Calculator.
    vega : result object | None
        Output of the relevant SA_*_Vega_Calculator.
        None for commodity (no vega in CRR3 SA).
    curvature : result object | None
        Output of the relevant SA_*_Curvature_Calculator.
        None until gamma inputs are available from quant-risk-engine.
    """

    delta    : Any | None = None
    vega     : Any | None = None
    curvature: Any | None = None

    @property
    def capital(self) -> float:
        return sum(
            r.capital for r in (self.delta, self.vega, self.curvature)
            if r is not None
        )


# ── Facade ────────────────────────────────────────────────────────────────────

class FRTB_SA:
    """FRTB Standardised Approach orchestrator.

    Runs all risk-class calculators for the given portfolio and curve,
    aggregates capital at both the risk-class and total SA level.

    Parameters
    ----------
    portfolio : Trading_Portfolio
        Any object satisfying the Trading_Portfolio interface.
    curve : Zero_Curve
        Risk-free / OIS curve used for rate sensitivity calculations.
        Must satisfy the Zero_Curve protocol (zero_rate, discount).
    """

    def __init__(
        self,
        portfolio : Trading_Portfolio,
        curve     : Zero_Curve,
    ) -> None:
        self._portfolio = portfolio
        self._curve     = curve
        self._compute()

    # ── Per-class drill-down attributes ──────────────────────────────────────

    @property
    def girr(self) -> Risk_Class_View:
        return self._girr

    @property
    def csr(self) -> Risk_Class_View:
        return self._csr

    @property
    def equity(self) -> Risk_Class_View:
        return self._equity

    @property
    def fx(self) -> Risk_Class_View:
        return self._fx

    @property
    def commodity(self) -> Risk_Class_View:
        return self._commodity

    # ── Top-level results ─────────────────────────────────────────────────────

    @property
    def result(self) -> FRTB_SA_Result:
        return self._result

    @property
    def total(self) -> float:
        return self._result.total

    # ── Reporting ─────────────────────────────────────────────────────────────

    def to_table(self) -> pd.DataFrame:
        """Risk class × (delta / vega / curvature / total) capital table."""
        return self._result.to_table()

    def plot(self) -> None:
        """Two-panel chart: stacked bar per risk class + pie of contributions."""
        from banking_risk.utils.reporting import Dark_Style
        Dark_Style().apply()
        p = Dark_Style().palette

        df    = self.to_table().drop(index="FRTB SA")
        names = df.index.tolist()
        d_val = df["delta"].values
        v_val = df["vega"].values
        c_val = df["curvature"].values
        totals = df["total"].values

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Panel 1 — stacked bar
        x = np.arange(len(names))
        w = 0.5
        ax1.bar(x, d_val, w, label="delta",     color=p["cyan"],  alpha=0.85)
        ax1.bar(x, v_val, w, label="vega",      color=p["green"], alpha=0.85,
                bottom=d_val)
        ax1.bar(x, c_val, w, label="curvature", color=p["amber"], alpha=0.85,
                bottom=d_val + v_val)
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, fontsize=9)
        ax1.set_ylabel("Capital charge")
        ax1.set_title("FRTB SA capital by risk class and measure",
                      color=p["text_title"])
        ax1.legend(fontsize=8)
        ax1.grid(axis="y", alpha=0.3)

        # Panel 2 — pie of risk-class contributions
        non_zero = [(n, t) for n, t in zip(names, totals) if t > 0]
        if non_zero:
            pie_labels, pie_vals = zip(*non_zero)
            pie_colors = [p["cyan"], p["green"], p["amber"],
                          p["blue"], p["purple"]][:len(pie_labels)]
            ax2.pie(
                pie_vals,
                labels=pie_labels,
                colors=pie_colors,
                autopct="%1.1f%%",
                startangle=90,
                textprops={"fontsize": 9},
            )
        else:
            ax2.text(0.5, 0.5, "no capital", ha="center", va="center",
                     transform=ax2.transAxes, color=p["text_muted"])
        ax2.set_title("Capital share by risk class", color=p["text_title"])

        fig.suptitle(
            f"FRTB SA Total Capital: {self.total:,.2f}",
            color=p["text_title"], fontweight="bold",
        )
        fig.tight_layout()
        plt.show()

    # ── Internal orchestration ────────────────────────────────────────────────

    def _compute(self) -> None:
        p = self._portfolio
        c = self._curve
        n_vega = len(GIRR_VEGA_VERTICES)

        # ── GIRR ──────────────────────────────────────────────────────────────
        girr_delta = SA_GIRR_Calculator().compute(
            p.girr_delta_sensitivities(c)
        )
        girr_vega_flat = p.girr_vega_sensitivities(c)
        girr_vega = SA_GIRR_Vega_Calculator().compute(
            {ccy: arr.reshape(n_vega, n_vega)
             for ccy, arr in girr_vega_flat.items()}
        ) if girr_vega_flat else None

        self._girr = Risk_Class_View(
            delta=girr_delta,
            vega=girr_vega,
            curvature=None,   # requires gamma from quant-risk-engine
        )

        # ── CSR ───────────────────────────────────────────────────────────────
        csr_delta_sens = p.csr_sensitivities(c)
        csr_delta = SA_CSR_Delta_Calculator().compute(csr_delta_sens) \
            if csr_delta_sens else None

        self._csr = Risk_Class_View(
            delta=csr_delta,
            vega=None,        # requires csr_vega_sensitivities on portfolio
            curvature=None,
        )

        # ── Equity ────────────────────────────────────────────────────────────
        eq_bucketed = p.equity_bucketed_sensitivities(c)
        eq_delta = SA_Equity_Delta_Calculator().compute(eq_bucketed) \
            if eq_bucketed else None

        self._equity = Risk_Class_View(
            delta=eq_delta,
            vega=None,
            curvature=None,
        )

        # ── FX ────────────────────────────────────────────────────────────────
        fx_sens  = p.fx_sensitivities(c)
        fx_delta = SA_FX_Delta_Calculator().compute(fx_sens) \
            if fx_sens else None

        self._fx = Risk_Class_View(
            delta=fx_delta,
            vega=None,
            curvature=None,
        )

        # ── Commodity ─────────────────────────────────────────────────────────
        comm_sens  = p.commodity_sensitivities(c)
        comm_delta = SA_Commodity_Delta_Calculator().compute(comm_sens) \
            if comm_sens else None

        self._commodity = Risk_Class_View(
            delta=comm_delta,
            vega=None,   # no vega in CRR3 SA for commodity
            curvature=None,
        )

        # ── Aggregate ─────────────────────────────────────────────────────────
        components = [
            Risk_Class_Capital(
                "GIRR",
                delta=self._girr.delta.capital if self._girr.delta else 0.0,
                vega=self._girr.vega.capital   if self._girr.vega else 0.0,
                curvature=0.0,
            ),
            Risk_Class_Capital(
                "CSR",
                delta=self._csr.delta.capital if self._csr.delta else 0.0,
                vega=0.0,
                curvature=0.0,
            ),
            Risk_Class_Capital(
                "equity",
                delta=self._equity.delta.capital if self._equity.delta else 0.0,
                vega=0.0,
                curvature=0.0,
            ),
            Risk_Class_Capital(
                "FX",
                delta=self._fx.delta.capital if self._fx.delta else 0.0,
                vega=0.0,
                curvature=0.0,
            ),
            Risk_Class_Capital(
                "commodity",
                delta=self._commodity.delta.capital if self._commodity.delta else 0.0,
                vega=0.0,
                curvature=0.0,
            ),
        ]

        self._result = FRTB_SA_Result(components=components)

"""
FRTB SA aggregation dataclasses — CRR3 Art. 325bb.

Two levels of aggregation:

  Level 1 — Risk_Class_Capital
    Within a single risk class: delta + vega + curvature = total.
    Additivity is prescribed by CRR3 Art. 325bb — no diversification
    benefit between the three measures within a risk class.

  Level 2 — FRTB_SA_Result
    Across all risk classes: GIRR + CSR + equity + FX + commodity
    + DRC + RRAO = total SA capital charge.
    Same additivity rule — no cross-class netting.

Both classes are pure data containers. Calculation lives in FRTB_SA (sa.py).

References
----------
CRR3 Art. 325bb : SA capital requirement = sum of all risk class charges
"""
from dataclasses import dataclass, field

import pandas as pd


# ── Level 1 ───────────────────────────────────────────────────────────────────

@dataclass
class Risk_Class_Capital:
    """Capital breakdown for a single FRTB SA risk class.

    Attributes
    ----------
    name : str
        Risk class label: 'GIRR' | 'CSR' | 'equity' | 'FX' | 'commodity'.
    delta : float
    vega : float
    curvature : float
    """

    name      : str
    delta     : float = 0.0
    vega      : float = 0.0
    curvature : float = 0.0

    @property
    def total(self) -> float:
        return self.delta + self.vega + self.curvature


# ── Level 2 ───────────────────────────────────────────────────────────────────

@dataclass
class FRTB_SA_Result:
    """Total FRTB SA capital and per-class breakdown.

    Attributes
    ----------
    components : list[Risk_Class_Capital]
        One entry per active risk class.
    drc : float
        Default Risk Charge — stub, 0 until implemented.
    rrao : float
        Residual Risk Add-On — stub, 0 until implemented.
    """

    components : list[Risk_Class_Capital] = field(default_factory=list)
    drc        : float = 0.0
    rrao       : float = 0.0

    @property
    def total(self) -> float:
        return sum(c.total for c in self.components) + self.drc + self.rrao

    def to_table(self) -> pd.DataFrame:
        """Risk class × measure capital breakdown table."""
        rows = []
        for c in self.components:
            rows.append({
                "risk_class": c.name,
                "delta"     : c.delta,
                "vega"      : c.vega,
                "curvature" : c.curvature,
                "total"     : c.total,
            })
        df = pd.DataFrame(rows).set_index("risk_class")

        # Summary row
        totals = pd.DataFrame([{
            "risk_class": "FRTB SA",
            "delta"     : df["delta"].sum(),
            "vega"      : df["vega"].sum(),
            "curvature" : df["curvature"].sum(),
            "total"     : self.total,
        }]).set_index("risk_class")

        return pd.concat([df, totals])

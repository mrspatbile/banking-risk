"""
NII Supervisory Outlier Test — EBA Standardised Approach.

SA_NII_Calculator computes ΔNII for the parallel up and parallel down
scenarios over a 12-month horizon and returns a structured NII_Result
with the SOT outlier flag.

Reference: EBA/RTS/2022/10, Art. 8
"""



from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from banking_risk.irrbb.book import Banking_Book, Position
from banking_risk.irrbb.constants import EBA_SHOCKS, SOT_NII_THRESHOLD
from banking_risk.shared.curves import Zero_Curve
from banking_risk.irrbb.scenarios import Scenario_Set

_HORIZON_MONTHS: int = 12
_NII_SCENARIOS: tuple[str, str] = ("parallel_up", "parallel_down")


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class NII_Result:
    """Output of SA_NII_Calculator.compute() — EBA/RTS/2022/10, Art. 8.

    Attributes
    ----------
    nii_base : pd.Series
        NII per position under base rates (index = position name).
    nii_shocked : dict[str, pd.Series]
        NII per position under parallel up and parallel down.
    delta_nii : dict[str, float]
        Aggregate ΔNII per scenario: sum(nii_base) − sum(nii_shocked).
    tier1_capital : float
    sot_ratio : float
        max(|ΔNII|) / tier1_capital.
    is_outlier : bool
        True if sot_ratio > 5 % (EBA/RTS/2022/10, Art. 8).
    """

    nii_base: pd.Series
    nii_shocked: dict[str, pd.Series]
    delta_nii: dict[str, float]
    tier1_capital: float
    sot_ratio: float
    is_outlier: bool

    def plot(self) -> None:
        """Delegate to NII_Reporter with default Dark_Style."""
        from banking_risk.utils.reporting import Dark_Style, NII_Reporter

        NII_Reporter(Dark_Style()).plot(self)

    def to_table(self) -> pd.DataFrame:
        """Delegate to NII_Reporter with default Dark_Style."""
        from banking_risk.utils.reporting import Dark_Style, NII_Reporter

        return NII_Reporter(Dark_Style()).to_table(self)


# ── Abstract calculator ───────────────────────────────────────────────────────

class NII_Calculator(ABC):
    """Abstract NII calculator."""

    @abstractmethod
    def compute(
        self,
        book: Banking_Book,
        scenarios: dict[str, Scenario_Set],
        curves: dict[str, Zero_Curve],
    ) -> NII_Result:
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_NII_Calculator(NII_Calculator):
    """EBA Standardised Approach NII calculator — EBA/RTS/2022/10, Art. 8.

    Only parallel up and parallel down apply to the NII SOT.

    Methodology
    -----------
    Horizon: 12 months.

    Fixed positions: rate is locked until maturity → ΔNII = 0.

    Floating positions: if the position reprices within the 12 M horizon
    (repricing_tenor_months ≤ 12), the new rate applies. Simplified to
    a full-period shock (conservative): shocked_rate = rate + shock.

    NII per position: signed_notional × rate × effective_fraction
    where effective_fraction = min(maturity_months, 12) / 12.

    ΔNII per scenario = Σ(NII_base) − Σ(NII_shocked).

    SOT: max(|ΔNII_up|, |ΔNII_down|) / Tier1 > 5 %.

    Shock sizes are taken directly from EBA_SHOCKS by position currency,
    so multi-currency books apply the correct per-currency bps.
    """

    def compute(
        self,
        book: Banking_Book,
        scenarios: dict[str, Scenario_Set],   # accepted for API consistency
        curves: dict[str, Zero_Curve],         # accepted for API consistency
    ) -> NII_Result:
        positions = book.positions()
        names = [p.name for p in positions]

        nii_base = pd.Series(
            {p.name: self._nii(p, p.rate) for p in positions}
        )

        nii_shocked: dict[str, pd.Series] = {}
        delta_nii: dict[str, float] = {}

        for scenario_name in _NII_SCENARIOS:
            shocked_vals = {
                p.name: self._nii(p, self._shocked_rate(p, scenario_name))
                for p in positions
            }
            nii_shocked[scenario_name] = pd.Series(shocked_vals)
            delta_nii[scenario_name] = float(nii_base.sum()) - float(
                nii_shocked[scenario_name].sum()
            )

        worst_abs = max(abs(v) for v in delta_nii.values())
        sot_ratio = worst_abs / book.equity()

        return NII_Result(
            nii_base=nii_base,
            nii_shocked=nii_shocked,
            delta_nii=delta_nii,
            tier1_capital=book.equity(),
            sot_ratio=sot_ratio,
            is_outlier=sot_ratio > SOT_NII_THRESHOLD,
        )

    @staticmethod
    def _effective_fraction(p: Position) -> float:
        """Fraction of the 12 M horizon during which the position is outstanding."""
        return min(p.maturity_months, _HORIZON_MONTHS) / _HORIZON_MONTHS

    @staticmethod
    def _shocked_rate(p: Position, scenario_name: str) -> float:
        """Return the effective rate for position p under the given scenario.

        Fixed positions are unaffected. Floating positions that reprice within
        the 12 M horizon absorb the full scenario shock.
        """
        if p.floating and p.repricing_tenor_months <= _HORIZON_MONTHS:
            shock_bps = EBA_SHOCKS[p.currency.upper()][scenario_name]
            return p.rate + shock_bps / 10_000
        return p.rate

    @classmethod
    def _nii(cls, p: Position, rate: float) -> float:
        """NII contribution: signed_notional × rate × effective_fraction."""
        return p.signed_notional * rate * cls._effective_fraction(p)

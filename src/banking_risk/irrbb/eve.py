"""
EVE Supervisory Outlier Test — EBA Standardised Approach.

SA_EVE_Calculator computes ΔEVE for all six EBA scenarios, aggregated
across currencies, and returns a structured EVE_Result with per-bucket
NPV breakdowns and the SOT outlier flag.

Reference: EBA/RTS/2022/10, Art. 6 and Annex III
"""



from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.irrbb.book import Banking_Book
from banking_risk.irrbb.constants import (
    EBA_BUCKET_BOUNDARIES,
    EBA_BUCKET_LABELS,
    EBA_BUCKET_MIDPOINTS,
    SOT_EVE_THRESHOLD,
)
from banking_risk.shared.curves import Zero_Curve
from banking_risk.irrbb.scenarios import Scenario_Set

_EBA_MIDS = np.array(EBA_BUCKET_MIDPOINTS)   # reference — used for validation only
_INNER    = EBA_BUCKET_BOUNDARIES[1:-1]       # 18 inner boundaries for searchsorted


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class EVE_Result:
    """Output of SA_EVE_Calculator.compute() — EBA/RTS/2022/10, Art. 6.

    Attributes
    ----------
    npv_base : pd.Series
        Base present value per EBA bucket (index = EBA_BUCKET_LABELS).
    npv_shocked : dict[str, pd.Series]
        Shocked PV per bucket for each scenario (same index).
    delta_eve : dict[str, float]
        Aggregate ΔEVE per scenario: sum(npv_base) − sum(npv_shocked).
    worst_scenario : str
        Scenario name producing the largest ΔEVE.
    worst_delta_eve : float
        Maximum ΔEVE across all scenarios.
    tier1_capital : float
        Tier 1 capital used as the SOT denominator.
    sot_ratio : float
        worst_delta_eve / tier1_capital.
    is_outlier : bool
        True if sot_ratio > 15 % (EBA/RTS/2022/10, Art. 6).
    """

    npv_base: pd.Series
    npv_shocked: dict[str, pd.Series]
    delta_eve: dict[str, float]
    worst_scenario: str
    worst_delta_eve: float
    tier1_capital: float
    sot_ratio: float
    is_outlier: bool

    def plot(self) -> None:
        """Delegate to EVE_Reporter with default Dark_Style."""
        from banking_risk.utils.reporting import Dark_Style, EVE_Reporter

        EVE_Reporter(Dark_Style()).plot(self)

    def to_table(self) -> pd.DataFrame:
        """Delegate to EVE_Reporter with default Dark_Style."""
        from banking_risk.utils.reporting import Dark_Style, EVE_Reporter

        return EVE_Reporter(Dark_Style()).to_table(self)


# ── Abstract calculator ───────────────────────────────────────────────────────

class EVE_Calculator(ABC):
    """Abstract EVE calculator."""

    @abstractmethod
    def compute(
        self,
        book: Banking_Book,
        scenarios: dict[str, Scenario_Set],
        curves: dict[str, Zero_Curve],
    ) -> EVE_Result:
        """Compute EVE SOT result.

        Parameters
        ----------
        book : Banking_Book
        scenarios : dict[str, Scenario_Set]
            Keyed by ISO currency code. Every currency present in the book
            must have a matching Scenario_Set.
        curves : dict[str, Zero_Curve]
            Keyed by ISO currency code. Every currency must have a base curve.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_EVE_Calculator(EVE_Calculator):
    """EBA Standardised Approach EVE calculator — EBA/RTS/2022/10, Art. 6.

    Methodology
    -----------
    For each currency present in the book:

    1. Evaluate base zero rates at the 19 EBA midpoints using the provided
       Zero_Curve. Compute base discount factors: DF = exp(−r × t).

    2. Slot each position's signed notional into the bucket corresponding to
       its next_repricing_years (maturity for fixed, reset tenor for floating).

    3. Base NPV per bucket i: CF_i × DF_base_i.

    4. For each scenario, compute shocked rates via Shock_Scenario.shock(),
       recompute discount factors, and obtain shocked NPV per bucket.

    5. ΔEVE per scenario = Σ(NPV_base) − Σ(NPV_shocked), summed across
       all currencies. Multi-currency aggregation assumes positions are
       expressed in the reporting currency (no FX conversion applied here).

    6. SOT ratio = max(ΔEVE) / Tier1. Outlier if ratio > 15 %.
    """

    def compute(
        self,
        book: Banking_Book,
        scenarios: dict[str, Scenario_Set],
        curves: dict[str, Zero_Curve],
    ) -> EVE_Result:
        currencies = {p.currency for p in book.positions()}

        npv_base_total = np.zeros(len(EBA_BUCKET_LABELS))
        npv_shocked_total: dict[str, np.ndarray] = {}

        for ccy in currencies:
            curve = curves[ccy]
            scenario_set = scenarios[ccy]
            mids = scenario_set.midpoints

            if not np.allclose(mids, _EBA_MIDS):
                raise ValueError(
                    f"Scenario_Set midpoints for {ccy} do not match EBA_BUCKET_MIDPOINTS. "
                    "EVE computation requires the 19 regulatory midpoints."
                )

            r_base = np.array([curve.zero_rate(t) for t in mids])
            df_base = np.exp(-r_base * mids)
            cf = self._slot(book, ccy)

            npv_base_total += cf * df_base

            for scenario in scenario_set:
                if scenario.name not in npv_shocked_total:
                    npv_shocked_total[scenario.name] = np.zeros(len(EBA_BUCKET_LABELS))
                r_shocked = scenario.shock(r_base, mids)
                df_shocked = np.exp(-r_shocked * mids)
                npv_shocked_total[scenario.name] += cf * df_shocked

        npv_base = pd.Series(npv_base_total, index=EBA_BUCKET_LABELS)
        npv_shocked = {
            name: pd.Series(arr, index=EBA_BUCKET_LABELS)
            for name, arr in npv_shocked_total.items()
        }

        eve_base = float(npv_base_total.sum())
        delta_eve = {name: eve_base - float(arr.sum()) for name, arr in npv_shocked_total.items()}

        worst = max(delta_eve, key=lambda k: delta_eve[k])
        sot_ratio = delta_eve[worst] / book.equity()

        return EVE_Result(
            npv_base=npv_base,
            npv_shocked=npv_shocked,
            delta_eve=delta_eve,
            worst_scenario=worst,
            worst_delta_eve=delta_eve[worst],
            tier1_capital=book.equity(),
            sot_ratio=sot_ratio,
            is_outlier=sot_ratio > SOT_EVE_THRESHOLD,
        )

    @staticmethod
    def _slot(book: Banking_Book, currency: str) -> np.ndarray:
        """Slot signed notionals into 19 EBA buckets by next repricing date."""
        cf = np.zeros(len(EBA_BUCKET_LABELS))
        for p in book.positions():
            if p.currency != currency:
                continue
            idx = int(np.searchsorted(_INNER, p.next_repricing_years, side="left"))
            idx = min(idx, len(EBA_BUCKET_LABELS) - 1)
            cf[idx] += p.signed_notional
        return cf

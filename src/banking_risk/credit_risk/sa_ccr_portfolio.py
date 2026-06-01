"""
SA-CCR Portfolio Management — BKR-68.

Groups derivative positions by netting set and computes SA-CCR EAD
per counterparty.

Usage
-----
    from banking_risk.credit_risk.sa_ccr_portfolio import Netting_Set, SA_CCR_Portfolio
    from banking_risk.credit_risk.sa_ccr import Derivative_Position, AssetClass

    # Build netting set with derivatives
    netting_set = Netting_Set(
        netting_set_id="JPM_USD_1",
        counterparty="JPMorgan Chase",
        collateral=50_000,
        positions=[
            Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000),
            Derivative_Position("FX_EURUSD", AssetClass.FX, 500_000, 2.0, mtm=-50_000),
        ]
    )

    # Compute SA-CCR EAD
    portfolio = SA_CCR_Portfolio([netting_set])
    results = portfolio.compute()  # dict[str, SA_CCR_Result]
    total_ead = portfolio.total_ead

References
----------
CRR3 Art. 274–276 : SA-CCR methodology, netting set definition
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from banking_risk.credit_risk.sa_ccr import (
    SA_CCR_Calculator,
    SA_CCR_Result,
    Derivative_Position,
)


@dataclass
class Netting_Set:
    """Collection of derivatives netting under a single agreement.

    Parameters
    ----------
    netting_set_id : str
        Unique identifier (e.g., "JPM_USD_1").
    counterparty : str
        Counterparty name or legal entity.
    positions : list[Derivative_Position]
        All derivatives in this netting set.
    collateral : float
        Collateral amount C held.
    """

    netting_set_id : str
    counterparty : str
    positions : list[Derivative_Position] = field(default_factory=list)
    collateral : float = 0.0

    @property
    def total_notional(self) -> float:
        """Sum of all position notionals."""
        return sum(p.notional for p in self.positions)

    @property
    def total_mtm(self) -> float:
        """Sum of all position mark-to-market values."""
        return sum(p.mtm for p in self.positions)


@dataclass
class SA_CCR_Portfolio_Result:
    """SA-CCR results across all netting sets.

    Attributes
    ----------
    results : dict[str, SA_CCR_Result]
        Keyed by netting_set_id.
    total_ead : float
        Sum of EAD across all netting sets.
    by_counterparty : dict[str, float]
        Total EAD keyed by counterparty name.
    """

    results : dict[str, SA_CCR_Result] = field(default_factory=dict)
    total_ead : float = 0.0
    by_counterparty : dict[str, float] = field(default_factory=dict)


class SA_CCR_Portfolio:
    """Manage SA-CCR computation across multiple netting sets.

    Parameters
    ----------
    netting_sets : list[Netting_Set]
        All netting sets in the portfolio.
    """

    def __init__(self, netting_sets: list[Netting_Set]) -> None:
        self._netting_sets = list(netting_sets)
        self._results = None
        self._total_ead = None

    @property
    def netting_sets(self) -> list[Netting_Set]:
        return self._netting_sets

    @property
    def results(self) -> dict[str, SA_CCR_Result]:
        """Lazily compute and cache SA-CCR results."""
        if self._results is None:
            self.compute()
        return self._results

    @property
    def total_ead(self) -> float:
        """Total EAD across all netting sets."""
        if self._total_ead is None:
            self.compute()
        return self._total_ead

    def compute(self) -> SA_CCR_Portfolio_Result:
        """Compute SA-CCR EAD for all netting sets.

        Returns
        -------
        SA_CCR_Portfolio_Result
            Results keyed by netting_set_id + aggregates.
        """
        calc = SA_CCR_Calculator()
        self._results = {}
        by_counterparty: dict[str, float] = {}
        total_ead = 0.0

        for ns in self._netting_sets:
            result = calc.compute(
                netting_set_id=ns.netting_set_id,
                positions=ns.positions,
                collateral=ns.collateral,
            )
            self._results[ns.netting_set_id] = result

            # Aggregate by counterparty
            if ns.counterparty not in by_counterparty:
                by_counterparty[ns.counterparty] = 0.0
            by_counterparty[ns.counterparty] += result.ead
            total_ead += result.ead

        self._total_ead = total_ead

        return SA_CCR_Portfolio_Result(
            results=self._results,
            total_ead=total_ead,
            by_counterparty=by_counterparty,
        )

    def to_table(self):
        """Tabular view of SA-CCR results."""
        import pandas as pd

        rows = []
        for ns_id, result in self.results.items():
            rows.append({
                'netting_set': ns_id,
                'collateral': result.collateral,
                'mtm': result.mtm,
                'rc': result.rc,
                'addon': result.addon,
                'pfe': result.pfe,
                'ead': result.ead,
            })
        return pd.DataFrame(rows).set_index('netting_set')

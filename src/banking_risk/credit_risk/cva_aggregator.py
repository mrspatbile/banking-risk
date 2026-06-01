"""
CVA Capital Aggregator — BKR-68.

Aggregates BA-CVA capital across counterparties and integrates with
capital stack.

Usage
-----
    from banking_risk.credit_risk.cva_aggregator import CVA_Aggregator
    from banking_risk.credit_risk.sa_ccr_portfolio import SA_CCR_Portfolio

    sa_ccr_port = SA_CCR_Portfolio(netting_sets)
    aggregator = CVA_Aggregator(sa_ccr_port)

    cva_capital = aggregator.cva_capital()         # Total CVA capital
    cva_by_cpty = aggregator.cva_by_counterparty() # Per-counterparty breakdown

References
----------
CRR3 Art. 383a : BA-CVA capital formula
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from banking_risk.credit_risk.ba_cva import (
    BA_CVA_Calculator,
    BA_CVA_Result,
    CVA_Counterparty,
)
from banking_risk.credit_risk.sa_ccr_portfolio import SA_CCR_Portfolio


@dataclass
class CVA_Aggregation_Result:
    """BA-CVA aggregation output.

    Attributes
    ----------
    cva_capital : float
        Total CVA capital charge.
    by_counterparty : dict[str, float]
        CVA capital per counterparty.
    ba_cva_result : Optional[BA_CVA_Result]
        Underlying BA_CVA_Result if computed.
    """

    cva_capital : float = 0.0
    by_counterparty : dict[str, float] = field(default_factory=dict)
    ba_cva_result : Optional[BA_CVA_Result] = None


class CVA_Aggregator:
    """Aggregate CVA capital from SA-CCR EAD across counterparties.

    Parameters
    ----------
    sa_ccr_portfolio : SA_CCR_Portfolio
        Portfolio with computed SA-CCR EAD.
    """

    def __init__(self, sa_ccr_portfolio: SA_CCR_Portfolio) -> None:
        self._sa_ccr_portfolio = sa_ccr_portfolio
        self._cva_result = None

    @property
    def sa_ccr_portfolio(self) -> SA_CCR_Portfolio:
        return self._sa_ccr_portfolio

    def cva_capital(self) -> float:
        """Total BA-CVA capital charge.

        Returns
        -------
        float
            CVA capital, summed across all counterparties.
        """
        result = self.compute()
        return result.cva_capital

    def cva_by_counterparty(self) -> dict[str, float]:
        """CVA capital per counterparty.

        Returns
        -------
        dict[str, float]
            Keyed by counterparty name.
        """
        result = self.compute()
        return result.by_counterparty

    def compute(self) -> CVA_Aggregation_Result:
        """Compute BA-CVA capital from SA-CCR EAD.

        Builds CVA_Counterparty list from SA-CCR results and netting
        sets, then delegates to BA_CVA_Calculator.

        Returns
        -------
        CVA_Aggregation_Result
        """
        if self._cva_result is not None:
            return self._cva_result

        # Collect counterparty data from SA-CCR results
        cpty_ead: dict[str, float] = {}
        cpty_maturity: dict[str, float] = {}
        cpty_rw: dict[str, float] = {}

        for ns in self._sa_ccr_portfolio.netting_sets:
            if ns.netting_set_id not in self._sa_ccr_portfolio.results:
                continue

            result = self._sa_ccr_portfolio.results[ns.netting_set_id]

            # Accumulate EAD by counterparty
            if ns.counterparty not in cpty_ead:
                cpty_ead[ns.counterparty] = 0.0
                cpty_maturity[ns.counterparty] = 0.0
                cpty_rw[ns.counterparty] = 0.045  # Default 4.5% risk weight

            cpty_ead[ns.counterparty] += result.ead

            # Average maturity (weighted by notional)
            if ns.total_notional > 0:
                avg_m = sum(
                    p.maturity_years * p.notional / ns.total_notional
                    for p in ns.positions
                )
                cpty_maturity[ns.counterparty] = max(
                    cpty_maturity[ns.counterparty], avg_m
                )

        # Build CVA_Counterparty list
        cpty_list = [
            CVA_Counterparty(
                cpty_name=cpty,
                ead=cpty_ead[cpty],
                maturity_years=cpty_maturity.get(cpty, 1.0),
                risk_weight=cpty_rw.get(cpty, 0.045),
            )
            for cpty in cpty_ead.keys()
        ]

        # Compute BA-CVA
        calc = BA_CVA_Calculator()
        ba_cva_result = calc.compute(cpty_list)

        # Build result
        self._cva_result = CVA_Aggregation_Result(
            cva_capital=ba_cva_result.capital,
            by_counterparty=ba_cva_result.by_counterparty,
            ba_cva_result=ba_cva_result,
        )

        return self._cva_result

    def to_dict(self) -> dict:
        """Export as dict for capital stack integration."""
        result = self.compute()
        return {
            'cva_capital': result.cva_capital,
            'by_counterparty': result.by_counterparty,
        }

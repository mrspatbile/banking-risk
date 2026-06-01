"""
Standardised Approach Counterparty Credit Risk (SA-CCR) — BKR-61.

Produces exposure at default (EAD) per netting set.

Formula (CRR3 Art. 274–276):
    EAD = alpha × (RC + PFE)
      alpha = 1.4

    RC  = max(V − C, 0)  (unmargined)
    PFE = multiplier × AddOn_aggregate

    multiplier = min(1, 0.05 + 0.95 × exp((V−C) / (2 × 0.95 × AddOn)))

    AddOn per asset class:
      supervisory_factor × effective_notional (maturity-adjusted)

References
----------
CRR3 Art. 274–276 : SA-CCR framework, supervisory factors, maturity adjustments
"""

from dataclasses import dataclass
from enum import Enum
import numpy as np


class AssetClass(Enum):
    """SA-CCR asset class."""
    IR = "IR"           # Interest rate
    FX = "FX"           # Foreign exchange
    CREDIT = "CREDIT"   # Credit
    EQUITY = "EQUITY"   # Equity
    COMMODITY = "COMM"  # Commodity


@dataclass
class Derivative_Position:
    """Single derivative in a netting set."""
    name: str
    asset_class: AssetClass
    notional: float
    maturity_years: float
    mtm: float = 0.0  # Mark-to-market current value


@dataclass
class SA_CCR_Result:
    """EAD output per netting set."""
    netting_set_id: str
    collateral: float  # C
    mtm: float         # V
    rc: float          # Replacement cost
    addon: float       # AddOn_aggregate
    pfe: float         # Potential future exposure
    ead: float         # Exposure at default


# Supervisory factors per asset class (CRR3 Art. 274 Table 1)
SUPERVISORY_FACTORS = {
    AssetClass.IR: 0.004,
    AssetClass.FX: 0.06,
    AssetClass.CREDIT: 0.038,
    AssetClass.EQUITY: 0.20,
    AssetClass.COMMODITY: 0.18,
}


def maturity_factor(maturity_years: float) -> float:
    """Maturity adjustment M_k per CRR3 Art. 274(3).

    M_k = sqrt(min(max(M, 1), 5) / 5)
    """
    m = np.sqrt(max(1.0, min(maturity_years, 5.0)) / 5.0)
    return m


class SA_CCR_Calculator:
    """Compute SA-CCR EAD per netting set."""

    def compute(
        self,
        netting_set_id: str,
        positions: list[Derivative_Position],
        collateral: float = 0.0,
    ) -> SA_CCR_Result:
        """
        Parameters
        ----------
        netting_set_id : str
        positions : list[Derivative_Position]
        collateral : float
            Collateral amount C.

        Returns
        -------
        SA_CCR_Result
        """
        if not positions:
            return SA_CCR_Result(
                netting_set_id=netting_set_id,
                collateral=collateral,
                mtm=0.0,
                rc=0.0,
                addon=0.0,
                pfe=0.0,
                ead=0.0,
            )

        # Current MtM value
        mtm = sum(p.mtm for p in positions)

        # Replacement cost RC = max(V - C, 0)
        rc = max(mtm - collateral, 0.0)

        # AddOn per asset class
        addon_by_class = {}
        for asset_class in AssetClass:
            positions_in_class = [p for p in positions if p.asset_class == asset_class]
            if not positions_in_class:
                continue

            sf = SUPERVISORY_FACTORS[asset_class]
            addon_sum = 0.0

            for pos in positions_in_class:
                m = maturity_factor(pos.maturity_years)
                addon_sum += sf * pos.notional * m

            addon_by_class[asset_class.value] = addon_sum

        addon_total = sum(addon_by_class.values())

        # Multiplier = min(1, 0.05 + 0.95 × exp((V-C) / (2 × 0.95 × AddOn)))
        if addon_total > 0:
            denom = 2 * 0.95 * addon_total
            mult = min(1.0, 0.05 + 0.95 * np.exp((mtm - collateral) / denom))
        else:
            mult = 1.0

        pfe = mult * addon_total

        # EAD = 1.4 × (RC + PFE)
        alpha = 1.4
        ead = alpha * (rc + pfe)

        return SA_CCR_Result(
            netting_set_id=netting_set_id,
            collateral=collateral,
            mtm=mtm,
            rc=rc,
            addon=addon_total,
            pfe=pfe,
            ead=ead,
        )

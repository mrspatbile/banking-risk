"""
FRTB SA FX delta — CRR3 Art. 325bm.

The simplest FRTB SA risk class: one bucket, one sensitivity per currency
pair, flat risk weight, flat cross-pair correlation.

Input shape
-----------
dict[str, float]  →  currency pair label → spot FX sensitivity

Each value s_k is the sensitivity of the portfolio to a 1% move in the
FX spot rate for pair k (currency units / 1%).

Methodology
-----------
1. Risk-weight: WS_k = s_k × RW_FX  (15% for all pairs)

2. Capital — single-bucket quadratic form (Art. 325bm):
   K = sqrt(max(0, Σ_k WS_k² + ρ_FX × Σ_{k≠l} WS_k × WS_l))
     = sqrt(WS^T @ RHO_FX @ WS)

   RHO_FX_kl = 1 if k = l,  ρ_FX (0.60) otherwise

   FX has no within/cross-bucket distinction — all currency pairs
   are in a single flat pool.

References
----------
CRR3 Art. 325bm : FX delta risk weight (15%) and cross-pair correlation (0.60)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import FX_RISK_WEIGHT, FX_CORRELATION_RHO


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class FX_Delta_Result:
    """Output of SA_FX_Delta_Calculator.compute().

    Attributes
    ----------
    ws : pd.Series
        Risk-weighted sensitivities per currency pair.
    capital : float
        Total FX delta capital.
    pairs : list[str]
    """

    ws      : pd.Series
    capital : float
    pairs   : list[str]

    def to_table(self) -> pd.DataFrame:
        return pd.DataFrame({
            "ws"     : self.ws,
            "rw_pct" : FX_RISK_WEIGHT * 100,
        })


# ── Abstract calculator ───────────────────────────────────────────────────────

class FX_Delta_Calculator(ABC):

    @abstractmethod
    def compute(self, sensitivities: dict[str, float]) -> FX_Delta_Result:
        """Compute FX delta capital.

        Parameters
        ----------
        sensitivities : dict[str, float]
            Currency pair label (e.g. 'EURUSD') → spot FX sensitivity.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_FX_Delta_Calculator(FX_Delta_Calculator):
    """CRR3 Art. 325bm SA FX delta calculator."""

    def compute(self, sensitivities: dict[str, float]) -> FX_Delta_Result:
        if not sensitivities:
            return FX_Delta_Result(
                ws=pd.Series(dtype=float), capital=0.0, pairs=[]
            )

        pairs = sorted(sensitivities.keys())
        s     = np.array([sensitivities[k] for k in pairs])
        ws    = s * FX_RISK_WEIGHT

        n   = len(ws)
        rho_mat = np.full((n, n), FX_CORRELATION_RHO)
        np.fill_diagonal(rho_mat, 1.0)

        capital = float(np.sqrt(max(0.0, ws @ rho_mat @ ws)))

        return FX_Delta_Result(
            ws=pd.Series(ws, index=pairs),
            capital=capital,
            pairs=pairs,
        )

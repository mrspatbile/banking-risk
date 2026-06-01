"""
FRTB SA FX curvature — CRR3 Art. 325e/325ef.

CVR^± ≈ −0.5 × γ_k × (RW_FX)²

FX has a single risk weight (15%) so the curvature formula reduces to
a scalar multiple of the total FX gamma, aggregated across currency pairs.

References
----------
CRR3 Art. 325e/325ef : Curvature definition and aggregation
CRR3 Art. 325bm      : FX correlation ρ = 0.60
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import FX_RISK_WEIGHT, FX_CORRELATION_RHO


def curvature_pnl_from_greeks(
    delta: float,
    gamma: float,
    risk_weight: float = FX_RISK_WEIGHT,
) -> tuple[float, float]:
    """Approximate FX curvature P&L for a single currency pair.

    Parameters
    ----------
    delta : float
        FX spot sensitivity (unused in symmetric Taylor formula).
    gamma : float
        Second-order FX spot sensitivity.
    risk_weight : float
        FX risk weight in decimal. Default 15%.
    """
    cvr = float(-0.5 * gamma * risk_weight ** 2)
    return cvr, cvr


@dataclass
class FX_Curvature_Result:
    cvr_up  : dict[str, float]
    cvr_down: dict[str, float]
    K       : dict[str, float]
    S       : dict[str, float]
    capital : float
    pairs   : list[str]

    def to_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"cvr_up": self.cvr_up, "cvr_down": self.cvr_down,
             "K": self.K, "S": self.S},
        ).T


class SA_FX_Curvature_Calculator:
    """CRR3 FX curvature capital — single pool, ρ = 0.60."""

    def compute(
        self,
        cvr_up  : dict[str, float],
        cvr_down: dict[str, float],
    ) -> FX_Curvature_Result:
        if set(cvr_up) != set(cvr_down):
            raise ValueError("cvr_up and cvr_down must have the same currency-pair keys.")

        pairs = sorted(cvr_up.keys())
        K_dict: dict[str, float] = {}
        S_dict: dict[str, float] = {}

        for p in pairs:
            up   = float(cvr_up[p])
            down = float(cvr_down[p])
            K    = max(up, down, 0.0)
            K_dict[p] = K
            worst = up if up >= down else down
            S_dict[p] = float(np.clip(worst, -K, K))

        K_vec   = np.array([K_dict[p] for p in pairs])
        S_vec   = np.array([S_dict[p] for p in pairs])
        n       = len(pairs)
        rho_mat = np.full((n, n), FX_CORRELATION_RHO)
        np.fill_diagonal(rho_mat, 0.0)
        cross   = rho_mat * (S_vec[:, None] * S_vec[None, :])
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return FX_Curvature_Result(
            cvr_up=cvr_up, cvr_down=cvr_down,
            K=K_dict, S=S_dict, capital=capital, pairs=pairs,
        )

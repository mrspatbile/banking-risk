"""
FRTB SA Equity curvature — CRR3 Art. 325e/325ef.

For equity (spot risk, no tenor dimension):
CVR^± ≈ −0.5 × γ × (RW_b)²

where γ is the total second-order equity spot sensitivity for the bucket
and RW_b is the bucket risk weight (same as delta).

References
----------
CRR3 Art. 325e/325ef : Curvature definition and aggregation
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    EQUITY_RISK_WEIGHTS,
    EQUITY_CROSS_BUCKET_GAMMA,
    EQUITY_RESIDUAL_BUCKET_GAMMA,
)

_N_BUCKETS    = len(EQUITY_RISK_WEIGHTS)
_RESIDUAL_BKT = 11


def curvature_pnl_from_greeks(
    delta: float,
    gamma: float,
    bucket: int,
    risk_weight: float | None = None,
) -> tuple[float, float]:
    """Approximate equity curvature P&L for a single name/bucket.

    Parameters
    ----------
    delta : float
        First-order equity spot sensitivity (unused in symmetric Taylor formula).
    gamma : float
        Second-order equity spot sensitivity (currency per (equity %)²).
    bucket : int
        Equity bucket (1–11) — determines the risk weight.
    risk_weight : float | None
        Override. Defaults to the prescribed RW for the bucket.
    """
    rw  = risk_weight if risk_weight is not None else EQUITY_RISK_WEIGHTS[bucket - 1]
    cvr = float(-0.5 * gamma * rw ** 2)
    return cvr, cvr


@dataclass
class Equity_Curvature_Result:
    cvr_up  : dict[int, float]
    cvr_down: dict[int, float]
    K       : dict[int, float]
    S       : dict[int, float]
    capital : float
    buckets : list[int]

    def to_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"cvr_up": self.cvr_up, "cvr_down": self.cvr_down,
             "K": self.K, "S": self.S},
        ).T


class SA_Equity_Curvature_Calculator:
    """CRR3 equity curvature capital."""

    def compute(
        self,
        cvr_up  : dict[int, float],
        cvr_down: dict[int, float],
    ) -> Equity_Curvature_Result:
        if set(cvr_up) != set(cvr_down):
            raise ValueError("cvr_up and cvr_down must have the same bucket keys.")

        buckets = sorted(cvr_up.keys())
        K_dict: dict[int, float] = {}
        S_dict: dict[int, float] = {}

        for b in buckets:
            up   = float(cvr_up[b])
            down = float(cvr_down[b])
            K    = max(up, down, 0.0)
            K_dict[b] = K
            worst = up if up >= down else down
            S_dict[b] = float(np.clip(worst, -K, K))

        K_vec = np.array([K_dict[b] for b in buckets])
        S_vec = np.array([S_dict[b] for b in buckets])

        gamma_mat = np.full((len(buckets), len(buckets)), EQUITY_CROSS_BUCKET_GAMMA)
        for i, bi in enumerate(buckets):
            for j, bj in enumerate(buckets):
                if bi == _RESIDUAL_BKT or bj == _RESIDUAL_BKT:
                    gamma_mat[i, j] = EQUITY_RESIDUAL_BUCKET_GAMMA
        np.fill_diagonal(gamma_mat, 0.0)

        cross   = gamma_mat * (S_vec[:, None] * S_vec[None, :])
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return Equity_Curvature_Result(
            cvr_up=cvr_up, cvr_down=cvr_down,
            K=K_dict, S=S_dict, capital=capital, buckets=buckets,
        )

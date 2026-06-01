"""
FRTB SA CSR securitisation curvature — CRR3 Art. 325e/325ef.

Same Taylor-approximation formula as GIRR curvature but applied to
credit spread risk: CVR^± ≈ −0.5 × Σ_k γ_k × ΔRW_k²

where ΔRW_k is the CSR sec delta risk weight for the relevant bucket.
Aggregation uses the same cross-bucket γ = 0.05 as CSR sec delta.

References
----------
CRR3 Art. 325e   : Curvature risk definition
CRR3 Art. 325ef  : Curvature aggregation
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    CSR_SEC_RISK_WEIGHTS,
    CSR_SEC_CROSS_BUCKET_GAMMA,
)

_N_BUCKETS = len(CSR_SEC_RISK_WEIGHTS)
_RW = np.array(CSR_SEC_RISK_WEIGHTS)


def curvature_pnl_from_greeks(
    delta: np.ndarray,
    gamma: np.ndarray,
    bucket: int,
    risk_weight: float | None = None,
) -> tuple[float, float]:
    """Approximate CSR sec curvature P&L for a single bucket.

    CVR^± ≈ −0.5 × Σ_k γ_k × ΔRW_k²

    For CSR, each bucket has a single risk weight (not per-vertex), so
    ΔRW_k = RW_bucket for all k. Gamma elements correspond to the 5
    CSR tenor vertices.

    Parameters
    ----------
    delta : np.ndarray, shape (5,)
        CS01 sensitivities (not used in symmetric Taylor formula).
    gamma : np.ndarray, shape (5,)
        Second-order spread sensitivities at the 5 CSR vertices.
    bucket : int
        CSR sec bucket number (1–41) — determines the risk weight.
    risk_weight : float | None
        Override. Defaults to the prescribed RW for the bucket.
    """
    delta = np.asarray(delta, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    if len(delta) != 5 or len(gamma) != 5:
        raise ValueError("delta and gamma must have length 5 (one per CSR tenor vertex).")
    rw  = risk_weight if risk_weight is not None else _RW[bucket - 1]
    cvr = float(-0.5 * (gamma * rw ** 2).sum())
    return cvr, cvr


@dataclass
class CSR_Sec_Curvature_Result:
    cvr_up    : dict[int, float]
    cvr_down  : dict[int, float]
    K         : dict[int, float]
    S         : dict[int, float]
    capital   : float
    buckets   : list[int]

    def to_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"cvr_up": self.cvr_up, "cvr_down": self.cvr_down,
             "K": self.K, "S": self.S},
        )


class SA_CSR_Sec_Curvature_Calculator:
    """CRR3 Art. 325e/325ef CSR sec curvature capital."""

    def compute(
        self,
        cvr_up  : dict[int, float],
        cvr_down: dict[int, float],
    ) -> CSR_Sec_Curvature_Result:
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
        cross = CSR_SEC_CROSS_BUCKET_GAMMA * (S_vec[:, None] * S_vec[None, :])
        np.fill_diagonal(cross, 0.0)
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return CSR_Sec_Curvature_Result(
            cvr_up=cvr_up, cvr_down=cvr_down,
            K=K_dict, S=S_dict, capital=capital, buckets=buckets,
        )

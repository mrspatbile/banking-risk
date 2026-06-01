"""
FRTB SA Equity delta — CRR3 Art. 325bk.

Receives per-name equity spot sensitivities grouped by bucket and returns
the delta capital charge.

Input shape
-----------
dict[int, list[float]]  →  bucket (1–11) → list of per-name sensitivities

Each element s_k is the sensitivity of the portfolio P&L to a 1% move in
the equity spot price of name k (equity vega in § currency units / 1%).

Methodology
-----------
1. Risk-weight: WS_k = s_k × RW_b  (same weight for all names in bucket b)

2. Within-bucket capital (Art. 325bk):
   K_b = sqrt(max(0, Σ_k WS_k² + ρ_b × Σ_{k≠l} WS_k × WS_l))

   Equivalently: K_b = sqrt(WS_b^T @ RHO_b @ WS_b)
   where RHO_b = (1 − ρ_b) × I + ρ_b × 11^T  (equicorrelation matrix)

3. Cross-bucket aggregation (Art. 325bk):
   γ_bc = 0.15 for b,c ∈ {1..10}
   γ_bc = 0    if b = 11 or c = 11 (residual bucket)

References
----------
CRR3 Art. 325bk   : Equity delta buckets and correlations
BCBS Table 11 (2019): Equity bucket parameters
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    EQUITY_BUCKET_LABELS,
    EQUITY_BUCKET_DESCS,
    EQUITY_RISK_WEIGHTS,
    EQUITY_RHO_INTRA,
    EQUITY_CROSS_BUCKET_GAMMA,
    EQUITY_RESIDUAL_BUCKET_GAMMA,
)

_N_BUCKETS    = len(EQUITY_RISK_WEIGHTS)
_RESIDUAL_BKT = 11


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class Equity_Delta_Result:
    """Output of SA_Equity_Delta_Calculator.compute().

    Attributes
    ----------
    ws : dict[int, np.ndarray]
        Risk-weighted sensitivities per bucket (one element per name).
    K : dict[int, float]
        Within-bucket capital.
    S : dict[int, float]
        Net sensitivity per bucket, capped at ±K_b.
    capital : float
        Total equity delta capital.
    buckets : list[int]
    """

    ws      : dict[int, np.ndarray]
    K       : dict[int, float]
    S       : dict[int, float]
    capital : float
    buckets : list[int]

    def to_table(self) -> pd.DataFrame:
        rows = []
        for b in self.buckets:
            rows.append({
                "bucket"   : b,
                "desc"     : EQUITY_BUCKET_DESCS[b - 1],
                "n_names"  : len(self.ws[b]),
                "WS_sum"   : float(self.ws[b].sum()),
                "K"        : self.K[b],
                "S"        : self.S[b],
            })
        return pd.DataFrame(rows).set_index("bucket")


# ── Abstract calculator ───────────────────────────────────────────────────────

class Equity_Delta_Calculator(ABC):

    @abstractmethod
    def compute(
        self,
        sensitivities: dict[int, list[float]],
    ) -> Equity_Delta_Result:
        """Compute equity delta capital.

        Parameters
        ----------
        sensitivities : dict[int, list[float]]
            Keyed by bucket (1–11). Each list contains one sensitivity per
            equity name/position within that bucket.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_Equity_Delta_Calculator(Equity_Delta_Calculator):
    """CRR3 Art. 325bk SA equity delta calculator."""

    def compute(
        self,
        sensitivities: dict[int, list[float]],
    ) -> Equity_Delta_Result:
        buckets = sorted(sensitivities.keys())
        ws_dict: dict[int, np.ndarray] = {}
        K_dict : dict[int, float]      = {}
        S_dict : dict[int, float]      = {}

        for b in buckets:
            if b < 1 or b > _N_BUCKETS:
                raise ValueError(f"Invalid equity bucket {b}: must be 1–{_N_BUCKETS}.")
            s  = np.asarray(sensitivities[b], dtype=float)
            rw = EQUITY_RISK_WEIGHTS[b - 1]
            ws = s * rw
            ws_dict[b] = ws

            rho = EQUITY_RHO_INTRA[b - 1]
            n   = len(ws)
            if n == 0:
                K_dict[b] = 0.0
                S_dict[b] = 0.0
                continue

            # Equicorrelation: WS^T @ ((1-ρ)I + ρ×11^T) @ WS
            #   = (1-ρ) Σ WS_k² + ρ (Σ WS_k)²
            quad = (1.0 - rho) * float((ws ** 2).sum()) + rho * float(ws.sum() ** 2)
            K = float(np.sqrt(max(0.0, quad)))
            K_dict[b] = K
            S_dict[b] = float(np.clip(ws.sum(), -K, K))

        K_vec = np.array([K_dict[b] for b in buckets])
        S_vec = np.array([S_dict[b] for b in buckets])

        # Cross-bucket: γ = 0 involving bucket 11, 0.15 otherwise
        gamma_mat = np.full((len(buckets), len(buckets)), EQUITY_CROSS_BUCKET_GAMMA)
        for i, bi in enumerate(buckets):
            for j, bj in enumerate(buckets):
                if bi == _RESIDUAL_BKT or bj == _RESIDUAL_BKT:
                    gamma_mat[i, j] = EQUITY_RESIDUAL_BUCKET_GAMMA
        np.fill_diagonal(gamma_mat, 0.0)

        cross   = gamma_mat * (S_vec[:, None] * S_vec[None, :])
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return Equity_Delta_Result(
            ws=ws_dict, K=K_dict, S=S_dict, capital=capital, buckets=buckets
        )

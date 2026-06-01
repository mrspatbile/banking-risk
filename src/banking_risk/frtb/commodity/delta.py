"""
FRTB SA Commodity delta — CRR3 Art. 325bp.

Receives commodity forward sensitivities bucketed by (commodity type, tenor
vertex) and returns the delta capital charge.

Input shape
-----------
dict[int, np.ndarray]  →  bucket (1–11) → array of shape (7,)
Each element is the sensitivity (currency per 1%) at the 7 commodity tenor
vertices: [0Y, 0.25Y, 0.5Y, 1Y, 2Y, 3Y, 5Y].

Methodology
-----------
1. Risk-weight: WS_bk = s_bk × RW_b

2. Within-bucket capital (Art. 325bp):
   Uses a flat intra-bucket correlation ρ_b (not tenor-dependent for commodity):
   K_b = sqrt(max(0, (1−ρ_b) Σ WS_bk² + ρ_b (Σ WS_bk)²))

3. Cross-bucket aggregation (Art. 325bp):
   K = sqrt(max(0, Σ K_b² + Σ_{b≠c} γ × S_b × S_c))
   γ = 0.20 (simplified uniform cross-bucket)

Note: CRR3 commodity SA does not include a prescribed vega or curvature
treatment for commodity (as of the current implementation scope).

References
----------
CRR3 Art. 325bp    : Commodity delta buckets and correlations
BCBS Tables 13–14 (2019): Commodity bucket parameters
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    COMMODITY_TENOR_LABELS,
    COMMODITY_BUCKET_LABELS,
    COMMODITY_BUCKET_DESCS,
    COMMODITY_RISK_WEIGHTS,
    COMMODITY_RHO_INTRA,
    COMMODITY_CROSS_BUCKET_GAMMA,
)

_N_BUCKETS = len(COMMODITY_RISK_WEIGHTS)
_N_TENORS  = len(COMMODITY_TENOR_LABELS)


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class Commodity_Delta_Result:
    """Output of SA_Commodity_Delta_Calculator.compute().

    Attributes
    ----------
    ws : dict[int, pd.Series]
        Risk-weighted sensitivities per bucket, indexed by tenor label.
    K : dict[int, float]
        Within-bucket capital.
    S : dict[int, float]
        Net sensitivity per bucket, capped at ±K_b.
    capital : float
        Total commodity delta capital.
    buckets : list[int]
    """

    ws      : dict[int, pd.Series]
    K       : dict[int, float]
    S       : dict[int, float]
    capital : float
    buckets : list[int]

    def to_table(self) -> pd.DataFrame:
        rows = []
        for b in self.buckets:
            rows.append({
                "bucket" : b,
                "desc"   : COMMODITY_BUCKET_DESCS[b - 1],
                "K"      : self.K[b],
                "S"      : self.S[b],
                "WS_sum" : float(self.ws[b].sum()),
            })
        return pd.DataFrame(rows).set_index("bucket")


# ── Abstract calculator ───────────────────────────────────────────────────────

class Commodity_Delta_Calculator(ABC):

    @abstractmethod
    def compute(
        self,
        sensitivities: dict[int, np.ndarray],
    ) -> Commodity_Delta_Result:
        """Compute commodity delta capital.

        Parameters
        ----------
        sensitivities : dict[int, np.ndarray]
            Keyed by bucket (1–11). Each array has shape (7,) — net
            commodity forward sensitivity at each tenor vertex.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_Commodity_Delta_Calculator(Commodity_Delta_Calculator):
    """CRR3 Art. 325bp SA commodity delta calculator."""

    def compute(
        self,
        sensitivities: dict[int, np.ndarray],
    ) -> Commodity_Delta_Result:
        buckets = sorted(sensitivities.keys())
        ws_dict: dict[int, pd.Series] = {}
        K_dict : dict[int, float]     = {}
        S_dict : dict[int, float]     = {}

        for b in buckets:
            if b < 1 or b > _N_BUCKETS:
                raise ValueError(f"Invalid commodity bucket {b}: must be 1–{_N_BUCKETS}.")
            s = np.asarray(sensitivities[b], dtype=float)
            if len(s) != _N_TENORS:
                raise ValueError(
                    f"Bucket {b}: expected array of length {_N_TENORS}, got {len(s)}."
                )
            rw  = COMMODITY_RISK_WEIGHTS[b - 1]
            ws  = s * rw
            ws_dict[b] = pd.Series(ws, index=COMMODITY_TENOR_LABELS)

            rho = COMMODITY_RHO_INTRA[b - 1]
            # Equicorrelation: (1-ρ) Σ WS² + ρ (Σ WS)²
            quad = (1.0 - rho) * float((ws ** 2).sum()) + rho * float(ws.sum() ** 2)
            K = float(np.sqrt(max(0.0, quad)))
            K_dict[b] = K
            S_dict[b] = float(np.clip(ws.sum(), -K, K))

        K_vec = np.array([K_dict[b] for b in buckets])
        S_vec = np.array([S_dict[b] for b in buckets])
        cross = COMMODITY_CROSS_BUCKET_GAMMA * (S_vec[:, None] * S_vec[None, :])
        np.fill_diagonal(cross, 0.0)
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return Commodity_Delta_Result(
            ws=ws_dict, K=K_dict, S=S_dict, capital=capital, buckets=buckets
        )

"""
FRTB SA CSR securitisation delta — CRR3 Art. 325bi/bj.

Receives CS01 sensitivities bucketed by (securitisation bucket, credit tenor vertex)
and returns the delta capital charge via within-bucket and cross-bucket
aggregation.

Input shape
-----------
dict[int, np.ndarray]  →  bucket (1–41) → array of shape (5,)
Each element is the net CS01 (currency per 1bp) at the corresponding
CSR tenor vertex: [0.5Y, 1Y, 3Y, 5Y, 10Y].

Buckets 1-25:   Non-CTP securitisations
Buckets 26-41:  CTP (credit tranched products)

Methodology
-----------
1. Risk-weight sensitivities: WS_bk = s_bk × RW_b

2. Within-bucket capital (Art. 325bi):
   K_b = sqrt(max(0, WS_b^T @ RHO_b @ WS_b))
   where RHO_b_kl = rho_name_b × exp(-alpha × |t_k - t_l|)  (k ≠ l)
                  = 1                                          (k = l)

3. Net sensitivity capped at ±K_b: S_b = clip(sum(WS_b), -K_b, K_b)

4. Cross-bucket aggregation (Art. 325bj):
   K = sqrt(max(0, Σ K_b² + Σ_{b≠c} γ × S_b × S_c))

References
----------
CRR3 Art. 325bi   : CSR sec buckets and risk weights
CRR3 Art. 325bj   : Cross-bucket aggregation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    CSR_TENOR_LABELS,
    CSR_TENOR_VERTICES,
    CSR_SEC_BUCKET_LABELS,
    CSR_SEC_BUCKET_DESCS,
    CSR_SEC_RISK_WEIGHTS,
    CSR_SEC_RHO_NAME,
    CSR_SEC_TENOR_ALPHA,
    CSR_SEC_CROSS_BUCKET_GAMMA,
)

_VERTICES  = np.array(CSR_TENOR_VERTICES)
_N_BUCKETS = len(CSR_SEC_RISK_WEIGHTS)
_N_TENORS  = len(_VERTICES)

# Pre-compute per-bucket within-bucket correlation matrices
# RHO_b_kl = rho_name_b × exp(-alpha × |t_k - t_l|)  for k ≠ l
#           = 1                                          for k = l
_diff = np.abs(_VERTICES[:, None] - _VERTICES[None, :])
_RHO_TENOR = np.exp(-CSR_SEC_TENOR_ALPHA * _diff)

def _bucket_rho(rho_name: float) -> np.ndarray:
    """Full (5×5) within-bucket correlation matrix for a given name correlation."""
    rho = rho_name * _RHO_TENOR
    np.fill_diagonal(rho, 1.0)
    return rho

_BUCKET_RHO = [_bucket_rho(rn) for rn in CSR_SEC_RHO_NAME]


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class CSR_Sec_Delta_Result:
    """Output of SA_CSR_Sec_Delta_Calculator.compute().

    Attributes
    ----------
    ws : dict[int, pd.Series]
        Risk-weighted sensitivities per bucket, indexed by tenor label.
    K : dict[int, float]
        Within-bucket capital per bucket.
    S : dict[int, float]
        Net sensitivity per bucket, capped at ±K_b.
    capital : float
        Total CSR sec delta capital charge.
    buckets : list[int]
        Populated bucket IDs.
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
                "desc"   : CSR_SEC_BUCKET_DESCS[b - 1],
                "K"      : self.K[b],
                "S"      : self.S[b],
                "WS_sum" : float(self.ws[b].sum()),
            })
        return pd.DataFrame(rows).set_index("bucket")


# ── Abstract calculator ───────────────────────────────────────────────────────

class CSR_Sec_Delta_Calculator(ABC):

    @abstractmethod
    def compute(
        self,
        sensitivities: dict[int, np.ndarray],
    ) -> CSR_Sec_Delta_Result:
        """Compute CSR sec delta capital.

        Parameters
        ----------
        sensitivities : dict[int, np.ndarray]
            Keyed by bucket number (1–41). Each array has shape (5,) —
            net CS01 at each CSR tenor vertex in currency per 1bp.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_CSR_Sec_Delta_Calculator(CSR_Sec_Delta_Calculator):
    """CRR3 Art. 325bi–325bj SA CSR securitisation delta calculator."""

    def compute(
        self,
        sensitivities: dict[int, np.ndarray],
    ) -> CSR_Sec_Delta_Result:
        buckets = sorted(sensitivities.keys())
        ws_dict: dict[int, pd.Series] = {}
        K_dict : dict[int, float]     = {}
        S_dict : dict[int, float]     = {}

        for b in buckets:
            if b < 1 or b > _N_BUCKETS:
                raise ValueError(f"Invalid CSR sec bucket {b}: must be 1–{_N_BUCKETS}.")
            s = np.asarray(sensitivities[b], dtype=float)
            if len(s) != _N_TENORS:
                raise ValueError(
                    f"Bucket {b}: expected array of length {_N_TENORS}, got {len(s)}."
                )
            rw = CSR_SEC_RISK_WEIGHTS[b - 1]
            ws = s * rw
            ws_dict[b] = pd.Series(ws, index=CSR_TENOR_LABELS)

            rho = _BUCKET_RHO[b - 1]
            K   = float(np.sqrt(max(0.0, ws @ rho @ ws)))
            K_dict[b] = K
            S_dict[b] = float(np.clip(ws.sum(), -K, K))

        K_vec = np.array([K_dict[b] for b in buckets])
        S_vec = np.array([S_dict[b] for b in buckets])
        cross = CSR_SEC_CROSS_BUCKET_GAMMA * (S_vec[:, None] * S_vec[None, :])
        np.fill_diagonal(cross, 0.0)
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return CSR_Sec_Delta_Result(
            ws=ws_dict, K=K_dict, S=S_dict, capital=capital, buckets=buckets
        )

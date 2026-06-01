"""
FRTB SA CSR non-securitisation vega — CRR3 Art. 325bd.

Vega sensitivities on a 5×5 (option expiry × credit tenor) grid per bucket,
same structure as GIRR vega but applied to credit spread volatility.

References
----------
CRR3 Art. 325bd  : Vega risk weight 0.4% flat
CRR3 Art. 325bf  : Correlation parameters (same as GIRR)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    CSR_NONSEC_BUCKET_DESCS,
    CSR_NONSEC_CROSS_BUCKET_GAMMA,
    CSR_VEGA_RISK_WEIGHT,
    CSR_VEGA_ALPHA,
    VEGA_EXPIRY_LABELS,
    VEGA_EXPIRY_VERTICES,
    CSR_TENOR_LABELS,
    CSR_TENOR_VERTICES,
)

_E   = np.array(VEGA_EXPIRY_VERTICES)
_T   = np.array(CSR_TENOR_VERTICES)
_N_E = len(_E)
_N_T = len(_T)
_N   = _N_E * _N_T

_NODE_LABELS = [
    (e_lbl, t_lbl)
    for e_lbl in VEGA_EXPIRY_LABELS
    for t_lbl in CSR_TENOR_LABELS
]

def _build_rho(alpha: float, v: np.ndarray) -> np.ndarray:
    diff = np.abs(v[:, None] - v[None, :])
    mn   = np.minimum(v[:, None], v[None, :])
    rho  = np.exp(-alpha * diff / np.where(mn > 0, mn, 1.0))
    np.fill_diagonal(rho, 1.0)
    return rho

_RHO_E    = _build_rho(CSR_VEGA_ALPHA, _E)
_RHO_T    = _build_rho(CSR_VEGA_ALPHA, _T)
_RHO_VEGA = np.kron(_RHO_E, _RHO_T)


@dataclass
class CSR_Vega_Result:
    ws        : dict[int, pd.Series]
    K         : dict[int, float]
    S         : dict[int, float]
    capital   : float
    buckets   : list[int]

    def to_table(self) -> pd.DataFrame:
        rows = []
        for b in self.buckets:
            rows.append({"bucket": b, "desc": CSR_NONSEC_BUCKET_DESCS[b-1],
                         "K": self.K[b], "S": self.S[b]})
        return pd.DataFrame(rows).set_index("bucket")


class CSR_Vega_Calculator(ABC):
    @abstractmethod
    def compute(self, sensitivities: dict[int, np.ndarray]) -> CSR_Vega_Result: ...


class SA_CSR_Vega_Calculator(CSR_Vega_Calculator):
    """CRR3 Art. 325bd CSR vega calculator — 5×5 expiry×tenor grid per bucket."""

    def compute(self, sensitivities: dict[int, np.ndarray]) -> CSR_Vega_Result:
        buckets = sorted(sensitivities.keys())
        ws_dict: dict[int, pd.Series] = {}
        K_dict : dict[int, float]     = {}
        S_dict : dict[int, float]     = {}

        for b in buckets:
            s = np.asarray(sensitivities[b], dtype=float)
            if s.shape != (_N_E, _N_T):
                raise ValueError(
                    f"Bucket {b}: expected shape ({_N_E}, {_N_T}), got {s.shape}."
                )
            ws_flat = s.ravel() * CSR_VEGA_RISK_WEIGHT
            ws_dict[b] = pd.Series(
                ws_flat,
                index=pd.MultiIndex.from_tuples(_NODE_LABELS, names=["expiry", "tenor"]),
            )
            K = float(np.sqrt(max(0.0, ws_flat @ _RHO_VEGA @ ws_flat)))
            K_dict[b] = K
            S_dict[b] = float(np.clip(ws_flat.sum(), -K, K))

        K_vec = np.array([K_dict[b] for b in buckets])
        S_vec = np.array([S_dict[b] for b in buckets])
        cross = CSR_NONSEC_CROSS_BUCKET_GAMMA * (S_vec[:, None] * S_vec[None, :])
        np.fill_diagonal(cross, 0.0)
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return CSR_Vega_Result(
            ws=ws_dict, K=K_dict, S=S_dict, capital=capital, buckets=buckets
        )

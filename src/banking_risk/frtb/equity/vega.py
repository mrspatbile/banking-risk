"""
FRTB SA Equity vega — CRR3 Art. 325bd.

5 option-expiry vertices per equity bucket (no underlying tenor dimension
for equity). Correlation is expiry-only (no Kronecker product needed).

RW_equity_vega = 0.78% flat — higher than GIRR because equity vol is more
volatile than interest rate vol.

References
----------
CRR3 Art. 325bd : Vega risk weight
CRR3 Art. 325bk : Equity bucket structure and cross-bucket correlations
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    EQUITY_BUCKET_DESCS,
    EQUITY_CROSS_BUCKET_GAMMA,
    EQUITY_RESIDUAL_BUCKET_GAMMA,
    EQUITY_VEGA_RISK_WEIGHT,
    EQUITY_VEGA_ALPHA,
    VEGA_EXPIRY_LABELS,
    VEGA_EXPIRY_VERTICES,
)

_E   = np.array(VEGA_EXPIRY_VERTICES)
_N_E = len(_E)
_RESIDUAL_BKT = 11

# Expiry correlation matrix
_diff_e = np.abs(_E[:, None] - _E[None, :])
_min_e  = np.minimum(_E[:, None], _E[None, :])
_RHO_E  = np.exp(-EQUITY_VEGA_ALPHA * _diff_e / np.where(_min_e > 0, _min_e, 1.0))
np.fill_diagonal(_RHO_E, 1.0)


@dataclass
class Equity_Vega_Result:
    ws      : dict[int, pd.Series]
    K       : dict[int, float]
    S       : dict[int, float]
    capital : float
    buckets : list[int]

    def to_table(self) -> pd.DataFrame:
        rows = []
        for b in self.buckets:
            rows.append({"bucket": b, "desc": EQUITY_BUCKET_DESCS[b-1],
                         "K": self.K[b], "S": self.S[b]})
        return pd.DataFrame(rows).set_index("bucket")


class Equity_Vega_Calculator(ABC):
    @abstractmethod
    def compute(self, sensitivities: dict[int, np.ndarray]) -> Equity_Vega_Result: ...


class SA_Equity_Vega_Calculator(Equity_Vega_Calculator):
    """CRR3 equity vega: 5 expiry vertices per bucket, RW = 0.78%."""

    def compute(self, sensitivities: dict[int, np.ndarray]) -> Equity_Vega_Result:
        buckets = sorted(sensitivities.keys())
        ws_dict: dict[int, pd.Series] = {}
        K_dict : dict[int, float]     = {}
        S_dict : dict[int, float]     = {}

        for b in buckets:
            s = np.asarray(sensitivities[b], dtype=float)
            if len(s) != _N_E:
                raise ValueError(
                    f"Bucket {b}: expected array of length {_N_E}, got {len(s)}."
                )
            ws = s * EQUITY_VEGA_RISK_WEIGHT
            ws_dict[b] = pd.Series(ws, index=VEGA_EXPIRY_LABELS)
            K = float(np.sqrt(max(0.0, ws @ _RHO_E @ ws)))
            K_dict[b] = K
            S_dict[b] = float(np.clip(ws.sum(), -K, K))

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

        return Equity_Vega_Result(
            ws=ws_dict, K=K_dict, S=S_dict, capital=capital, buckets=buckets
        )

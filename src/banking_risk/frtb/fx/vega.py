"""
FRTB SA FX vega — CRR3 Art. 325bd.

5 expiry vertices per currency pair, same flat cross-pair correlation ρ = 0.60
as FX delta. Within-pair vega correlation uses the same relative-difference
expiry decay as GIRR vega.

References
----------
CRR3 Art. 325bd  : Vega risk weight 0.4% flat
CRR3 Art. 325bm  : FX correlation ρ = 0.60
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    FX_CORRELATION_RHO,
    FX_VEGA_RISK_WEIGHT,
    FX_VEGA_ALPHA,
    VEGA_EXPIRY_LABELS,
    VEGA_EXPIRY_VERTICES,
)

_E   = np.array(VEGA_EXPIRY_VERTICES)
_N_E = len(_E)

_diff_e = np.abs(_E[:, None] - _E[None, :])
_min_e  = np.minimum(_E[:, None], _E[None, :])
_RHO_E  = np.exp(-FX_VEGA_ALPHA * _diff_e / np.where(_min_e > 0, _min_e, 1.0))
np.fill_diagonal(_RHO_E, 1.0)


@dataclass
class FX_Vega_Result:
    ws      : dict[str, pd.Series]
    K       : dict[str, float]
    capital : float
    pairs   : list[str]

    def to_table(self) -> pd.DataFrame:
        return pd.DataFrame({"K": self.K})


class FX_Vega_Calculator(ABC):
    @abstractmethod
    def compute(self, sensitivities: dict[str, np.ndarray]) -> FX_Vega_Result: ...


class SA_FX_Vega_Calculator(FX_Vega_Calculator):
    """CRR3 FX vega: 5 expiry vertices per currency pair, ρ = 0.60 across pairs."""

    def compute(self, sensitivities: dict[str, np.ndarray]) -> FX_Vega_Result:
        if not sensitivities:
            return FX_Vega_Result(ws={}, K={}, capital=0.0, pairs=[])

        pairs = sorted(sensitivities.keys())
        ws_dict: dict[str, pd.Series] = {}
        K_dict : dict[str, float]     = {}
        S_vec  : list[float]          = []

        for pair in pairs:
            s = np.asarray(sensitivities[pair], dtype=float)
            if len(s) != _N_E:
                raise ValueError(
                    f"Pair {pair}: expected length {_N_E}, got {len(s)}."
                )
            ws = s * FX_VEGA_RISK_WEIGHT
            ws_dict[pair] = pd.Series(ws, index=VEGA_EXPIRY_LABELS)
            K = float(np.sqrt(max(0.0, ws @ _RHO_E @ ws)))
            K_dict[pair] = K
            S_vec.append(float(np.clip(ws.sum(), -K, K)))

        K_vec   = np.array([K_dict[p] for p in pairs])
        S_arr   = np.array(S_vec)
        n       = len(pairs)
        rho_mat = np.full((n, n), FX_CORRELATION_RHO)
        np.fill_diagonal(rho_mat, 0.0)
        cross   = rho_mat * (S_arr[:, None] * S_arr[None, :])
        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return FX_Vega_Result(ws=ws_dict, K=K_dict, capital=capital, pairs=pairs)

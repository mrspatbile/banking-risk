"""
FRTB SA GIRR vega risk charge — CRR3 Art. 325bd.

SA_GIRR_Vega_Calculator receives vega sensitivities on a 2D grid of
(option expiry × underlying tenor) nodes per currency and returns the
vega capital charge.

Sensitivities come from quant-risk-engine option pricers — this module
applies only the regulatory aggregation formula.

Reference: CRR3 Art. 325bd (risk weight), Art. 325bf (correlations)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    GIRR_CROSS_BUCKET_GAMMA,
    GIRR_VEGA_ALPHA,
    GIRR_VEGA_LABELS,
    GIRR_VEGA_VERTICES,
    GIRR_VEGA_RISK_WEIGHT,
)

_E   = np.array(GIRR_VEGA_VERTICES)   # shape (n_E,)
_T   = np.array(GIRR_VEGA_VERTICES)    # shape (n_T,)
_N_E = len(_E)
_N_T = len(_T)
_N   = _N_E * _N_T                            # total nodes per currency (25)

# Node labels: "(expiry, tenor)" — used as MultiIndex for result Series
_NODE_LABELS = [
    (e_label, t_label)
    for e_label in GIRR_VEGA_LABELS
    for t_label in GIRR_VEGA_LABELS
]

# Expiry correlation matrix — relative difference formula, CRR3 Art. 325bf
# rho(e_k, e_l) = exp(-alpha × |e_k - e_l| / min(e_k, e_l))
_diff_e  = np.abs(_E[:, None] - _E[None, :])
_min_e   = np.minimum(_E[:, None], _E[None, :])
_RHO_E   = np.exp(-GIRR_VEGA_ALPHA * _diff_e / _min_e)
np.fill_diagonal(_RHO_E, 1.0)

# Tenor correlation matrix
_diff_t  = np.abs(_T[:, None] - _T[None, :])
_min_t   = np.minimum(_T[:, None], _T[None, :])
_RHO_T   = np.exp(-GIRR_VEGA_ALPHA * _diff_t / _min_t)
np.fill_diagonal(_RHO_T, 1.0)

# Full (n_E*n_T × n_E*n_T) correlation matrix via Kronecker product.
# RHO[i1*n_T+j1, i2*n_T+j2] = rho_expiry[i1,i2] × rho_tenor[j1,j2]
_RHO_VEGA = np.kron(_RHO_E, _RHO_T)


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class GIRR_Vega_Result:
    """Output of SA_GIRR_Vega_Calculator.compute() — CRR3 Art. 325bd.

    Attributes
    ----------
    ws : dict[str, pd.Series]
        Risk-weighted vega sensitivities per currency.
        Index is a MultiIndex of (expiry_label, tenor_label).
        WS_k = vega_k × RW  where RW = 0.4% flat.
    K : dict[str, float]
        Within-bucket capital per currency.
    S : dict[str, float]
        Net sensitivity per currency, capped at ±K.
    capital : float
        Total GIRR vega capital charge.
    currencies : list[str]
    """

    ws        : dict[str, pd.Series]
    K         : dict[str, float]
    S         : dict[str, float]
    capital   : float
    currencies: list[str]

    def to_table(self) -> pd.DataFrame:
        from banking_risk.utils.reporting import Dark_Style, GIRR_Reporter
        return GIRR_Reporter(Dark_Style()).to_table(self)

    def plot(self) -> None:
        from banking_risk.utils.reporting import Dark_Style, GIRR_Reporter
        GIRR_Reporter(Dark_Style()).plot(self)


# ── Abstract calculator ───────────────────────────────────────────────────────

class GIRR_Vega_Calculator(ABC):

    @abstractmethod
    def compute(
        self,
        sensitivities: dict[str, np.ndarray],
    ) -> GIRR_Vega_Result:
        """Compute GIRR vega capital charge.

        Parameters
        ----------
        sensitivities : dict[str, np.ndarray]
            Keyed by ISO currency code. Each array has shape (n_expiries, n_tenors)
            — sensitivity of instrument value to a 1% move in implied vol at each
            (option expiry, underlying tenor) node. Produced by quant-risk-engine.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_GIRR_Vega_Calculator(GIRR_Vega_Calculator):
    """CRR3 Standardised Approach GIRR vega calculator — Art. 325bd/bf.

    Methodology
    -----------
    1. Flatten sensitivities to shape (n_E * n_T,) — row-major ordering
       (expiry outer, tenor inner).

    2. Risk-weight: WS_k = vega_k × RW  where RW = 0.4% flat.

    3. Within-bucket correlation — Art. 325bf:
       rho_kl = rho_expiry(k,l) × rho_tenor(k,l)
       Built via Kronecker product: RHO = RHO_expiry ⊗ RHO_tenor.

    4. Within-bucket capital:
       K_b = sqrt(max(0, WS^T @ RHO @ WS))

    5. Net sensitivity capped at ±K_b:
       S_b = max(-K_b, min(K_b, sum(WS)))

    6. Cross-bucket aggregation (same formula as delta):
       Capital = sqrt(max(0, sum_b K_b^2 + sum_{b≠c} gamma × S_b × S_c))
       gamma = 0.5 for all GIRR bucket pairs — Art. 325bf.
    """

    def compute(
        self,
        sensitivities: dict[str, np.ndarray],
    ) -> GIRR_Vega_Result:
        currencies = list(sensitivities.keys())

        ws_dict: dict[str, pd.Series] = {}
        K_dict : dict[str, float]     = {}
        S_dict : dict[str, float]     = {}

        for ccy, s in sensitivities.items():
            s = np.asarray(s, dtype=float)

            if s.shape != (_N_E, _N_T):
                raise ValueError(
                    f"Sensitivity array for {ccy} has shape {s.shape}, "
                    f"expected ({_N_E}, {_N_T}) — (n_expiries, n_tenors)."
                )

            ws_flat = s.ravel() * GIRR_VEGA_RISK_WEIGHT
            ws_dict[ccy] = pd.Series(
                ws_flat,
                index=pd.MultiIndex.from_tuples(_NODE_LABELS, names=["expiry", "tenor"]),
            )

            K = float(np.sqrt(max(0.0, ws_flat @ _RHO_VEGA @ ws_flat)))
            K_dict[ccy] = K
            S_dict[ccy] = float(np.clip(ws_flat.sum(), -K, K))

        # Cross-bucket aggregation — identical to delta
        K_vec = np.array([K_dict[c] for c in currencies])
        S_vec = np.array([S_dict[c] for c in currencies])

        cross = GIRR_CROSS_BUCKET_GAMMA * (S_vec[:, None] * S_vec[None, :])
        np.fill_diagonal(cross, 0.0)

        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return GIRR_Vega_Result(
            ws=ws_dict,
            K=K_dict,
            S=S_dict,
            capital=capital,
            currencies=currencies,
        )

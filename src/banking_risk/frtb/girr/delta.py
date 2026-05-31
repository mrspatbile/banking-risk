"""
FRTB SA GIRR delta risk charge — CRR3 Art. 325bd.

SA_GIRR_Calculator receives PV01 sensitivities at the 10 prescribed GIRR
vertices per currency and returns the delta capital charge following the
within-bucket and cross-bucket aggregation rules.

Sensitivities come from quant-risk-engine pricers — this module applies
only the regulatory aggregation formula. No pricing logic lives here.

Reference: CRR3 Art. 325bd (risk weights), Art. 325bf (correlations)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    FRTB_GIRR_LABELS,
    FRTB_GIRR_RISK_WEIGHTS,
    FRTB_GIRR_VERTICES,
    GIRR_CORRELATION_ALPHA,
    GIRR_CROSS_BUCKET_GAMMA,
)

_VERTICES = np.array(FRTB_GIRR_VERTICES)
_WEIGHTS  = np.array(FRTB_GIRR_RISK_WEIGHTS)

# Within-bucket correlation matrix — precomputed once at import time.
# rho_kl = exp(-alpha × |t_k - t_l|) — CRR3 Art. 325bf
_diff = np.abs(_VERTICES[:, None] - _VERTICES[None, :])
_RHO  = np.exp(-GIRR_CORRELATION_ALPHA * _diff)


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class GIRR_Result:
    """Output of SA_GIRR_Calculator.compute() — CRR3 Art. 325bd.

    Attributes
    ----------
    ws : dict[str, pd.Series]
        Risk-weighted sensitivities per currency, indexed by vertex label.
        WS_k = PV01_k × RW_k.
    K : dict[str, float]
        Within-bucket capital charge per currency.
        K_b = sqrt(max(0, WS^T @ RHO @ WS)).
    S : dict[str, float]
        Net sensitivity per currency, capped at ±K_b for cross-bucket use.
    capital : float
        Total GIRR delta capital charge after cross-bucket aggregation.
    currencies : list[str]
        Currencies included in the computation.
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

class GIRR_Calculator(ABC):
    """Abstract GIRR delta calculator."""

    @abstractmethod
    def compute(
        self,
        sensitivities: dict[str, np.ndarray],
    ) -> GIRR_Result:
        """Compute the GIRR delta capital charge.

        Parameters
        ----------
        sensitivities : dict[str, np.ndarray]
            Keyed by ISO currency code. Each array has shape (10,) — one
            PV01 value per prescribed GIRR vertex (in currency units per 1bp).
            Produced by quant-risk-engine pricers, never computed here.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_GIRR_Calculator(GIRR_Calculator):
    """CRR3 Standardised Approach GIRR delta calculator — Art. 325bd/bf.

    Methodology
    -----------
    1. Risk-weight sensitivities: WS_k = PV01_k × RW_k
       where RW_k is the prescribed risk weight in bps (Art. 325bd Table 3).

    2. Within-bucket capital per currency:
       K_b = sqrt(max(0, WS^T @ RHO @ WS))
       where RHO_kl = exp(-alpha × |t_k - t_l|) — Art. 325bf.

    3. Net sensitivity capped at ±K_b:
       S_b = max(-K_b, min(K_b, sum(WS_k)))

    4. Cross-bucket (cross-currency) aggregation — Art. 325bf:
       Capital = sqrt(max(0, sum_b K_b^2 + sum_{b≠c} gamma × S_b × S_c))
       where gamma = 0.5 for all GIRR bucket pairs.
    """

    def compute(
        self,
        sensitivities: dict[str, np.ndarray],
    ) -> GIRR_Result:
        currencies = list(sensitivities.keys())

        ws_dict: dict[str, pd.Series] = {}
        K_dict : dict[str, float]     = {}
        S_dict : dict[str, float]     = {}

        for ccy, s in sensitivities.items():
            s = np.asarray(s, dtype=float)
            if len(s) != len(_VERTICES):
                raise ValueError(
                    f"Sensitivity array for {ccy} has length {len(s)}, "
                    f"expected {len(_VERTICES)} (one per GIRR vertex)."
                )

            ws = s * _WEIGHTS
            ws_dict[ccy] = pd.Series(ws, index=FRTB_GIRR_LABELS)

            K = float(np.sqrt(max(0.0, ws @ _RHO @ ws)))
            K_dict[ccy] = K
            S_dict[ccy] = float(np.clip(ws.sum(), -K, K))

        # Cross-bucket aggregation
        K_vec = np.array([K_dict[c] for c in currencies])
        S_vec = np.array([S_dict[c] for c in currencies])

        cross = GIRR_CROSS_BUCKET_GAMMA * (S_vec[:, None] * S_vec[None, :])
        np.fill_diagonal(cross, 0.0)

        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return GIRR_Result(
            ws=ws_dict,
            K=K_dict,
            S=S_dict,
            capital=capital,
            currencies=currencies,
        )

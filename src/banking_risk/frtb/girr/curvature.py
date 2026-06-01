"""
FRTB SA GIRR curvature risk charge — CRR3 Art. 325e.

SA_GIRR_Curvature_Calculator receives the net curvature P&L (CVR^+ and
CVR^-) per currency and returns the curvature capital charge following
the aggregation rules in Art. 325ef.

Curvature P&L is computed outside this module — either by full repricing
of instruments under stressed curves (preferred) or via the second-order
Taylor approximation using delta and gamma from quant-risk-engine. The
utility function curvature_pnl_from_greeks() provides the Taylor path.

Design
------
CVR_b^± = Σ_i [-V_i(r ± ΔRW) + V_i(r) + Σ_k ΔRW_k × s_ik]

where s_ik = delta sensitivity and ΔRW_k = GIRR curvature risk weight at
vertex k (same table as delta — CRR3 Art. 325bd Table 3).

With the second-order Taylor approximation:
V_i(r ± ΔRW) ≈ V_i(r) ± Σ_k ΔRW_k × s_ik + 0.5 × Σ_k γ_ik × ΔRW_k²

→ CVR_b^± ≈ -0.5 × Σ_i Σ_k γ_ik × ΔRW_k²

For linear instruments (bonds, IRS) gamma ≈ 0, so CVR ≈ 0.
Non-zero curvature charges arise from instruments with convexity
(swaptions, callable bonds, caps/floors).

References
----------
CRR3 Art. 325e  : curvature risk definition
CRR3 Art. 325ef : curvature aggregation formula
CRR3 Art. 325bd : GIRR risk weights (Table 3) — same for delta and curvature
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from banking_risk.frtb.constants import (
    FRTB_GIRR_LABELS,
    FRTB_GIRR_RISK_WEIGHTS,
    GIRR_CROSS_BUCKET_GAMMA,
)

# Curvature risk weight = delta risk weight (CRR3 Art. 325e).
# Stored in decimal for arithmetic convenience; constants.py holds bps.
_CVR_WEIGHTS = np.array(FRTB_GIRR_RISK_WEIGHTS) / 10_000   # bps → decimal


# ── Utility: Taylor-approximation CVR ────────────────────────────────────────

def curvature_pnl_from_greeks(
    delta: np.ndarray,
    gamma: np.ndarray,
    risk_weights: np.ndarray | None = None,
) -> tuple[float, float]:
    """Approximate GIRR curvature P&L from delta and gamma sensitivities.

    Uses the second-order Taylor expansion:
        CVR^± ≈ -0.5 × Σ_k γ_k × ΔRW_k²

    Because the approximation is symmetric, CVR^+ = CVR^-.
    For instruments with positive convexity (long options) the result is
    negative (gain under stress); for negative convexity (short options)
    it is positive (loss). The calculator applies max(CVR^+, CVR^-, 0) so
    only net losses contribute to capital.

    Parameters
    ----------
    delta : np.ndarray, shape (10,)
        PV01 sensitivities at the 10 GIRR vertices (currency per 1bp).
        Not used in the symmetric Taylor formula but required for the
        full repricing path (included for API completeness).
    gamma : np.ndarray, shape (10,)
        Second-order sensitivities at the 10 GIRR vertices
        (currency per 1bp²). Produced by quant-risk-engine.
    risk_weights : np.ndarray, shape (10,), optional
        Curvature risk weights in decimal. Defaults to the CRR3 Art. 325bd
        GIRR delta risk weights converted to decimal.

    Returns
    -------
    tuple[float, float]
        (cvr_up, cvr_down) — symmetric under the Taylor approximation.
    """
    delta = np.asarray(delta, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    rw    = np.asarray(risk_weights, dtype=float) if risk_weights is not None else _CVR_WEIGHTS

    if len(delta) != len(_CVR_WEIGHTS) or len(gamma) != len(_CVR_WEIGHTS):
        raise ValueError(
            f"delta and gamma must have length {len(_CVR_WEIGHTS)} "
            f"(one per GIRR vertex); got delta={len(delta)}, gamma={len(gamma)}."
        )

    cvr = float(-0.5 * (gamma * rw ** 2).sum())
    return cvr, cvr


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class GIRR_Curvature_Result:
    """Output of SA_GIRR_Curvature_Calculator.compute() — CRR3 Art. 325e.

    Attributes
    ----------
    cvr_up : dict[str, float]
        Net curvature P&L per currency under the up stress scenario.
        Positive = curvature loss (increases capital).
    cvr_down : dict[str, float]
        Net curvature P&L per currency under the down stress scenario.
    K : dict[str, float]
        Per-currency curvature capital charge: max(CVR_b^+, CVR_b^-, 0).
    S : dict[str, float]
        Net curvature sensitivity capped at ±K_b, used for cross-bucket
        aggregation.
    capital : float
        Total GIRR curvature capital charge after cross-currency aggregation.
    currencies : list[str]
    """

    cvr_up    : dict[str, float]
    cvr_down  : dict[str, float]
    K         : dict[str, float]
    S         : dict[str, float]
    capital   : float
    currencies: list[str]

    def to_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"cvr_up": self.cvr_up, "cvr_down": self.cvr_down,
             "K": self.K, "S": self.S},
        ).T


# ── Abstract calculator ───────────────────────────────────────────────────────

class GIRR_Curvature_Calculator(ABC):

    @abstractmethod
    def compute(
        self,
        cvr_up  : dict[str, float],
        cvr_down: dict[str, float],
    ) -> GIRR_Curvature_Result:
        """Compute the GIRR curvature capital charge.

        Parameters
        ----------
        cvr_up : dict[str, float]
            Net curvature P&L per currency under the simultaneous upward
            stress of all GIRR risk factors (Σ_i CVR_i^+ per currency).
            Computed externally via full repricing or curvature_pnl_from_greeks().
        cvr_down : dict[str, float]
            Same for the downward stress scenario. Must have the same
            currency keys as cvr_up.
        """
        ...


# ── SA implementation ─────────────────────────────────────────────────────────

class SA_GIRR_Curvature_Calculator(GIRR_Curvature_Calculator):
    """CRR3 Standardised Approach GIRR curvature calculator — Art. 325e/325ef.

    Methodology
    -----------
    1. Per-currency capital charge:
       K_b = max(CVR_b^+, CVR_b^-, 0)
       Only positive curvature losses (net losses under stress) attract
       capital. The worse of the two scenarios drives K_b.

    2. Net sensitivity for cross-bucket aggregation:
       S_b = max(-K_b, min(K_b, CVR_b^worst))
       where CVR_b^worst is the scenario that produced K_b.

    3. Cross-currency aggregation — same formula as GIRR delta (Art. 325bf):
       Capital = sqrt(max(0, Σ_b K_b² + Σ_{b≠c} γ × S_b × S_c))
       γ = 0.5 for all GIRR currency pairs.
    """

    def compute(
        self,
        cvr_up  : dict[str, float],
        cvr_down: dict[str, float],
    ) -> GIRR_Curvature_Result:
        if set(cvr_up) != set(cvr_down):
            raise ValueError(
                "cvr_up and cvr_down must contain the same currency keys."
            )

        currencies = list(cvr_up.keys())
        K_dict: dict[str, float] = {}
        S_dict: dict[str, float] = {}

        for ccy in currencies:
            up   = float(cvr_up[ccy])
            down = float(cvr_down[ccy])
            K    = max(up, down, 0.0)
            K_dict[ccy] = K
            worst = up if up >= down else down
            S_dict[ccy] = float(np.clip(worst, -K, K))

        K_vec = np.array([K_dict[c] for c in currencies])
        S_vec = np.array([S_dict[c] for c in currencies])

        cross = GIRR_CROSS_BUCKET_GAMMA * (S_vec[:, None] * S_vec[None, :])
        np.fill_diagonal(cross, 0.0)

        capital = float(np.sqrt(max(0.0, (K_vec ** 2).sum() + cross.sum())))

        return GIRR_Curvature_Result(
            cvr_up=cvr_up,
            cvr_down=cvr_down,
            K=K_dict,
            S=S_dict,
            capital=capital,
            currencies=currencies,
        )

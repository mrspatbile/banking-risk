"""
Probability of Default (PD) models.

PD is the likelihood that a counterparty defaults within a one-year horizon.
Two standard approaches are provided:

1. Rating_PD_Model — maps S&P-style ratings to through-the-cycle PDs using
   Basel/EBA anchor calibrations (long-run observed default rates).

2. Logistic_PD_Model — point-in-time PD from financial statement features
   via logistic regression: PD = σ(β₀ + Σ βₖ xₖ).

References
----------
CRR Art. 163         : PD floor — 0.03 % for non-defaulted exposures
EBA/GL/2017/16       : Guidelines on PD estimation
Basel III (2017) §7  : PD calibration and through-the-cycle requirements
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


# ── CRR Art. 163 minimum PD ───────────────────────────────────────────────────

_PD_FLOOR: float = 0.0003   # 0.03 % — applies to all non-defaulted exposures


# ── Basel / EBA anchor PD table ───────────────────────────────────────────────
# Through-the-cycle 1-year PDs calibrated to long-run agency default rates.
# S&P scale; also compatible with Moody's / Fitch mappings.

RATING_PD_TABLE: dict[str, float] = {
    "AAA"  : 0.0003,   # floored at CRR minimum
    "AA+"  : 0.0003,
    "AA"   : 0.0005,
    "AA-"  : 0.0007,
    "A+"   : 0.0009,
    "A"    : 0.0009,
    "A-"   : 0.0013,
    "BBB+" : 0.0025,
    "BBB"  : 0.0025,
    "BBB-" : 0.0050,
    "BB+"  : 0.0075,
    "BB"   : 0.0100,
    "BB-"  : 0.0200,
    "B+"   : 0.0350,
    "B"    : 0.0500,
    "B-"   : 0.1000,
    "CCC+" : 0.1500,
    "CCC"  : 0.2000,
    "CCC-" : 0.3000,
    "CC"   : 0.5000,
    "D"    : 1.0000,   # already in default
}


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class PD_Estimate:
    """PD estimate for a single obligor.

    Attributes
    ----------
    pd : float
        1-year PD in decimal; clamped to [0.0003, 1.0].
    rating : str | None
        Rating used (rating-based model) or None (logistic model).
    model : str
        'rating_table' or 'logistic'.
    log_odds : float | None
        Raw log-odds from the logistic model; None for rating-based.
    """

    pd       : float
    rating   : str | None
    model    : str
    log_odds : float | None = None


# ── Rating-based model ────────────────────────────────────────────────────────

class Rating_PD_Model:
    """Maps S&P-style ratings to through-the-cycle PDs.

    Parameters
    ----------
    pd_table : dict[str, float], optional
        Custom rating → PD mapping. Defaults to RATING_PD_TABLE.
    """

    def __init__(self, pd_table: dict[str, float] | None = None) -> None:
        self._table = pd_table if pd_table is not None else RATING_PD_TABLE

    def predict(self, rating: str) -> PD_Estimate:
        """Return the PD for a given rating string.

        Parameters
        ----------
        rating : str
            S&P-style rating (e.g. 'BBB', 'BB+', 'D'). Case-insensitive.

        Raises
        ------
        ValueError
            If the rating is not present in the table.
        """
        key = rating.upper()
        if key not in self._table:
            raise ValueError(
                f"Unknown rating '{rating}'. "
                f"Valid ratings: {sorted(self._table)}"
            )
        raw = self._table[key]
        pd_val = raw if key == "D" else max(raw, _PD_FLOOR)
        return PD_Estimate(pd=pd_val, rating=key, model="rating_table")


# ── Logistic regression model ─────────────────────────────────────────────────

class Logistic_PD_Model:
    """Point-in-time PD from financial features via logistic regression.

    PD = σ(β₀ + Σ βₖ xₖ)  where σ(z) = 1 / (1 + e^−z)

    Typical features in corporate credit scoring
    --------------------------------------------
    leverage         :  total_debt / ebitda
    interest_coverage:  ebit / interest_expense  (negative coef)
    roa              :  net_income / total_assets (negative coef)
    current_ratio    :  current_assets / current_liabilities (negative coef)
    size             :  log(total_assets in €M)   (negative coef — larger firms less risky)

    Parameters
    ----------
    coefficients : dict[str, float]
        Feature name → β coefficient. Positive coef → higher feature → higher PD.
    intercept : float
        β₀ intercept term. Default 0.0 (neutral prior).
    """

    def __init__(
        self,
        coefficients : dict[str, float],
        intercept    : float = 0.0,
    ) -> None:
        self._coef      = dict(coefficients)
        self._intercept = float(intercept)

    def predict(self, features: dict[str, float]) -> PD_Estimate:
        """Compute PD from financial features.

        Unknown feature names are ignored; features absent from
        `coefficients` contribute zero to the log-odds.

        Parameters
        ----------
        features : dict[str, float]

        Returns
        -------
        PD_Estimate
            PD clamped to [0.0003, 1.0] per CRR Art. 163.
        """
        log_odds = self._intercept + sum(
            self._coef.get(k, 0.0) * v for k, v in features.items()
        )
        with np.errstate(over="ignore"):
            raw = float(1.0 / (1.0 + np.exp(-log_odds)))
        pd_val = float(np.clip(raw, _PD_FLOOR, 1.0))
        return PD_Estimate(
            pd=pd_val,
            rating=None,
            model="logistic",
            log_odds=float(log_odds),
        )

"""
Expected Loss and IRB unexpected-loss capital formula.

Expected Loss (EL = PD × LGD × EAD) is the statistical average loss on a
credit portfolio over a one-year horizon. It is the basis for loan-loss
provisioning (IFRS 9 Stage classification) and is deducted from CET1 to
the extent it exceeds accounting provisions.

The IRB unexpected-loss (UL) capital requirement K represents the additional
loss beyond EL at a 99.9 % confidence level. Risk-Weighted Assets (RWA) are
derived from K via the Basel capital multiplier.

IRB capital formula — CRR Art. 153 (corporate / institution exposures)
-----------------------------------------------------------------------
1. Asset correlation:
   R = 0.12 × h + 0.24 × (1 − h)
   where h = (1 − e^(−50 PD)) / (1 − e^(−50))

2. Unexpected-loss capital K (fraction of EAD):
   K = max(0, LGD × N[(1−R)^(−½) × G(PD) + (R/(1−R))^½ × G(0.999)] − PD × LGD)
   N = standard normal CDF, G = its inverse.

3. Maturity adjustment (CRR Art. 162):
   b   = (0.11852 − 0.05478 × ln(PD))²
   MA  = (1 + (M − 2.5) × b) / (1 − 1.5 × b)
   At M = 1.0 year, MA = 1.0 exactly.

4. Risk-Weighted Assets:
   RWA = K × 12.5 × EAD × MA

References
----------
CRR Art. 153    : Asset correlation and IRB capital formula
CRR Art. 154    : Retail IRB (not implemented here — uses fixed R = 0.15)
CRR Art. 157    : EAD estimation
CRR Art. 162    : Effective maturity and maturity adjustment
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm as _norm

_N    = _norm.cdf    # standard normal CDF
_G    = _norm.ppf    # standard normal quantile function (inverse CDF)

_CORR_A  : float = 0.12    # CRR Art. 153 lower correlation bound
_CORR_B  : float = 0.24    # CRR Art. 153 upper correlation bound
_CONF    : float = 0.999   # supervisory confidence level
_EXP_50  : float = float(np.exp(-50.0))


# ── Input ─────────────────────────────────────────────────────────────────────

@dataclass
class EL_Position:
    """A single credit exposure for EL and IRB capital calculation.

    Parameters
    ----------
    name : str
    ead : float
        Exposure at Default in currency units.
    pd : float
        1-year PD in decimal (e.g. 0.0025 = 0.25 %).
    lgd : float
        LGD in decimal (e.g. 0.45 = 45 %).
    maturity_years : float
        Effective maturity M in years. CRR Art. 162 typical default is 2.5.
        Clamped to [1, 5] by the maturity adjustment.
    """

    name           : str
    ead            : float
    pd             : float
    lgd            : float
    maturity_years : float = 2.5


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class EL_Result:
    """Output of Expected_Loss_Calculator.compute().

    Attributes
    ----------
    detail : pd.DataFrame
        Per-position columns: ead, pd, lgd, maturity_years, el, K, rwa.
        Index = position name.
    total_el : float
        Portfolio expected loss (sum of all ELs).
    total_ead : float
        Portfolio total EAD.
    total_rwa : float
        Portfolio total RWA from the IRB formula.
    el_ratio : float
        total_el / total_ead — portfolio average EL rate.
    """

    detail    : pd.DataFrame
    total_el  : float
    total_ead : float
    total_rwa : float
    el_ratio  : float


# ── Calculator ────────────────────────────────────────────────────────────────

class Expected_Loss_Calculator:
    """Compute EL and IRB unexpected-loss capital for a portfolio.

    EL = PD × LGD × EAD (expected loss — provisioned against IFRS 9).
    K  = IRB formula above (unexpected loss — regulatory capital charge).
    RWA = K × 12.5 × EAD × MA.

    Usage
    -----
    positions = [
        EL_Position("Corp_A", ead=5_000_000, pd=0.0025, lgd=0.45, maturity_years=3.0),
        EL_Position("SME_B",  ead=1_000_000, pd=0.0100, lgd=0.35, maturity_years=2.0),
    ]
    result = Expected_Loss_Calculator().compute(positions)
    result.detail[["el", "K", "rwa"]]
    """

    def compute(self, positions: list[EL_Position]) -> EL_Result:
        if not positions:
            empty = pd.DataFrame(
                columns=["ead", "pd", "lgd", "maturity_years", "el", "K", "rwa"]
            )
            return EL_Result(
                detail=empty,
                total_el=0.0,
                total_ead=0.0,
                total_rwa=0.0,
                el_ratio=0.0,
            )

        rows = []
        for pos in positions:
            el  = pos.pd * pos.lgd * pos.ead
            k   = _irb_capital(pos.pd, pos.lgd)
            ma  = _maturity_adjustment(pos.pd, pos.maturity_years)
            rwa = k * 12.5 * pos.ead * ma
            rows.append(
                {
                    "name"          : pos.name,
                    "ead"           : pos.ead,
                    "pd"            : pos.pd,
                    "lgd"           : pos.lgd,
                    "maturity_years": pos.maturity_years,
                    "el"            : el,
                    "K"             : k,
                    "rwa"           : rwa,
                }
            )

        detail    = pd.DataFrame(rows).set_index("name")
        total_el  = float(detail["el"].sum())
        total_ead = float(detail["ead"].sum())
        total_rwa = float(detail["rwa"].sum())
        el_ratio  = total_el / total_ead if total_ead > 0.0 else 0.0

        return EL_Result(
            detail=detail,
            total_el=total_el,
            total_ead=total_ead,
            total_rwa=total_rwa,
            el_ratio=el_ratio,
        )


# ── Private helpers ───────────────────────────────────────────────────────────

def _asset_correlation(pd: float) -> float:
    """CRR Art. 153 corporate asset correlation R(PD)."""
    h = (1.0 - np.exp(-50.0 * pd)) / (1.0 - _EXP_50)
    return _CORR_A * h + _CORR_B * (1.0 - h)


def _irb_capital(pd: float, lgd: float) -> float:
    """CRR Art. 153 unexpected-loss capital K as a fraction of EAD.

    Returns 0.0 for pd ≤ 0 (no default risk) and for pd ≥ 1.0
    (fully defaulted — all loss is expected, no unexpected-loss charge).
    """
    if pd <= 0.0:
        return 0.0
    if pd >= 1.0:
        return 0.0

    r = _asset_correlation(pd)
    k = (
        lgd * float(_N(
            (1.0 - r) ** (-0.5) * float(_G(pd))
            + (r / (1.0 - r)) ** 0.5 * float(_G(_CONF))
        ))
        - pd * lgd
    )
    return float(max(0.0, k))


def _maturity_adjustment(pd: float, maturity_years: float) -> float:
    """CRR Art. 162 maturity adjustment factor.

    MA = (1 + (M − 2.5) × b) / (1 − 1.5 × b)
    At M = 1.0, MA = 1.0 exactly (denominator equals numerator).
    """
    pd_safe = max(pd, 1e-10)
    b  = (0.11852 - 0.05478 * np.log(pd_safe)) ** 2
    ma = (1.0 + (maturity_years - 2.5) * b) / (1.0 - 1.5 * b)
    return float(ma)

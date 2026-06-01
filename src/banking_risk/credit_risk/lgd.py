"""
Loss Given Default (LGD) models.

LGD is the expected fraction of the Exposure at Default (EAD) that is
lost if the counterparty defaults. This module implements the CRR
Foundation IRB approach, which derives LGD from collateral type,
collateral value (net of haircuts), and regulatory floor values.

Methodology — CRR Art. 228–230
-------------------------------
1. Net collateral:
   C_net = collateral_value × (1 − haircut)

2. Coverage ratio:
   coverage = min(1, C_net / EAD)

3. Blended LGD:
   LGD = LGD_unsecured × (1 − coverage) + LGD_floor × coverage

   Equivalent to:
   LGD = LGD_unsecured − (LGD_unsecured − LGD_floor) × coverage

4. Regulatory floor:
   LGD = max(LGD_blended, LGD_floor)

For UNSECURED and SUBORDINATED exposures there is no collateral and
LGD equals the prescribed floor directly.

References
----------
CRR Art. 228–230 : Collateral valuation and LGD floors
CRR Art. 161     : LGD input floors for Foundation IRB
EBA/GL/2020/06   : Guidelines on LGD estimation
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


# ── Collateral types and CRR floors ──────────────────────────────────────────

class Collateral_Type(StrEnum):
    RESIDENTIAL_RE  = "residential_re"   # CRR Art. 230 — 10 % floor
    COMMERCIAL_RE   = "commercial_re"    # CRR Art. 230 — 15 % floor
    FINANCIAL       = "financial"        # Eligible financial collateral — 0 %
    UNSECURED       = "unsecured"        # Senior unsecured — 45 %
    SUBORDINATED    = "subordinated"     # Subordinated / junior — 75 %


LGD_FLOORS: dict[Collateral_Type, float] = {
    Collateral_Type.RESIDENTIAL_RE  : 0.10,
    Collateral_Type.COMMERCIAL_RE   : 0.15,
    Collateral_Type.FINANCIAL       : 0.00,
    Collateral_Type.UNSECURED       : 0.45,
    Collateral_Type.SUBORDINATED    : 0.75,
}

_LGD_UNSECURED: float = 0.45   # CRR Art. 230 senior unsecured baseline


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class LGD_Estimate:
    """LGD estimate for a single exposure.

    Attributes
    ----------
    lgd : float
        LGD in decimal; in [lgd_floor, 1.0].
    collateral_type : Collateral_Type
    coverage_ratio : float
        Effective collateral coverage = min(1, C_net / EAD).
        0.0 = unsecured; 1.0 = fully collateralised.
    lgd_floor : float
        Regulatory minimum for this collateral type.
    """

    lgd             : float
    collateral_type : Collateral_Type
    coverage_ratio  : float
    lgd_floor       : float


# ── CRR LGD model ────────────────────────────────────────────────────────────

class CRR_LGD_Model:
    """Foundation IRB LGD via CRR Art. 228–230 collateral haircut approach.

    Parameters
    ----------
    lgd_unsecured : float, optional
        Senior unsecured LGD before any collateral benefit.
        Default 0.45 per CRR Art. 230.
    """

    def __init__(self, lgd_unsecured: float = _LGD_UNSECURED) -> None:
        self._lgd_u = float(lgd_unsecured)

    def estimate(
        self,
        ead              : float,
        collateral_value : float,
        collateral_type  : Collateral_Type,
        haircut          : float = 0.0,
    ) -> LGD_Estimate:
        """Compute LGD for a single exposure.

        Parameters
        ----------
        ead : float
            Exposure at Default in currency units.
        collateral_value : float
            Gross collateral value in currency units. Pass 0.0 for
            unsecured exposures.
        collateral_type : Collateral_Type
            Determines the regulatory LGD floor.
        haircut : float, optional
            Collateral value haircut in decimal (e.g. 0.25 = 25 %).
            Default 0.0 (no haircut).

        Returns
        -------
        LGD_Estimate
        """
        floor = LGD_FLOORS[collateral_type]

        if collateral_type in (Collateral_Type.UNSECURED, Collateral_Type.SUBORDINATED):
            return LGD_Estimate(
                lgd=floor,
                collateral_type=collateral_type,
                coverage_ratio=0.0,
                lgd_floor=floor,
            )

        c_net    = collateral_value * (1.0 - haircut)
        coverage = min(1.0, c_net / ead) if ead > 0.0 else 0.0

        lgd_blended = self._lgd_u * (1.0 - coverage) + floor * coverage
        lgd         = max(lgd_blended, floor)

        return LGD_Estimate(
            lgd=float(lgd),
            collateral_type=collateral_type,
            coverage_ratio=float(coverage),
            lgd_floor=floor,
        )

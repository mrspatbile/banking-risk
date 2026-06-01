"""
Collateral Management — Encumbrance and Availability.

Tracks asset encumbrance (pledged vs. free assets), identifies the
unencumbered HQLA buffer, and quantifies the pool available for additional
secured funding.

Asset encumbrance is reported under EBA ITS 2021/05 and is a key input
to both the LCR liquidity buffer and ILAAP contingency capacity assessments.

References
----------
EBA ITS 2021/05      : Supervisory reporting — asset encumbrance
EBA/GL/2014/03       : Asset encumbrance guidelines
CRR Art. 416–425     : HQLA eligibility for LCR
"""

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


# ── Asset classes and HQLA eligibility ───────────────────────────────────────

class Asset_Class(StrEnum):
    CASH                = "cash"
    CENTRAL_BANK        = "central_bank_reserves"
    GOVT_BOND           = "government_bond"
    COVERED_BOND        = "covered_bond"
    RMBS                = "rmbs"
    CORPORATE_BOND      = "corporate_bond_ig"
    EQUITY              = "equity"
    LOAN                = "loan"
    OTHER               = "other"


# Default HQLA level per asset class (None = not HQLA eligible)
HQLA_ELIGIBILITY: dict[Asset_Class, str | None] = {
    Asset_Class.CASH:          "1",
    Asset_Class.CENTRAL_BANK:  "1",
    Asset_Class.GOVT_BOND:     "1",
    Asset_Class.COVERED_BOND:  "2A",
    Asset_Class.RMBS:          "2B",
    Asset_Class.CORPORATE_BOND:"2B",
    Asset_Class.EQUITY:        "2B",
    Asset_Class.LOAN:          None,
    Asset_Class.OTHER:         None,
}


# ── Input ─────────────────────────────────────────────────────────────────────

@dataclass
class Collateral_Asset:
    """A single balance-sheet asset.

    Parameters
    ----------
    name : str
    asset_class : Asset_Class
    market_value : float
        Current market value in currency units.
    encumbered : bool
        True if pledged (repo, covered bond pool, derivative margin, etc.).
    haircut : float
        Standard repo/central-bank haircut in decimal.
        Used to compute collateral value available for funding.
    hqla_level : str | None
        Override HQLA_ELIGIBILITY default. E.g. pass "1" for an ECB-eligible
        government bond when the default would differ.
    """

    name        : str
    asset_class : Asset_Class
    market_value: float
    encumbered  : bool
    haircut     : float       = 0.0
    hqla_level  : str | None  = None

    @property
    def effective_hqla_level(self) -> str | None:
        if self.hqla_level is not None:
            return self.hqla_level
        return HQLA_ELIGIBILITY[self.asset_class]

    @property
    def collateral_value(self) -> float:
        """Post-haircut value available as collateral."""
        return self.market_value * (1.0 - self.haircut)


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class Encumbrance_Result:
    """Output of Collateral_Manager.analyse().

    Attributes
    ----------
    total_assets : float
        Sum of all market values.
    encumbered : float
        Market value of pledged assets.
    unencumbered : float
        Market value of free assets.
    encumbrance_ratio : float
        encumbered / total_assets.
    available_hqla : float
        Post-haircut value of unencumbered HQLA-eligible assets (LCR buffer).
    available_hqla_by_level : dict[str, float]
        Breakdown by HQLA level: {"1": ..., "2A": ..., "2B": ...}.
    available_for_repo : float
        Post-haircut value of all unencumbered assets (HQLA and non-HQLA).
    detail : pd.DataFrame
        Per-asset: asset_class, market_value, encumbered, haircut,
        hqla_level, collateral_value.
    """

    total_assets            : float
    encumbered              : float
    unencumbered            : float
    encumbrance_ratio       : float
    available_hqla          : float
    available_hqla_by_level : dict[str, float]
    available_for_repo      : float
    detail                  : pd.DataFrame


# ── Manager ───────────────────────────────────────────────────────────────────

class Collateral_Manager:
    """Analyse asset encumbrance and collateral availability."""

    def analyse(self, assets: list[Collateral_Asset]) -> Encumbrance_Result:
        rows = []
        total_mv  = 0.0
        encumbered_mv = 0.0
        hqla_by_level: dict[str, float] = {"1": 0.0, "2A": 0.0, "2B": 0.0}
        repo_available = 0.0

        for asset in assets:
            total_mv += asset.market_value
            if asset.encumbered:
                encumbered_mv += asset.market_value

            lvl = asset.effective_hqla_level
            if not asset.encumbered:
                repo_available += asset.collateral_value
                if lvl in hqla_by_level:
                    hqla_by_level[lvl] += asset.collateral_value

            rows.append(
                {
                    "name"           : asset.name,
                    "asset_class"    : asset.asset_class,
                    "market_value"   : asset.market_value,
                    "encumbered"     : asset.encumbered,
                    "haircut"        : asset.haircut,
                    "hqla_level"     : lvl if lvl else "—",
                    "collateral_value": asset.collateral_value,
                }
            )

        unencumbered     = total_mv - encumbered_mv
        enc_ratio        = encumbered_mv / total_mv if total_mv > 0.0 else 0.0
        available_hqla   = sum(hqla_by_level.values())

        return Encumbrance_Result(
            total_assets=total_mv,
            encumbered=encumbered_mv,
            unencumbered=unencumbered,
            encumbrance_ratio=enc_ratio,
            available_hqla=available_hqla,
            available_hqla_by_level=hqla_by_level,
            available_for_repo=repo_available,
            detail=pd.DataFrame(rows),
        )

"""
Net Stable Funding Ratio (NSFR) — CRR Art. 428a–428ax.

NSFR = Available Stable Funding (ASF) / Required Stable Funding (RSF) ≥ 100%

ASF: liabilities and equity weighted by their stability over a 1-year horizon.
RSF: assets weighted by the stable funding they require over a 1-year horizon.

References
----------
CRR Art. 428a–428ax : NSFR framework and factor tables
EBA/GL/2021/03      : NSFR reporting guidelines
"""

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


# ── Standard ASF factors (CRR Art. 428k–428o) ────────────────────────────────

class ASF_Category(StrEnum):
    TIER1_CAPITAL          = "tier1_capital"
    TIER2_CAPITAL_GT1Y     = "tier2_capital_gt1y"
    RETAIL_STABLE_GT6M     = "retail_stable_gt6m"
    RETAIL_STABLE_LT6M     = "retail_stable_lt6m"
    RETAIL_LESS_STABLE_GT6M = "retail_less_stable_gt6m"
    RETAIL_LESS_STABLE_LT6M = "retail_less_stable_lt6m"
    CORP_NON_FIN_GT6M      = "corporate_non_financial_gt6m"
    CORP_NON_FIN_LT6M      = "corporate_non_financial_lt6m"
    FIN_INSTITUTION_GT6M   = "financial_institution_gt6m"
    FIN_INSTITUTION_LT6M   = "financial_institution_lt6m"
    SECURED_FUNDING_GT1Y   = "secured_funding_gt1y"
    OTHER_LIABILITIES_GT1Y = "other_liabilities_gt1y"
    OTHER_LIABILITIES_LT1Y = "other_liabilities_lt1y"


ASF_FACTORS: dict[ASF_Category, float] = {
    ASF_Category.TIER1_CAPITAL:           1.00,
    ASF_Category.TIER2_CAPITAL_GT1Y:      1.00,
    ASF_Category.RETAIL_STABLE_GT6M:      0.975,
    ASF_Category.RETAIL_STABLE_LT6M:      0.95,
    ASF_Category.RETAIL_LESS_STABLE_GT6M: 0.90,
    ASF_Category.RETAIL_LESS_STABLE_LT6M: 0.90,
    ASF_Category.CORP_NON_FIN_GT6M:       0.90,
    ASF_Category.CORP_NON_FIN_LT6M:       0.50,
    ASF_Category.FIN_INSTITUTION_GT6M:    0.50,
    ASF_Category.FIN_INSTITUTION_LT6M:    0.00,
    ASF_Category.SECURED_FUNDING_GT1Y:    1.00,
    ASF_Category.OTHER_LIABILITIES_GT1Y:  1.00,
    ASF_Category.OTHER_LIABILITIES_LT1Y:  0.00,
}


# ── Standard RSF factors (CRR Art. 428r–428ae) ────────────────────────────────

class RSF_Category(StrEnum):
    CASH                    = "cash"
    CENTRAL_BANK_RESERVES   = "central_bank_reserves"
    HQLA_L1_UNENCUMBERED    = "hqla_l1_unencumbered"
    HQLA_L2A_UNENCUMBERED   = "hqla_l2a_unencumbered"
    HQLA_L2B_UNENCUMBERED   = "hqla_l2b_unencumbered"
    NON_HQLA_SECURITIES_LT6M = "non_hqla_securities_lt6m"
    NON_HQLA_SECURITIES_GT6M = "non_hqla_securities_gt6m"
    LOANS_RETAIL_LT1Y        = "loans_retail_lt1y"
    LOANS_RETAIL_MORTGAGE_GT1Y = "loans_retail_mortgage_gt1y"
    LOANS_CORPORATE_GT1Y     = "loans_corporate_gt1y"
    OTHER_ASSETS              = "other_assets"
    OFF_BALANCE_COMMITMENTS   = "off_balance_sheet_commitments"


RSF_FACTORS: dict[RSF_Category, float] = {
    RSF_Category.CASH:                       0.00,
    RSF_Category.CENTRAL_BANK_RESERVES:      0.00,
    RSF_Category.HQLA_L1_UNENCUMBERED:       0.05,
    RSF_Category.HQLA_L2A_UNENCUMBERED:      0.15,
    RSF_Category.HQLA_L2B_UNENCUMBERED:      0.50,
    RSF_Category.NON_HQLA_SECURITIES_LT6M:   0.10,
    RSF_Category.NON_HQLA_SECURITIES_GT6M:   0.50,
    RSF_Category.LOANS_RETAIL_LT1Y:          0.50,
    RSF_Category.LOANS_RETAIL_MORTGAGE_GT1Y: 0.65,
    RSF_Category.LOANS_CORPORATE_GT1Y:       0.65,
    RSF_Category.OTHER_ASSETS:               1.00,
    RSF_Category.OFF_BALANCE_COMMITMENTS:    0.05,
}


# ── Input data classes ────────────────────────────────────────────────────────

@dataclass
class ASF_Item:
    """A liability or equity item contributing to Available Stable Funding.

    Parameters
    ----------
    name : str
    amount : float
    category : ASF_Category | None
        Use standard factor. Pass None and set factor to override.
    factor : float | None
        Custom ASF factor in [0, 1].
    """

    name     : str
    amount   : float
    category : ASF_Category | None = None
    factor   : float | None        = None

    @property
    def asf_factor(self) -> float:
        if self.category is not None:
            return ASF_FACTORS[self.category]
        if self.factor is not None:
            return self.factor
        raise ValueError(f"ASF_Item '{self.name}': set category or factor.")

    @property
    def asf_contribution(self) -> float:
        return self.amount * self.asf_factor


@dataclass
class RSF_Item:
    """An asset item requiring stable funding.

    Parameters
    ----------
    name : str
    amount : float
    category : RSF_Category | None
    factor : float | None
        Custom RSF factor in [0, 1].
    """

    name     : str
    amount   : float
    category : RSF_Category | None = None
    factor   : float | None        = None

    @property
    def rsf_factor(self) -> float:
        if self.category is not None:
            return RSF_FACTORS[self.category]
        if self.factor is not None:
            return self.factor
        raise ValueError(f"RSF_Item '{self.name}': set category or factor.")

    @property
    def rsf_contribution(self) -> float:
        return self.amount * self.rsf_factor


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class NSFR_Result:
    """Output of SA_NSFR_Calculator.compute().

    Attributes
    ----------
    available_stable_funding : float
    required_stable_funding : float
    nsfr : float
        ASF / RSF expressed as a ratio (1.0 = 100%).
    passes : bool
        True when nsfr ≥ 1.0.
    asf_detail, rsf_detail : pd.DataFrame
    """

    available_stable_funding : float
    required_stable_funding  : float
    nsfr                     : float
    passes                   : bool
    asf_detail               : pd.DataFrame
    rsf_detail               : pd.DataFrame


# ── Calculator ────────────────────────────────────────────────────────────────

class SA_NSFR_Calculator:
    """CRR Art. 428a–428ax NSFR calculator."""

    def compute(
        self,
        asf_items : list[ASF_Item],
        rsf_items : list[RSF_Item],
    ) -> NSFR_Result:

        asf_rows = []
        total_asf = 0.0
        for item in asf_items:
            contrib = item.asf_contribution
            total_asf += contrib
            asf_rows.append(
                {
                    "name"    : item.name,
                    "amount"  : item.amount,
                    "factor"  : item.asf_factor,
                    "asf"     : contrib,
                }
            )

        rsf_rows = []
        total_rsf = 0.0
        for item in rsf_items:
            contrib = item.rsf_contribution
            total_rsf += contrib
            rsf_rows.append(
                {
                    "name"    : item.name,
                    "amount"  : item.amount,
                    "factor"  : item.rsf_factor,
                    "rsf"     : contrib,
                }
            )

        nsfr   = total_asf / total_rsf if total_rsf > 0.0 else float("inf")
        passes = nsfr >= 1.0

        return NSFR_Result(
            available_stable_funding=total_asf,
            required_stable_funding=total_rsf,
            nsfr=nsfr,
            passes=passes,
            asf_detail=pd.DataFrame(asf_rows),
            rsf_detail=pd.DataFrame(rsf_rows),
        )

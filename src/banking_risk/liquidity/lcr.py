"""
Liquidity Coverage Ratio (LCR) — CRR Art. 412–428, EBA/GL/2019/02.

LCR = HQLA / Net Cash Outflows ≥ 100%

Net Cash Outflows = Total Outflows − min(Total Inflows, 75% × Total Outflows)

HQLA is subject to level caps:
  Level 2B ≤ 15% of HQLA  →  L2B ≤ (0.15/0.85) × (L1 + L2A)
  Level 2  ≤ 40% of HQLA  →  L2A + L2B ≤ (2/3) × L1

References
----------
CRR Art. 412–428   : LCR framework
EBA/GL/2019/02     : Additional outflow and inflow rates
Commission DR 2015/61 : LCR calibration (outflow / inflow rates)
"""

from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd


# ── HQLA types and haircuts ───────────────────────────────────────────────────

class HQLA_Level(StrEnum):
    L1            = "1"             # cash, central bank, 0% RW govt bonds
    L2A           = "2A"            # covered bonds AA-, 20% RW govt
    L2B_RMBS      = "2B_rmbs"       # qualifying RMBS
    L2B_CORPORATE = "2B_corporate"  # investment-grade corporate bonds
    L2B_EQUITY    = "2B_equity"     # main-index equities


HQLA_HAIRCUTS: dict[HQLA_Level, float] = {
    HQLA_Level.L1:            0.00,
    HQLA_Level.L2A:           0.15,
    HQLA_Level.L2B_RMBS:      0.25,
    HQLA_Level.L2B_CORPORATE: 0.50,
    HQLA_Level.L2B_EQUITY:    0.50,
}

_L2_CAP_RATIO  : float = 0.40   # Level 2 ≤ 40% of HQLA
_L2B_CAP_RATIO : float = 0.15   # Level 2B ≤ 15% of HQLA
_INFLOW_CAP    : float = 0.75   # Inflows capped at 75% of outflows


# ── Standard outflow / inflow rates ──────────────────────────────────────────

class Outflow_Type(StrEnum):
    RETAIL_STABLE       = "retail_stable"
    RETAIL_LESS_STABLE  = "retail_less_stable"
    OPERATIONAL_DEPOSIT = "operational_deposit"
    NON_FINANCIAL_CORP  = "non_financial_corporate"
    FINANCIAL_INST      = "financial_institution"
    COMMITTED_CREDIT    = "committed_credit_facility"
    COMMITTED_LIQUIDITY = "committed_liquidity_facility"


OUTFLOW_RATES: dict[Outflow_Type, float] = {
    Outflow_Type.RETAIL_STABLE:       0.05,
    Outflow_Type.RETAIL_LESS_STABLE:  0.10,
    Outflow_Type.OPERATIONAL_DEPOSIT: 0.25,
    Outflow_Type.NON_FINANCIAL_CORP:  0.25,
    Outflow_Type.FINANCIAL_INST:      1.00,
    Outflow_Type.COMMITTED_CREDIT:    0.10,
    Outflow_Type.COMMITTED_LIQUIDITY: 0.30,
}


class Inflow_Type(StrEnum):
    RETAIL    = "retail"
    WHOLESALE = "wholesale"
    SECURED_L1 = "secured_level1"
    SECURED_L2 = "secured_level2"


INFLOW_RATES: dict[Inflow_Type, float] = {
    Inflow_Type.RETAIL:     0.50,
    Inflow_Type.WHOLESALE:  1.00,
    Inflow_Type.SECURED_L1: 0.00,
    Inflow_Type.SECURED_L2: 0.15,
}


# ── Input data classes ────────────────────────────────────────────────────────

@dataclass
class HQLA_Asset:
    """A single asset held as part of the liquidity buffer.

    Parameters
    ----------
    name : str
    level : HQLA_Level
    market_value : float
        Pre-haircut market value in currency units.
    additional_haircut : float
        Idiosyncratic/stress haircut on top of the regulatory minimum.
        Default 0.0.
    """

    name               : str
    level              : HQLA_Level
    market_value       : float
    additional_haircut : float = 0.0

    @property
    def adjusted_value(self) -> float:
        h = HQLA_HAIRCUTS[self.level] + self.additional_haircut
        return self.market_value * (1.0 - h)


@dataclass
class Cash_Outflow:
    """A 30-day stress outflow item.

    Parameters
    ----------
    name : str
    balance : float
        Outstanding balance or notional of the facility.
    outflow_type : Outflow_Type | None
        Use the prescribed rate from OUTFLOW_RATES. Pass None and set
        rate directly to override with a custom rate.
    rate : float | None
        Custom outflow rate in [0, 1]. Ignored when outflow_type is set.
    """

    name         : str
    balance      : float
    outflow_type : Outflow_Type | None = None
    rate         : float | None        = None

    @property
    def outflow_rate(self) -> float:
        if self.outflow_type is not None:
            return OUTFLOW_RATES[self.outflow_type]
        if self.rate is not None:
            return self.rate
        raise ValueError(f"Cash_Outflow '{self.name}': set outflow_type or rate.")

    @property
    def stressed_amount(self) -> float:
        return self.balance * self.outflow_rate


@dataclass
class Cash_Inflow:
    """A 30-day stress inflow item.

    Parameters
    ----------
    name : str
    balance : float
        Receivable balance or notional.
    inflow_type : Inflow_Type | None
    rate : float | None
        Custom inflow rate override.
    """

    name        : str
    balance     : float
    inflow_type : Inflow_Type | None = None
    rate        : float | None       = None

    @property
    def inflow_rate(self) -> float:
        if self.inflow_type is not None:
            return INFLOW_RATES[self.inflow_type]
        if self.rate is not None:
            return self.rate
        raise ValueError(f"Cash_Inflow '{self.name}': set inflow_type or rate.")

    @property
    def stressed_amount(self) -> float:
        return self.balance * self.inflow_rate


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class LCR_Result:
    """Output of SA_LCR_Calculator.compute().

    Attributes
    ----------
    hqla : float
        HQLA after haircuts and level caps.
    hqla_detail : pd.DataFrame
        Per-asset: market_value, adjusted_value, level.
    hqla_l1, hqla_l2a, hqla_l2b : float
        Level contributions after capping.
    gross_outflows : float
    gross_inflows : float
    net_outflows : float
        gross_outflows − min(gross_inflows, 75% × gross_outflows).
    lcr : float
        HQLA / net_outflows expressed as a ratio (1.0 = 100%).
    passes : bool
        True when lcr ≥ 1.0.
    outflow_detail : pd.DataFrame
    inflow_detail : pd.DataFrame
    """

    hqla           : float
    hqla_l1        : float
    hqla_l2a       : float
    hqla_l2b       : float
    hqla_detail    : pd.DataFrame
    gross_outflows : float
    gross_inflows  : float
    net_outflows   : float
    lcr            : float
    passes         : bool
    outflow_detail : pd.DataFrame
    inflow_detail  : pd.DataFrame


# ── Calculator ────────────────────────────────────────────────────────────────

class SA_LCR_Calculator:
    """CRR / Commission DR 2015/61 LCR calculator.

    Applies HQLA level caps, the 75% inflow cap, and computes
    LCR = HQLA / Net Cash Outflows.
    """

    def compute(
        self,
        hqla_assets : list[HQLA_Asset],
        outflows    : list[Cash_Outflow],
        inflows     : list[Cash_Inflow],
    ) -> LCR_Result:

        # ── HQLA ──────────────────────────────────────────────────────────────
        hqla_rows = []
        l1 = l2a = l2b = 0.0

        for asset in hqla_assets:
            av = asset.adjusted_value
            if asset.level == HQLA_Level.L1:
                l1 += av
            elif asset.level == HQLA_Level.L2A:
                l2a += av
            else:
                l2b += av
            hqla_rows.append(
                {
                    "name"          : asset.name,
                    "level"         : asset.level,
                    "market_value"  : asset.market_value,
                    "adjusted_value": av,
                }
            )

        hqla, l1_used, l2a_used, l2b_used = _apply_hqla_caps(l1, l2a, l2b)

        # ── Outflows ──────────────────────────────────────────────────────────
        out_rows = []
        gross_outflows = 0.0
        for o in outflows:
            sa = o.stressed_amount
            gross_outflows += sa
            out_rows.append(
                {
                    "name"   : o.name,
                    "balance": o.balance,
                    "rate"   : o.outflow_rate,
                    "amount" : sa,
                }
            )

        # ── Inflows (capped at 75% of gross outflows) ─────────────────────────
        in_rows = []
        raw_inflows = 0.0
        for i in inflows:
            sa = i.stressed_amount
            raw_inflows += sa
            in_rows.append(
                {
                    "name"   : i.name,
                    "balance": i.balance,
                    "rate"   : i.inflow_rate,
                    "amount" : sa,
                }
            )
        gross_inflows = raw_inflows
        capped_inflows = min(gross_inflows, _INFLOW_CAP * gross_outflows)
        net_outflows   = gross_outflows - capped_inflows

        lcr    = hqla / net_outflows if net_outflows > 0.0 else float("inf")
        passes = lcr >= 1.0

        return LCR_Result(
            hqla=hqla,
            hqla_l1=l1_used,
            hqla_l2a=l2a_used,
            hqla_l2b=l2b_used,
            hqla_detail=pd.DataFrame(hqla_rows),
            gross_outflows=gross_outflows,
            gross_inflows=gross_inflows,
            net_outflows=net_outflows,
            lcr=lcr,
            passes=passes,
            outflow_detail=pd.DataFrame(out_rows),
            inflow_detail=pd.DataFrame(in_rows),
        )


# ── HQLA cap logic ────────────────────────────────────────────────────────────

def _apply_hqla_caps(
    l1: float, l2a: float, l2b: float
) -> tuple[float, float, float, float]:
    """Apply CRR level caps; return (hqla, l1_used, l2a_used, l2b_used)."""
    # Level 2B cap: L2B ≤ (0.15/0.85) × (L1 + L2A)
    l2b_max = (_L2B_CAP_RATIO / (1.0 - _L2B_CAP_RATIO)) * (l1 + l2a)
    l2b_c   = min(l2b, l2b_max)

    # Level 2 cap: L2A + L2B ≤ (2/3) × L1
    l2_max = (_L2_CAP_RATIO / (1.0 - _L2_CAP_RATIO)) * l1
    level2  = l2a + l2b_c

    if level2 <= l2_max:
        l2a_used = l2a
        l2b_used = l2b_c
    else:
        excess   = level2 - l2_max
        l2b_red  = min(excess, l2b_c)
        l2b_used = l2b_c - l2b_red
        excess  -= l2b_red
        l2a_used = max(0.0, l2a - excess)

    return l1 + l2a_used + l2b_used, l1, l2a_used, l2b_used

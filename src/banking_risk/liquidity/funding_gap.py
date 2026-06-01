"""
Funding Gap Analysis and Rollover Risk.

Buckets contractual asset and liability cash flows by remaining maturity
to identify cumulative funding gaps and rollover risk concentrations.

A positive gap in a bucket means more assets mature than liabilities —
a liquidity surplus that reduces rollover pressure. A negative gap means
more liabilities mature, requiring the bank to refinance or liquidate assets.

Standard maturity buckets (days remaining):
  overnight (≤1), 2–7, 8–30, 31–90, 91–180, 181–365, 366–730 (1–2Y),
  731–1825 (2–5Y), >1825 (>5Y)

References
----------
EBA/GL/2015/09   : SREP liquidity adequacy — maturity ladder
EBA ITS 2021/05  : Additional monitoring metrics (maturity ladder)
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ── Standard maturity buckets (upper bound in days, inclusive) ────────────────

FUNDING_BUCKETS: list[tuple[str, float, float]] = [
    # (label, lower_days_exclusive, upper_days_inclusive)
    ("Overnight",  0,    1),
    ("2-7D",       1,    7),
    ("8-30D",      7,   30),
    ("31-90D",    30,   90),
    ("91-180D",   90,  180),
    ("181-365D", 180,  365),
    ("1-2Y",     365,  730),
    ("2-5Y",     730, 1825),
    (">5Y",     1825, float("inf")),
]

BUCKET_LABELS: list[str] = [b[0] for b in FUNDING_BUCKETS]


# ── Input ─────────────────────────────────────────────────────────────────────

@dataclass
class Funding_Item:
    """A single asset or liability cash flow.

    Parameters
    ----------
    name : str
    amount : float
        Nominal cash flow in currency units.
    maturity_days : float
        Remaining days to maturity (or next repricing date for floating).
    item_type : str
        'asset'  — cash inflow at maturity (reduces funding need)
        'liability' — cash outflow at maturity (creates rollover need)
    counterparty : str | None
        Optional counterparty for concentration calculation.
    """

    name          : str
    amount        : float
    maturity_days : float
    item_type     : str            # "asset" or "liability"
    counterparty  : str | None = None

    def __post_init__(self) -> None:
        if self.item_type not in ("asset", "liability"):
            raise ValueError(
                f"item_type must be 'asset' or 'liability', got '{self.item_type}'"
            )


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class Funding_Gap_Result:
    """Output of Funding_Gap_Analyser.compute().

    Attributes
    ----------
    gap_table : pd.DataFrame
        Index = bucket label. Columns: assets, liabilities, gap, cumulative_gap.
    rollover_30d : float
        Total liability cash flows maturing within 30 days.
    rollover_90d : float
        Total liability cash flows maturing within 90 days.
    rollover_1y : float
        Total liability cash flows maturing within 365 days.
    rollover_ratio_30d : float
        rollover_30d / total_liabilities.
    concentration : pd.Series | None
        Top-counterparty concentration: counterparty → total liability amount.
        None if no counterparty data supplied.
    """

    gap_table           : pd.DataFrame
    rollover_30d        : float
    rollover_90d        : float
    rollover_1y         : float
    rollover_ratio_30d  : float
    concentration       : pd.Series | None


# ── Analyser ──────────────────────────────────────────────────────────────────

class Funding_Gap_Analyser:
    """Compute maturity ladder funding gap and rollover risk metrics."""

    def compute(self, items: list[Funding_Item]) -> Funding_Gap_Result:

        bucket_assets = {lbl: 0.0 for lbl in BUCKET_LABELS}
        bucket_liabs  = {lbl: 0.0 for lbl in BUCKET_LABELS}
        total_liabs   = 0.0
        counterparty_liabs: dict[str, float] = {}

        for item in items:
            lbl = _assign_bucket(item.maturity_days)
            if item.item_type == "asset":
                bucket_assets[lbl] += item.amount
            else:
                bucket_liabs[lbl]  += item.amount
                total_liabs        += item.amount
                if item.counterparty:
                    counterparty_liabs[item.counterparty] = (
                        counterparty_liabs.get(item.counterparty, 0.0) + item.amount
                    )

        rows = []
        cumulative = 0.0
        for lbl in BUCKET_LABELS:
            gap        = bucket_assets[lbl] - bucket_liabs[lbl]
            cumulative += gap
            rows.append(
                {
                    "bucket"         : lbl,
                    "assets"         : bucket_assets[lbl],
                    "liabilities"    : bucket_liabs[lbl],
                    "gap"            : gap,
                    "cumulative_gap" : cumulative,
                }
            )

        gap_table = pd.DataFrame(rows).set_index("bucket")

        rollover_30d = sum(
            bucket_liabs[lbl]
            for lbl, lo, hi in FUNDING_BUCKETS
            if hi <= 30
        )
        rollover_90d = sum(
            bucket_liabs[lbl]
            for lbl, lo, hi in FUNDING_BUCKETS
            if hi <= 90
        )
        rollover_1y = sum(
            bucket_liabs[lbl]
            for lbl, lo, hi in FUNDING_BUCKETS
            if hi <= 365
        )
        ratio_30d = rollover_30d / total_liabs if total_liabs > 0.0 else 0.0

        concentration = None
        if counterparty_liabs:
            concentration = (
                pd.Series(counterparty_liabs, name="liability_amount")
                .sort_values(ascending=False)
            )

        return Funding_Gap_Result(
            gap_table=gap_table,
            rollover_30d=rollover_30d,
            rollover_90d=rollover_90d,
            rollover_1y=rollover_1y,
            rollover_ratio_30d=ratio_30d,
            concentration=concentration,
        )


# ── Private helper ────────────────────────────────────────────────────────────

def _assign_bucket(maturity_days: float) -> str:
    for lbl, lo, hi in FUNDING_BUCKETS:
        if lo < maturity_days <= hi:
            return lbl
    return BUCKET_LABELS[-1]

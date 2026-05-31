"""
Repricing gap analysis — EBA 19 bucket slotting.

Repricing_Gap slots all banking book positions into the 19 EBA maturity
buckets by next repricing date. Equity is slotted as a liability in the
>20Y bucket, consistent with the EBA convention.
"""

import numpy as np
import pandas as pd

from banking_risk.irrbb.constants import (
    EBA_BUCKET_BOUNDARIES,
    EBA_BUCKET_LABELS,
    EBA_BUCKET_MIDPOINTS,
    PositionType,
)
from banking_risk.irrbb.book import Banking_Book

# Inner boundaries used by searchsorted (excludes 0 and inf).
_INNER = EBA_BUCKET_BOUNDARIES[1:-1]


class Repricing_Gap:
    """Slots banking book positions into EBA 19 maturity buckets.

    Fixed positions are slotted at their final maturity date.
    Floating positions are slotted at their next repricing date.
    Equity (Tier 1) is added as a liability in the >20Y bucket — it has no
    contractual repricing date and is treated as the longest-duration item.

    Parameters
    ----------
    book : Banking_Book
    """

    def __init__(self, book: Banking_Book) -> None:
        self._book = book

    def compute(self) -> pd.DataFrame:
        """Compute the repricing gap across all 19 EBA buckets.

        Returns
        -------
        pd.DataFrame
            Index: EBA bucket label (str).
            Columns:
              midpoint_years  — representative maturity used for discounting
              assets          — sum of asset notionals repricing in bucket
              liabilities     — sum of liability notionals repricing in bucket
              gap             — assets − liabilities
              cumulative_gap  — running cumulative gap
        """
        assets = np.zeros(len(EBA_BUCKET_LABELS))
        liabilities = np.zeros(len(EBA_BUCKET_LABELS))

        # assign each position to a bucket by next repricing date, then sum notionals
        for p in self._book.positions():
            idx = int(np.searchsorted(_INNER, p.next_repricing_years, side="left"))
            idx = min(idx, len(EBA_BUCKET_LABELS) - 1)
            if p.type == PositionType.ASSET:
                assets[idx] += p.notional
            else:
                liabilities[idx] += p.notional

        # Equity has no contractual repricing — slotted at the >20Y bucket.
        liabilities[-1] += self._book.equity()

        gap = assets - liabilities

        return pd.DataFrame(
            {
                "midpoint_years": EBA_BUCKET_MIDPOINTS,
                "assets": assets,
                "liabilities": liabilities,
                "gap": gap,
                "cumulative_gap": np.cumsum(gap),
            },
            index=pd.Index(EBA_BUCKET_LABELS, name="bucket"),
        )

    def plot(self) -> None:
        """Grouped bar chart of assets/liabilities and cumulative gap line."""
        from banking_risk.utils.reporting import Dark_Style, Gap_Reporter

        Gap_Reporter(Dark_Style()).plot(self.compute())

    def to_table(self) -> pd.DataFrame:
        return self.compute()

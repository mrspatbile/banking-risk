"""
FRTB Default Risk Charge (DRC) — BKR-58.

Jump-to-default capital for credit instruments in the trading book.

Formula (CRR3 Art. 325w):
    JTD_long  = max(LGD × notional − MtM, 0)
    JTD_short = max(−(LGD × notional − MtM), 0)
    HBR = Σ JTD_short / (Σ JTD_long + Σ JTD_short)
    K_b = max(Σ JTD_long − HBR × Σ JTD_short, 0)
    DRC = Σ_b K_b

No diversification across buckets per CRR3 Art. 325x.

References
----------
CRR3 Art. 325w : Default Risk Charge formula
CRR3 Art. 325x : Aggregation (no across-bucket diversification)
"""

from dataclasses import dataclass, field
import pandas as pd


@dataclass
class DRC_Position:
    """Single credit instrument for DRC computation."""
    name: str
    notional: float
    lgd: float
    mtm: float
    bucket: int
    is_long: bool


@dataclass
class DRC_Result:
    """DRC capital charge output."""
    capital: float
    K_by_bucket: dict[int, float] = field(default_factory=dict)
    detail: pd.DataFrame | None = None

    def to_table(self) -> pd.DataFrame:
        """Capital breakdown by bucket."""
        if self.detail is not None:
            return self.detail
        return pd.DataFrame(
            {'bucket': list(self.K_by_bucket.keys()), 'K': list(self.K_by_bucket.values())}
        ).set_index('bucket')


class DRC_Calculator:
    """Compute Default Risk Charge per CRR3 Art. 325w/x."""

    def compute(self, positions: list[DRC_Position]) -> DRC_Result:
        """
        Parameters
        ----------
        positions : list[DRC_Position]

        Returns
        -------
        DRC_Result
            Total DRC capital + breakdown by bucket.
        """
        if not positions:
            return DRC_Result(capital=0.0)

        # Group by bucket
        by_bucket: dict[int, list[DRC_Position]] = {}
        for pos in positions:
            by_bucket.setdefault(pos.bucket, []).append(pos)

        K_by_bucket: dict[int, float] = {}
        detail_rows = []

        for bucket, bucket_positions in by_bucket.items():
            jtd_long_sum = 0.0
            jtd_short_sum = 0.0

            for pos in bucket_positions:
                jtd_gross = pos.lgd * pos.notional - pos.mtm
                if pos.is_long:
                    jtd_long_sum += max(jtd_gross, 0.0)
                else:
                    jtd_short_sum += max(-jtd_gross, 0.0)

            # Hedge benefit ratio
            jtd_total = jtd_long_sum + jtd_short_sum
            if jtd_total > 0:
                hbr = jtd_short_sum / jtd_total
            else:
                hbr = 0.0

            # K per bucket
            K = max(jtd_long_sum - hbr * jtd_short_sum, 0.0)
            K_by_bucket[bucket] = K

            detail_rows.append({
                'bucket': bucket,
                'JTD_long': jtd_long_sum,
                'JTD_short': jtd_short_sum,
                'HBR': hbr,
                'K': K,
            })

        total_drc = sum(K_by_bucket.values())
        detail_df = pd.DataFrame(detail_rows).set_index('bucket') if detail_rows else None

        return DRC_Result(capital=total_drc, K_by_bucket=K_by_bucket, detail=detail_df)

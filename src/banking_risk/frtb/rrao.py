"""
FRTB Residual Risk Add-On (RRAO) — BKR-59.

Notional-based capital charge for instruments with risk not captured
by delta/vega/curvature.

Formula (CRR3 Art. 325u):
    RRAO = 1.0% × Σ notional (exotic)
         + 0.1% × Σ notional (other residual)

Exotic underlyings (1%): longevity, weather, natural disasters, variance.
Other residual (0.1%): gap risk, correlation risk, behavioural risk.

References
----------
CRR3 Art. 325u : Residual Risk Add-On
"""

from dataclasses import dataclass, field
from enum import Enum


class RRAO_Category(Enum):
    """Residual risk classification."""
    EXOTIC = 0.01  # 1% — longevity, weather, variance, etc.
    OTHER = 0.001  # 0.1% — gap, correlation, behavioural


@dataclass
class RRAO_Position:
    """Single instrument contributing to RRAO."""
    name: str
    notional: float
    category: RRAO_Category


@dataclass
class RRAO_Result:
    """RRAO capital charge output."""
    capital: float
    by_category: dict[str, float] = field(default_factory=dict)

    def to_table(self):
        """Capital breakdown by category."""
        import pandas as pd
        return pd.DataFrame(
            {'category': list(self.by_category.keys()), 'capital': list(self.by_category.values())}
        ).set_index('category')


class RRAO_Calculator:
    """Compute Residual Risk Add-On per CRR3 Art. 325u."""

    def compute(self, positions: list[RRAO_Position]) -> RRAO_Result:
        """
        Parameters
        ----------
        positions : list[RRAO_Position]

        Returns
        -------
        RRAO_Result
            Total RRAO capital + breakdown by category.
        """
        if not positions:
            return RRAO_Result(capital=0.0)

        by_category: dict[str, float] = {}
        total = 0.0

        for pos in positions:
            charge = pos.notional * pos.category.value
            key = pos.category.name
            by_category[key] = by_category.get(key, 0.0) + charge
            total += charge

        return RRAO_Result(capital=total, by_category=by_category)

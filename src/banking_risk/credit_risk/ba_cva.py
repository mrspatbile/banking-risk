"""
Basic Approach CVA Capital (BA-CVA) — BKR-62.

CVA capital charge from counterparty credit risk.

Formula (CRR3 Art. 383a):
    K = 0.5 × Σ_c sqrt((ρ × SCVAc)² + (1−ρ²) × (Σ_c SCVAc)²)

    SCVAc = RWc × MRc × EADcnoMVA
      ρ   = 0.5 (cross-counterparty correlation)
      RWc = risk weight per counterparty credit quality
      MRc = maturity factor: (exp(−0.05 × Mc) − 1) / (−0.05 × Mc)

References
----------
CRR3 Art. 383a : BA-CVA capital formula
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class CVA_Counterparty:
    """Single counterparty for CVA capital."""
    cpty_name: str
    ead: float
    maturity_years: float
    risk_weight: float  # As decimal (e.g., 0.045 = 4.5%)


@dataclass
class BA_CVA_Result:
    """BA-CVA capital output."""
    capital: float
    by_counterparty: dict[str, float] = None

    def __post_init__(self):
        if self.by_counterparty is None:
            self.by_counterparty = {}


class BA_CVA_Calculator:
    """Compute BA-CVA capital per CRR3 Art. 383a."""

    RHO = 0.5  # Cross-counterparty correlation

    def compute(self, counterparties: list[CVA_Counterparty]) -> BA_CVA_Result:
        """
        Parameters
        ----------
        counterparties : list[CVA_Counterparty]

        Returns
        -------
        BA_CVA_Result
        """
        if not counterparties:
            return BA_CVA_Result(capital=0.0)

        scva_by_cpty = {}
        sum_scva = 0.0

        for cpty in counterparties:
            # Maturity factor MRc
            m = max(1.0, min(cpty.maturity_years, 5.0))
            mr = (np.exp(-0.05 * m) - 1) / (-0.05 * m)

            # SCVAc = RWc × MRc × EAD
            scva = cpty.risk_weight * mr * cpty.ead
            scva_by_cpty[cpty.cpty_name] = scva
            sum_scva += scva

        # K = 0.5 × sqrt(Σ (ρ × SCVAc)² + (1-ρ²) × (Σ SCVAc)²)
        sum_squared = 0.0
        for scva in scva_by_cpty.values():
            sum_squared += (self.RHO * scva) ** 2

        sum_squared += (1 - self.RHO ** 2) * sum_scva ** 2
        k = 0.5 * np.sqrt(sum_squared)

        return BA_CVA_Result(capital=k, by_counterparty=scva_by_cpty)

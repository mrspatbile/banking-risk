"""
Standardised Measurement Approach (SMA) — BKR-63.

Pillar 1 operational risk capital. Replaces BIA and AMA.

Formula (CRR3 Art. 312–324):
    Business Indicator Component (BIC):
      BI = ILDC + SC + FC
      BIC = α × BI
        bucket 1 (BI ≤ €1bn):   α = 12%
        bucket 2 (€1–30bn):      α = 15%
        bucket 3 (> €30bn):      α = 18%

    Internal Loss Multiplier (ILM):
      ILM = 1.0  (no internal loss data)
      ILM = ln(exp(1) − 1 + (LC/BIC)^0.8)  (with loss data)

    SMA = BIC × ILM

References
----------
CRR3 Art. 312–324 : SMA framework, BI components, ILM formula
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class BI_Components:
    """Business Indicator components."""
    ildc: float  # Interest, Loan Commissions, Dividends Component
    sc: float    # Services Component (fees for services)
    fc: float    # Financial Component (net profit/loss)


@dataclass
class SMA_Result:
    """SMA capital output."""
    bi: float
    bi_bucket: int
    alpha: float
    bic: float
    ilm: float
    capital: float


class SMA_Calculator:
    """Compute SMA operational risk capital per CRR3 Art. 312–324."""

    def compute(
        self,
        bi_components: BI_Components,
        loss_component: float = 0.0,
    ) -> SMA_Result:
        """
        Parameters
        ----------
        bi_components : BI_Components
            Income components for BI calculation.
        loss_component : float, optional
            Internal loss component (LC). If 0, ILM = 1.0.

        Returns
        -------
        SMA_Result
        """
        # Business Indicator
        bi = bi_components.ildc + bi_components.sc + bi_components.fc

        # Alpha bucket based on BI (in millions)
        bi_millions = bi / 1e6
        if bi_millions <= 1_000:
            alpha = 0.12
            bi_bucket = 1
        elif bi_millions <= 30_000:
            alpha = 0.15
            bi_bucket = 2
        else:
            alpha = 0.18
            bi_bucket = 3

        # Business Indicator Component
        bic = alpha * bi

        # Internal Loss Multiplier
        if loss_component <= 0 or bic <= 0:
            ilm = 1.0
        else:
            lc_bic_ratio = loss_component / bic
            ilm = np.log(np.e - 1 + lc_bic_ratio ** 0.8)

        # SMA capital
        capital = bic * ilm

        return SMA_Result(
            bi=bi,
            bi_bucket=bi_bucket,
            alpha=alpha,
            bic=bic,
            ilm=ilm,
            capital=capital,
        )

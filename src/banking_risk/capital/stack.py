"""
Regulatory Capital Stack & MDA Trigger — BKR-64.

Assembles Pillar 1 capital charges into unified RWA and capital ratios.
Computes MDA (Maximum Distributable Amount) trigger for regulatory restrictions.

Formula (CRR Art. 26–88, 128–142):
    RWA = (FRTB + SA-CCR × 12.5 + OpRisk-SMA × 12.5) + Credit-RWA

    Capital ratios:
      CET1 ≥ 4.5% RWA
      Tier 1 ≥ 6.0% RWA
      Total ≥ 8.0% RWA

    Combined buffer:
      CCB = 2.5% (countercyclical)
      CCyB = 0–2.5% (jurisdiction)
      GSII/OSII = 1–3.5%

    MDA trigger = Pillar 1 + combined buffer
      breach → restrictions on distributions

References
----------
CRR Art. 26–88   : Capital definitions (CET1, Tier 1, Tier 2)
CRR Art. 128–142 : Capital buffer requirements and MDA
"""

from dataclasses import dataclass


@dataclass
class Capital_Stack:
    """Regulatory capital and ratios.

    Attributes
    ----------
    cet1, tier1, tier2 : float
        Capital amounts
    total_capital : float
        Sum of all capital tiers
    frtb_rwa, credit_rwa, oprisk_rwa : float
        Risk-weighted assets by pillar 1 component
    total_rwa : float
        Sum of all RWA components
    cet1_ratio, tier1_ratio, total_ratio : float
        Capital ratios vs. total RWA
    sa_ccr_ead : float, optional
        SA-CCR exposure at default (before RWA conversion)
    cva_capital : float, optional
        BA-CVA capital charge
    ccb, ccyb, gsii_buffer : float
        Buffer rates for MDA trigger calculation
    """

    cet1: float
    tier1: float
    tier2: float
    total_capital: float

    frtb_rwa: float
    credit_rwa: float
    oprisk_rwa: float
    total_rwa: float

    cet1_ratio: float
    tier1_ratio: float
    total_ratio: float

    sa_ccr_ead: float = 0.0  # Exposure at default (optional detail)
    cva_capital: float = 0.0  # CVA capital charge (part of pillar 1)

    ccb: float = 0.025  # Fixed 2.5%
    ccyb: float = 0.0   # Jurisdiction-specific, 0–2.5%
    gsii_buffer: float = 0.0  # G-SII buffer, 1–3.5%

    def __post_init__(self):
        """Compute derived metrics."""
        # MDA trigger = Pillar 1 min (4.5%) + CCB (2.5%) + CCyB + 50% of GSII buffer
        self.total_buffer = self.ccb + self.ccyb + (0.5 * self.gsii_buffer)
        self.mda_trigger = 0.045 + self.total_buffer

    @property
    def mda_headroom_bps(self) -> float:
        """Basis points above MDA trigger (negative = in breach)."""
        return (self.cet1_ratio - self.mda_trigger) * 10_000

    @property
    def is_under_mda(self) -> bool:
        """Whether institution is below MDA trigger."""
        return self.cet1_ratio < self.mda_trigger

    @property
    def mda_restrictions(self) -> str:
        """Description of MDA restrictions."""
        if not self.is_under_mda:
            return "None"
        return "Restrictions on distributions (dividends, coupons, bonuses)"


class Capital_Stack_Builder:
    """Assemble capital ratios from regulatory components."""

    @staticmethod
    def from_components(
        cet1: float,
        tier1: float,
        tier2: float,
        frtb_rwa: float,
        credit_rwa: float,
        oprisk_rwa: float,
        sa_ccr_ead: float = 0.0,
        cva_capital: float = 0.0,
        ccb: float = 0.025,
        ccyb: float = 0.0,
        gsii_buffer: float = 0.0,
    ) -> Capital_Stack:
        """
        Parameters
        ----------
        cet1 : float
            CET1 capital amount
        tier1 : float
            Tier 1 capital amount
        tier2 : float
            Tier 2 capital amount
        frtb_rwa : float
            FRTB Standardised Approach RWA
        credit_rwa : float
            Credit risk IRB/SA RWA
        oprisk_rwa : float
            Operational risk SMA RWA
        sa_ccr_ead : float, optional
            SA-CCR exposure at default (for detail; not directly RWA)
        cva_capital : float, optional
            BA-CVA capital charge (part of pillar 1)
        ccb : float, optional
            Countercyclical buffer (default 2.5%)
        ccyb : float, optional
            Jurisdiction CCyB (0–2.5%)
        gsii_buffer : float, optional
            G-SII surcharge (1–3.5%)

        Returns
        -------
        Capital_Stack
        """
        total_capital = cet1 + tier1 + tier2
        total_rwa = frtb_rwa + credit_rwa + oprisk_rwa

        if total_rwa > 0:
            cet1_ratio = cet1 / total_rwa
            tier1_ratio = tier1 / total_rwa
            total_ratio = total_capital / total_rwa
        else:
            cet1_ratio = tier1_ratio = total_ratio = 0.0

        return Capital_Stack(
            cet1=cet1,
            tier1=tier1,
            tier2=tier2,
            total_capital=total_capital,
            frtb_rwa=frtb_rwa,
            credit_rwa=credit_rwa,
            oprisk_rwa=oprisk_rwa,
            total_rwa=total_rwa,
            cet1_ratio=cet1_ratio,
            tier1_ratio=tier1_ratio,
            total_ratio=total_ratio,
            sa_ccr_ead=sa_ccr_ead,
            cva_capital=cva_capital,
            ccb=ccb,
            ccyb=ccyb,
            gsii_buffer=gsii_buffer,
        )

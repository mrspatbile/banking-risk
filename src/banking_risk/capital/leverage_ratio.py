"""
Leverage Ratio — BKR-66.

Simple backstop independent of RWA per CRR Art. 429–429b.

Formula:
    Leverage ratio = Tier 1 capital / Exposure measure

    Exposure measure:
      + on-balance sheet assets (net of certain deductions)
      + derivative exposure (SA-CCR EAD × 12.5 or gross notional)
      + SFT exposure (repo, securities lending, collateral)
      + off-balance sheet items × CCF (credit conversion factor)

Minimum requirement: 3% (CRR Art. 429a).
G-SII surcharge: +50% of G-SII buffer (e.g., +1.75% for 3.5% G-SII buffer).

References
----------
CRR Art. 429–429b : Leverage ratio framework and exemptions
"""

from dataclasses import dataclass


@dataclass
class Leverage_Exposure:
    """Components of leverage ratio exposure measure."""
    on_balance_sheet: float
    derivative_exposure: float = 0.0
    sft_exposure: float = 0.0
    off_balance_sheet: float = 0.0
    ccf_adjustment: float = 1.0  # Credit conversion factor for OBS


@dataclass
class Leverage_Ratio_Result:
    """Leverage ratio output."""
    tier1_capital: float
    total_exposure: float
    leverage_ratio: float
    minimum_required: float
    is_compliant: bool
    headroom_bps: float


class Leverage_Ratio_Calculator:
    """Compute leverage ratio per CRR Art. 429–429b."""

    MINIMUM_RATIO = 0.03  # 3%
    GSII_SURCHARGE_MULTIPLIER = 0.50  # 50% of G-SII buffer

    def compute(
        self,
        tier1_capital: float,
        exposure: Leverage_Exposure,
        gsii_buffer: float = 0.0,
    ) -> Leverage_Ratio_Result:
        """
        Parameters
        ----------
        tier1_capital : float
            Tier 1 capital amount
        exposure : Leverage_Exposure
            Leverage exposure components
        gsii_buffer : float, optional
            G-SII buffer (e.g., 0.035 = 3.5%)

        Returns
        -------
        Leverage_Ratio_Result
        """
        # Total exposure measure
        total_exposure = (
            exposure.on_balance_sheet
            + exposure.derivative_exposure
            + exposure.sft_exposure
            + exposure.off_balance_sheet * exposure.ccf_adjustment
        )

        if total_exposure > 0:
            leverage_ratio = tier1_capital / total_exposure
        else:
            leverage_ratio = 0.0

        # Minimum requirement with G-SII surcharge
        minimum_required = self.MINIMUM_RATIO + (
            self.GSII_SURCHARGE_MULTIPLIER * gsii_buffer
        )

        is_compliant = leverage_ratio >= minimum_required
        headroom_bps = (leverage_ratio - minimum_required) * 10_000

        return Leverage_Ratio_Result(
            tier1_capital=tier1_capital,
            total_exposure=total_exposure,
            leverage_ratio=leverage_ratio,
            minimum_required=minimum_required,
            is_compliant=is_compliant,
            headroom_bps=headroom_bps,
        )

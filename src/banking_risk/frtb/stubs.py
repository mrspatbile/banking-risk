"""
Stub QRE instruments for notebooks and integration tests.

Each class implements the minimal QRE instrument interface expected by
FRTB_Sensitivity_Engine without depending on quant-risk-engine. Replace
with real QRE instruments in production.

Public API
----------
build_example_portfolio() -> tuple[Standard_Trading_Portfolio, Stub_Curve]
    A ready-made mixed trading book spanning all five FRTB SA risk classes.
"""

import numpy as np

from banking_risk.frtb.portfolio import (
    Trading_Instrument,
    Standard_Trading_Portfolio,
    FRTB_Risk_Class,
)


# ── Stub instruments ──────────────────────────────────────────────────────────

class Stub_Rate_Instrument:
    """Stub for Bond / IRSwap.

    Implements rate_sensitivities(curve, tenors) and npv(curve).
    dv01_by_tenor maps tenor (years) → DV01 in currency per 1bp.
    """

    def __init__(self, dv01_by_tenor: dict[float, float], npv: float) -> None:
        self._dv01 = dv01_by_tenor
        self._npv  = npv

    def rate_sensitivities(self, curve, tenors, bump: float = 0.0001):
        return {t: self._dv01.get(t, 0.0) for t in tenors}

    def npv(self, curve) -> float:
        return self._npv


class Stub_CDS_Instrument:
    """Stub for CreditDefaultSwap.

    Implements cs01(curve, tenors) and npv(curve).
    cs01_by_tenor maps tenor (years) → CS01 in currency per 1bp.
    """

    def __init__(self, cs01_by_tenor: dict[float, float], npv: float) -> None:
        self._cs01 = cs01_by_tenor
        self._npv  = npv

    def cs01(self, curve, tenors, bump: float = 0.0001):
        return {t: self._cs01.get(t, 0.0) for t in tenors}

    def npv(self, curve) -> float:
        return self._npv


class Stub_Equity_Instrument:
    """Stub for plain equity position (stock, equity index).

    Implements npv(curve) returning the full market value in currency.
    """

    def __init__(self, market_value: float) -> None:
        self._mv = market_value

    def npv(self, curve) -> float:
        return self._mv


class Stub_FX_Instrument:
    """Stub for FX forward / FX spot position.

    Implements npv(curve) returning the domestic-currency notional.
    """

    def __init__(self, notional: float) -> None:
        self._notional = notional

    def npv(self, curve) -> float:
        return self._notional


class Stub_Curve:
    """Minimal curve satisfying the Zero_Curve protocol.

    Simple upward-sloping OIS-like curve: 3% + 0.1% per year.
    Sufficient for stub instruments which ignore the curve value.
    """

    def zero_rate(self, t: float) -> float:
        return 0.03 + 0.001 * t

    def discount(self, t: float) -> float:
        return float(np.exp(-self.zero_rate(t) * t))


# ── Example portfolio factory ─────────────────────────────────────────────────

def build_example_portfolio() -> tuple[Standard_Trading_Portfolio, Stub_Curve]:
    """Return a mixed trading book spanning all five FRTB SA risk classes.

    Positions
    ---------
    GIRR  : payer IRS 5Y (long), receiver IRS 10Y (long), short bund 3Y
    CSR   : IG financials corp bond (bucket 6), HY basic materials CDS (bucket 9)
    Equity: long AAPL (bucket 5), long GS (bucket 8), short AMZN (bucket 5)
    FX    : long EURUSD forward, long GBPUSD forward
    Comm  : long Brent oil forward (bucket 2), long natural gas forward (bucket 6)
    """
    instruments = [
        # ── GIRR ──────────────────────────────────────────────────────────────
        Trading_Instrument(
            name='IRS_5Y', currency='EUR',
            risk_classes=frozenset({FRTB_Risk_Class.GIRR}),
            instrument=Stub_Rate_Instrument({5.0: 4_500.0, 10.0: 200.0}, npv=12_500.0),
            is_long=True,
        ),
        Trading_Instrument(
            name='IRS_10Y', currency='EUR',
            risk_classes=frozenset({FRTB_Risk_Class.GIRR}),
            instrument=Stub_Rate_Instrument({10.0: 8_800.0, 15.0: 500.0}, npv=-6_000.0),
            is_long=True,
        ),
        Trading_Instrument(
            name='BUND_3Y', currency='EUR',
            risk_classes=frozenset({FRTB_Risk_Class.GIRR}),
            instrument=Stub_Rate_Instrument({3.0: 2_800.0}, npv=5_200.0),
            is_long=False,  # short bund
        ),

        # ── CSR ───────────────────────────────────────────────────────────────
        Trading_Instrument(
            name='CORP_5Y', currency='EUR',
            risk_classes=frozenset({FRTB_Risk_Class.CSR_NON_SEC}),
            instrument=Stub_Rate_Instrument({5.0: 1_200.0, 10.0: 600.0}, npv=3_100.0),
            is_long=True, csr_bucket=6, issuer='JPMorgan',
        ),
        Trading_Instrument(
            name='HY_CDS', currency='EUR',
            risk_classes=frozenset({FRTB_Risk_Class.CSR_NON_SEC}),
            instrument=Stub_CDS_Instrument({3.0: 950.0, 5.0: 1_800.0}, npv=-2_200.0),
            is_long=True, csr_bucket=9, issuer='ArcelorMittal',
        ),

        # ── Equity ────────────────────────────────────────────────────────────
        Trading_Instrument(
            name='AAPL', currency='USD',
            risk_classes=frozenset({FRTB_Risk_Class.EQUITY}),
            instrument=Stub_Equity_Instrument(450_000.0),
            is_long=True, equity_bucket=5, underlying='AAPL', issuer='Apple Inc',
        ),
        Trading_Instrument(
            name='GS', currency='USD',
            risk_classes=frozenset({FRTB_Risk_Class.EQUITY}),
            instrument=Stub_Equity_Instrument(220_000.0),
            is_long=True, equity_bucket=8, underlying='GS', issuer='Goldman Sachs',
        ),
        Trading_Instrument(
            name='AMZN', currency='USD',
            risk_classes=frozenset({FRTB_Risk_Class.EQUITY}),
            instrument=Stub_Equity_Instrument(380_000.0),
            is_long=False, equity_bucket=5, underlying='AMZN', issuer='Amazon',  # short
        ),

        # ── FX ────────────────────────────────────────────────────────────────
        Trading_Instrument(
            name='EURUSD_FWD', currency='EUR',
            risk_classes=frozenset({FRTB_Risk_Class.FX}),
            instrument=Stub_FX_Instrument(800_000.0),
            is_long=True, ccy_pair='EURUSD',
        ),
        Trading_Instrument(
            name='GBPUSD_FWD', currency='GBP',
            risk_classes=frozenset({FRTB_Risk_Class.FX}),
            instrument=Stub_FX_Instrument(350_000.0),
            is_long=True, ccy_pair='GBPUSD',
        ),

        # ── Commodity ─────────────────────────────────────────────────────────
        Trading_Instrument(
            name='BRENT', currency='USD',
            risk_classes=frozenset({FRTB_Risk_Class.COMMODITY}),
            instrument=Stub_Rate_Instrument(
                {1.0: 3_200.0, 2.0: 2_800.0, 3.0: 1_500.0}, npv=6_000.0
            ),
            is_long=True, commodity_bucket=2,
        ),
        Trading_Instrument(
            name='NATGAS', currency='USD',
            risk_classes=frozenset({FRTB_Risk_Class.COMMODITY}),
            instrument=Stub_Rate_Instrument({0.5: 1_800.0, 1.0: 2_100.0}, npv=3_200.0),
            is_long=True, commodity_bucket=6,
        ),
    ]

    return Standard_Trading_Portfolio(instruments), Stub_Curve()

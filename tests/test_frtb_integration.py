"""
FRTB SA integration tests — real QRE instruments end-to-end.

These tests verify the full pipeline:
    real QRE instrument → FRTB_Sensitivity_Engine → SA calculators → FRTB_SA

Requires quant-risk-engine to be installed:
    pip install -e /path/to/quant-risk-engine

Run in isolation:
    pytest tests/test_frtb_integration.py -v

Skipped automatically if quant-risk-engine is not installed.
"""

import math
import numpy as np
import pytest

# ── Guard: skip entire module if QRE not available ────────────────────────────
ql_mod   = pytest.importorskip("QuantLib",   reason="QuantLib not available")
qre_mod  = pytest.importorskip("quant_risk", reason="quant-risk-engine not installed")

import QuantLib as ql
from quant_risk.instruments.bond    import Bond
from quant_risk.instruments.swap    import IRSwap
from quant_risk.instruments.option  import VanillaOption
from quant_risk.instruments.cds     import (
    CreditDefaultSwap, STANDARD_RECOVERY, STANDARD_COUPON_IG, STANDARD_COUPON_HY
)
from quant_risk.instruments.fx_forward import FXForward
from quant_risk.curves.array_curve import ArrayCurve

from banking_risk.frtb.portfolio import (
    Trading_Instrument, Standard_Trading_Portfolio, FRTB_Risk_Class,
)
from banking_risk.frtb.sensitivity_engine import FRTB_Sensitivity_Engine
from banking_risk.frtb.girr.delta          import SA_GIRR_Calculator
from banking_risk.frtb.csr.delta           import SA_CSR_Delta_Calculator
from banking_risk.frtb.equity.delta        import SA_Equity_Delta_Calculator
from banking_risk.frtb.fx.delta            import SA_FX_Delta_Calculator
from banking_risk.frtb.sa                  import FRTB_SA


# ── Shared fixtures ───────────────────────────────────────────────────────────

TODAY      = ql.Date(1, 6, 2026)
TODAY_STR  = "2026-06-01"
EXPIRY_1Y  = ql.Date(1, 6, 2027)
EXPIRY_5Y  = ql.Date(1, 6, 2031)


@pytest.fixture(autouse=True)
def set_eval_date():
    ql.Settings.instance().evaluationDate = TODAY
    yield
    ql.Settings.instance().evaluationDate = ql.Date.todaysDate()


@pytest.fixture
def eur_curve():
    maturities = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0])
    rates      = np.array([0.030, 0.032, 0.035, 0.038, 0.042, 0.045, 0.047])
    return ArrayCurve(maturities, rates)


@pytest.fixture
def usd_curve():
    maturities = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0])
    rates      = np.array([0.050, 0.052, 0.053, 0.054, 0.055, 0.056])
    return ArrayCurve(maturities, rates)


# ── Individual instrument smoke tests ─────────────────────────────────────────

class TestBond:
    def test_npv_is_finite(self, eur_curve):
        bond = Bond(
            isin='TEST001', face_value=1_000_000.0, coupon_rate=0.035,
            issue_date='2024-06-01', maturity_date='2029-06-01', currency='EUR',
        )
        assert math.isfinite(bond.npv(eur_curve))
        assert bond.npv(eur_curve) > 0

    def test_rate_sensitivities_returns_dict(self, eur_curve):
        bond = Bond(
            isin='TEST002', face_value=1_000_000.0, coupon_rate=0.035,
            issue_date='2024-06-01', maturity_date='2029-06-01', currency='EUR',
        )
        from banking_risk.frtb.vertex_mapping import FRTB_GIRR_VERTICES
        sens = bond.rate_sensitivities(eur_curve, FRTB_GIRR_VERTICES)
        assert isinstance(sens, dict)
        assert all(math.isfinite(v) for v in sens.values())

    def test_rate_sensitivities_nonzero_at_maturity_vertex(self, eur_curve):
        bond = Bond(
            isin='TEST003', face_value=1_000_000.0, coupon_rate=0.035,
            issue_date='2024-06-01', maturity_date='2029-06-01', currency='EUR',
        )
        sens = bond.rate_sensitivities(eur_curve, [5.0])
        assert abs(sens[5.0]) > 0


class TestIRSwap:
    def test_npv_is_finite(self, eur_curve):
        swap = IRSwap(
            notional=5_000_000.0, maturity_years=5, fixed_rate=0.038,
            valuation_date=TODAY_STR, pay_fixed=True, currency='EUR',
        )
        assert math.isfinite(swap.npv(eur_curve))

    def test_rate_sensitivities_positive_payer(self, eur_curve):
        swap = IRSwap(
            notional=5_000_000.0, maturity_years=5, fixed_rate=0.038,
            valuation_date=TODAY_STR, pay_fixed=True, currency='EUR',
        )
        sens = swap.rate_sensitivities(eur_curve, [5.0])
        # payer swap: rates up → positive NPV change
        assert sens[5.0] > 0

    def test_receiver_swap_opposite_sign(self, eur_curve):
        payer    = IRSwap(5_000_000.0, 5, 0.038, TODAY_STR, pay_fixed=True)
        receiver = IRSwap(5_000_000.0, 5, 0.038, TODAY_STR, pay_fixed=False)
        s_payer    = payer.rate_sensitivities(eur_curve, [5.0])[5.0]
        s_receiver = receiver.rate_sensitivities(eur_curve, [5.0])[5.0]
        assert s_payer * s_receiver < 0   # opposite signs


class TestVanillaOption:
    def _call(self):
        return VanillaOption(
            spot=100.0, strike=105.0, expiry_date=EXPIRY_1Y,
            valuation_date=TODAY, sigma=0.20, option_type='call',
            notional_=100_000.0, currency_='EUR', underlying='SPX',
        )

    def test_price_is_finite(self, eur_curve):
        assert math.isfinite(self._call().price(eur_curve))

    def test_npv_equals_price(self, eur_curve):
        opt = self._call()
        assert opt.npv(eur_curve) == pytest.approx(opt.price(eur_curve), rel=1e-9)

    def test_sigma_override_changes_price(self, eur_curve):
        opt  = self._call()
        base = opt.price(eur_curve)
        high = opt.price(eur_curve, sigma=0.25)
        assert high > base   # higher vol → higher call price

    def test_delta_is_positive_call(self, eur_curve):
        assert self._call().delta(eur_curve) > 0

    def test_delta_is_notional_scaled(self, eur_curve):
        opt_1  = VanillaOption(100.0, 105.0, EXPIRY_1Y, TODAY, 0.20, notional_=1.0)
        opt_100k = VanillaOption(100.0, 105.0, EXPIRY_1Y, TODAY, 0.20, notional_=100_000.0)
        assert opt_100k.delta(eur_curve) == pytest.approx(
            opt_1.delta(eur_curve) * 100_000.0, rel=1e-6
        )


class TestCreditDefaultSwap:
    def _cds(self):
        return CreditDefaultSwap.from_flat_spread(
            valuation_date=TODAY, maturity=EXPIRY_5Y,
            notional_=5_000_000.0, par_spread=0.0150,
            coupon=STANDARD_COUPON_IG, recovery=STANDARD_RECOVERY,
            currency_='EUR', protection_buyer=True,
        )

    def test_npv_is_finite(self, eur_curve):
        assert math.isfinite(self._cds().npv(eur_curve))

    def test_cs01_returns_dict(self, eur_curve):
        from banking_risk.frtb.vertex_mapping import FRTB_CSR_VERTICES
        sens = self._cds().cs01(eur_curve, FRTB_CSR_VERTICES)
        assert isinstance(sens, dict)
        assert len(sens) == len(FRTB_CSR_VERTICES)
        assert all(math.isfinite(v) for v in sens.values())

    def test_cs01_positive_protection_buyer(self, eur_curve):
        from banking_risk.frtb.vertex_mapping import FRTB_CSR_VERTICES
        sens = self._cds().cs01(eur_curve, FRTB_CSR_VERTICES)
        # protection buyer: spread widens → position value rises → positive CS01
        assert any(v > 0 for v in sens.values())


class TestFXForward:
    def _fx(self, usd_curve):
        usd_handle = ql.YieldTermStructureHandle(usd_curve.ql_curve)
        return FXForward(
            notional_foreign=1_000_000.0, spot_rate=1.0850, f0=None,
            maturity_date=EXPIRY_1Y, valuation_date=TODAY,
            usd_disc_handle=usd_handle,
            domestic_currency='EUR', foreign_currency='USD', exporter=True,
        )

    def test_npv_is_finite(self, eur_curve, usd_curve):
        assert math.isfinite(self._fx(usd_curve).npv(eur_curve))


# ── FRTB Sensitivity Engine integration ───────────────────────────────────────

@pytest.fixture
def mixed_portfolio(eur_curve, usd_curve):
    usd_handle = ql.YieldTermStructureHandle(usd_curve.ql_curve)

    bond = Bond(
        isin='BUND1', face_value=5_000_000.0, coupon_rate=0.025,
        issue_date='2023-06-01', maturity_date='2028-06-01', currency='EUR',
    )
    swap = IRSwap(
        notional=10_000_000.0, maturity_years=10, fixed_rate=0.040,
        valuation_date=TODAY_STR, pay_fixed=True, currency='EUR',
    )
    corp_bond = Bond(
        isin='CORP1', face_value=2_000_000.0, coupon_rate=0.055,
        issue_date='2024-01-01', maturity_date='2029-01-01', currency='EUR',
    )
    cds = CreditDefaultSwap.from_flat_spread(
        valuation_date=TODAY, maturity=EXPIRY_5Y,
        notional_=5_000_000.0, par_spread=0.0200,
        coupon=STANDARD_COUPON_HY, recovery=STANDARD_RECOVERY,
        currency_='EUR', protection_buyer=True,
    )
    option = VanillaOption(
        spot=100.0, strike=100.0, expiry_date=EXPIRY_1Y,
        valuation_date=TODAY, sigma=0.22, option_type='call',
        notional_=500_000.0, currency_='EUR', underlying='SPX',
    )
    fx_fwd = FXForward(
        notional_foreign=2_000_000.0, spot_rate=1.0850, f0=None,
        maturity_date=EXPIRY_1Y, valuation_date=TODAY,
        usd_disc_handle=usd_handle,
        domestic_currency='EUR', foreign_currency='USD', exporter=True,
    )

    instruments = [
        Trading_Instrument('BUND',      'EUR', frozenset({FRTB_Risk_Class.GIRR}),        bond,      is_long=True),
        Trading_Instrument('IRS_10Y',   'EUR', frozenset({FRTB_Risk_Class.GIRR}),        swap,      is_long=True),
        Trading_Instrument('CORP_BOND', 'EUR', frozenset({FRTB_Risk_Class.CSR_NON_SEC}), corp_bond, is_long=True,  csr_bucket=6),
        Trading_Instrument('HY_CDS',    'EUR', frozenset({FRTB_Risk_Class.CSR_NON_SEC}), cds,       is_long=True,  csr_bucket=9),
        Trading_Instrument('SPX_CALL',  'EUR', frozenset({FRTB_Risk_Class.EQUITY}),      option,    is_long=True,  equity_bucket=5, is_linear=False),
        Trading_Instrument('EURUSD',    'EUR', frozenset({FRTB_Risk_Class.FX}),           fx_fwd,    is_long=True,  ccy_pair='EURUSD'),
    ]
    return Standard_Trading_Portfolio(instruments)


class TestSensitivityEngineIntegration:

    def test_girr_delta_nonzero(self, mixed_portfolio, eur_curve):
        engine = FRTB_Sensitivity_Engine(mixed_portfolio, eur_curve)
        sens   = engine.girr_delta()
        assert 'EUR' in sens
        assert sens['EUR'].sum() != pytest.approx(0.0)

    def test_girr_delta_shape(self, mixed_portfolio, eur_curve):
        from banking_risk.frtb.vertex_mapping import FRTB_GIRR_VERTICES
        engine = FRTB_Sensitivity_Engine(mixed_portfolio, eur_curve)
        assert engine.girr_delta()['EUR'].shape == (len(FRTB_GIRR_VERTICES),)

    def test_csr_delta_both_buckets_populated(self, mixed_portfolio, eur_curve):
        engine = FRTB_Sensitivity_Engine(mixed_portfolio, eur_curve)
        sens   = engine.csr_delta()
        assert 6 in sens   # corp bond
        assert 9 in sens   # CDS

    def test_csr_routes_cs01_for_cds(self, mixed_portfolio, eur_curve):
        engine = FRTB_Sensitivity_Engine(mixed_portfolio, eur_curve)
        # bucket 9 = CDS — cs01 returns flat sensitivity across tenors
        csr = engine.csr_delta()
        assert csr[9].sum() != pytest.approx(0.0)

    def test_equity_delta_uses_option_delta(self, mixed_portfolio, eur_curve):
        engine = FRTB_Sensitivity_Engine(mixed_portfolio, eur_curve)
        eq     = engine.equity_delta()
        assert 5 in eq
        # non-linear instrument → delta() called, not npv()
        assert any(abs(s) > 0 for s in eq[5])

    def test_fx_delta_eurusd_populated(self, mixed_portfolio, eur_curve):
        engine = FRTB_Sensitivity_Engine(mixed_portfolio, eur_curve)
        fx     = engine.fx_delta()
        assert 'EURUSD' in fx
        assert math.isfinite(fx['EURUSD'])

    def test_short_position_negates_sensitivity(self, eur_curve):
        bond = Bond(
            isin='SHORT1', face_value=1_000_000.0, coupon_rate=0.035,
            issue_date='2024-06-01', maturity_date='2029-06-01',
        )
        long_p  = Standard_Trading_Portfolio([
            Trading_Instrument('B', 'EUR', frozenset({FRTB_Risk_Class.GIRR}), bond, is_long=True)
        ])
        short_p = Standard_Trading_Portfolio([
            Trading_Instrument('B', 'EUR', frozenset({FRTB_Risk_Class.GIRR}), bond, is_long=False)
        ])
        e_long  = FRTB_Sensitivity_Engine(long_p,  eur_curve).girr_delta()
        e_short = FRTB_Sensitivity_Engine(short_p, eur_curve).girr_delta()
        np.testing.assert_allclose(e_long['EUR'], -e_short['EUR'], rtol=1e-9)


class TestFRTBSAIntegration:

    def test_frtb_sa_runs_without_error(self, mixed_portfolio, eur_curve):
        frtb = FRTB_SA(mixed_portfolio, eur_curve)
        assert math.isfinite(frtb.total)

    def test_total_capital_positive(self, mixed_portfolio, eur_curve):
        frtb = FRTB_SA(mixed_portfolio, eur_curve)
        assert frtb.total > 0

    def test_girr_capital_positive(self, mixed_portfolio, eur_curve):
        frtb = FRTB_SA(mixed_portfolio, eur_curve)
        assert frtb.girr.capital > 0

    def test_csr_capital_positive(self, mixed_portfolio, eur_curve):
        frtb = FRTB_SA(mixed_portfolio, eur_curve)
        assert frtb.csr.capital > 0

    def test_to_table_shape(self, mixed_portfolio, eur_curve):
        table = FRTB_SA(mixed_portfolio, eur_curve).to_table()
        assert len(table) == 6          # 5 risk classes + total
        assert table.index[-1] == 'FRTB SA'
        assert (table['total'] >= 0).all()

    def test_total_equals_sum_of_components(self, mixed_portfolio, eur_curve):
        frtb   = FRTB_SA(mixed_portfolio, eur_curve)
        total_ = sum([
            frtb.girr.capital, frtb.csr.capital, frtb.equity.capital,
            frtb.fx.capital,   frtb.commodity.capital,
        ])
        assert frtb.total == pytest.approx(total_, rel=1e-9)

    def test_sa_calculator_capital_matches_facade(self, mixed_portfolio, eur_curve):
        engine = FRTB_Sensitivity_Engine(mixed_portfolio, eur_curve)
        direct = SA_GIRR_Calculator().compute(engine.girr_delta()).capital
        facade = FRTB_SA(mixed_portfolio, eur_curve).girr.capital
        assert direct == pytest.approx(facade, rel=1e-9)

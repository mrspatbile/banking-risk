import numpy as np
import pytest

from banking_risk.frtb.portfolio import (
    FRTB_Risk_Class,
    Trading_Instrument,
    Standard_Trading_Portfolio,
)
from banking_risk.frtb.vertex_mapping import (
    FRTB_GIRR_VERTICES,
    FRTB_CSR_VERTICES,
    FRTB_COMMODITY_VERTICES,
)


# ── Stubs ─────────────────────────────────────────────────────────────────────

class _FlatRateInstrument:
    """Returns a uniform sensitivity at every requested tenor."""
    def __init__(self, sensitivity_per_vertex: float = 1.0):
        self._s = sensitivity_per_vertex

    def rate_sensitivities(self, curve, tenors):
        return {t: self._s for t in tenors}

    def delta(self, curve):
        return self._s

    def delta_fx(self, curve):
        return self._s


class _NullCurve:
    def zero_rate(self, t): return 0.035
    def discount(self, t):  return 1.0


_CURVE = _NullCurve()


def _girr(name="IRS", ccy="EUR", s=1.0):
    return Trading_Instrument(
        name=name,
        currency=ccy,
        risk_classes=frozenset({FRTB_Risk_Class.GIRR}),
        instrument=_FlatRateInstrument(s),
    )


def _csr(name="Bond", ccy="EUR", s=1.0):
    return Trading_Instrument(
        name=name,
        currency=ccy,
        risk_classes=frozenset({FRTB_Risk_Class.CSR_NON_SEC}),
        instrument=_FlatRateInstrument(s),
    )


def _commodity(name="Oil_Fwd", ccy="USD", s=1.0):
    return Trading_Instrument(
        name=name,
        currency=ccy,
        risk_classes=frozenset({FRTB_Risk_Class.COMMODITY}),
        instrument=_FlatRateInstrument(s),
    )


# ── FRTB_Risk_Class ───────────────────────────────────────────────────────────

def test_risk_class_coercion_from_string():
    ti = Trading_Instrument(
        name="x", currency="EUR",
        risk_classes=frozenset({"girr"}),
        instrument=None,
    )
    assert FRTB_Risk_Class.GIRR in ti.risk_classes


def test_invalid_risk_class_raises():
    with pytest.raises(ValueError):
        Trading_Instrument(
            name="x", currency="EUR",
            risk_classes=frozenset({"not_a_class"}),
            instrument=None,
        )


# ── instruments() ─────────────────────────────────────────────────────────────

def test_instruments_returns_all():
    ti1, ti2 = _girr("A"), _csr("B")
    p = Standard_Trading_Portfolio([ti1, ti2])
    assert p.instruments() == [ti1, ti2]


# ── girr_delta_sensitivities() ────────────────────────────────────────────────

def test_girr_empty_portfolio_returns_empty():
    p = Standard_Trading_Portfolio([])
    assert p.girr_delta_sensitivities(_CURVE) == {}


def test_girr_single_instrument_output_shape():
    p = Standard_Trading_Portfolio([_girr()])
    sens = p.girr_delta_sensitivities(_CURVE)
    assert "EUR" in sens
    assert sens["EUR"].shape == (len(FRTB_GIRR_VERTICES),)


def test_girr_sensitivity_values_correct():
    # FlatRateInstrument returns 1.0 per vertex, 10 GIRR vertices → sum = 10
    p = Standard_Trading_Portfolio([_girr(s=1.0)])
    sens = p.girr_delta_sensitivities(_CURVE)
    assert sens["EUR"].sum() == pytest.approx(10.0)


def test_girr_two_instruments_same_currency_aggregate():
    p = Standard_Trading_Portfolio([_girr("A", s=2.0), _girr("B", s=3.0)])
    sens = p.girr_delta_sensitivities(_CURVE)
    # each produces 10.0*s total → 20 + 30 = 50
    assert sens["EUR"].sum() == pytest.approx(50.0)


def test_girr_two_currencies_bucketed_separately():
    p = Standard_Trading_Portfolio([_girr("A", ccy="EUR"), _girr("B", ccy="USD")])
    sens = p.girr_delta_sensitivities(_CURVE)
    assert set(sens.keys()) == {"EUR", "USD"}


def test_non_girr_instrument_excluded_from_girr():
    p = Standard_Trading_Portfolio([_csr()])
    assert p.girr_delta_sensitivities(_CURVE) == {}


# ── csr_sensitivities() ───────────────────────────────────────────────────────

def test_csr_output_shape():
    p = Standard_Trading_Portfolio([_csr()])
    sens = p.csr_sensitivities(_CURVE)
    assert sens["EUR"].shape == (len(FRTB_CSR_VERTICES),)


def test_csr_excludes_girr_instruments():
    p = Standard_Trading_Portfolio([_girr()])
    assert p.csr_sensitivities(_CURVE) == {}


# ── commodity_sensitivities() ─────────────────────────────────────────────────

def test_commodity_output_shape():
    p = Standard_Trading_Portfolio([_commodity()])
    sens = p.commodity_sensitivities(_CURVE)
    assert sens["USD"].shape == (len(FRTB_COMMODITY_VERTICES),)


# ── equity_sensitivities() ────────────────────────────────────────────────────

def test_equity_returns_per_name():
    eq = Trading_Instrument(
        name="AAPL", currency="USD",
        risk_classes=frozenset({FRTB_Risk_Class.EQUITY}),
        instrument=_FlatRateInstrument(5.0),
    )
    p = Standard_Trading_Portfolio([eq])
    sens = p.equity_sensitivities(_CURVE)
    assert sens["AAPL"] == pytest.approx(5.0)


# ── fx_sensitivities() ────────────────────────────────────────────────────────

def test_fx_returns_per_name():
    fx = Trading_Instrument(
        name="EURUSD", currency="EUR",
        risk_classes=frozenset({FRTB_Risk_Class.FX}),
        instrument=_FlatRateInstrument(3.0),
    )
    p = Standard_Trading_Portfolio([fx])
    sens = p.fx_sensitivities(_CURVE)
    assert sens["EURUSD"] == pytest.approx(3.0)

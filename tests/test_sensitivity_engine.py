"""
Tests for FRTB_Sensitivity_Engine — BKR-56.

All QRE instruments are mocked. Tests verify routing, sign application,
aggregation shape, and error handling — not regulatory arithmetic (that
is tested in the individual SA calculator test files).
"""

import numpy as np
import pytest
from unittest.mock import Mock

from banking_risk.frtb.sensitivity_engine import FRTB_Sensitivity_Engine
from banking_risk.frtb.portfolio import (
    Trading_Instrument,
    Standard_Trading_Portfolio,
    FRTB_Risk_Class,
)
from banking_risk.frtb.vertex_mapping import (
    FRTB_GIRR_VERTICES,
    FRTB_CSR_VERTICES,
    FRTB_COMMODITY_VERTICES,
    FRTB_EQUITY_VEGA_VERTICES,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_curve():
    c = Mock()
    c.bumped_at = Mock(return_value=Mock())
    return c


def _rate_instr(sensitivity: float = 1.0, npv_val: float = 100.0) -> Mock:
    instr = Mock()
    instr.rate_sensitivities = Mock(
        return_value={t: sensitivity for t in FRTB_GIRR_VERTICES}
    )
    instr.npv   = Mock(return_value=npv_val)
    instr.delta = Mock(return_value=npv_val)
    return instr


def _csr_rate_instr(sensitivity: float = 1.0) -> Mock:
    # spec limits auto-attribute creation — prevents hasattr('cs01') returning True
    instr = Mock(spec=["rate_sensitivities"])
    instr.rate_sensitivities = Mock(
        return_value={t: sensitivity for t in FRTB_CSR_VERTICES}
    )
    return instr


def _cds_instr(sensitivity: float = 1.0) -> Mock:
    instr = Mock(spec=["cs01"])
    instr.cs01 = Mock(
        return_value={t: sensitivity for t in FRTB_CSR_VERTICES}
    )
    return instr


def _commodity_instr(sensitivity: float = 1.0) -> Mock:
    instr = Mock()
    instr.rate_sensitivities = Mock(
        return_value={t: sensitivity for t in FRTB_COMMODITY_VERTICES}
    )
    return instr


def _equity_instr(npv_val: float = 100.0) -> Mock:
    instr = Mock()
    instr.npv = Mock(return_value=npv_val)
    return instr


def _fx_instr(npv_val: float = 50.0) -> Mock:
    instr = Mock()
    instr.npv = Mock(return_value=npv_val)
    return instr


def _girr_ti(name="IRS", ccy="EUR", sensitivity=1.0, is_long=True):
    return Trading_Instrument(
        name=name, currency=ccy,
        risk_classes=frozenset({FRTB_Risk_Class.GIRR}),
        instrument=_rate_instr(sensitivity),
        is_long=is_long,
    )


def _csr_ti(name="Bond", bucket=1, sensitivity=1.0, is_long=True):
    return Trading_Instrument(
        name=name, currency="EUR",
        risk_classes=frozenset({FRTB_Risk_Class.CSR_NON_SEC}),
        instrument=_csr_rate_instr(sensitivity),
        csr_bucket=bucket,
        is_long=is_long,
    )


def _cds_ti(name="CDS", bucket=7, sensitivity=1.0, is_long=True):
    return Trading_Instrument(
        name=name, currency="EUR",
        risk_classes=frozenset({FRTB_Risk_Class.CSR_NON_SEC}),
        instrument=_cds_instr(sensitivity),
        csr_bucket=bucket,
        is_long=is_long,
    )


def _equity_ti(name="AAPL", bucket=5, npv_val=100.0, is_long=True):
    return Trading_Instrument(
        name=name, currency="USD",
        risk_classes=frozenset({FRTB_Risk_Class.EQUITY}),
        instrument=_equity_instr(npv_val),
        equity_bucket=bucket,
        is_long=is_long,
    )


def _fx_ti(name="EURUSD", ccy_pair="EURUSD", npv_val=50.0, is_long=True):
    return Trading_Instrument(
        name=name, currency="EUR",
        risk_classes=frozenset({FRTB_Risk_Class.FX}),
        instrument=_fx_instr(npv_val),
        ccy_pair=ccy_pair,
        is_long=is_long,
    )


def _commodity_ti(name="Oil", bucket=2, sensitivity=1.0, is_long=True):
    return Trading_Instrument(
        name=name, currency="USD",
        risk_classes=frozenset({FRTB_Risk_Class.COMMODITY}),
        instrument=_commodity_instr(sensitivity),
        commodity_bucket=bucket,
        is_long=is_long,
    )


def _engine(*instruments):
    portfolio = Standard_Trading_Portfolio(list(instruments))
    return FRTB_Sensitivity_Engine(portfolio, _mock_curve())


# ── Empty portfolio ───────────────────────────────────────────────────────────

def test_empty_portfolio_all_delta_empty():
    e = _engine()
    assert e.girr_delta()      == {}
    assert e.csr_delta()       == {}
    assert e.equity_delta()    == {}
    assert e.fx_delta()        == {}
    assert e.commodity_delta() == {}


# ── GIRR delta ────────────────────────────────────────────────────────────────

def test_girr_delta_output_shape():
    result = _engine(_girr_ti()).girr_delta()
    assert "EUR" in result
    assert result["EUR"].shape == (len(FRTB_GIRR_VERTICES),)


def test_girr_delta_flat_sensitivity_sums_correctly():
    # sensitivity=2 at each of 10 vertices → sum = 20
    result = _engine(_girr_ti(sensitivity=2.0)).girr_delta()
    assert result["EUR"].sum() == pytest.approx(20.0)


def test_girr_delta_long_positive_short_negative():
    long_result  = _engine(_girr_ti(is_long=True,  sensitivity=1.0)).girr_delta()
    short_result = _engine(_girr_ti(is_long=False, sensitivity=1.0)).girr_delta()
    np.testing.assert_allclose(long_result["EUR"], -short_result["EUR"])


def test_girr_delta_two_currencies_independent():
    e = _engine(_girr_ti("A", ccy="EUR"), _girr_ti("B", ccy="USD"))
    assert set(e.girr_delta().keys()) == {"EUR", "USD"}


def test_girr_delta_same_currency_aggregates():
    e = _engine(_girr_ti("A", sensitivity=1.0), _girr_ti("B", sensitivity=2.0))
    assert e.girr_delta()["EUR"].sum() == pytest.approx(30.0)


def test_girr_delta_non_girr_instrument_excluded():
    assert _engine(_csr_ti()).girr_delta() == {}


# ── CSR delta ─────────────────────────────────────────────────────────────────

def test_csr_delta_output_shape():
    result = _engine(_csr_ti(bucket=1)).csr_delta()
    assert 1 in result
    assert result[1].shape == (len(FRTB_CSR_VERTICES),)


def test_csr_delta_routes_to_cs01_for_cds():
    ti     = _cds_ti(bucket=7)
    result = _engine(ti).csr_delta()
    ti.instrument.cs01.assert_called_once()
    assert 7 in result


def test_csr_delta_routes_to_rate_sensitivities_for_bond():
    ti     = _csr_ti(bucket=1)
    result = _engine(ti).csr_delta()
    ti.instrument.rate_sensitivities.assert_called_once()
    assert 1 in result


def test_csr_delta_long_positive_short_negative():
    long_r  = _engine(_csr_ti(is_long=True)).csr_delta()
    short_r = _engine(_csr_ti(is_long=False)).csr_delta()
    np.testing.assert_allclose(long_r[1], -short_r[1])


def test_csr_delta_missing_bucket_raises():
    instr = _csr_rate_instr()
    ti = Trading_Instrument(
        name="NoBucket", currency="EUR",
        risk_classes=frozenset({FRTB_Risk_Class.CSR_NON_SEC}),
        instrument=instr,
    )
    with pytest.raises(ValueError, match="csr_bucket"):
        _engine(ti).csr_delta()


# ── Equity delta ──────────────────────────────────────────────────────────────

def test_equity_delta_uses_npv_for_linear():
    result = _engine(_equity_ti(bucket=5, npv_val=200.0)).equity_delta()
    assert 5 in result
    assert result[5] == [pytest.approx(200.0)]


def test_equity_delta_long_positive_short_negative():
    long_r  = _engine(_equity_ti(is_long=True,  npv_val=100.0)).equity_delta()
    short_r = _engine(_equity_ti(is_long=False, npv_val=100.0)).equity_delta()
    assert long_r[5][0]  == pytest.approx( 100.0)
    assert short_r[5][0] == pytest.approx(-100.0)


def test_equity_delta_no_bucket_defaults_to_residual():
    instr = _equity_instr(npv_val=50.0)
    ti = Trading_Instrument(
        name="X", currency="USD",
        risk_classes=frozenset({FRTB_Risk_Class.EQUITY}),
        instrument=instr,
    )
    assert 11 in _engine(ti).equity_delta()


def test_equity_delta_multiple_names_same_bucket():
    e = _engine(_equity_ti("AAPL", bucket=5, npv_val=100.0),
                _equity_ti("MSFT", bucket=5, npv_val=200.0))
    result = e.equity_delta()
    assert len(result[5]) == 2
    assert sum(result[5]) == pytest.approx(300.0)


# ── FX delta ──────────────────────────────────────────────────────────────────

def test_fx_delta_keyed_by_ccy_pair():
    result = _engine(_fx_ti(ccy_pair="EURUSD", npv_val=300.0)).fx_delta()
    assert "EURUSD" in result
    assert result["EURUSD"] == pytest.approx(300.0)


def test_fx_delta_long_positive_short_negative():
    long_r  = _engine(_fx_ti(is_long=True,  npv_val=100.0)).fx_delta()
    short_r = _engine(_fx_ti(is_long=False, npv_val=100.0)).fx_delta()
    assert long_r["EURUSD"]  == pytest.approx( 100.0)
    assert short_r["EURUSD"] == pytest.approx(-100.0)


def test_fx_delta_same_pair_aggregates():
    e = _engine(_fx_ti("A", ccy_pair="EURUSD", npv_val=100.0),
                _fx_ti("B", ccy_pair="EURUSD", npv_val=200.0))
    assert e.fx_delta()["EURUSD"] == pytest.approx(300.0)


# ── Commodity delta ───────────────────────────────────────────────────────────

def test_commodity_delta_output_shape():
    result = _engine(_commodity_ti(bucket=2)).commodity_delta()
    assert 2 in result
    assert result[2].shape == (len(FRTB_COMMODITY_VERTICES),)


def test_commodity_delta_long_positive_short_negative():
    long_r  = _engine(_commodity_ti(is_long=True)).commodity_delta()
    short_r = _engine(_commodity_ti(is_long=False)).commodity_delta()
    np.testing.assert_allclose(long_r[2], -short_r[2])


def test_commodity_delta_missing_bucket_raises():
    ti = Trading_Instrument(
        name="NoBucket", currency="USD",
        risk_classes=frozenset({FRTB_Risk_Class.COMMODITY}),
        instrument=_commodity_instr(),
    )
    with pytest.raises(ValueError, match="commodity_bucket"):
        _engine(ti).commodity_delta()


# ── Cross-class isolation ─────────────────────────────────────────────────────

def test_girr_instrument_only_populates_girr():
    e = _engine(_girr_ti())
    assert e.csr_delta()       == {}
    assert e.equity_delta()    == {}
    assert e.fx_delta()        == {}
    assert e.commodity_delta() == {}


def test_mixed_portfolio_each_class_isolated():
    e = _engine(
        _girr_ti("IRS"),
        _csr_ti("Bond"),
        _equity_ti("AAPL"),
        _fx_ti("EURUSD"),
        _commodity_ti("Oil"),
    )
    assert "EUR"     in e.girr_delta()
    assert 1         in e.csr_delta()
    assert 5         in e.equity_delta()
    assert "EURUSD"  in e.fx_delta()
    assert 2         in e.commodity_delta()


# ── Vega: linear instruments contribute nothing ───────────────────────────────

def test_linear_instruments_excluded_from_vega():
    e = _engine(_girr_ti())          # is_linear=True by default
    assert e.girr_vega()   == {}
    assert e.equity_vega() == {}
    assert e.fx_vega()     == {}

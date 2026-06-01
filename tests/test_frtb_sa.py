"""
Tests for FRTB_SA orchestrator — BKR-55.

Tests the facade layer that wires all risk-class calculators and
aggregates capital at both levels.
"""

import pytest
from unittest.mock import Mock
from banking_risk.frtb.sa import FRTB_SA, Risk_Class_View
from banking_risk.frtb.aggregator import Risk_Class_Capital, FRTB_SA_Result
from banking_risk.frtb.portfolio import Standard_Trading_Portfolio


def _empty_portfolio():
    return Standard_Trading_Portfolio([])


def _mock_curve():
    return Mock()


def _mock_result(capital=100.0):
    r = Mock()
    r.capital = capital
    return r


# ── Basic orchestration ───────────────────────────────────────────────────────

def test_frtb_sa_empty_portfolio():
    frtb = FRTB_SA(_empty_portfolio(), _mock_curve())
    assert frtb.total == pytest.approx(0.0)
    assert frtb.girr.capital == pytest.approx(0.0)
    assert frtb.csr.capital == pytest.approx(0.0)
    assert frtb.equity.capital == pytest.approx(0.0)
    assert frtb.fx.capital == pytest.approx(0.0)
    assert frtb.commodity.capital == pytest.approx(0.0)


def test_frtb_sa_total_is_sum_of_components():
    frtb = FRTB_SA(_empty_portfolio(), _mock_curve())
    components_sum = sum([
        frtb.girr.capital,
        frtb.csr.capital,
        frtb.equity.capital,
        frtb.fx.capital,
        frtb.commodity.capital,
    ])
    assert frtb.total == pytest.approx(components_sum)


def test_risk_class_view_sums_delta_vega_curvature():
    """Risk_Class_View.capital = delta + vega + curvature (or 0 if None)."""
    view = Risk_Class_View(
        delta=_mock_result(50.0),
        vega=_mock_result(30.0),
        curvature=_mock_result(10.0),
    )
    assert view.capital == pytest.approx(90.0)


def test_risk_class_view_handles_none_measures():
    """Risk_Class_View.capital skips None results."""
    view = Risk_Class_View(
        delta=_mock_result(50.0),
        vega=None,
        curvature=_mock_result(10.0),
    )
    assert view.capital == pytest.approx(60.0)


def test_risk_class_view_all_none():
    """Risk_Class_View.capital returns 0 when all measures are None."""
    view = Risk_Class_View(delta=None, vega=None, curvature=None)
    assert view.capital == pytest.approx(0.0)


# ── Reporting ─────────────────────────────────────────────────────────────────

def test_to_table_has_correct_shape():
    frtb  = FRTB_SA(_empty_portfolio(), _mock_curve())
    table = frtb.to_table()
    assert len(table) == 6   # 5 risk classes + FRTB SA total
    assert "delta"     in table.columns
    assert "vega"      in table.columns
    assert "curvature" in table.columns
    assert "total"     in table.columns


def test_to_table_last_row_is_total():
    frtb  = FRTB_SA(_empty_portfolio(), _mock_curve())
    assert frtb.to_table().index[-1] == "FRTB SA"


def test_to_table_sums_correctly():
    frtb  = FRTB_SA(_empty_portfolio(), _mock_curve())
    table = frtb.to_table()
    delta_sum       = table.loc[table.index != "FRTB SA", "delta"].sum()
    total_row_delta = table.loc["FRTB SA", "delta"]
    assert total_row_delta == pytest.approx(delta_sum)


# ── Aggregator dataclasses ────────────────────────────────────────────────────

def test_risk_class_capital_total():
    """Risk_Class_Capital.total = delta + vega + curvature."""
    rc = Risk_Class_Capital("GIRR", delta=100.0, vega=20.0, curvature=5.0)
    assert rc.total == pytest.approx(125.0)


def test_frtb_sa_result_total():
    """FRTB_SA_Result.total = sum(components) + drc + rrao."""
    components = [
        Risk_Class_Capital("GIRR", delta=100.0),
        Risk_Class_Capital("CSR", delta=50.0),
    ]
    result = FRTB_SA_Result(components=components, drc=10.0, rrao=5.0)
    assert result.total == pytest.approx(165.0)


def test_frtb_sa_result_to_table():
    """FRTB_SA_Result.to_table() returns proper shape."""
    components = [
        Risk_Class_Capital("GIRR", delta=100.0, vega=20.0),
        Risk_Class_Capital("CSR", delta=50.0),
    ]
    result = FRTB_SA_Result(components=components)
    table = result.to_table()
    assert len(table) == 3  # 2 components + total
    assert table.index[-1] == "FRTB SA"


# ── Porfolio interface calls ──────────────────────────────────────────────────

def test_frtb_sa_uses_sensitivity_engine():
    """FRTB_SA delegates to FRTB_Sensitivity_Engine — empty portfolio yields zero capital."""
    frtb = FRTB_SA(_empty_portfolio(), _mock_curve())
    assert frtb.total == pytest.approx(0.0)


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_commodity_has_no_vega():
    frtb = FRTB_SA(_empty_portfolio(), _mock_curve())
    assert frtb.commodity.vega is None


def test_curvature_csr_equity_fx_not_yet_computed():
    frtb = FRTB_SA(_empty_portfolio(), _mock_curve())
    # GIRR curvature is wired. Others need spot/spread bump in QRE.
    assert frtb.csr.curvature      is None
    assert frtb.equity.curvature   is None
    assert frtb.fx.curvature       is None
    assert frtb.commodity.curvature is None


def test_result_property_returns_frtb_sa_result():
    frtb = FRTB_SA(_empty_portfolio(), _mock_curve())
    assert isinstance(frtb.result, FRTB_SA_Result)

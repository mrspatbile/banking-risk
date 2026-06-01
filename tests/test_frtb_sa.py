"""
Tests for FRTB_SA orchestrator — BKR-55.

Tests the facade layer that wires all risk-class calculators and
aggregates capital at both levels.
"""

import pytest
from unittest.mock import Mock, MagicMock
from banking_risk.frtb.sa import FRTB_SA, Risk_Class_View
from banking_risk.frtb.aggregator import Risk_Class_Capital, FRTB_SA_Result


def _mock_portfolio():
    """Minimal mock Trading_Portfolio with all sensitivity methods."""
    p = Mock()
    p.girr_delta_sensitivities = Mock(return_value={})
    p.girr_vega_sensitivities = Mock(return_value={})
    p.csr_sensitivities = Mock(return_value={})
    p.equity_sensitivities = Mock(return_value={})
    p.fx_sensitivities = Mock(return_value={})
    p.commodity_sensitivities = Mock(return_value={})
    return p


def _mock_curve():
    """Minimal mock Zero_Curve."""
    return Mock()


def _mock_result(capital=100.0):
    """Result object with .capital attribute."""
    r = Mock()
    r.capital = capital
    return r


# ── Basic orchestration ───────────────────────────────────────────────────────

def test_frtb_sa_empty_portfolio():
    """Empty portfolio → all risk class capitals are 0."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
    assert frtb.total == pytest.approx(0.0)
    assert frtb.girr.capital == pytest.approx(0.0)
    assert frtb.csr.capital == pytest.approx(0.0)
    assert frtb.equity.capital == pytest.approx(0.0)
    assert frtb.fx.capital == pytest.approx(0.0)
    assert frtb.commodity.capital == pytest.approx(0.0)


def test_frtb_sa_total_is_sum_of_components():
    """total = girr + csr + equity + fx + commodity."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
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
    """to_table() has 5 risk classes + 1 total row, 4 columns."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
    table = frtb.to_table()
    assert len(table) == 6  # 5 risk classes + FRTB SA total
    assert "delta" in table.columns
    assert "vega" in table.columns
    assert "curvature" in table.columns
    assert "total" in table.columns


def test_to_table_last_row_is_total():
    """to_table() last row is the summary 'FRTB SA'."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
    table = frtb.to_table()
    assert table.index[-1] == "FRTB SA"


def test_to_table_sums_correctly():
    """to_table() total row delta = sum of all delta values."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
    table = frtb.to_table()
    delta_sum = table.loc[table.index != "FRTB SA", "delta"].sum()
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

def test_frtb_sa_calls_all_sensitivity_methods():
    """FRTB_SA.__init__ calls all portfolio sensitivity methods."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)

    p.girr_delta_sensitivities.assert_called_once_with(c)
    p.girr_vega_sensitivities.assert_called_once_with(c)
    p.csr_sensitivities.assert_called_once_with(c)
    p.equity_sensitivities.assert_called_once_with(c)
    p.fx_sensitivities.assert_called_once_with(c)
    p.commodity_sensitivities.assert_called_once_with(c)


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_commodity_has_no_vega():
    """Commodity risk class has no vega measure."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
    assert frtb.commodity.vega is None


def test_curvature_not_yet_computed():
    """All curvature measures are None (no gamma inputs yet)."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
    assert frtb.girr.curvature is None
    assert frtb.csr.curvature is None
    assert frtb.equity.curvature is None
    assert frtb.fx.curvature is None
    assert frtb.commodity.curvature is None


def test_result_property_returns_frtb_sa_result():
    """FRTB_SA.result returns an FRTB_SA_Result object."""
    p = _mock_portfolio()
    c = _mock_curve()
    frtb = FRTB_SA(p, c)
    assert isinstance(frtb.result, FRTB_SA_Result)

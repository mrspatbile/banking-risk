"""
Tests for SA-CCR Portfolio — BKR-68.

Tests netting set grouping and SA-CCR EAD computation across
multiple counterparties.
"""

import pytest
from banking_risk.credit_risk.sa_ccr_portfolio import (
    Netting_Set, SA_CCR_Portfolio, SA_CCR_Portfolio_Result
)
from banking_risk.credit_risk.sa_ccr import Derivative_Position, AssetClass


def test_netting_set_creation():
    """Netting_Set holds derivative positions and collateral."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set(
        netting_set_id="JPM_USD_1",
        counterparty="JPMorgan Chase",
        positions=[pos],
        collateral=50_000,
    )
    assert ns.netting_set_id == "JPM_USD_1"
    assert ns.counterparty == "JPMorgan Chase"
    assert len(ns.positions) == 1
    assert ns.collateral == 50_000


def test_netting_set_total_notional():
    """Netting_Set.total_notional sums position notionals."""
    pos1 = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0)
    pos2 = Derivative_Position("FX_EURUSD", AssetClass.FX, 500_000, 2.0)
    ns = Netting_Set("ns1", "JPM", [pos1, pos2])
    assert ns.total_notional == pytest.approx(1_500_000)


def test_netting_set_total_mtm():
    """Netting_Set.total_mtm sums position MTM values."""
    pos1 = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    pos2 = Derivative_Position("FX_EURUSD", AssetClass.FX, 500_000, 2.0, mtm=-50_000)
    ns = Netting_Set("ns1", "JPM", [pos1, pos2])
    assert ns.total_mtm == pytest.approx(50_000)


def test_sa_ccr_portfolio_empty():
    """SA_CCR_Portfolio with no netting sets returns zero EAD."""
    portfolio = SA_CCR_Portfolio([])
    assert portfolio.total_ead == pytest.approx(0.0)
    assert len(portfolio.results) == 0


def test_sa_ccr_portfolio_single_netting_set():
    """SA_CCR_Portfolio computes EAD for single netting set."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set("ns1", "JPM", [pos], collateral=0.0)
    portfolio = SA_CCR_Portfolio([ns])

    assert "ns1" in portfolio.results
    result = portfolio.results["ns1"]
    assert result.netting_set_id == "ns1"
    assert result.ead > 0  # Should have positive EAD


def test_sa_ccr_portfolio_multiple_netting_sets():
    """SA_CCR_Portfolio aggregates EAD across netting sets."""
    pos1 = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    pos2 = Derivative_Position("FX_EURUSD", AssetClass.FX, 500_000, 2.0, mtm=50_000)

    ns1 = Netting_Set("JPM_1", "JPMorgan Chase", [pos1], collateral=0.0)
    ns2 = Netting_Set("GS_1", "Goldman Sachs", [pos2], collateral=0.0)

    portfolio = SA_CCR_Portfolio([ns1, ns2])
    assert portfolio.total_ead > 0
    assert "JPM_1" in portfolio.results
    assert "GS_1" in portfolio.results


def test_sa_ccr_portfolio_by_counterparty():
    """SA_CCR_Portfolio aggregates EAD by counterparty name."""
    pos1 = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    pos2 = Derivative_Position("CDS_5Y", AssetClass.CREDIT, 500_000, 5.0, mtm=50_000)

    # Two netting sets with same counterparty
    ns1 = Netting_Set("JPM_USD", "JPMorgan Chase", [pos1], collateral=0.0)
    ns2 = Netting_Set("JPM_EUR", "JPMorgan Chase", [pos2], collateral=0.0)

    portfolio = SA_CCR_Portfolio([ns1, ns2])
    by_cpty = portfolio.results  # Trigger compute

    # Check aggregation
    assert "JPMorgan Chase" in portfolio.compute().by_counterparty
    jpm_ead = portfolio.compute().by_counterparty["JPMorgan Chase"]
    assert jpm_ead == pytest.approx(
        portfolio.results["JPM_USD"].ead + portfolio.results["JPM_EUR"].ead
    )


def test_sa_ccr_portfolio_result_dataclass():
    """SA_CCR_Portfolio_Result holds aggregated results."""
    from banking_risk.credit_risk.sa_ccr import SA_CCR_Result

    result1 = SA_CCR_Result("ns1", 0, 100_000, 100_000, 0, 50_000, 210_000)
    result2 = SA_CCR_Result("ns2", 0, 50_000, 50_000, 0, 25_000, 105_000)

    portfolio_result = SA_CCR_Portfolio_Result(
        results={"ns1": result1, "ns2": result2},
        total_ead=315_000,
        by_counterparty={"JPM": 315_000},
    )

    assert portfolio_result.total_ead == pytest.approx(315_000)
    assert portfolio_result.by_counterparty["JPM"] == pytest.approx(315_000)


def test_sa_ccr_portfolio_to_table():
    """SA_CCR_Portfolio.to_table() produces summary dataframe."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set("ns1", "JPM", [pos], collateral=50_000)
    portfolio = SA_CCR_Portfolio([ns])

    table = portfolio.to_table()
    assert "ns1" in table.index
    assert "ead" in table.columns
    assert table.loc["ns1", "ead"] > 0

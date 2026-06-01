"""
Tests for CVA Aggregator — BKR-68.

Tests BA-CVA capital computation from SA-CCR EAD across counterparties.
"""

import pytest
from banking_risk.credit_risk.cva_aggregator import CVA_Aggregator, CVA_Aggregation_Result
from banking_risk.credit_risk.sa_ccr_portfolio import Netting_Set, SA_CCR_Portfolio
from banking_risk.credit_risk.sa_ccr import Derivative_Position, AssetClass


def test_cva_aggregation_result_creation():
    """CVA_Aggregation_Result holds CVA capital and breakdown."""
    result = CVA_Aggregation_Result(
        cva_capital=50_000,
        by_counterparty={"JPM": 30_000, "GS": 20_000},
    )
    assert result.cva_capital == pytest.approx(50_000)
    assert result.by_counterparty["JPM"] == pytest.approx(30_000)


def test_cva_aggregator_empty_portfolio():
    """CVA_Aggregator with no counterparties returns zero capital."""
    portfolio = SA_CCR_Portfolio([])
    aggregator = CVA_Aggregator(portfolio)
    assert aggregator.cva_capital() == pytest.approx(0.0)


def test_cva_aggregator_single_counterparty():
    """CVA_Aggregator computes CVA capital for single counterparty."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set("ns1", "JPMorgan Chase", [pos], collateral=0.0)
    portfolio = SA_CCR_Portfolio([ns])

    aggregator = CVA_Aggregator(portfolio)
    cva_cap = aggregator.cva_capital()
    assert cva_cap >= 0.0  # CVA capital should be non-negative


def test_cva_aggregator_multiple_counterparties():
    """CVA_Aggregator aggregates across multiple counterparties."""
    pos1 = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    pos2 = Derivative_Position("FX_EURUSD", AssetClass.FX, 500_000, 2.0, mtm=50_000)

    ns1 = Netting_Set("JPM_1", "JPMorgan Chase", [pos1], collateral=0.0)
    ns2 = Netting_Set("GS_1", "Goldman Sachs", [pos2], collateral=0.0)

    portfolio = SA_CCR_Portfolio([ns1, ns2])
    aggregator = CVA_Aggregator(portfolio)

    cva_cap = aggregator.cva_capital()
    assert cva_cap >= 0.0

    by_cpty = aggregator.cva_by_counterparty()
    assert "JPMorgan Chase" in by_cpty
    assert "Goldman Sachs" in by_cpty


def test_cva_aggregator_compute():
    """CVA_Aggregator.compute() returns full CVA_Aggregation_Result."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set("ns1", "JPM", [pos], collateral=0.0)
    portfolio = SA_CCR_Portfolio([ns])

    aggregator = CVA_Aggregator(portfolio)
    result = aggregator.compute()

    assert isinstance(result, CVA_Aggregation_Result)
    assert result.cva_capital >= 0.0
    assert result.ba_cva_result is not None


def test_cva_aggregator_caching():
    """CVA_Aggregator caches computed results."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set("ns1", "JPM", [pos], collateral=0.0)
    portfolio = SA_CCR_Portfolio([ns])

    aggregator = CVA_Aggregator(portfolio)
    result1 = aggregator.compute()
    result2 = aggregator.compute()

    # Should return the same object (cached)
    assert result1 is result2


def test_cva_aggregator_to_dict():
    """CVA_Aggregator.to_dict() exports for capital stack integration."""
    pos = Derivative_Position("IRS_5Y", AssetClass.IR, 1_000_000, 5.0, mtm=100_000)
    ns = Netting_Set("ns1", "JPM", [pos], collateral=0.0)
    portfolio = SA_CCR_Portfolio([ns])

    aggregator = CVA_Aggregator(portfolio)
    export = aggregator.to_dict()

    assert "cva_capital" in export
    assert "by_counterparty" in export
    assert export["cva_capital"] >= 0.0

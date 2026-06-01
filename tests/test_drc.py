"""Tests for FRTB Default Risk Charge (DRC) — BKR-58."""

import pytest
from banking_risk.frtb.drc import DRC_Calculator, DRC_Position


def test_drc_empty_portfolio():
    calc = DRC_Calculator()
    result = calc.compute([])
    assert result.capital == pytest.approx(0.0)


def test_drc_single_long_position():
    pos = DRC_Position(
        name="Corp_Bond", notional=1_000_000.0, lgd=0.4, mtm=950_000.0,
        bucket=6, is_long=True
    )
    calc = DRC_Calculator()
    result = calc.compute([pos])

    # JTD_long = max(0.4 × 1M - 950k, 0) = max(400k - 950k, 0) = 0
    assert result.capital == pytest.approx(0.0)


def test_drc_single_short_position():
    pos = DRC_Position(
        name="Corp_Bond", notional=1_000_000.0, lgd=0.4, mtm=900_000.0,
        bucket=6, is_long=False
    )
    calc = DRC_Calculator()
    result = calc.compute([pos])

    # JTD_short = max(-(0.4 × 1M - 900k), 0) = max(-(400k - 900k), 0) = max(500k, 0) = 500k
    # No long to offset, K = 0
    assert result.capital == pytest.approx(0.0)


def test_drc_long_short_netting():
    long_pos = DRC_Position(
        name="Bond_Long", notional=1_000_000.0, lgd=0.4, mtm=800_000.0,
        bucket=6, is_long=True
    )
    short_pos = DRC_Position(
        name="Bond_Short", notional=500_000.0, lgd=0.4, mtm=300_000.0,
        bucket=6, is_long=False
    )
    calc = DRC_Calculator()
    result = calc.compute([long_pos, short_pos])

    # Long: JTD_long = max(400k - 800k, 0) = 0
    # Short: JTD_short = max(-(200k - 300k), 0) = 100k
    # No long position, K = 0
    assert result.capital == pytest.approx(0.0)


def test_drc_result_to_table():
    pos = DRC_Position(
        name="Bond", notional=1_000_000.0, lgd=0.5, mtm=400_000.0,
        bucket=6, is_long=True
    )
    calc = DRC_Calculator()
    result = calc.compute([pos])

    table = result.to_table()
    assert len(table) > 0

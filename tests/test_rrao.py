"""Tests for FRTB Residual Risk Add-On (RRAO) — BKR-59."""

import pytest
from banking_risk.frtb.rrao import RRAO_Calculator, RRAO_Position, RRAO_Category


def test_rrao_empty():
    calc = RRAO_Calculator()
    result = calc.compute([])
    assert result.capital == pytest.approx(0.0)


def test_rrao_exotic_1pct():
    pos = RRAO_Position("Longevity_Swap", 10_000_000.0, RRAO_Category.EXOTIC)
    calc = RRAO_Calculator()
    result = calc.compute([pos])
    assert result.capital == pytest.approx(100_000.0)  # 1% × 10M


def test_rrao_other_0_1pct():
    pos = RRAO_Position("Gap_Risk", 10_000_000.0, RRAO_Category.OTHER)
    calc = RRAO_Calculator()
    result = calc.compute([pos])
    assert result.capital == pytest.approx(10_000.0)  # 0.1% × 10M


def test_rrao_mixed():
    exotic = RRAO_Position("Variance", 5_000_000.0, RRAO_Category.EXOTIC)
    other = RRAO_Position("Correlation", 20_000_000.0, RRAO_Category.OTHER)
    calc = RRAO_Calculator()
    result = calc.compute([exotic, other])
    expected = 5_000_000 * 0.01 + 20_000_000 * 0.001
    assert result.capital == pytest.approx(expected)

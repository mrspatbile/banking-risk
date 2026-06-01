"""Tests for SA Counterparty Credit Risk (SA-CCR) — BKR-61."""

import pytest
import numpy as np
from banking_risk.credit_risk.sa_ccr import (
    SA_CCR_Calculator, Derivative_Position, AssetClass
)


def test_sa_ccr_empty():
    calc = SA_CCR_Calculator()
    result = calc.compute("NS1", [])
    assert result.ead == pytest.approx(0.0)


def test_sa_ccr_single_ir_swap():
    pos = Derivative_Position(
        name="IRS_5Y", asset_class=AssetClass.IR,
        notional=10_000_000.0, maturity_years=5.0, mtm=200_000.0
    )
    calc = SA_CCR_Calculator()
    result = calc.compute("NS1", [pos], collateral=0.0)

    # SF for IR = 0.004
    # M = sqrt(5/5) = 1
    # AddOn = 0.004 × 10M × 1 = 40k
    # RC = max(200k - 0, 0) = 200k
    assert result.addon == pytest.approx(40_000.0)
    assert result.rc == pytest.approx(200_000.0)
    assert result.ead > 0


def test_sa_ccr_with_collateral():
    pos = Derivative_Position(
        name="Swap", asset_class=AssetClass.IR,
        notional=10_000_000.0, maturity_years=5.0, mtm=200_000.0
    )
    calc = SA_CCR_Calculator()
    result = calc.compute("NS1", [pos], collateral=150_000.0)

    # RC = max(200k - 150k, 0) = 50k
    assert result.rc == pytest.approx(50_000.0)


def test_sa_ccr_negative_mtm():
    pos = Derivative_Position(
        name="Swap", asset_class=AssetClass.IR,
        notional=10_000_000.0, maturity_years=5.0, mtm=-100_000.0
    )
    calc = SA_CCR_Calculator()
    result = calc.compute("NS1", [pos])

    # RC = max(-100k, 0) = 0
    assert result.rc == pytest.approx(0.0)


def test_sa_ccr_maturity_factor():
    # M < 1 → use 1
    pos_short = Derivative_Position(
        name="Short", asset_class=AssetClass.IR,
        notional=10_000_000.0, maturity_years=0.5, mtm=0.0
    )
    # M > 5 → use 5
    pos_long = Derivative_Position(
        name="Long", asset_class=AssetClass.IR,
        notional=10_000_000.0, maturity_years=10.0, mtm=0.0
    )
    calc = SA_CCR_Calculator()
    result_short = calc.compute("NS1", [pos_short])
    result_long = calc.compute("NS2", [pos_long])

    # Both should use the same SF and M since maturity is clamped to [1, 5]
    # Short: M = sqrt(1/5) = 0.447
    # Long: M = sqrt(5/5) = 1.0
    assert result_short.addon == pytest.approx(10_000_000 * 0.004 * np.sqrt(1/5))
    assert result_long.addon == pytest.approx(10_000_000 * 0.004 * 1.0)

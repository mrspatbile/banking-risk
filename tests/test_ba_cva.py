"""Tests for BA-CVA Capital — BKR-62."""

import pytest
from banking_risk.credit_risk.ba_cva import BA_CVA_Calculator, CVA_Counterparty


def test_ba_cva_empty():
    calc = BA_CVA_Calculator()
    result = calc.compute([])
    assert result.capital == pytest.approx(0.0)


def test_ba_cva_single_counterparty():
    cpty = CVA_Counterparty(
        cpty_name="Bank_A", ead=10_000_000.0, maturity_years=3.0, risk_weight=0.045
    )
    calc = BA_CVA_Calculator()
    result = calc.compute([cpty])

    # MR for 3Y = (exp(-0.05×3) - 1) / (-0.05×3)
    import numpy as np
    mr = (np.exp(-0.05 * 3) - 1) / (-0.05 * 3)
    # SCVA = 0.045 × MR × 10M
    scva = 0.045 * mr * 10_000_000
    # K = 0.5 × sqrt((0.5 × SCVA)² + (1-0.5²) × SCVA²)
    k = 0.5 * np.sqrt((0.5 * scva) ** 2 + (1 - 0.5 ** 2) * scva ** 2)
    assert result.capital == pytest.approx(k)


def test_ba_cva_two_counterparties():
    cpty1 = CVA_Counterparty("Bank_A", 5_000_000.0, 2.0, 0.03)
    cpty2 = CVA_Counterparty("Bank_B", 3_000_000.0, 4.0, 0.05)
    calc = BA_CVA_Calculator()
    result = calc.compute([cpty1, cpty2])

    assert result.capital > 0
    assert "Bank_A" in result.by_counterparty
    assert "Bank_B" in result.by_counterparty

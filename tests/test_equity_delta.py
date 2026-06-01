import numpy as np
import pytest
from banking_risk.frtb.equity.delta import SA_Equity_Delta_Calculator
from banking_risk.frtb.constants import EQUITY_RISK_WEIGHTS, EQUITY_RHO_INTRA

_CALC = SA_Equity_Delta_Calculator()


def _sens(bucket: int, names: list[float]) -> dict[int, list[float]]:
    return {bucket: names}


def test_zero_sensitivity_zero_capital():
    result = _CALC.compute({5: [0.0, 0.0]})
    assert result.capital == pytest.approx(0.0)


def test_single_name_K_equals_rw_times_sensitivity():
    # Single name: no cross-name correlation → K = WS = s × RW
    result = _CALC.compute({5: [100.0]})
    rw = EQUITY_RISK_WEIGHTS[4]  # bucket 5, index 4
    assert result.K[5] == pytest.approx(abs(100.0 * rw), rel=1e-9)


def test_capital_increases_with_more_names():
    r1 = _CALC.compute({5: [100.0]})
    r2 = _CALC.compute({5: [100.0, 100.0]})
    assert r2.capital >= r1.capital


def test_higher_rw_bucket_higher_capital():
    # Bucket 9 (small cap EM, RW=70%) > bucket 5 (large cap DM, RW=30%)
    r5 = _CALC.compute({5: [100.0]})
    r9 = _CALC.compute({9: [100.0]})
    assert r9.K[9] > r5.K[5]


def test_residual_bucket_no_cross_bucket():
    r5  = _CALC.compute({5: [100.0]})
    r11 = _CALC.compute({11: [100.0]})
    r_both = _CALC.compute({5: [100.0], 11: [100.0]})
    # bucket 11 contributes K_11² to total, but cross-term = 0
    import math
    expected = math.sqrt(r5.K[5]**2 + r11.K[11]**2)
    assert r_both.capital == pytest.approx(expected, rel=1e-6)


def test_two_regular_buckets_cross_bucket():
    r_both = _CALC.compute({5: [100.0], 6: [100.0]})
    r5 = _CALC.compute({5: [100.0]})
    r6 = _CALC.compute({6: [100.0]})
    # With γ = 0.15 and S > 0, combined > sqrt(K5² + K6²)
    import math
    naive = math.sqrt(r5.K[5]**2 + r6.K[6]**2)
    assert r_both.capital >= naive


def test_invalid_bucket_raises():
    with pytest.raises(ValueError):
        _CALC.compute({0: [1.0]})
    with pytest.raises(ValueError):
        _CALC.compute({12: [1.0]})


def test_result_buckets_populated():
    result = _CALC.compute({5: [1.0], 8: [1.0]})
    assert sorted(result.buckets) == [5, 8]


def test_to_table_has_expected_columns():
    result = _CALC.compute({5: [10.0, 20.0]})
    table  = result.to_table()
    assert "K" in table.columns
    assert "n_names" in table.columns

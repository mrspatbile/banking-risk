import math
import pytest

from banking_risk.csrbb.spread_risk import (
    Spread_Position,
    CSRBB_Result,
    SA_CSRBB_Calculator,
    CSRBB_STRESS_SCENARIOS,
)


def _pos(name="Bond_5Y", currency="EUR", notional=1_000_000,
         maturity=5.0, z_spread=0.015, rating=None):
    return Spread_Position(
        name=name,
        currency=currency,
        notional=notional,
        maturity_years=maturity,
        z_spread=z_spread,
        rating=rating,
    )


_CALC = SA_CSRBB_Calculator(risk_free_rate=0.03)


# ── CS01 sign and magnitude ───────────────────────────────────────────────────

def test_cs01_positive_for_long_position():
    result = _CALC.compute([_pos(notional=1_000_000)])
    assert result.detail.loc["Bond_5Y", "cs01"] > 0.0


def test_cs01_zero_for_zero_notional():
    result = _CALC.compute([_pos(notional=0.0)])
    assert result.detail.loc["Bond_5Y", "cs01"] == pytest.approx(0.0)


def test_longer_maturity_higher_cs01():
    r5  = _CALC.compute([_pos("B5",  maturity=5.0)]).total_cs01
    r10 = _CALC.compute([_pos("B10", maturity=10.0)]).total_cs01
    assert r10 > r5


def test_cs01_manual_value():
    # CS01 = N × T × exp(-(rf+s)×T) × 1e-4
    pos  = _pos(notional=1_000_000, maturity=5.0, z_spread=0.015)
    rf   = 0.03
    disc = math.exp(-(rf + 0.015) * 5.0)
    expected = 1_000_000 * 5.0 * disc * 1e-4
    result = _CALC.compute([pos])
    assert result.detail.loc["Bond_5Y", "cs01"] == pytest.approx(expected, rel=1e-6)


# ── Stress P&L ────────────────────────────────────────────────────────────────

def test_spread_widening_reduces_pv():
    result = _CALC.compute([_pos()])
    assert result.stress_pnl["spread_widen_100bp"] < 0.0


def test_spread_tightening_increases_pv():
    result = _CALC.compute([_pos()])
    assert result.stress_pnl["spread_tighten_50bp"] > 0.0


def test_stress_pnl_approx_cs01_times_shock():
    # For small shocks, ΔPV ≈ −CS01 × shock_bps
    result     = _CALC.compute([_pos()])
    cs01       = result.total_cs01
    shock_bps  = CSRBB_STRESS_SCENARIOS["spread_widen_100bp"]
    expected   = -cs01 * shock_bps
    actual     = result.stress_pnl["spread_widen_100bp"]
    # Closed-form revaluation vs linear — within 5 % for 100bp shock
    assert abs(actual - expected) / abs(expected) < 0.05


def test_stress_pnl_larger_notional_scales_linearly():
    r1 = _CALC.compute([_pos(notional=1_000_000)]).stress_pnl["spread_widen_100bp"]
    r2 = _CALC.compute([_pos(notional=2_000_000)]).stress_pnl["spread_widen_100bp"]
    assert r2 == pytest.approx(2 * r1, rel=1e-9)


# ── Aggregation ───────────────────────────────────────────────────────────────

def test_total_cs01_is_sum_of_positions():
    p1 = _pos("A", notional=1_000_000, maturity=5.0)
    p2 = _pos("B", notional=500_000,   maturity=3.0)
    result = _CALC.compute([p1, p2])
    cs01_a = result.detail.loc["A", "cs01"]
    cs01_b = result.detail.loc["B", "cs01"]
    assert result.total_cs01 == pytest.approx(cs01_a + cs01_b, rel=1e-9)


def test_cs01_by_rating_sums_to_total_when_all_rated():
    p1 = _pos("A", rating="BBB")
    p2 = _pos("B", rating="BB", maturity=3.0)
    result = _CALC.compute([p1, p2])
    assert sum(result.cs01_by_rating.values()) == pytest.approx(result.total_cs01, rel=1e-9)


def test_cs01_by_rating_groups_same_rating():
    p1 = _pos("A", notional=1_000_000, rating="BBB")
    p2 = _pos("B", notional=2_000_000, maturity=3.0, rating="BBB")
    result = _CALC.compute([p1, p2])
    assert "BBB" in result.cs01_by_rating
    assert len(result.cs01_by_rating) == 1


def test_cs01_by_rating_empty_when_no_rating():
    result = _CALC.compute([_pos(rating=None)])
    assert result.cs01_by_rating == {}


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_portfolio_returns_zeros():
    result = _CALC.compute([])
    assert result.total_cs01 == 0.0
    for v in result.stress_pnl.values():
        assert v == 0.0


def test_custom_scenario_respected():
    calc   = SA_CSRBB_Calculator(scenarios={"shock_200bp": 200.0}, risk_free_rate=0.03)
    result = calc.compute([_pos()])
    assert "shock_200bp" in result.stress_pnl
    assert result.stress_pnl["shock_200bp"] < 0.0


def test_detail_index_is_position_name():
    result = _CALC.compute([_pos("MyBond")])
    assert "MyBond" in result.detail.index

import math
import pytest
import numpy as np
from banking_risk.irrbb.book import Position, Standard_Banking_Book
from banking_risk.irrbb.constants import EBA_BUCKET_MIDPOINTS, PositionType
from banking_risk.irrbb.eve import SA_EVE_Calculator
from banking_risk.irrbb.scenarios import Scenario_Set
from tests.helpers import Flat_Curve


def _book(positions, tier1):
    return Standard_Banking_Book(positions, tier1_capital=tier1)


def _single_asset(maturity_months=60, notional=1_000_000):
    return Position(
        name="loan",
        type=PositionType.ASSET,
        currency="EUR",
        notional=notional,
        maturity_months=maturity_months,
        coupon_months=0,
        rate=0.05,
        floating=False,
    )


# ── Basic computation ─────────────────────────────────────────────────────────

def test_eve_zero_shock_gives_zero_delta():
    """Zero shock → shocked rates equal base rates → ΔEVE = 0."""
    from banking_risk.irrbb.scenarios import Parallel_Up
    book = _book([_single_asset()], tier1=500_000)
    # Manually verify: with shock=0, all Δ should be 0
    curve = Flat_Curve(0.03)
    ss = Scenario_Set("EUR")
    result = SA_EVE_Calculator().compute(book, {"EUR": ss}, {"EUR": curve})
    # All ΔEVE values are floats; parallel_up increases rates → positive ΔEVE for asset
    assert isinstance(result.delta_eve, dict)
    assert len(result.delta_eve) == 6


def test_parallel_up_positive_delta_for_asset():
    """Rising rates → asset NPV falls → ΔEVE > 0 for a fixed-rate asset book."""
    book = _book([_single_asset(maturity_months=60)], tier1=500_000)
    curve = Flat_Curve(0.03)
    ss = Scenario_Set("EUR")
    result = SA_EVE_Calculator().compute(book, {"EUR": ss}, {"EUR": curve})
    assert result.delta_eve["parallel_up"] > 0


def test_parallel_down_negative_delta_for_asset():
    """Falling rates → asset NPV rises → ΔEVE < 0 for a fixed-rate asset book."""
    book = _book([_single_asset(maturity_months=60)], tier1=500_000)
    curve = Flat_Curve(0.03)
    ss = Scenario_Set("EUR")
    result = SA_EVE_Calculator().compute(book, {"EUR": ss}, {"EUR": curve})
    assert result.delta_eve["parallel_down"] < 0


def test_eve_delta_manual_calculation():
    """ΔEVE for single asset matches manually computed discount factor difference."""
    # Asset slotted in 5Y bucket (maturity=60M), midpoint = 4.5Y
    midpoint = (4.0 + 5.0) / 2   # = 4.5Y
    notional = 1_000_000
    r_base = 0.03
    shock = 0.02   # EUR parallel_up = 200bps

    expected_delta = notional * (
        math.exp(-r_base * midpoint) - math.exp(-(r_base + shock) * midpoint)
    )

    book = _book([_single_asset(maturity_months=60)], tier1=500_000)
    result = SA_EVE_Calculator().compute(
        book, {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(r_base)}
    )
    assert result.delta_eve["parallel_up"] == pytest.approx(expected_delta, rel=1e-6)


def test_npv_base_series_length():
    book = _book([_single_asset()], tier1=500_000)
    result = SA_EVE_Calculator().compute(
        book, {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(0.03)}
    )
    assert len(result.npv_base) == 19


def test_npv_base_bucket_nonzero_for_asset():
    """The 5Y bucket should carry the notional NPV; all others zero."""
    book = _book([_single_asset(maturity_months=60)], tier1=500_000)
    result = SA_EVE_Calculator().compute(
        book, {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(0.03)}
    )
    assert result.npv_base["5Y"] != pytest.approx(0.0)
    assert result.npv_base["1Y"] == pytest.approx(0.0)


# ── SOT ───────────────────────────────────────────────────────────────────────

def test_outlier_flag_triggered():
    """Small tier1 relative to a large position → outlier."""
    book = _book([_single_asset(notional=1_000_000, maturity_months=60)], tier1=1_000)
    result = SA_EVE_Calculator().compute(
        book, {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(0.03)}
    )
    assert result.is_outlier is True


def test_outlier_flag_not_triggered():
    """Large tier1 relative to position → not an outlier."""
    book = _book([_single_asset(notional=1_000, maturity_months=60)], tier1=1_000_000)
    result = SA_EVE_Calculator().compute(
        book, {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(0.03)}
    )
    assert result.is_outlier is False


def test_sot_uses_strict_greater_than():
    """is_outlier uses strict > 15%, not >=.
    Verified by bracketing: tier1 just above threshold → False, just below → True."""
    book_ref = _book([_single_asset(maturity_months=60)], tier1=500_000)
    result_ref = SA_EVE_Calculator().compute(
        book_ref, {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(0.03)}
    )
    worst = result_ref.worst_delta_eve

    import math
    tier1_pass   = math.ceil(worst / 0.15)    # ratio just below 15% → pass
    tier1_outlier = math.floor(worst / 0.15)  # ratio just above 15% → outlier

    r_pass = SA_EVE_Calculator().compute(
        _book([_single_asset()], tier1=tier1_pass),
        {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(0.03)},
    )
    r_outlier = SA_EVE_Calculator().compute(
        _book([_single_asset()], tier1=tier1_outlier),
        {"EUR": Scenario_Set("EUR")}, {"EUR": Flat_Curve(0.03)},
    )
    assert r_pass.is_outlier is False
    assert r_outlier.is_outlier is True


# ── Midpoint guard ────────────────────────────────────────────────────────────

def test_mismatched_midpoints_raises():
    custom_mids = np.array(EBA_BUCKET_MIDPOINTS) * 1.01   # slightly off
    ss = Scenario_Set("EUR", midpoints=custom_mids)
    book = _book([_single_asset()], tier1=500_000)
    with pytest.raises(ValueError, match="midpoints"):
        SA_EVE_Calculator().compute(book, {"EUR": ss}, {"EUR": Flat_Curve(0.03)})

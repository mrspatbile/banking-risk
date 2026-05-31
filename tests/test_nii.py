import pytest
from banking_risk.irrbb.book import Position, Standard_Banking_Book
from banking_risk.irrbb.constants import EBA_SHOCKS, PositionType
from banking_risk.irrbb.nii import SA_NII_Calculator
from banking_risk.irrbb.scenarios import Scenario_Set
from tests.helpers import Flat_Curve


def _fixed_asset(notional=1_000_000, maturity_months=60, rate=0.05):
    return Position(
        name="loan", type=PositionType.ASSET, currency="EUR",
        notional=notional, maturity_months=maturity_months,
        coupon_months=0, rate=rate, floating=False,
    )


def _floating_asset(notional=1_000_000, maturity_months=60,
                    repricing_tenor_months=3, rate=0.04):
    return Position(
        name="floater", type=PositionType.ASSET, currency="EUR",
        notional=notional, maturity_months=maturity_months,
        coupon_months=0, rate=rate, floating=True,
        repricing_tenor_months=repricing_tenor_months,
    )


def _floating_liability(notional=800_000, maturity_months=120,
                        repricing_tenor_months=3, rate=0.02):
    return Position(
        name="deposit", type=PositionType.LIABILITY, currency="EUR",
        notional=notional, maturity_months=maturity_months,
        coupon_months=0, rate=rate, floating=True,
        repricing_tenor_months=repricing_tenor_months,
    )


def _run(positions, tier1=500_000):
    book = Standard_Banking_Book(positions, tier1_capital=tier1)
    ss = {"EUR": Scenario_Set("EUR")}
    curves = {"EUR": Flat_Curve(0.03)}
    return SA_NII_Calculator().compute(book, ss, curves)


# ── Fixed positions ───────────────────────────────────────────────────────────

def test_fixed_asset_delta_nii_is_zero():
    """Fixed rate does not reprice → ΔNII = 0 for both scenarios."""
    result = _run([_fixed_asset()])
    assert result.delta_nii["parallel_up"] == pytest.approx(0.0)
    assert result.delta_nii["parallel_down"] == pytest.approx(0.0)


def test_fixed_nii_base_correct():
    """NII = notional × rate × min(maturity, 12) / 12."""
    result = _run([_fixed_asset(notional=1_000_000, maturity_months=60, rate=0.05)])
    expected = 1_000_000 * 0.05 * 1.0   # full 12M horizon (60M > 12M)
    assert result.nii_base["loan"] == pytest.approx(expected)


def test_fixed_short_maturity_nii():
    """Position maturing in 6M contributes only 6 months of NII."""
    result = _run([_fixed_asset(maturity_months=6, rate=0.05)])
    expected = 1_000_000 * 0.05 * 0.5
    assert result.nii_base["loan"] == pytest.approx(expected)


# ── Floating positions ────────────────────────────────────────────────────────

def test_floating_asset_parallel_up_increases_nii():
    """Rising rates → floating asset earns more → ΔNII < 0 (base > shocked is wrong,
    shocked > base → nii_shocked > nii_base → delta = base - shocked < 0)."""
    result = _run([_floating_asset(repricing_tenor_months=3)])
    # base - shocked: shocked NII is higher → delta is negative
    assert result.delta_nii["parallel_up"] < 0


def test_floating_liability_parallel_up_increases_cost():
    """Rising rates → floating liability costs more → ΔNII > 0."""
    result = _run([_floating_liability(repricing_tenor_months=3)], tier1=100_000)
    assert result.delta_nii["parallel_up"] > 0


def test_floating_delta_nii_manual():
    """ΔNII = -signed_notional × shock × fraction for a floating position."""
    notional = 1_000_000
    shock_bps = EBA_SHOCKS["EUR"]["parallel_up"]
    shock = shock_bps / 10_000   # 0.02
    fraction = 1.0               # maturity 60M > 12M

    result = _run([_floating_asset(notional=notional, maturity_months=60,
                                   repricing_tenor_months=3, rate=0.04)])
    # ΔNII = base - shocked = notional*rate - notional*(rate+shock) = -notional*shock
    expected_delta = -(notional * shock * fraction)
    assert result.delta_nii["parallel_up"] == pytest.approx(expected_delta, rel=1e-6)


def test_floating_beyond_horizon_not_shocked():
    """Floating with repricing_tenor > 12M does not reprice within horizon → ΔNII = 0."""
    result = _run([_floating_asset(repricing_tenor_months=24)])
    assert result.delta_nii["parallel_up"] == pytest.approx(0.0)


# ── SOT ───────────────────────────────────────────────────────────────────────

def test_nii_outlier_triggered():
    result = _run([_floating_liability(notional=10_000_000)], tier1=1_000)
    assert result.is_outlier is True


def test_nii_outlier_not_triggered():
    result = _run([_floating_liability(notional=1_000)], tier1=1_000_000)
    assert result.is_outlier is False


def test_nii_result_has_two_scenarios():
    result = _run([_fixed_asset()])
    assert set(result.delta_nii.keys()) == {"parallel_up", "parallel_down"}

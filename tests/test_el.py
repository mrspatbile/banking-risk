import math
import pytest
import numpy as np

from banking_risk.credit_risk.el import (
    EL_Position,
    EL_Result,
    Expected_Loss_Calculator,
    _irb_capital,
    _maturity_adjustment,
    _asset_correlation,
)

_CALC = Expected_Loss_Calculator()


def _pos(name="Corp_A", ead=5_000_000, pd=0.0025, lgd=0.45, mat=2.5):
    return EL_Position(name=name, ead=ead, pd=pd, lgd=lgd, maturity_years=mat)


# ── Expected Loss = PD × LGD × EAD ──────────────────────────────────────────

def test_el_equals_pd_times_lgd_times_ead():
    pos    = _pos(ead=1_000_000, pd=0.01, lgd=0.40)
    result = _CALC.compute([pos])
    assert result.detail.loc["Corp_A", "el"] == pytest.approx(0.01 * 0.40 * 1_000_000)


def test_zero_pd_zero_el():
    result = _CALC.compute([_pos(pd=0.0)])
    assert result.detail.loc["Corp_A", "el"] == pytest.approx(0.0)


def test_zero_ead_zero_el():
    result = _CALC.compute([_pos(ead=0.0)])
    assert result.detail.loc["Corp_A", "el"] == pytest.approx(0.0)


def test_total_el_is_sum_of_positions():
    p1 = _pos("A", ead=1_000_000, pd=0.01,  lgd=0.45)
    p2 = _pos("B", ead=2_000_000, pd=0.005, lgd=0.35)
    result = _CALC.compute([p1, p2])
    expected = (0.01 * 0.45 * 1_000_000) + (0.005 * 0.35 * 2_000_000)
    assert result.total_el == pytest.approx(expected, rel=1e-9)


def test_total_ead_is_sum():
    p1 = _pos("A", ead=1_000_000)
    p2 = _pos("B", ead=3_000_000)
    result = _CALC.compute([p1, p2])
    assert result.total_ead == pytest.approx(4_000_000)


def test_el_ratio_correct():
    pos    = _pos(ead=1_000_000, pd=0.02, lgd=0.50)
    result = _CALC.compute([pos])
    assert result.el_ratio == pytest.approx(0.02 * 0.50, rel=1e-9)


# ── IRB capital K ────────────────────────────────────────────────────────────

def test_irb_capital_positive_for_typical_bbb():
    k = _irb_capital(pd=0.0025, lgd=0.45)
    assert k > 0.0


def test_irb_capital_zero_for_zero_pd():
    assert _irb_capital(pd=0.0, lgd=0.45) == pytest.approx(0.0)


def test_irb_capital_zero_for_full_default():
    # Fully defaulted: PD = 1 → no unexpected loss, all loss is expected
    assert _irb_capital(pd=1.0, lgd=0.45) == pytest.approx(0.0)


def test_irb_capital_increases_with_pd():
    k_low  = _irb_capital(pd=0.001, lgd=0.45)
    k_high = _irb_capital(pd=0.05,  lgd=0.45)
    assert k_high > k_low


def test_irb_capital_increases_with_lgd():
    k_low  = _irb_capital(pd=0.005, lgd=0.20)
    k_high = _irb_capital(pd=0.005, lgd=0.60)
    assert k_high > k_low


def test_irb_capital_less_than_lgd():
    # K < LGD: capital covers unexpected loss only (EL is provisioned separately)
    k = _irb_capital(pd=0.005, lgd=0.45)
    assert k < 0.45


# ── Asset correlation R ───────────────────────────────────────────────────────

def test_asset_correlation_in_range():
    for pd in [0.0003, 0.001, 0.01, 0.05, 0.20]:
        r = _asset_correlation(pd)
        assert 0.12 <= r <= 0.24, f"R = {r} out of [0.12, 0.24] for PD={pd}"


def test_asset_correlation_higher_for_lower_pd():
    # Low PD (investment grade) → higher R (more systematic risk)
    r_low_pd  = _asset_correlation(0.0003)
    r_high_pd = _asset_correlation(0.20)
    assert r_low_pd > r_high_pd


# ── Maturity adjustment MA ────────────────────────────────────────────────────

def test_maturity_adjustment_one_at_M1():
    # MA = (1 - 1.5b) / (1 - 1.5b) = 1 exactly when M = 1
    for pd in [0.001, 0.005, 0.01, 0.05]:
        ma = _maturity_adjustment(pd, maturity_years=1.0)
        assert ma == pytest.approx(1.0, rel=1e-9), f"MA != 1 at M=1, pd={pd}"


def test_maturity_adjustment_increases_with_maturity():
    ma_short = _maturity_adjustment(0.01, 1.0)
    ma_long  = _maturity_adjustment(0.01, 5.0)
    assert ma_long > ma_short


# ── RWA = K × 12.5 × EAD × MA ───────────────────────────────────────────────

def test_rwa_formula_at_M1():
    # At M = 1, MA = 1 → RWA = K × 12.5 × EAD
    pos    = _pos(ead=1_000_000, pd=0.005, lgd=0.45, mat=1.0)
    result = _CALC.compute([pos])
    k      = result.detail.loc["Corp_A", "K"]
    rwa    = result.detail.loc["Corp_A", "rwa"]
    assert rwa == pytest.approx(k * 12.5 * 1_000_000, rel=1e-9)


def test_total_rwa_is_sum():
    p1 = _pos("A", ead=1_000_000, mat=2.5)
    p2 = _pos("B", ead=2_000_000, mat=3.0, pd=0.01)
    result = _CALC.compute([p1, p2])
    expected = result.detail["rwa"].sum()
    assert result.total_rwa == pytest.approx(expected, rel=1e-9)


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_portfolio():
    result = _CALC.compute([])
    assert result.total_el  == 0.0
    assert result.total_ead == 0.0
    assert result.total_rwa == 0.0
    assert result.el_ratio  == 0.0


def test_detail_index_is_name():
    result = _CALC.compute([_pos("MyExposure")])
    assert "MyExposure" in result.detail.index


def test_detail_has_expected_columns():
    result = _CALC.compute([_pos()])
    for col in ["ead", "pd", "lgd", "el", "K", "rwa"]:
        assert col in result.detail.columns

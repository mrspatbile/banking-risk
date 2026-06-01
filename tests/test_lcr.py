import pytest
from banking_risk.liquidity.lcr import (
    HQLA_Asset, HQLA_Level, Cash_Outflow, Cash_Inflow,
    Outflow_Type, Inflow_Type, SA_LCR_Calculator,
    HQLA_HAIRCUTS, OUTFLOW_RATES, _apply_hqla_caps,
)

_CALC = SA_LCR_Calculator()


def _l1(mv=100): return HQLA_Asset("L1", HQLA_Level.L1, mv)
def _l2a(mv=40): return HQLA_Asset("L2A", HQLA_Level.L2A, mv)
def _l2b(mv=20): return HQLA_Asset("L2B", HQLA_Level.L2B_CORPORATE, mv)
def _out(bal=100, t=Outflow_Type.RETAIL_STABLE): return Cash_Outflow("O", bal, t)
def _in(bal=50, t=Inflow_Type.WHOLESALE): return Cash_Inflow("I", bal, t)


# ── HQLA haircuts ─────────────────────────────────────────────────────────────

def test_l1_zero_haircut():
    a = _l1(100)
    assert a.adjusted_value == pytest.approx(100.0)


def test_l2a_15pct_haircut():
    a = _l2a(100)
    assert a.adjusted_value == pytest.approx(85.0)


def test_l2b_corporate_50pct_haircut():
    a = HQLA_Asset("x", HQLA_Level.L2B_CORPORATE, 100)
    assert a.adjusted_value == pytest.approx(50.0)


def test_additional_haircut_applied():
    a = HQLA_Asset("x", HQLA_Level.L1, 100, additional_haircut=0.10)
    assert a.adjusted_value == pytest.approx(90.0)


# ── HQLA cap logic ────────────────────────────────────────────────────────────

def test_no_cap_when_within_limits():
    # L1 = 100, L2A = 20, L2B = 5 — all within caps
    hqla, l1, l2a, l2b = _apply_hqla_caps(100, 20, 5)
    assert hqla == pytest.approx(125.0)
    assert l1   == pytest.approx(100.0)
    assert l2a  == pytest.approx(20.0)
    assert l2b  == pytest.approx(5.0)


def test_l2b_cap_applied():
    # L1=100, L2A=0, L2B=30 → L2B_max = (0.15/0.85)*100 ≈ 17.65
    hqla, l1, l2a, l2b = _apply_hqla_caps(100, 0, 30)
    expected_l2b = (0.15 / 0.85) * 100
    assert l2b == pytest.approx(expected_l2b, rel=1e-6)


def test_level2_cap_applied():
    # L1=100, L2A=80, L2B=0 → L2A+L2B ≤ (2/3)*100 ≈ 66.67
    hqla, l1, l2a, l2b = _apply_hqla_caps(100, 80, 0)
    assert l2a + l2b == pytest.approx((2 / 3) * 100, rel=1e-6)


def test_no_l1_means_no_l2():
    # No L1 → Level 2 cap = 0
    hqla, l1, l2a, l2b = _apply_hqla_caps(0, 50, 20)
    assert hqla == pytest.approx(0.0)


# ── LCR formula ───────────────────────────────────────────────────────────────

def test_lcr_simple_pass():
    # HQLA 100, outflows 50 (retail stable 5%), net = 2.5 → LCR = 40x
    result = _CALC.compute([_l1(100)], [_out(50)], [])
    assert result.lcr > 1.0
    assert result.passes is True


def test_lcr_fails_when_hqla_insufficient():
    # HQLA 5, outflow 100 × 100% = 100 → net = 100 → LCR = 5%
    assets   = [_l1(5)]
    outflows = [Cash_Outflow("O", 100, Outflow_Type.FINANCIAL_INST)]
    result   = _CALC.compute(assets, outflows, [])
    assert result.lcr < 1.0
    assert result.passes is False


def test_lcr_equals_hqla_divided_by_net_outflows():
    assets   = [_l1(120)]
    outflows = [Cash_Outflow("O", 1000, Outflow_Type.RETAIL_STABLE)]
    result   = _CALC.compute(assets, outflows, [])
    expected = 120 / result.net_outflows
    assert result.lcr == pytest.approx(expected, rel=1e-9)


def test_inflow_cap_75pct_of_outflows():
    assets   = [_l1(200)]
    outflows = [Cash_Outflow("O", 100, Outflow_Type.FINANCIAL_INST)]  # 100 outflow
    inflows  = [Cash_Inflow("I", 1000, Inflow_Type.WHOLESALE)]        # 1000 inflow, capped at 75
    result   = _CALC.compute(assets, outflows, inflows)
    # Net outflows = 100 - min(1000, 75) = 25
    assert result.net_outflows == pytest.approx(25.0)


def test_gross_outflows_sum():
    o1 = Cash_Outflow("O1", 100, Outflow_Type.RETAIL_STABLE)    # 5
    o2 = Cash_Outflow("O2", 200, Outflow_Type.RETAIL_LESS_STABLE)  # 20
    result = _CALC.compute([_l1(1000)], [o1, o2], [])
    assert result.gross_outflows == pytest.approx(5 + 20)


def test_custom_rate_outflow():
    o = Cash_Outflow("O", 100, outflow_type=None, rate=0.50)
    result = _CALC.compute([_l1(1000)], [o], [])
    assert result.gross_outflows == pytest.approx(50.0)


def test_lcr_detail_has_all_assets():
    assets = [_l1(100), _l2a(40)]
    result = _CALC.compute(assets, [_out()], [])
    assert len(result.hqla_detail) == 2


def test_empty_inputs_infinite_lcr():
    result = _CALC.compute([], [], [])
    assert result.lcr == float("inf")

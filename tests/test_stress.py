import pytest
from banking_risk.liquidity.lcr import (
    HQLA_Asset, HQLA_Level, Cash_Outflow, Cash_Inflow,
    Outflow_Type, Inflow_Type,
)
from banking_risk.liquidity.stress import (
    Stress_Scenario, Liquidity_Stress_Calculator,
    IDIOSYNCRATIC_SCENARIO, MARKET_WIDE_SCENARIO, COMBINED_SCENARIO,
)

# Shared inputs — LCR just passes at base (HQLA=100, net_out≈50)
_ASSETS   = [HQLA_Asset("L1", HQLA_Level.L1, 100)]
_OUTFLOWS = [Cash_Outflow("O", 1000, Outflow_Type.RETAIL_STABLE)]  # 50
_INFLOWS  = []

_CALC = Liquidity_Stress_Calculator()


# ── Stressed LCR ≤ base LCR ──────────────────────────────────────────────────

def test_stressed_lcr_le_base_lcr_idiosyncratic():
    results = Liquidity_Stress_Calculator([IDIOSYNCRATIC_SCENARIO]).compute(
        _ASSETS, _OUTFLOWS, _INFLOWS
    )
    r = results[0]
    assert r.lcr_stressed <= r.base_lcr + 1e-9


def test_stressed_lcr_le_base_lcr_market_wide():
    results = Liquidity_Stress_Calculator([MARKET_WIDE_SCENARIO]).compute(
        _ASSETS, _OUTFLOWS, _INFLOWS
    )
    r = results[0]
    assert r.lcr_stressed <= r.base_lcr + 1e-9


def test_combined_worst_of_all():
    res = Liquidity_Stress_Calculator(
        [IDIOSYNCRATIC_SCENARIO, MARKET_WIDE_SCENARIO, COMBINED_SCENARIO]
    ).compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    lcrs = [r.lcr_stressed for r in res]
    # Combined should have lowest LCR among the three
    assert min(lcrs) == pytest.approx(lcrs[2], rel=1e-6)


# ── Scenario names ────────────────────────────────────────────────────────────

def test_result_scenario_names_match():
    scenarios = [IDIOSYNCRATIC_SCENARIO, MARKET_WIDE_SCENARIO]
    results = Liquidity_Stress_Calculator(scenarios).compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    names = [r.scenario for r in results]
    assert names == ["idiosyncratic", "market_wide"]


# ── Survival days ─────────────────────────────────────────────────────────────

def test_survival_days_positive():
    results = _CALC.compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    for r in results:
        assert r.survival_days > 0.0


def test_survival_days_lcr_relationship():
    # survival_days = HQLA / daily_outflow = HQLA / (net_outflows/30)
    # = 30 × (HQLA / net_outflows) = 30 × lcr_stressed
    results = _CALC.compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    for r in results:
        expected = 30 * r.lcr_stressed
        assert r.survival_days == pytest.approx(expected, rel=1e-6)


# ── HQLA haircut add-on ───────────────────────────────────────────────────────

def test_hqla_haircut_reduces_stressed_hqla():
    scenario_no_hc = Stress_Scenario("no_hc", hqla_haircut_addon=0.0, outflow_multiplier=1.0)
    scenario_with_hc = Stress_Scenario("with_hc", hqla_haircut_addon=0.20, outflow_multiplier=1.0)
    r_no  = Liquidity_Stress_Calculator([scenario_no_hc]).compute(_ASSETS, _OUTFLOWS, _INFLOWS)[0]
    r_hc  = Liquidity_Stress_Calculator([scenario_with_hc]).compute(_ASSETS, _OUTFLOWS, _INFLOWS)[0]
    assert r_hc.hqla_stressed < r_no.hqla_stressed


# ── Outflow multiplier ────────────────────────────────────────────────────────

def test_outflow_multiplier_increases_net_outflows():
    base_results   = Liquidity_Stress_Calculator(
        [Stress_Scenario("base", outflow_multiplier=1.0)]
    ).compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    stress_results = Liquidity_Stress_Calculator(
        [Stress_Scenario("stress", outflow_multiplier=2.0)]
    ).compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    assert stress_results[0].net_outflows_stressed > base_results[0].net_outflows_stressed


# ── Custom scenario ───────────────────────────────────────────────────────────

def test_custom_scenario_with_zero_stress_equals_base():
    neutral = Stress_Scenario("neutral", hqla_haircut_addon=0.0, outflow_multiplier=1.0, inflow_multiplier=1.0)
    results = Liquidity_Stress_Calculator([neutral]).compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    r = results[0]
    assert r.lcr_stressed == pytest.approx(r.base_lcr, rel=1e-6)


# ── Default three scenarios ───────────────────────────────────────────────────

def test_default_calculator_runs_three_scenarios():
    results = _CALC.compute(_ASSETS, _OUTFLOWS, _INFLOWS)
    assert len(results) == 3

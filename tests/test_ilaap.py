import pytest
from banking_risk.liquidity.lcr import (
    HQLA_Asset, HQLA_Level, Cash_Outflow, Cash_Inflow,
    Outflow_Type, SA_LCR_Calculator,
)
from banking_risk.liquidity.nsfr import (
    ASF_Item, ASF_Category, RSF_Item, RSF_Category, SA_NSFR_Calculator,
)
from banking_risk.liquidity.stress import Liquidity_Stress_Calculator
from banking_risk.liquidity.ewi import EWI_Monitor, lcr_indicator, nsfr_indicator
from banking_risk.liquidity.ilaap import ILAAP_Aggregator, ILAAP_Report

_AGG = ILAAP_Aggregator()

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _passing_lcr():
    assets   = [HQLA_Asset("L1", HQLA_Level.L1, 500)]
    outflows = [Cash_Outflow("O", 1000, Outflow_Type.RETAIL_STABLE)]  # net ≈ 50
    return SA_LCR_Calculator().compute(assets, outflows, [])


def _failing_lcr():
    assets   = [HQLA_Asset("L1", HQLA_Level.L1, 10)]
    outflows = [Cash_Outflow("O", 1000, Outflow_Type.RETAIL_STABLE)]
    return SA_LCR_Calculator().compute(assets, outflows, [])


def _passing_nsfr():
    asf = [ASF_Item("T1", 300, category=ASF_Category.TIER1_CAPITAL)]
    rsf = [RSF_Item("L",  200, category=RSF_Category.LOANS_CORPORATE_GT1Y)]
    return SA_NSFR_Calculator().compute(asf, rsf)


def _stress_results(passing=True):
    assets   = [HQLA_Asset("L1", HQLA_Level.L1, 500 if passing else 10)]
    outflows = [Cash_Outflow("O", 1000, Outflow_Type.RETAIL_STABLE)]
    return Liquidity_Stress_Calculator().compute(assets, outflows, [])


# ── Summary table ─────────────────────────────────────────────────────────────

def test_summary_has_lcr_row():
    report = _AGG.compile(lcr_result=_passing_lcr())
    assert "LCR" in report.summary["metric"].values


def test_summary_has_nsfr_row():
    report = _AGG.compile(nsfr_result=_passing_nsfr())
    assert "NSFR" in report.summary["metric"].values


def test_summary_has_stress_rows():
    report = _AGG.compile(stress_results=_stress_results())
    stress_rows = report.summary[report.summary["metric"].str.startswith("LCR stressed")]
    assert len(stress_rows) == 3  # three default scenarios


def test_summary_has_ewi_row():
    dash   = EWI_Monitor().evaluate([lcr_indicator(1.40)])
    report = _AGG.compile(ewi_dashboard=dash)
    assert "EWI dashboard" in report.summary["metric"].values


def test_empty_compile_produces_empty_summary():
    report = _AGG.compile()
    assert len(report.summary) == 0


# ── Adequacy status ───────────────────────────────────────────────────────────

def test_adequate_when_all_pass():
    report = _AGG.compile(
        lcr_result=_passing_lcr(),
        nsfr_result=_passing_nsfr(),
        stress_results=_stress_results(passing=True),
        ewi_dashboard=EWI_Monitor().evaluate([lcr_indicator(1.50)]),
    )
    assert report.adequacy_status == "adequate"


def test_inadequate_when_lcr_fails():
    report = _AGG.compile(lcr_result=_failing_lcr())
    assert report.adequacy_status == "inadequate"


def test_concerns_when_stress_fails():
    report = _AGG.compile(
        lcr_result=_passing_lcr(),
        stress_results=_stress_results(passing=False),
    )
    assert report.adequacy_status == "concerns"


def test_concerns_when_amber_ewi():
    from banking_risk.liquidity.ewi import nsfr_indicator
    dash   = EWI_Monitor().evaluate([nsfr_indicator(1.05)])  # amber
    report = _AGG.compile(ewi_dashboard=dash)
    assert report.adequacy_status == "concerns"


def test_inadequate_when_red_ewi():
    from banking_risk.liquidity.ewi import lcr_indicator
    dash   = EWI_Monitor().evaluate([lcr_indicator(0.90)])  # red
    report = _AGG.compile(ewi_dashboard=dash)
    assert report.adequacy_status == "inadequate"


# ── Report fields ─────────────────────────────────────────────────────────────

def test_report_stores_lcr_result():
    lcr    = _passing_lcr()
    report = _AGG.compile(lcr_result=lcr)
    assert report.lcr_result is lcr


def test_report_stores_stress_results():
    sr     = _stress_results()
    report = _AGG.compile(stress_results=sr)
    assert len(report.stress_results) == 3


def test_report_none_components_allowed():
    report = _AGG.compile(lcr_result=None, nsfr_result=None)
    assert report.lcr_result is None
    assert report.nsfr_result is None

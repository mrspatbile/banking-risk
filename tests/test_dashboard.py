"""
Test suite for Banking Risk Dashboard (BKR-75).

Covers:
- Chart rendering and logic (MDA gauge, KPI cards, traffic light)
- Dashboard page rendering
- Data loading and validation
- JSON parsing
- Export functionality

References
----------
EBA/GL/2022/14 : Capital adequacy governance
CRR3 Art. 325bb : FRTB SA aggregation
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import pandas as pd

from banking_risk.reporting.charts import (
    mda_gauge,
    capital_bar_chart,
    stacked_composition_chart,
    stress_line_chart,
    kpi_card,
    traffic_light,
)
from banking_risk.reporting.dashboard import (
    load_demo_capital_stack,
    load_demo_frtb_sa,
    parse_capital_stack_json,
    parse_frtb_sa_json,
)


# ── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def demo_capital_stack():
    """Load demo capital stack for testing."""
    return load_demo_capital_stack()


@pytest.fixture
def demo_frtb_sa():
    """Load demo FRTB SA result for testing."""
    return load_demo_frtb_sa()


@pytest.fixture
def sample_capital_data():
    """Sample capital stack data for edge case testing."""
    return {
        "cet1": 500.0,
        "tier1": 600.0,
        "tier2": 200.0,
        "total_capital": 1300.0,
        "frtb_rwa": 5000.0,
        "credit_rwa": 3000.0,
        "oprisk_rwa": 1000.0,
        "total_rwa": 9000.0,
        "cet1_ratio": 0.0956,
        "tier1_ratio": 0.1144,
        "total_ratio": 0.1556,
        "ccb": 0.025,
        "ccyb": 0.0,
        "gsii_buffer": 0.015,
    }


# ── Test: Demo Data Loading ────────────────────────────────────────────────────

def test_load_demo_capital_stack():
    """Test that demo capital stack loads and has required fields."""
    data = load_demo_capital_stack()

    assert isinstance(data, dict)
    assert "cet1" in data
    assert "total_capital" in data
    assert "total_rwa" in data
    assert "cet1_ratio" in data
    assert data["cet1"] > 0
    assert data["total_rwa"] > 0
    assert 0 < data["cet1_ratio"] < 1


def test_load_demo_frtb_sa():
    """Test that demo FRTB SA loads and has required fields."""
    data = load_demo_frtb_sa()

    assert isinstance(data, dict)
    assert "components" in data
    assert len(data["components"]) > 0
    assert "drc" in data
    assert "rrao" in data

    # Check component structure
    for comp in data["components"]:
        assert "name" in comp
        assert "delta" in comp
        assert "vega" in comp
        assert "curvature" in comp


def test_parse_capital_stack_json_valid(sample_capital_data):
    """Test that valid capital stack JSON is parsed correctly."""
    result = parse_capital_stack_json(sample_capital_data)
    assert result == sample_capital_data


def test_parse_capital_stack_json_missing_field(sample_capital_data):
    """Test that missing required field raises ValueError."""
    del sample_capital_data["cet1_ratio"]
    with pytest.raises(ValueError, match="Missing required field"):
        parse_capital_stack_json(sample_capital_data)


def test_parse_frtb_sa_json_valid(demo_frtb_sa):
    """Test that valid FRTB SA JSON is parsed correctly."""
    result = parse_frtb_sa_json(demo_frtb_sa)
    assert result == demo_frtb_sa


def test_parse_frtb_sa_json_missing_components():
    """Test that missing components field raises ValueError."""
    invalid_data = {"drc": 100.0, "rrao": 50.0}
    with pytest.raises(ValueError, match="Missing required field: components"):
        parse_frtb_sa_json(invalid_data)


# ── Test: MDA Gauge Logic ──────────────────────────────────────────────────────

def test_mda_gauge_compliant():
    """Test MDA gauge for compliant institution (CET1 > MDA + 100bps)."""
    fig = mda_gauge(cet1_ratio=0.095, mda_trigger=0.070)

    assert fig is not None
    assert hasattr(fig, 'data')
    assert len(fig.data) > 0


def test_mda_gauge_at_risk():
    """Test MDA gauge for at-risk institution (CET1 within 100bps of MDA)."""
    # CET1 at 7.05%, MDA at 7.0% → 5 bps headroom = at risk
    fig = mda_gauge(cet1_ratio=0.0705, mda_trigger=0.070)
    assert fig is not None
    assert hasattr(fig, 'data')


def test_mda_gauge_breach():
    """Test MDA gauge for breaching institution (CET1 < MDA)."""
    fig = mda_gauge(cet1_ratio=0.065, mda_trigger=0.070)
    assert fig is not None
    assert hasattr(fig, 'data')


# ── Test: KPI Card Logic ───────────────────────────────────────────────────────

def test_kpi_card_compliant():
    """Test KPI card for compliant ratio (above threshold + buffer)."""
    kpi = kpi_card("CET1 Ratio", value=0.095, threshold=0.045)

    assert kpi["status"] == "OK"
    assert kpi["color"] == "#00CC96"  # Green
    assert "OK" in kpi["status"]


def test_kpi_card_at_risk():
    """Test KPI card for at-risk ratio (within 100bps of threshold)."""
    kpi = kpi_card("CET1 Ratio", value=0.0505, threshold=0.045)

    assert kpi["status"] == "AT RISK"
    assert kpi["color"] == "#FFA15A"  # Amber


def test_kpi_card_breach():
    """Test KPI card for breaching ratio (below threshold)."""
    kpi = kpi_card("CET1 Ratio", value=0.040, threshold=0.045)

    assert kpi["status"] == "BREACH"
    assert kpi["color"] == "#EF553B"  # Red


def test_kpi_card_percentage_format():
    """Test KPI card percentage formatting."""
    kpi = kpi_card("Tier 1 Ratio", value=0.075, threshold=0.060, is_percentage=True)

    assert "7.5%" in kpi["value"]
    assert "6.0%" in kpi["threshold"]


def test_kpi_card_decimal_format():
    """Test KPI card decimal formatting."""
    kpi = kpi_card("Leverage Ratio", value=0.055, threshold=0.030, is_percentage=False)

    assert "0.05" in kpi["value"]
    assert "0.03" in kpi["threshold"]


# ── Test: Traffic Light Logic ──────────────────────────────────────────────────

def test_traffic_light_all_pass():
    """Test traffic light when all signals pass."""
    result = traffic_light(
        pillar1_compliant=True,
        ccb_compliant=True,
        mda_compliant=True,
        gsii_compliant=True,
    )

    assert result["overall_status"] == "COMPLIANT"
    assert len(result["signals"]) == 5  # 4 + overall

    # Check all signals pass
    for signal in result["signals"]:
        assert signal["status"] == "PASS"
        assert signal["color"] == "#00CC96"


def test_traffic_light_mda_fail():
    """Test traffic light when MDA signal fails."""
    result = traffic_light(
        pillar1_compliant=True,
        ccb_compliant=True,
        mda_compliant=False,
        gsii_compliant=True,
    )

    assert result["overall_status"] == "NON-COMPLIANT"

    mda_signal = next((s for s in result["signals"] if s["name"] == "MDA"), None)
    assert mda_signal is not None
    assert mda_signal["status"] == "FAIL"
    assert mda_signal["color"] == "#EF553B"


def test_traffic_light_pillar1_fail():
    """Test traffic light when Pillar 1 signal fails."""
    result = traffic_light(
        pillar1_compliant=False,
        ccb_compliant=True,
        mda_compliant=True,
        gsii_compliant=True,
    )

    assert result["overall_status"] == "NON-COMPLIANT"

    pillar1_signal = next((s for s in result["signals"] if s["name"] == "Pillar 1"), None)
    assert pillar1_signal["status"] == "FAIL"


# ── Test: Chart Rendering ──────────────────────────────────────────────────────

def test_capital_bar_chart():
    """Test capital bar chart rendering."""
    risk_classes = {"GIRR": 150.0, "Equity": 500.0, "FX": 100.0}
    fig = capital_bar_chart(risk_classes)

    assert fig is not None
    assert hasattr(fig, 'data')
    assert len(fig.data) > 0
    # Check that title includes "FRTB SA Capital"
    assert "FRTB SA Capital" in fig.layout.title.text


def test_capital_bar_chart_labels():
    """Test that bar chart labels are correctly formatted."""
    risk_classes = {"GIRR": 150.0, "Equity": 500.0}
    fig = capital_bar_chart(risk_classes)

    # Verify chart structure
    assert fig.layout.xaxis.title.text == "Risk Class"
    assert fig.layout.yaxis.title.text == "Capital Requirement ($M)"


def test_stacked_composition_chart():
    """Test stacked composition chart rendering."""
    composition = {
        "GIRR": {"delta": 100, "vega": 20, "curvature": 10, "drc": 0, "rrao": 0},
        "Equity": {"delta": 500, "vega": 100, "curvature": 50, "drc": 0, "rrao": 0},
    }
    fig = stacked_composition_chart(composition)

    assert fig is not None
    assert hasattr(fig, 'data')
    # Should have 5 traces (delta, vega, curvature, drc, rrao)
    assert len(fig.data) == 5


def test_stacked_composition_chart_empty():
    """Test stacked composition chart with empty data."""
    composition = {}
    fig = stacked_composition_chart(composition)

    assert fig is not None


def test_stress_line_chart():
    """Test stress line chart rendering."""
    scenarios = {
        "Baseline": 0.095,
        "Adverse": 0.082,
        "Severely Adverse": 0.065,
    }
    fig = stress_line_chart(scenarios)

    assert fig is not None
    assert hasattr(fig, 'data')
    # Should have scatter trace + hline annotation
    assert len(fig.data) > 0


def test_stress_line_chart_mda_line():
    """Test that stress line chart includes MDA trigger line."""
    scenarios = {"Baseline": 0.095, "Adverse": 0.082}
    fig = stress_line_chart(scenarios)

    # Check for MDA trigger line in shapes (hline creates a shape)
    assert hasattr(fig, 'shapes') or any(
        "MDA" in str(ann.text) if hasattr(ann, 'text') else False
        for ann in fig.layout.annotations
    )


# ── Test: Dashboard Page Rendering (integration) ────────────────────────────────

@pytest.mark.parametrize("input_mode", ["demo", "json"])
def test_capital_adequacy_page_renders(input_mode):
    """Test that capital adequacy page renders without error."""
    # Mock streamlit
    with patch("banking_risk.reporting.dashboard.st") as mock_st:
        mock_st.set_page_config = MagicMock()
        mock_st.title = MagicMock()
        mock_st.markdown = MagicMock()
        mock_st.sidebar.selectbox = MagicMock(return_value="Demo Mode")
        mock_st.sidebar.radio = MagicMock(return_value="Demo Mode")
        mock_st.sidebar.file_uploader = MagicMock(return_value=None)
        mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
        mock_st.subheader = MagicMock()
        mock_st.metric = MagicMock()
        mock_st.plotly_chart = MagicMock()
        mock_st.dataframe = MagicMock()
        mock_st.info = MagicMock()

        from banking_risk.reporting.dashboard import page_capital_adequacy

        # Should not raise an exception
        try:
            page_capital_adequacy()
        except Exception as e:
            if "st.set_page_config" not in str(e):
                raise


@pytest.mark.parametrize("input_mode", ["demo", "json"])
def test_frtb_sa_page_renders(input_mode):
    """Test that FRTB SA page renders without error."""
    # Mock streamlit
    with patch("banking_risk.reporting.dashboard.st") as mock_st:
        mock_st.title = MagicMock()
        mock_st.markdown = MagicMock()
        mock_st.sidebar.selectbox = MagicMock(return_value="Demo Mode")
        mock_st.sidebar.radio = MagicMock(return_value="Demo Mode")
        mock_st.sidebar.file_uploader = MagicMock(return_value=None)
        mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
        mock_st.subheader = MagicMock()
        mock_st.plotly_chart = MagicMock()
        mock_st.dataframe = MagicMock()
        mock_st.info = MagicMock()

        from banking_risk.reporting.dashboard import page_frtb_sa

        # Should not raise an exception
        try:
            page_frtb_sa()
        except Exception as e:
            if "st.set_page_config" not in str(e):
                raise


# ── Test: Data Loading and Validation ──────────────────────────────────────────

def test_demo_capital_stack_structure(demo_capital_stack):
    """Test that demo capital stack has all required fields."""
    required_fields = [
        "cet1", "tier1", "tier2", "total_capital",
        "frtb_rwa", "credit_rwa", "oprisk_rwa", "total_rwa",
        "cet1_ratio", "tier1_ratio", "total_ratio",
    ]

    for field in required_fields:
        assert field in demo_capital_stack


def test_demo_capital_stack_consistency(demo_capital_stack):
    """Test that demo capital stack ratios are consistent with amounts."""
    # RWA should be sum of components
    total_rwa = (
        demo_capital_stack["frtb_rwa"] +
        demo_capital_stack["credit_rwa"] +
        demo_capital_stack["oprisk_rwa"]
    )
    assert demo_capital_stack["total_rwa"] == total_rwa

    # Capital should be sum of tiers
    total_capital = (
        demo_capital_stack["cet1"] +
        demo_capital_stack["tier1"] +
        demo_capital_stack["tier2"]
    )
    assert demo_capital_stack["total_capital"] == total_capital


def test_demo_frtb_sa_structure(demo_frtb_sa):
    """Test that demo FRTB SA has all required fields."""
    assert "components" in demo_frtb_sa
    assert "drc" in demo_frtb_sa
    assert "rrao" in demo_frtb_sa

    # Check components
    for comp in demo_frtb_sa["components"]:
        assert "name" in comp
        assert "delta" in comp
        assert "vega" in comp
        assert "curvature" in comp


def test_demo_frtb_sa_all_risk_classes(demo_frtb_sa):
    """Test that demo FRTB SA covers all 6 risk classes."""
    risk_class_names = {c["name"] for c in demo_frtb_sa["components"]}

    expected_classes = {"GIRR", "CSR-nonsec", "CSR-sec", "Equity", "FX", "Commodity"}
    assert risk_class_names == expected_classes


# ── Test: Edge Cases and Error Handling ───────────────────────────────────────

def test_kpi_card_zero_threshold():
    """Test KPI card with zero threshold."""
    kpi = kpi_card("Test Ratio", value=0.05, threshold=0.0)
    assert kpi["status"] == "OK"
    assert kpi["color"] == "#00CC96"


def test_capital_bar_chart_single_class():
    """Test bar chart with single risk class."""
    risk_classes = {"GIRR": 150.0}
    fig = capital_bar_chart(risk_classes)
    assert fig is not None


def test_capital_bar_chart_zero_values():
    """Test bar chart with zero values."""
    risk_classes = {"GIRR": 0.0, "Equity": 500.0}
    fig = capital_bar_chart(risk_classes)
    assert fig is not None


def test_stress_line_chart_single_scenario():
    """Test stress line chart with single scenario."""
    scenarios = {"Baseline": 0.095}
    fig = stress_line_chart(scenarios)
    assert fig is not None


# ── Test: Demo Files Exist and Are Valid ───────────────────────────────────────

def test_demo_capital_stack_file_exists():
    """Test that demo_capital_stack.json file exists."""
    demo_path = Path(__file__).parent.parent / "src" / "banking_risk" / "reporting" / "demo_capital_stack.json"
    assert demo_path.exists(), f"Demo file not found at {demo_path}"


def test_demo_frtb_sa_file_exists():
    """Test that demo_frtb_sa.json file exists."""
    demo_path = Path(__file__).parent.parent / "src" / "banking_risk" / "reporting" / "demo_frtb_sa.json"
    assert demo_path.exists(), f"Demo file not found at {demo_path}"


def test_demo_capital_stack_file_valid_json():
    """Test that demo_capital_stack.json is valid JSON."""
    demo_path = Path(__file__).parent.parent / "src" / "banking_risk" / "reporting" / "demo_capital_stack.json"
    with open(demo_path) as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_demo_frtb_sa_file_valid_json():
    """Test that demo_frtb_sa.json is valid JSON."""
    demo_path = Path(__file__).parent.parent / "src" / "banking_risk" / "reporting" / "demo_frtb_sa.json"
    with open(demo_path) as f:
        data = json.load(f)
    assert isinstance(data, dict)

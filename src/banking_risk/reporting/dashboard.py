"""
Banking Risk Dashboard — Streamlit application.

Two-page interactive dashboard for:
  - Page 1: Capital Adequacy Assessment (MDA gauge, KPI cards, stress scenarios)
  - Page 2: FRTB SA Capital Breakdown (risk class composition, drill-down)

Data input: JSON upload or demo mode with built-in test data.

References
----------
EBA/GL/2022/14 : IRRBB governance and board communication
CRR3 Art. 325bb : FRTB SA capital requirement aggregation

Usage
-----
    streamlit run banking_risk_dashboard.py
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st
import pandas as pd

from banking_risk.reporting.charts import (
    mda_gauge,
    capital_bar_chart,
    stacked_composition_chart,
    stress_line_chart,
    kpi_card,
    traffic_light,
)


# ── Demo data loading ─────────────────────────────────────────────────────────

def load_demo_capital_stack() -> Dict[str, Any]:
    """Load demo Capital_Stack from JSON file."""
    demo_path = Path(__file__).parent / "demo_capital_stack.json"
    with open(demo_path) as f:
        return json.load(f)


def load_demo_frtb_sa() -> Dict[str, Any]:
    """Load demo FRTB_SA_Result from JSON file."""
    demo_path = Path(__file__).parent / "demo_frtb_sa.json"
    with open(demo_path) as f:
        return json.load(f)


def parse_capital_stack_json(json_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate Capital_Stack JSON structure."""
    required_keys = [
        "cet1", "tier1", "tier2", "total_capital",
        "frtb_rwa", "credit_rwa", "oprisk_rwa", "total_rwa",
        "cet1_ratio", "tier1_ratio", "total_ratio",
    ]

    for key in required_keys:
        if key not in json_dict:
            raise ValueError(f"Missing required field: {key}")

    return json_dict


def parse_frtb_sa_json(json_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate FRTB_SA_Result JSON structure."""
    if "components" not in json_dict:
        raise ValueError("Missing required field: components")

    for component in json_dict["components"]:
        if not all(k in component for k in ["name", "delta", "vega", "curvature"]):
            raise ValueError("Component missing required fields: name, delta, vega, curvature")

    return json_dict


# ── Page 1: Capital Adequacy ──────────────────────────────────────────────────

def page_capital_adequacy():
    """Capital Adequacy Assessment page."""
    st.title("Capital Adequacy Assessment")
    st.markdown("---")

    # Data input section
    st.sidebar.header("Data Input")
    input_mode = st.sidebar.radio("Data Source", ["Demo Mode", "Upload JSON"])

    if input_mode == "Demo Mode":
        capital_data = load_demo_capital_stack()
    else:
        uploaded_file = st.sidebar.file_uploader("Upload Capital_Stack.json", type="json")
        if uploaded_file is None:
            st.info("Please upload a Capital_Stack.json file or use Demo Mode")
            return
        try:
            capital_data = parse_capital_stack_json(json.load(uploaded_file))
        except ValueError as e:
            st.error(f"Invalid JSON format: {e}")
            return

    # Compute additional metrics
    leverage_ratio = capital_data["total_capital"] / (capital_data["total_rwa"] / 0.08)
    ccb = capital_data.get("ccb", 0.025)
    ccyb = capital_data.get("ccyb", 0.0)
    gsii_buffer = capital_data.get("gsii_buffer", 0.0)
    mda_trigger = 0.045 + ccb + ccyb + (0.5 * gsii_buffer)

    # ── MDA Gauge (top section) ───────────────────────────────────────────────
    st.subheader("MDA Trigger Assessment")
    col1, col2 = st.columns([3, 1])

    with col1:
        fig_mda = mda_gauge(capital_data["cet1_ratio"], mda_trigger)
        st.plotly_chart(fig_mda, use_container_width=True)

    with col2:
        mda_headroom = (capital_data["cet1_ratio"] - mda_trigger) * 10_000
        st.metric(
            "Headroom to MDA",
            f"{mda_headroom:.0f} bps",
            delta=None,
            delta_color="off",
        )
        st.metric(
            "MDA Trigger",
            f"{mda_trigger * 100:.2f}%",
            delta=None,
            delta_color="off",
        )

    # ── KPI Cards (regulatory minimums) ────────────────────────────────────────
    st.subheader("Capital Ratios vs. Regulatory Minimums")

    kpi_cet1 = kpi_card("CET1 Ratio", capital_data["cet1_ratio"], 0.045)
    kpi_tier1 = kpi_card("Tier 1 Ratio", capital_data["tier1_ratio"], 0.060)
    kpi_total = kpi_card("Total Capital Ratio", capital_data["total_ratio"], 0.080)
    kpi_leverage = kpi_card("Leverage Ratio", leverage_ratio, 0.030, is_percentage=False)

    cols = st.columns(4)
    for col, kpi in zip(cols, [kpi_cet1, kpi_tier1, kpi_total, kpi_leverage]):
        with col:
            st.markdown(
                f"""
                <div style="background-color: {kpi['color']}20; border-left: 4px solid {kpi['color']}; padding: 15px; border-radius: 4px;">
                <p style="margin: 0; font-size: 12px; color: #666;">{kpi['label']}</p>
                <p style="margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: {kpi['color']};">{kpi['value']}</p>
                <p style="margin: 5px 0 0 0; font-size: 11px; color: #999;">Min: {kpi['threshold']}</p>
                <p style="margin: 5px 0 0 0; font-size: 11px; color: {kpi['color']}; font-weight: bold;">{kpi['status']}</p>
                <p style="margin: 5px 0 0 0; font-size: 10px; color: #999;">{kpi['headroom']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Traffic Light Signals ─────────────────────────────────────────────────
    st.subheader("Regulatory Compliance Status")

    pillar1_ok = (
        capital_data["cet1_ratio"] >= 0.045 and
        capital_data["tier1_ratio"] >= 0.060 and
        capital_data["total_ratio"] >= 0.080
    )
    ccb_ok = capital_data["cet1_ratio"] >= (0.045 + ccb)
    mda_ok = capital_data["cet1_ratio"] >= mda_trigger
    gsii_ok = capital_data["cet1_ratio"] >= (0.045 + gsii_buffer)

    traffic = traffic_light(pillar1_ok, ccb_ok, mda_ok, gsii_ok)

    cols = st.columns(5)
    for col, signal in zip(cols, traffic["signals"]):
        with col:
            st.markdown(
                f"""
                <div style="text-align: center; padding: 20px; background-color: {signal['color']}20; border-radius: 8px;">
                <div style="width: 60px; height: 60px; background-color: {signal['color']}; border-radius: 50%; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: bold; font-size: 12px;">{signal['status']}</span>
                </div>
                <p style="margin: 0; font-weight: bold; color: {signal['color']};">{signal['name']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Capital Stack Table ───────────────────────────────────────────────────
    st.subheader("Capital Stack Summary")

    capital_table = pd.DataFrame({
        "Tier": ["CET1", "Tier 1 (excl. CET1)", "Tier 2", "Total Capital"],
        "Amount ($M)": [
            capital_data["cet1"],
            capital_data["tier1"] - capital_data["cet1"],
            capital_data["tier2"],
            capital_data["total_capital"],
        ],
        "% of Total": [
            capital_data["cet1"] / capital_data["total_capital"] * 100,
            (capital_data["tier1"] - capital_data["cet1"]) / capital_data["total_capital"] * 100,
            capital_data["tier2"] / capital_data["total_capital"] * 100,
            100.0,
        ],
    })

    st.dataframe(capital_table, use_container_width=True, hide_index=True)

    # ── RWA Breakdown ─────────────────────────────────────────────────────────
    st.subheader("Risk-Weighted Assets Breakdown")

    rwa_table = pd.DataFrame({
        "RWA Component": ["FRTB", "Credit Risk", "Operational Risk", "Total RWA"],
        "Amount ($M)": [
            capital_data["frtb_rwa"],
            capital_data["credit_rwa"],
            capital_data["oprisk_rwa"],
            capital_data["total_rwa"],
        ],
        "% of Total": [
            capital_data["frtb_rwa"] / capital_data["total_rwa"] * 100,
            capital_data["credit_rwa"] / capital_data["total_rwa"] * 100,
            capital_data["oprisk_rwa"] / capital_data["total_rwa"] * 100,
            100.0,
        ],
    })

    st.dataframe(rwa_table, use_container_width=True, hide_index=True)

    # ── Stress Testing ────────────────────────────────────────────────────────
    st.subheader("Stress Testing: CET1 Ratio Across Scenarios")

    stress_data = capital_data.get("stress_scenarios", {})
    if stress_data:
        scenarios_dict = {
            k.replace("_", " ").title(): v.get("cet1_ratio", 0)
            for k, v in stress_data.items()
        }

        fig_stress = stress_line_chart(scenarios_dict)
        st.plotly_chart(fig_stress, use_container_width=True)

        # Stress scenario table
        stress_table = pd.DataFrame({
            "Scenario": list(scenarios_dict.keys()),
            "CET1 Ratio": [f"{v * 100:.2f}%" for v in scenarios_dict.values()],
            "Above MDA": [
                "Yes" if v >= mda_trigger else "No"
                for v in scenarios_dict.values()
            ],
        })
        st.dataframe(stress_table, use_container_width=True, hide_index=True)
    else:
        st.info("No stress scenario data available")


# ── Page 2: FRTB SA Capital ───────────────────────────────────────────────────

def page_frtb_sa():
    """FRTB SA Capital Breakdown page."""
    st.title("FRTB SA Capital Breakdown")
    st.markdown("---")

    # Data input section
    st.sidebar.header("Data Input")
    input_mode = st.sidebar.radio("Data Source", ["Demo Mode", "Upload JSON"])

    if input_mode == "Demo Mode":
        frtb_data = load_demo_frtb_sa()
    else:
        uploaded_file = st.sidebar.file_uploader("Upload FRTB_SA_Result.json", type="json")
        if uploaded_file is None:
            st.info("Please upload an FRTB_SA_Result.json file or use Demo Mode")
            return
        try:
            frtb_data = parse_frtb_sa_json(json.load(uploaded_file))
        except ValueError as e:
            st.error(f"Invalid JSON format: {e}")
            return

    # Compute totals
    components = frtb_data.get("components", [])
    drc = frtb_data.get("drc", 0.0)
    rrao = frtb_data.get("rrao", 0.0)

    total_crm = sum(c.get("delta", 0) + c.get("vega", 0) + c.get("curvature", 0)
                    for c in components) + drc + rrao

    # ── Risk class selector ───────────────────────────────────────────────────
    st.sidebar.header("Filter")
    selected_class = st.sidebar.selectbox(
        "Risk Class Detail",
        options=["All Risk Classes"] + [c["name"] for c in components],
        key="risk_class_filter",
    )

    # ── Top: Risk class bar chart ─────────────────────────────────────────────
    st.subheader("Capital Requirement by Risk Class")

    risk_classes_dict = {
        c["name"]: c["delta"] + c["vega"] + c["curvature"]
        for c in components
    }
    if drc > 0:
        risk_classes_dict["DRC"] = drc
    if rrao > 0:
        risk_classes_dict["RRAO"] = rrao

    fig_bar = capital_bar_chart(risk_classes_dict)
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Composition chart ─────────────────────────────────────────────────────
    st.subheader("Capital Composition: Delta / Vega / Curvature / DRC / RRAO")

    composition_dict = {}
    for c in components:
        composition_dict[c["name"]] = {
            "delta": c.get("delta", 0),
            "vega": c.get("vega", 0),
            "curvature": c.get("curvature", 0),
            "drc": 0.0,
            "rrao": 0.0,
        }

    # Add DRC and RRAO if present
    if drc > 0:
        composition_dict["DRC"] = {"delta": 0, "vega": 0, "curvature": 0, "drc": drc, "rrao": 0}
    if rrao > 0:
        composition_dict["RRAO"] = {"delta": 0, "vega": 0, "curvature": 0, "drc": 0, "rrao": rrao}

    fig_stacked = stacked_composition_chart(composition_dict)
    st.plotly_chart(fig_stacked, use_container_width=True)

    # ── Left: CRM Total, Right: Detail Table ──────────────────────────────────
    st.subheader("Detail View")

    col_crm, col_detail = st.columns([1, 3])

    with col_crm:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #636EFA 0%, #AB63FA 100%);
                        padding: 30px; border-radius: 8px; text-align: center; color: white;">
            <p style="margin: 0; font-size: 14px; opacity: 0.9;">Total CRM</p>
            <p style="margin: 10px 0 0 0; font-size: 48px; font-weight: bold;">${total_crm:.0f}M</p>
            <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.8;">FRTB SA Capital</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_detail:
        st.markdown("**Detail Table: Selected Risk Class**")

        if selected_class == "All Risk Classes":
            # Show summary table
            detail_rows = []
            for c in components:
                detail_rows.append({
                    "Risk Class": c["name"],
                    "Delta ($M)": f"{c.get('delta', 0):.1f}",
                    "Vega ($M)": f"{c.get('vega', 0):.1f}",
                    "Curvature ($M)": f"{c.get('curvature', 0):.1f}",
                    "Total ($M)": f"{c.get('delta', 0) + c.get('vega', 0) + c.get('curvature', 0):.1f}",
                })

            if drc > 0:
                detail_rows.append({
                    "Risk Class": "DRC",
                    "Delta ($M)": "0.0",
                    "Vega ($M)": "0.0",
                    "Curvature ($M)": "0.0",
                    "Total ($M)": f"{drc:.1f}",
                })

            if rrao > 0:
                detail_rows.append({
                    "Risk Class": "RRAO",
                    "Delta ($M)": "0.0",
                    "Vega ($M)": "0.0",
                    "Curvature ($M)": "0.0",
                    "Total ($M)": f"{rrao:.1f}",
                })

            detail_df = pd.DataFrame(detail_rows)
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

        else:
            # Show detail for selected risk class
            selected_component = next(
                (c for c in components if c["name"] == selected_class),
                None
            )

            if selected_component:
                detail_data = {
                    "Component": ["Delta", "Vega", "Curvature", "Total"],
                    "Capital ($M)": [
                        f"{selected_component.get('delta', 0):.1f}",
                        f"{selected_component.get('vega', 0):.1f}",
                        f"{selected_component.get('curvature', 0):.1f}",
                        f"{selected_component.get('delta', 0) + selected_component.get('vega', 0) + selected_component.get('curvature', 0):.1f}",
                    ],
                }
                detail_df = pd.DataFrame(detail_data)
                st.dataframe(detail_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"No data available for {selected_class}")


# ── Main App ──────────────────────────────────────────────────────────────────

def main():
    """Main Streamlit app."""
    st.set_page_config(
        layout="wide",
        page_title="Banking Risk Dashboard",
        page_icon="📊",
    )

    # Sidebar navigation
    st.sidebar.title("Banking Risk Dashboard")
    st.sidebar.markdown("---")

    page = st.sidebar.selectbox(
        "Select Page",
        ["Capital Adequacy", "FRTB SA"],
        key="page_select",
    )

    st.sidebar.markdown("---")
    st.sidebar.info(
        """
        **Dashboard Info**

        - **Capital Adequacy**: MDA assessment, capital ratios, regulatory compliance
        - **FRTB SA**: Risk class breakdown, capital composition analysis

        Data input via JSON upload or demo mode.
        """
    )

    if page == "Capital Adequacy":
        page_capital_adequacy()
    else:
        page_frtb_sa()


if __name__ == "__main__":
    main()

"""
Reporting module — dashboards and visualizations.

Exports dashboard components and helper functions for KPI visualization,
capital stack analysis, and FRTB SA capital breakdown.

Public API
----------
mda_gauge : Create MDA trigger gauge chart
capital_bar_chart : Risk class capital breakdown bar chart
stacked_composition_chart : Delta/vega/curvature composition stacked bars
stress_line_chart : Stress test scenario line chart
kpi_card : Formatted KPI card with threshold
traffic_light : Multi-signal compliance traffic light

Dashboard pages
---------------
Capital_Adequacy_Page : Interactive capital adequacy dashboard
FRTB_SA_Dashboard : FRTB SA capital breakdown dashboard

Usage
-----
    from banking_risk.reporting import mda_gauge, capital_bar_chart
    import streamlit as st

    fig = mda_gauge(cet1_ratio=0.095, mda_trigger=0.070)
    st.plotly_chart(fig)
"""

from banking_risk.reporting.charts import (
    mda_gauge,
    capital_bar_chart,
    stacked_composition_chart,
    stress_line_chart,
    kpi_card,
    traffic_light,
)

__all__ = [
    "mda_gauge",
    "capital_bar_chart",
    "stacked_composition_chart",
    "stress_line_chart",
    "kpi_card",
    "traffic_light",
]

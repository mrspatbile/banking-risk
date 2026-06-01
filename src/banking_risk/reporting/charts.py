"""
Plotly chart helpers for Banking Risk dashboards.

Provides reusable chart components for capital adequacy and FRTB SA visualization.

References
----------
EBA/GL/2022/14 : IRRBB governance and board communication
CRR3 Art. 325bb : FRTB SA capital requirement aggregation
"""

from typing import Dict, Any, Optional
import plotly.graph_objects as go
import plotly.express as px


def mda_gauge(cet1_ratio: float, mda_trigger: float) -> go.Figure:
    """
    Create an MDA trigger gauge chart showing headroom to breach.

    Parameters
    ----------
    cet1_ratio : float
        Current CET1 ratio (e.g., 0.095 for 9.5%)
    mda_trigger : float
        MDA trigger level (e.g., 0.070 for 7.0%)

    Returns
    -------
    go.Figure
        Plotly gauge chart with red/amber/green zones
    """
    headroom_bps = (cet1_ratio - mda_trigger) * 10_000

    # Color zones: red if breach, amber if <100bps, green if >100bps
    if cet1_ratio < mda_trigger:
        gauge_color = "#EF553B"  # Red
        status = "BREACH"
    elif headroom_bps < 100:
        gauge_color = "#FFA15A"  # Amber
        status = "AT RISK"
    else:
        gauge_color = "#00CC96"  # Green
        status = "COMPLIANT"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=cet1_ratio * 100,
            title={"text": "CET1 Ratio (MDA Assessment)"},
            delta={"reference": mda_trigger * 100, "suffix": " vs MDA trigger"},
            gauge={
                "axis": {"range": [0, 15]},
                "bar": {"color": gauge_color},
                "steps": [
                    {"range": [0, mda_trigger * 100], "color": "#FADDC6"},
                    {
                        "range": [mda_trigger * 100, (mda_trigger + 0.01) * 100],
                        "color": "#FFF5E6",
                    },
                    {"range": [(mda_trigger + 0.01) * 100, 15], "color": "#E6F9F3"},
                ],
                "threshold": {
                    "line": {"color": "#EF553B", "width": 3},
                    "thickness": 0.75,
                    "value": mda_trigger * 100,
                },
            },
            number={"suffix": "%"},
        )
    )

    fig.add_annotation(
        text=f"<b>{status}</b><br>Headroom: {headroom_bps:.0f} bps",
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.25,
        showarrow=False,
        font={"size": 12, "color": gauge_color},
    )

    fig.update_layout(
        height=400,
        font={"size": 12},
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 40, "b": 80},
    )

    return fig


def capital_bar_chart(risk_classes_dict: Dict[str, float]) -> go.Figure:
    """
    Create a bar chart of capital by risk class.

    Parameters
    ----------
    risk_classes_dict : dict
        Mapping of risk class name to capital amount (e.g., {"GIRR": 150, "Equity": 500})

    Returns
    -------
    go.Figure
        Plotly bar chart with total CRM labeled at top
    """
    names = list(risk_classes_dict.keys())
    values = list(risk_classes_dict.values())
    total = sum(values)

    fig = go.Figure(
        data=[
            go.Bar(
                x=names,
                y=values,
                marker=dict(
                    color=values,
                    colorscale=[
                        [0, "#636EFA"],
                        [0.2, "#EF553B"],
                        [0.4, "#FFA15A"],
                        [0.6, "#00CC96"],
                        [0.8, "#AB63FA"],
                        [1, "#FFA15A"],
                    ],
                ),
                text=[f"${v:.0f}M" for v in values],
                textposition="outside",
            )
        ]
    )

    fig.add_annotation(
        text=f"<b>Total CRM: ${total:.0f}M</b>",
        xref="paper",
        yref="paper",
        x=0.5,
        y=1.12,
        showarrow=False,
        font={"size": 14, "color": "#333333", "family": "Arial Black"},
    )

    fig.update_layout(
        title="FRTB SA Capital by Risk Class",
        xaxis_title="Risk Class",
        yaxis_title="Capital Requirement ($M)",
        height=400,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"size": 11},
        margin={"t": 100},
    )

    return fig


def stacked_composition_chart(
    risk_classes_dict: Dict[str, Dict[str, float]]
) -> go.Figure:
    """
    Create a stacked bar chart showing delta/vega/curvature/DRC/RRAO composition.

    Parameters
    ----------
    risk_classes_dict : dict
        Mapping of risk class to component breakdown.
        E.g., {"GIRR": {"delta": 100, "vega": 20, "curvature": 10, "drc": 0, "rrao": 0},
               "Equity": {"delta": 500, ...}}

    Returns
    -------
    go.Figure
        Plotly stacked bar chart
    """
    risk_classes = list(risk_classes_dict.keys())

    # Extract components for stacking
    components = ["delta", "vega", "curvature", "drc", "rrao"]
    colors_map = {
        "delta": "#636EFA",
        "vega": "#EF553B",
        "curvature": "#00CC96",
        "drc": "#FFA15A",
        "rrao": "#AB63FA",
    }

    fig = go.Figure()

    for component in components:
        values = [
            risk_classes_dict.get(rc, {}).get(component, 0) for rc in risk_classes
        ]
        fig.add_trace(
            go.Bar(
                name=component.upper(),
                x=risk_classes,
                y=values,
                marker=dict(color=colors_map.get(component, "#999999")),
                text=[f"${v:.0f}M" if v > 0 else "" for v in values],
                textposition="inside",
            )
        )

    fig.update_layout(
        title="FRTB SA Capital Composition by Risk Class",
        xaxis_title="Risk Class",
        yaxis_title="Capital ($M)",
        barmode="stack",
        height=400,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"size": 11},
        legend={"x": 1.02, "y": 1},
    )

    return fig


def stress_line_chart(scenarios_dict: Dict[str, float]) -> go.Figure:
    """
    Create a line chart showing capital ratios across stress scenarios.

    Parameters
    ----------
    scenarios_dict : dict
        Mapping of scenario name to CET1 ratio.
        E.g., {"Baseline": 0.10, "Adverse": 0.08, "Severely Adverse": 0.05}

    Returns
    -------
    go.Figure
        Plotly line chart with MDA trigger reference line
    """
    # Assume standard MDA trigger at 7%
    mda_trigger = 0.070

    scenarios = list(scenarios_dict.keys())
    ratios = [v * 100 for v in scenarios_dict.values()]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=scenarios,
            y=ratios,
            mode="lines+markers",
            name="CET1 Ratio",
            line=dict(color="#636EFA", width=3),
            marker=dict(size=10),
            text=[f"{r:.1f}%" for r in ratios],
            textposition="top center",
        )
    )

    # Add MDA trigger line
    fig.add_hline(
        y=mda_trigger * 100,
        line_dash="dash",
        line_color="red",
        name="MDA Trigger",
        annotation_text="MDA Trigger (7.0%)",
        annotation_position="right",
    )

    fig.update_layout(
        title="CET1 Ratio Across Stress Scenarios",
        xaxis_title="Scenario",
        yaxis_title="CET1 Ratio (%)",
        height=400,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"size": 11},
        hovermode="x unified",
    )

    fig.update_yaxes(range=[0, 15])

    return fig


def kpi_card(label: str, value: float, threshold: float, is_percentage: bool = True) -> Dict[str, Any]:
    """
    Create a KPI card data structure for display in Streamlit.

    Parameters
    ----------
    label : str
        KPI label (e.g., "CET1 Ratio")
    value : float
        Current value (e.g., 0.095 for 9.5%)
    threshold : float
        Regulatory threshold (e.g., 0.045 for 4.5%)
    is_percentage : bool
        Whether to format as percentage

    Returns
    -------
    dict
        Card data with color status (green/amber/red)
    """
    if is_percentage:
        value_str = f"{value * 100:.1f}%"
        threshold_str = f"{threshold * 100:.1f}%"
    else:
        value_str = f"{value:.2f}"
        threshold_str = f"{threshold:.2f}"

    # Determine color status
    if value < threshold:
        status = "BREACH"
        color = "#EF553B"  # Red
    elif value < threshold + 0.01:  # 100 bps buffer
        status = "AT RISK"
        color = "#FFA15A"  # Amber
    else:
        status = "OK"
        color = "#00CC96"  # Green

    return {
        "label": label,
        "value": value_str,
        "threshold": threshold_str,
        "status": status,
        "color": color,
        "headroom": f"{(value - threshold) * 10_000:.0f} bps",
    }


def traffic_light(
    pillar1_compliant: bool,
    ccb_compliant: bool,
    mda_compliant: bool,
    gsii_compliant: bool,
) -> Dict[str, Any]:
    """
    Create a traffic light signal showing multi-level compliance status.

    Parameters
    ----------
    pillar1_compliant : bool
        Pillar 1 minimum (CET1 >= 4.5%, Tier1 >= 6%, Total >= 8%)
    ccb_compliant : bool
        Countercyclical buffer (CCB) compliance
    mda_compliant : bool
        MDA trigger compliance
    gsii_compliant : bool
        G-SII buffer compliance

    Returns
    -------
    dict
        Traffic light signals with colors and status
    """
    signals = [
        {
            "name": "Pillar 1",
            "status": "PASS" if pillar1_compliant else "FAIL",
            "color": "#00CC96" if pillar1_compliant else "#EF553B",
        },
        {
            "name": "CCB",
            "status": "PASS" if ccb_compliant else "FAIL",
            "color": "#00CC96" if ccb_compliant else "#EF553B",
        },
        {
            "name": "MDA",
            "status": "PASS" if mda_compliant else "FAIL",
            "color": "#00CC96" if mda_compliant else "#EF553B",
        },
        {
            "name": "G-SII",
            "status": "PASS" if gsii_compliant else "FAIL",
            "color": "#00CC96" if gsii_compliant else "#EF553B",
        },
    ]

    # Overall status: all must pass
    overall_compliant = all(
        [pillar1_compliant, ccb_compliant, mda_compliant, gsii_compliant]
    )

    signals.append(
        {
            "name": "Overall",
            "status": "PASS" if overall_compliant else "FAIL",
            "color": "#00CC96" if overall_compliant else "#EF553B",
        }
    )

    return {"signals": signals, "overall_status": "COMPLIANT" if overall_compliant else "NON-COMPLIANT"}

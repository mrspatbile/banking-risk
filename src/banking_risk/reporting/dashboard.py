"""
Banking Risk Dashboard — BKR-75.

Run with:
    streamlit run banking_risk_dashboard.py
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Banking Risk",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── colours ───────────────────────────────────────────────────────────────────
BG     = "#0d1117"
BG2    = "#161b22"
BG3    = "#21262d"
BORDER = "#30363d"
TEXT   = "#c9d1d9"
MUTED  = "#8b949e"
BLUE   = "#1f6feb"
CYAN   = "#58a6ff"
GREEN  = "#3fb950"
AMBER  = "#d29922"
RED    = "#f85149"
PURPLE = "#8b5cf6"

# ── global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* hide metric delta arrow only, keep coloured text */
  [data-testid="stMetricDelta"] svg {{ display: none !important; }}

  /* center metric — label, value, delta all aligned with each other */
  [data-testid="metric-container"] > div {{
      display: flex !important; flex-direction: column !important;
      align-items: center !important;
  }}
  [data-testid="stMetricLabel"] > div {{ text-align: center !important; }}
  [data-testid="stMetricValue"]       {{ text-align: center !important; }}
  [data-testid="stMetricDelta"] {{
      display: flex !important; justify-content: center !important;
  }}
  [data-testid="stMetricDelta"] p {{ font-size: 0.85rem !important; }}

  /* table header background like plot bg */
  [data-testid="stTable"] thead th {{
      background-color: {BG2} !important;
      color: {MUTED} !important;
      font-family: monospace;
  }}
  /* table body */
  [data-testid="stTable"] table {{ font-family: monospace; font-size: 13px; }}
  [data-testid="stTable"] td {{
      border-bottom-color: rgba(255,255,255,0.15) !important;
  }}
  [data-testid="stTable"] th {{
      white-space: nowrap !important;
      vertical-align: middle !important;
      padding: 6px 12px !important;
  }}
  /* right-align all columns except first */
  [data-testid="stTable"] td:not(:first-child),
  [data-testid="stTable"] th:not(:first-child) {{ text-align: right !important; }}
  /* center last column (Status) */
  [data-testid="stTable"] td:last-child,
  [data-testid="stTable"] th:last-child {{ text-align: center !important; }}

  /* ── tabs: filing-separator style ── */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {{
      gap: 3px !important;
      background: transparent !important;
      border-bottom: 1px solid {BORDER} !important;
      padding-left: 0 !important;
  }}
  [data-testid="stTabs"] [data-baseweb="tab"] {{
      border-radius: 7px 7px 0 0 !important;
      background: {BG3} !important;
      border: 1px solid {BORDER} !important;
      border-bottom: none !important;
      padding: 10px 28px !important;
      font-size: 14px !important;
      font-family: monospace !important;
      color: {CYAN} !important;
      margin-bottom: -1px !important;
  }}
  [data-testid="stTabs"] [aria-selected="true"][data-baseweb="tab"] {{
      background: {BG2} !important;
      color: rgba(88,166,255,0.55) !important;
      border-color: {BORDER} !important;
      border-bottom: 1px solid {BG2} !important;
  }}
  [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
      color: {CYAN} !important;
      background: {BG} !important;
  }}
  /* hide the default underline indicator Streamlit adds */
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
      display: none !important;
  }}
  [data-testid="stTabs"] [data-baseweb="tab-border"] {{
      display: none !important;
  }}

  /* right-align dataframe numeric column headers */
  [data-testid="stDataFrame"] [role="columnheader"]:not(:first-child) {{
      text-align: right !important;
      justify-content: flex-end !important;
  }}

  /* round plotly containers */
  .js-plotly-plot, .plotly, .plot-container {{
      border-radius: 8px !important; overflow: hidden !important;
  }}
  [data-testid="stPlotlyChart"] > div {{
      border-radius: 8px !important; overflow: hidden !important;
      background: {BG2} !important;
  }}
</style>
""", unsafe_allow_html=True)

# ── plotly defaults ───────────────────────────────────────────────────────────
_STATIC = {"staticPlot": True, "displayModeBar": False}

_GRID  = "rgba(255,255,255,0.18)"
_SPINE = "rgba(160,160,160,0.45)"
_BASE = dict(
    paper_bgcolor=BG2,
    plot_bgcolor=BG2,
    font=dict(family="monospace", size=11, color=TEXT),
    margin=dict(l=50, r=20, t=30, b=50),
    height=270,
    showlegend=True,
    legend=dict(bgcolor=BG3, bordercolor=BORDER, borderwidth=1,
                font=dict(size=10, color=TEXT)),
    xaxis=dict(gridcolor=_GRID, gridwidth=0.5, zeroline=False,
               showline=True, linecolor=_SPINE, linewidth=2,
               tickfont=dict(size=11, color=MUTED),
               tickcolor=MUTED),
    yaxis=dict(gridcolor=_GRID, gridwidth=0.5, zeroline=False,
               linecolor="rgba(0,0,0,0)", rangemode="tozero",
               tickfont=dict(size=11, color=MUTED),
               title_font=dict(size=11, color=MUTED)),
)


def _html_table(rows: list[dict], right_cols: list[str]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    n = len(cols)
    th_base = f"padding:6px 12px;color:{MUTED};background:{BG2};border-bottom:1px solid {BORDER};font-family:monospace;font-size:13px;white-space:nowrap;"
    td_base = f"padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.05);font-family:monospace;font-size:13px;white-space:nowrap;"

    head_cells = []
    for i, c in enumerate(cols):
        r = "8px 0 0 0" if i == 0 else ("0 8px 0 0" if i == n - 1 else "0")
        align = "right" if c in right_cols else "left"
        head_cells.append(f'<th style="{th_base}text-align:{align};border-radius:{r};">{c}</th>')
    head = "".join(head_cells)

    body = ""
    for ri, row in enumerate(rows):
        is_last = ri == len(rows) - 1
        cells = []
        for i, c in enumerate(cols):
            style = td_base
            if is_last:
                style = style.replace("border-bottom:1px solid rgba(255,255,255,0.05);", "")
                if i == 0:       style += "border-radius:0 0 0 8px;"
                elif i == n - 1: style += "border-radius:0 0 8px 0;"
            align = "right" if c in right_cols else "left"
            v = row[c] if row[c] is not None else ""
            cells.append(f'<td style="{style}text-align:{align};">{v}</td>')
        body += f'<tr>{"".join(cells)}</tr>'

    html = (
        f'<table style="width:100%;border-collapse:separate;border-spacing:0;'
        f'border:1px solid {BORDER};border-radius:8px;font-family:monospace;">'
        f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _fig(**kw) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(**_BASE)
    if kw:
        fig.update_layout(**kw)
    return fig


def _show(fig: go.Figure):
    st.plotly_chart(fig, config=_STATIC, use_container_width=True)


# ── data helpers ──────────────────────────────────────────────────────────────
_DATA = Path(__file__).parent


def load_demo_capital_stack() -> dict:
    with open(_DATA / "demo_capital_stack.json") as f:
        return json.load(f)


def load_demo_frtb_sa() -> dict:
    with open(_DATA / "demo_frtb_sa.json") as f:
        return json.load(f)


def parse_capital_stack_json(d: dict) -> dict:
    for k in ["cet1", "tier1", "tier2", "total_capital",
              "frtb_rwa", "credit_rwa", "oprisk_rwa", "total_rwa",
              "cet1_ratio", "tier1_ratio", "total_ratio"]:
        if k not in d:
            raise ValueError(f"Missing required field: {k}")
    return d


def parse_frtb_sa_json(d: dict) -> dict:
    if "components" not in d:
        raise ValueError("Missing required field: components")
    for c in d["components"]:
        if not all(k in c for k in ["name", "delta", "vega", "curvature"]):
            raise ValueError("Component missing required fields")
    return d


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _m(v: float) -> str:
    if abs(v) >= 1e9:
        return f"€{v / 1e9:.1f}bn"
    return f"€{v / 1e6:.1f}m"


def _mda(d: dict) -> float:
    return 0.045 + d.get("ccb", 0.025) + d.get("ccyb", 0.0) + 0.5 * d.get("gsii_buffer", 0.0)


def _lev(d: dict) -> float:
    # Leverage ratio = Tier 1 / Total Exposure (CRR Art. 429)
    # If not provided directly, approximate as Tier1 / Total RWA
    if "leverage_ratio" in d:
        return d["leverage_ratio"]
    rwa = d["total_rwa"]
    return d["tier1"] / rwa if rwa else 0.0


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏦 Banking Risk")
    st.markdown("---")
    mode = st.radio("Data source", ["Demo", "Upload JSON"], horizontal=True)
    st.markdown("---")
    st.caption("CRR3 Art. 325 · EBA/GL/2022/14")

if mode == "Demo":
    cap  = load_demo_capital_stack()
    frtb = load_demo_frtb_sa()
else:
    cap_f  = st.sidebar.file_uploader("Capital_Stack.json",  type="json")
    frtb_f = st.sidebar.file_uploader("FRTB_SA_Result.json", type="json")
    if not cap_f or not frtb_f:
        st.info("Upload both JSON files or switch to Demo.")
        st.stop()
    cap  = json.load(cap_f)
    frtb = json.load(frtb_f)

# ── derived ───────────────────────────────────────────────────────────────────
mda    = _mda(cap)
lev    = _lev(cap)
hdroom = (cap["cet1_ratio"] - mda) * 10_000

components  = frtb.get("components", [])
drc         = frtb.get("drc",  0.0)
rrao        = frtb.get("rrao", 0.0)
total_crm   = sum(c.get("delta", 0) + c.get("vega", 0) + c.get("curvature", 0)
                  for c in components) + drc + rrao

# ── tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["   Capital Adequacy   ", "   FRTB SA   "])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Capital Adequacy
# ═════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Row 1: KPI strip ──────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    _gp  = f'background:#1a3a1f;color:{GREEN};padding:2px 10px;border-radius:12px;font-size:0.82rem;font-family:monospace'
    _pd  = 'display:flex;justify-content:center;margin-top:-8px'
    _lbl = f'text-align:center;font-size:0.82rem;color:{MUTED};font-family:monospace;margin-bottom:-12px'

    def _kpi(col, label, value, pill):
        with col:
            st.markdown(f'<div style="{_lbl}">{label}</div>', unsafe_allow_html=True)
            st.metric("", value, label_visibility="collapsed")
            st.markdown(f'<div style="{_pd}"><span style="{_gp}">{pill}</span></div>', unsafe_allow_html=True)

    _kpi(k1, "CET1 Ratio",   _pct(cap["cet1_ratio"]),  "min 4.5%")
    _kpi(k2, "Tier 1 Ratio", _pct(cap["tier1_ratio"]), "min 6.0%")
    _kpi(k3, "Total Ratio",  _pct(cap["total_ratio"]), "min 8.0%")
    _kpi(k4, "Leverage",     _pct(lev),                "max 3.0%")
    _kpi(k5, "MDA Headroom", f"{hdroom:.0f} bps",      f"trigger {mda*100:.1f}%")

    st.markdown("---")

    # ── Row 2: Capital stack | RWA pie + table ───────────────────────────
    r2a, r2b = st.columns(2)

    with r2a:
        st.markdown("##### Capital Stack")
        lbls = ["CET1", "AT1", "Tier 2"]
        vals = [cap["cet1"] / 1e6,
                max(cap["tier1"] - cap["cet1"], 0) / 1e6,
                cap["tier2"] / 1e6]
        fig = _fig(yaxis_title="EUR Million")
        fig.add_trace(go.Bar(
            x=lbls, y=vals,
            marker_color=[BLUE, CYAN, PURPLE],
            text=[_m(v * 1e6) for v in vals],
            textposition="outside", textfont=dict(size=12, color=TEXT),
            showlegend=False,
        ))
        _show(fig)

    with r2b:
        st.markdown("##### RWA Composition")
        rwa_v   = [cap["frtb_rwa"], cap["credit_rwa"], cap["oprisk_rwa"]]
        rwa_l   = ["FRTB", "Credit Risk", "Op Risk"]
        rwa_clr = ["#7c3aed", "#b054e8", "#db2777"]
        total_rwa = cap["total_rwa"]

        fig = _fig(height=270, showlegend=True,
                   margin=dict(l=10, r=200, t=20, b=10),
                   legend=dict(x=0.72, y=0.5, bgcolor="rgba(0,0,0,0)",
                               borderwidth=0, font=dict(size=10)))
        fig.add_trace(go.Pie(
            labels=rwa_l, values=rwa_v,
            marker=dict(colors=rwa_clr, line=dict(width=0)),
            textfont=dict(size=12, color="white"), hole=0.42,
            textinfo="percent", rotation=15, direction="clockwise",
            domain=dict(x=[0, 0.65]),
        ))
        _r = f'<span style="color:{rwa_clr[0]}">●</span> FRTB      {_m(cap["frtb_rwa"]):>7}   {cap["frtb_rwa"]/total_rwa*100:>4.1f}%'
        _c = f'<span style="color:{rwa_clr[1]}">●</span> Credit    {_m(cap["credit_rwa"]):>7}   {cap["credit_rwa"]/total_rwa*100:>4.1f}%'
        _o = f'<span style="color:{rwa_clr[2]}">●</span> Op Risk   {_m(cap["oprisk_rwa"]):>7}   {cap["oprisk_rwa"]/total_rwa*100:>4.1f}%'
        _t = f'  Total     {_m(total_rwa):>7}   100.0%'
        ann_text = (
            f"{_r}<br><br>{_c}<br><br>{_o}"
            f"<br>────────────────────────────<br>"
            f"{_t}"
        )
        fig.add_annotation(
            x=0.70, y=0.5, xref="paper", yref="paper",
            text=ann_text,
            showarrow=False, align="left", xanchor="left",
            font=dict(family="monospace", size=15, color=TEXT),
            bgcolor=BG3, bordercolor=BORDER, borderwidth=1, borderpad=14,
        )
        _show(fig)


    st.markdown("---")

    # ── Row 3: Compliance table | Stress test chart ───────────────────────
    r3a, r3b = st.columns([1, 1])

    with r3a:
        st.markdown("##### Regulatory Compliance")
        checks = [
            ("CET1  min 4.5%",  cap["cet1_ratio"]  >= 0.045, _pct(cap["cet1_ratio"]),  "4.50%"),
            ("Tier1 min 6.0%",  cap["tier1_ratio"] >= 0.060, _pct(cap["tier1_ratio"]), "6.00%"),
            ("Total min 8.0%",  cap["total_ratio"] >= 0.080, _pct(cap["total_ratio"]), "8.00%"),
            ("CCB   min 7.0%",  cap["cet1_ratio"]  >= 0.070, _pct(cap["cet1_ratio"]),  "7.00%"),
            ("MDA headroom",    hdroom > 0,                   f"{hdroom:.0f} bps",      "pos."),
            ("Leverage max 3%", lev >= 0.030,                 _pct(lev),                "3.00%"),
        ]
        df_c = pd.DataFrame(checks, columns=["Requirement", "_ok", "Current", "Min"])
        df_c["Status"] = df_c["_ok"].map({True: "✅ PASS", False: "❌ FAIL"})
        st.table(df_c[["Requirement", "Current", "Status"]])

    with r3b:
        stress = cap.get("stress_scenarios", {})
        if stress:
            st.markdown("##### Stress Test — CET1 Ratio")
            s_names  = list(stress.keys())
            s_ratios = [v.get("cet1_ratio", 0) * 100 for v in stress.values()]
            s_colors = [GREEN if r >= mda * 100 else RED for r in s_ratios]

            fig = _fig(yaxis_title="CET1 (%)", height=237)
            fig.add_trace(go.Bar(
                x=s_names, y=s_ratios, marker_color=s_colors,
                text=[f"{r:.1f}%" for r in s_ratios],
                textposition="outside", textfont=dict(size=12, color=TEXT),
                showlegend=False,
            ))
            fig.add_hline(y=mda * 100, line_dash="dot", line_color=RED,
                          layer="above", line_width=1.3,
                          annotation_text=f"MDA {mda*100:.1f}%",
                          annotation_font_color=RED,
                          annotation_font_size=9,
                          annotation_position="top right")
            _show(fig)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — FRTB SA
# ═════════════════════════════════════════════════════════════════════════════
with tab2:

    total_delta     = sum(c.get("delta", 0)     for c in components)
    total_vega      = sum(c.get("vega", 0)      for c in components)
    total_curvature = sum(c.get("curvature", 0) for c in components)

    # ── Row 1: KPI strip ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    _bp  = f'background:#0d2b4e;color:{CYAN};padding:2px 10px;border-radius:12px;font-size:0.82rem;font-family:monospace'
    _pd2 = 'display:flex;justify-content:center;margin-top:-8px'
    _lbl2 = f'text-align:center;font-size:0.82rem;color:{MUTED};font-family:monospace;margin-bottom:-12px'

    with c1:
        st.markdown(f'<div style="{_lbl2}">CRM Total</div>', unsafe_allow_html=True)
        st.metric("", _m(total_crm), label_visibility="collapsed")
    with c2:
        st.markdown(f'<div style="{_lbl2}">Δ  Delta</div>', unsafe_allow_html=True)
        st.metric("", _m(total_delta), label_visibility="collapsed")
        if total_crm:
            st.markdown(f'<div style="{_pd2}"><span style="{_bp}">{total_delta/total_crm*100:.0f}% of CRM</span></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="{_lbl2}">υ  Vega</div>', unsafe_allow_html=True)
        st.metric("", _m(total_vega), label_visibility="collapsed")
        if total_crm:
            st.markdown(f'<div style="{_pd2}"><span style="{_bp}">{total_vega/total_crm*100:.0f}% of CRM</span></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div style="{_lbl2}">κ  Curvature</div>', unsafe_allow_html=True)
        st.metric("", _m(total_curvature), label_visibility="collapsed")
        if total_crm:
            st.markdown(f'<div style="{_pd2}"><span style="{_bp}">{total_curvature/total_crm*100:.0f}% of CRM</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Row 2: Capital by class | Composition ────────────────────────────
    r2a, r2b = st.columns(2)
    names       = [c["name"] for c in components]
    bar_palette = [BLUE, CYAN, PURPLE, GREEN, "#e879f9", "#fb923c"]

    with r2a:
        st.markdown("##### Capital by Risk Class")
        totals = [(c.get("delta", 0) + c.get("vega", 0) + c.get("curvature", 0)) / 1e6
                  for c in components]
        fig = _fig(yaxis_title="EUR Million")
        fig.add_trace(go.Bar(
            x=names, y=totals,
            marker_color=bar_palette[:len(names)],
            text=[_m(v * 1e6) for v in totals],
            textposition="outside", textfont=dict(size=12, color=MUTED),
            showlegend=False,
        ))
        _show(fig)

    with r2b:
        st.markdown("##### Composition — Δ Delta / υ Vega / κ Curvature")
        deltas     = [c.get("delta", 0)     / 1e6 for c in components]
        vegas      = [c.get("vega", 0)      / 1e6 for c in components]
        curvatures = [c.get("curvature", 0) / 1e6 for c in components]
        stack_totals = [d + v + k for d, v, k in zip(deltas, vegas, curvatures)]

        fig = _fig(yaxis_title="EUR Million", barmode="stack")
        fig.add_trace(go.Bar(x=names, y=deltas,     name="Delta",
                             marker_color=BLUE,   opacity=0.9))
        fig.add_trace(go.Bar(x=names, y=vegas,      name="Vega",
                             marker_color=CYAN,   opacity=0.9))
        fig.add_trace(go.Bar(x=names, y=curvatures, name="Curvature",
                             marker_color=PURPLE, opacity=0.9))
        for name, total in zip(names, stack_totals):
            fig.add_annotation(x=name, y=total, text=_m(total * 1e6),
                               showarrow=False, yshift=8,
                               font=dict(size=9, color=MUTED))
        _show(fig)

    st.markdown("---")

    # ── Row 3: Detail table | Capital share chart ─────────────────────────
    r3a, r3b = st.columns([3, 2])

    with r3a:
        st.markdown("##### Risk Class Detail")
        def _fv(v): return f"{v/1e6:.1f}"
        def _fp(v): return f"{v/total_crm*100:.1f}%" if total_crm else "—"

        rows = []
        for c in components:
            d, v, k = c.get("delta", 0), c.get("vega", 0), c.get("curvature", 0)
            rows.append({
                "Risk Class": c["name"],
                "Delta":      _fv(d),
                "Vega":       _fv(v),
                "Curv.":      _fv(k),
                "Total":      _fv(d + v + k),
                "% CRM":      _fp(d + v + k),
            })
        if drc:
            rows.append({"Risk Class": "DRC",  "Delta": "—", "Vega": "—",
                         "Curv.": "—", "Total": _fv(drc), "% CRM": _fp(drc)})
        if rrao:
            rows.append({"Risk Class": "RRAO", "Delta": "—", "Vega": "—",
                         "Curv.": "—", "Total": _fv(rrao), "% CRM": _fp(rrao)})
        _html_table(rows, right_cols=["Delta", "Vega", "Curv.", "Total", "% CRM"])

    with r3b:
        st.markdown("##### Measure Mix per Risk Class")
        cls_names = [c["name"] for c in components]
        d_pcts, v_pcts, k_pcts = [], [], []
        for c in components:
            d = c.get("delta", 0)
            v = c.get("vega", 0)
            k = c.get("curvature", 0)
            tot = d + v + k or 1
            d_pcts.append(round(d / tot * 100, 1))
            v_pcts.append(round(v / tot * 100, 1))
            k_pcts.append(round(k / tot * 100, 1))

        n_rows = len(components) + (1 if drc else 0) + (1 if rrao else 0)
        fig = _fig(
            barmode="stack", height=max(300, 36 * n_rows + 30),
            margin=dict(l=80, r=30, t=20, b=30),
            xaxis=dict(title="% of class total", gridcolor=_GRID,
                       gridwidth=0.5, tickfont=dict(size=9),
                       range=[0, 100], zeroline=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=9),
                       zeroline=False),
        )
        _no_line = dict(marker_line_width=0)
        fig.add_trace(go.Bar(
            y=cls_names, x=d_pcts, name="Delta",
            orientation="h", marker_color=BLUE, opacity=0.9,
            marker_line_width=0,
            text=[f"{v:.0f}%" for v in d_pcts],
            textposition="inside", textfont=dict(size=8, color=TEXT),
        ))
        fig.add_trace(go.Bar(
            y=cls_names, x=v_pcts, name="Vega",
            orientation="h", marker_color=CYAN, opacity=0.9,
            marker_line_width=0,
            text=[f"{v:.0f}%" for v in v_pcts],
            textposition="inside", textfont=dict(size=8, color=TEXT),
        ))
        fig.add_trace(go.Bar(
            y=cls_names, x=k_pcts, name="Curvature",
            orientation="h", marker_color=PURPLE, opacity=0.9,
            marker_line_width=0,
            text=[f"{v:.0f}%" for v in k_pcts],
            textposition="inside", textfont=dict(size=8, color=TEXT),
        ))
        _show(fig)

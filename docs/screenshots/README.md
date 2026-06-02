# Dashboard Screenshots

## Capital Adequacy Dashboard

- **MDA Gauge**: Large gauge showing CET1 ratio vs. MDA trigger
  - Green zone: Compliant (>100bps above trigger)
  - Amber zone: At risk (0-100bps headroom)
  - Red zone: Breach (<0 headroom)

- **KPI Cards**: Four cards showing
  - CET1 Ratio (min 4.5%)
  - Tier 1 Ratio (min 6.0%)
  - Total Capital Ratio (min 8.0%)
  - Leverage Ratio (min 3.0%)


- **Traffic Light**: Five signals
  - Pillar 1 compliance
  - Countercyclical buffer (CCB)
  - Maximum Distributable Amount (MDA)
  - G-SII buffer
  - Overall status

- **Capital Stack Table**: Breakdown of CET1/Tier1/Tier2 amounts and percentages

- **RWA Table**: Risk-weighted assets by component (FRTB, Credit, OpRisk)

- **Stress Testing Chart**: Bar chart showing CET1 ratio across three scenarios
  - Baseline
  - Adverse
  - Severely Adverse

## FRTB SA Dashboard

- **Risk Class Bar Chart**: Capital requirement by risk class
  - GIRR, CSR-nonsec, CSR-sec, Equity, FX, Commodity
  - Total CRM labeled at top

- **Composition Stacked Chart**: Breakdown by delta/vega/curvature/DRC/RRAO

- **CRM Total**: Large highlight of total capital requirement


### Screenshots to populate after first run

- `dashboard_capital_adequacy.png`
- `dashboard_frtb_sa.png`

## Running the Dashboard

```bash
pip install -e .[dashboard]
streamlit run banking_risk_dashboard.py
```

Then open http://localhost:8501 in your browser.

### Demo Mode

By default, the dashboard loads sample data from:
- `banking_risk/reporting/demo_capital_stack.json`
- `banking_risk/reporting/demo_frtb_sa.json`

### Upload JSON

You can also upload your own JSON files with Capital_Stack and FRTB_SA_Result data.

## Regulatory References

- **EBA/GL/2022/14**: IRRBB governance and board communication
- **CRR3 Art. 325bb**: FRTB SA capital requirement aggregation
- **CRR Art. 26–88, 128–142**: Capital definitions and buffer requirements

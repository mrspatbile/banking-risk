#!/usr/bin/env python3
"""
Banking Risk Dashboard — Main entry point for Streamlit application.

Run with:
    streamlit run banking_risk_dashboard.py

This is a wrapper script that imports and runs the dashboard application.

References
----------
BKR-75 : Two Core Dashboards (Streamlit)
EBA/GL/2022/14 : Capital adequacy governance
"""

from banking_risk.reporting.dashboard import main

if __name__ == "__main__":
    main()

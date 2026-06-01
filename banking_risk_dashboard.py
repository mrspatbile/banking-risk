#!/usr/bin/env python3
"""
Banking Risk Dashboard — BKR-75.

Run with:
    streamlit run banking_risk_dashboard.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import banking_risk.reporting.dashboard  # noqa: F401, E402

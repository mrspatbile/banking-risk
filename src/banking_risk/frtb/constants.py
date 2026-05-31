"""
Regulatory constants for the FRTB Standardised Approach.

All magic numbers live here. No module in banking_risk hardcodes risk weights,
vertex tenors, or correlation parameters — import from this file instead.

Reference: CRR3 Art. 325bd (GIRR delta risk weights and vertices)
           BCBS January 2019 / revised 2020 — Minimum capital requirements
           for market risk (FRTB), Table 3
"""


_GIRR_NODES = [
    #  label     tenor   risk weight (bps)
    ("0.25Y",   0.25,   1.7),
    ("0.5Y",    0.5,    1.7),
    ("1Y",      1.0,    1.6),
    ("2Y",      2.0,    1.3),
    ("3Y",      3.0,    1.2),
    ("5Y",      5.0,    1.1),
    ("10Y",    10.0,    1.1),
    ("15Y",    15.0,    1.1),
    ("20Y",    20.0,    1.1),
    ("30Y",    30.0,    1.1),
]

FRTB_GIRR_LABELS       : list[str]   = [n[0] for n in _GIRR_NODES]
FRTB_GIRR_VERTICES     : list[float] = [n[1] for n in _GIRR_NODES]
FRTB_GIRR_RISK_WEIGHTS : list[float] = [n[2] for n in _GIRR_NODES]  # bps

GIRR_CORRELATION_ALPHA   : float = 0.03   # within-bucket decay — CRR3 Art. 325bf
GIRR_CROSS_BUCKET_GAMMA  : float = 0.50 


# ── GIRR Vega vertices ────────────────────────────────────────────────────────
# CRR3 Art. 325bd — option expiry and underlying tenor nodes

_VEGA_NODES = [
    ("0.5Y",  0.5),
    ("1Y",    1.0),
    ("3Y",    3.0),
    ("5Y",    5.0),
    ("10Y",  10.0),
]

GIRR_VEGA_LABELS  : list[str]   = [n[0] for n in _VEGA_NODES]
GIRR_VEGA_VERTICES: list[float] = [n[1] for n in _VEGA_NODES]

GIRR_VEGA_RISK_WEIGHT: float = 0.004   # 0.4% flat — CRR3 Art. 325bd
GIRR_VEGA_ALPHA      : float = 0.01    # correlation decay — CRR3 Art. 325bf
  # cross-currency correlation — CRR3 Art. 325bf


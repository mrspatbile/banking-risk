"""
Regulatory constants for the IRRBB standardised approach.

All magic numbers live here. No module in banking_risk hardcodes bps values,
bucket boundaries, or SOT thresholds — import from this file instead.

Reference: EBA/RTS/2022/10 (IRRBB Supervisory Outlier Tests)
"""

from enum import StrEnum


# ── EBA 19 maturity buckets ──────────────────────────────────────────────────
# EBA/RTS/2022/10, Annex III — boundaries in years (20 boundaries = 19 buckets)

# labels / boundaries / midpoints for EBA maturity buckets
_BUCKETS = [
    ("Overnight", 0.0,     1/365),
    ("1M",        1/365,   1/12),
    ("3M",        1/12,    3/12),
    ("6M",        3/12,    6/12),
    ("9M",        6/12,    9/12),
    ("1Y",        9/12,    1.0),
    ("1.5Y",      1.0,     1.5),
    ("2Y",        1.5,     2.0),
    ("3Y",        2.0,     3.0),
    ("4Y",        3.0,     4.0),
    ("5Y",        4.0,     5.0),
    ("6Y",        5.0,     6.0),
    ("7Y",        6.0,     7.0),
    ("8Y",        7.0,     8.0),
    ("9Y",        8.0,     9.0),
    ("10Y",       9.0,     10.0),
    ("15Y",       10.0,    15.0),
    ("20Y",       15.0,    20.0),
    (">20Y",      20.0,    float("inf")),
]

EBA_BUCKET_LABELS     : list[str]   = [b[0] for b in _BUCKETS]
EBA_BUCKET_BOUNDARIES : list[float] = [b[1] for b in _BUCKETS] + [float("inf")]
EBA_BUCKET_MIDPOINTS  : list[float] = [
    (lo + hi) / 2 if hi != float("inf") else 25.0 # convention: midpoint of >20Y bucket is 25Y
    for _, lo, hi in _BUCKETS
]

assert len(EBA_BUCKET_LABELS) == 19
assert len(EBA_BUCKET_MIDPOINTS) == 19

# ── Post-shock interest rate floor ───────────────────────────────────────────
# EBA/RTS/2022/10, Art. 7
# floor(t) = max(shocked_rate, -150bps + 3bps × t_years)

POST_SHOCK_FLOOR_INTERCEPT: float = -0.0150   # -150 bps
POST_SHOCK_FLOOR_SLOPE: float      =  0.0003  # 3 bps per year

# Maturity beyond which the short-end weight w(t) reaches zero.
# EBA/RTS/2022/10, Annex III — used in steepener, flattener, short rate shocks.
SHOCK_WEIGHT_CUTOFF_YEARS: float = 20.0

# ── Supervisory Outlier Test thresholds ──────────────────────────────────────
# EBA/RTS/2022/10, Art. 6 (EVE) and Art. 8 (NII)

SOT_EVE_THRESHOLD: float = 0.15   # ΔEVE / Tier1 > 15% → outlier
SOT_NII_THRESHOLD: float = 0.05   # |ΔNII| / Tier1 > 5% → outlier

# ── Position type labels ─────────────────────────────────────────────────────

class PositionType(StrEnum):
    ASSET     = "asset"
    LIABILITY = "liability"


# ── NMD modelling ─────────────────────────────────────────────────────────────
# EBA/GL/2022/14, Chapter 6 — non-maturity deposit behavioural assumptions

class NMD_Type(StrEnum):
    RETAIL    = "retail"
    WHOLESALE = "wholesale"

# Maximum average repricing date for the stable (core) NMD portion.
# EBA/GL/2022/14, para. 115 — caps applied per deposit type.
NMD_REPRICING_CAP: dict[str, float] = {
    NMD_Type.RETAIL:    5.0,   # years
    NMD_Type.WHOLESALE: 4.5,   # years
}


# ── EBA supervisory shock sizes by currency ──────────────────────────────────
# EBA/RTS/2022/10, Annex III, Table A — all values in bps.
#
# parallel_up / parallel_down : uniform shift across full curve
# short_up / short_down       : short-end shock (w(t) weighted, fades at 20Y)
# delta_s                     : short-end magnitude for steepener / flattener
# delta_l                     : long-end magnitude for steepener / flattener
#
# Steepener:  Δr(t) = -0.65 × δs × w(t) + 0.9 × δl × (1 − w(t))
# Flattener:  Δr(t) = +0.8 × δs × w(t) − 0.6 × δl × (1 − w(t))

EBA_SHOCKS: dict[str, dict[str, float]] = {
    "EUR": {
        "parallel_up":   200,
        "parallel_down": -200,
        "short_up":       250,
        "short_down":    -250,
        "delta_s":        250,
        "delta_l":        100,
    },
    "USD": {
        "parallel_up":   200,
        "parallel_down": -200,
        "short_up":       300,
        "short_down":    -300,
        "delta_s":        300,
        "delta_l":        150,
    },
    "GBP": {
        "parallel_up":   250,
        "parallel_down": -250,
        "short_up":       300,
        "short_down":    -300,
        "delta_s":        300,
        "delta_l":        150,
    },
    "JPY": {
        "parallel_up":   100,
        "parallel_down": -100,
        "short_up":       100,
        "short_down":    -100,
        "delta_s":        100,
        "delta_l":        100,
    },
    "CHF": {
        "parallel_up":   100,
        "parallel_down": -100,
        "short_up":       100,
        "short_down":    -100,
        "delta_s":        100,
        "delta_l":        100,
    },
}

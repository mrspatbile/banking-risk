"""
Regulatory constants for the FRTB Standardised Approach.

All magic numbers live here. No module in banking_risk hardcodes risk weights,
vertex tenors, or correlation parameters — import from this file instead.

References
----------
CRR3 Art. 325bd  : GIRR delta risk weights and vertices (Table 3)
CRR3 Art. 325bf  : GIRR correlations
CRR3 Art. 325bh  : CSR non-sec buckets, risk weights, correlations
CRR3 Art. 325bk  : Equity delta buckets, risk weights, correlations
CRR3 Art. 325bm  : FX delta risk weight and correlation
CRR3 Art. 325bp  : Commodity delta buckets, risk weights, correlations
BCBS Jan 2019    : Minimum capital requirements for market risk, Tables 3–14
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


# ═══════════════════════════════════════════════════════════════════════════════
# CSR NON-SECURITISATION — CRR3 Art. 325bh / BCBS Table 8
# ═══════════════════════════════════════════════════════════════════════════════

# 5 tenor vertices shared with FX vega and CSR vega
_CSR_TENOR_NODES = [
    ("0.5Y",  0.5),
    ("1Y",    1.0),
    ("3Y",    3.0),
    ("5Y",    5.0),
    ("10Y",  10.0),
]
CSR_TENOR_LABELS  : list[str]   = [n[0] for n in _CSR_TENOR_NODES]
CSR_TENOR_VERTICES: list[float] = [n[1] for n in _CSR_TENOR_NODES]

# 18 buckets: (label, risk_weight_decimal, intra_bucket_name_correlation)
_CSR_NONSEC_BUCKETS = [
    # bucket, description,                                      RW,    rho_name
    ( 1, "Sovereign IG",                                       0.005,  0.65),
    ( 2, "Sovereign HY/NR",                                    0.020,  0.35),
    ( 3, "Local govt IG",                                      0.010,  0.65),
    ( 4, "Local govt HY/NR",                                   0.030,  0.35),
    ( 5, "Financials covered bond IG",                         0.005,  0.65),
    ( 6, "Financials other IG",                                0.010,  0.65),
    ( 7, "Financials HY/NR",                                   0.050,  0.35),
    ( 8, "Basic materials / Energy / Agriculture IG",          0.016,  0.65),
    ( 9, "Basic materials / Energy / Agriculture HY/NR",       0.080,  0.35),
    (10, "Technology / Telecom IG",                            0.013,  0.65),
    (11, "Technology / Telecom HY/NR",                         0.065,  0.35),
    (12, "Health / Utilities / Real estate IG",                0.013,  0.65),
    (13, "Health / Utilities / Real estate HY/NR",             0.060,  0.35),
    (14, "Consumer IG",                                        0.013,  0.65),
    (15, "Consumer HY/NR",                                     0.060,  0.35),
    (16, "Other sector",                                       0.013,  0.50),
    (17, "IG index",                                           0.010,  0.65),
    (18, "HY/NR index",                                        0.050,  0.35),
]

CSR_NONSEC_BUCKET_LABELS  : list[str]   = [str(b[0]) for b in _CSR_NONSEC_BUCKETS]
CSR_NONSEC_BUCKET_DESCS   : list[str]   = [b[1] for b in _CSR_NONSEC_BUCKETS]
CSR_NONSEC_RISK_WEIGHTS   : list[float] = [b[2] for b in _CSR_NONSEC_BUCKETS]
CSR_NONSEC_RHO_NAME       : list[float] = [b[3] for b in _CSR_NONSEC_BUCKETS]

CSR_NONSEC_TENOR_ALPHA    : float = 0.05   # tenor correlation decay — CRR3 Art. 325bh
CSR_NONSEC_CROSS_BUCKET_GAMMA: float = 0.05  # cross-bucket correlation — CRR3 Art. 325bj

CSR_VEGA_RISK_WEIGHT : float = 0.004   # 0.4% — same as GIRR vega — CRR3 Art. 325bd
CSR_VEGA_ALPHA       : float = 0.01    # correlation decay


# ═══════════════════════════════════════════════════════════════════════════════
# CSR SECURITISATION — CRR3 Art. 325bi/bj / BCBS Table 8 (Securitisations)
# ═══════════════════════════════════════════════════════════════════════════════

# 41 buckets total:
# - Buckets 1-25: Non-CTP buckets (senior/non-senior × RMBS/CMBS/ABS/CLO/other)
# - Buckets 26-41: CTP buckets (index/bespoke × senior/mezzanine/junior)

_CSR_SEC_BUCKETS = [
    # Non-CTP buckets (senior)
    ( 1, "RMBS — senior",                          0.020, 0.50),
    ( 2, "RMBS — non-senior",                      0.030, 0.45),
    ( 3, "CMBS — senior",                          0.025, 0.50),
    ( 4, "CMBS — non-senior",                      0.035, 0.45),
    ( 5, "ABS — senior",                           0.020, 0.50),
    ( 6, "ABS — non-senior",                       0.030, 0.45),
    ( 7, "CLO — senior",                           0.015, 0.50),
    ( 8, "CLO — non-senior",                       0.025, 0.45),
    ( 9, "Other sec — senior",                     0.020, 0.50),
    (10, "Other sec — non-senior",                 0.030, 0.45),
    # Additional granularity (buckets 11-25) for institutional securitisations
    (11, "RMBS — AAA",                             0.015, 0.55),
    (12, "RMBS — AA-A",                            0.025, 0.50),
    (13, "RMBS — BBB",                             0.045, 0.40),
    (14, "CMBS — AAA",                             0.020, 0.55),
    (15, "CMBS — AA-A",                            0.030, 0.50),
    (16, "CMBS — BBB",                             0.050, 0.40),
    (17, "ABS — AAA",                              0.015, 0.55),
    (18, "ABS — AA-A",                             0.025, 0.50),
    (19, "ABS — BBB",                              0.045, 0.40),
    (20, "CLO — AAA",                              0.012, 0.55),
    (21, "CLO — AA-A",                             0.020, 0.50),
    (22, "CLO — BBB",                              0.035, 0.40),
    (23, "Other — AAA",                            0.015, 0.55),
    (24, "Other — AA-A",                           0.025, 0.50),
    (25, "Other — BBB",                            0.045, 0.40),
    # CTP buckets (credit tranched products — indices and bespoke)
    (26, "CTP index — senior",                     0.018, 0.50),
    (27, "CTP index — mezzanine",                  0.030, 0.45),
    (28, "CTP index — junior",                     0.035, 0.40),
    (29, "CTP index — equity",                     0.050, 0.35),
    (30, "CTP bespoke — senior",                   0.020, 0.50),
    (31, "CTP bespoke — mezzanine",                0.032, 0.45),
    (32, "CTP bespoke — junior",                   0.040, 0.40),
    (33, "CTP bespoke — equity",                   0.060, 0.35),
    (34, "CTP other index — senior",               0.018, 0.50),
    (35, "CTP other index — mezzanine",            0.030, 0.45),
    (36, "CTP other index — junior",               0.035, 0.40),
    (37, "CTP other index — equity",               0.050, 0.35),
    (38, "CTP other bespoke — senior",             0.020, 0.50),
    (39, "CTP other bespoke — mezzanine",          0.032, 0.45),
    (40, "CTP other bespoke — junior",             0.040, 0.40),
    (41, "CTP other bespoke — equity",             0.060, 0.35),
]

CSR_SEC_BUCKET_LABELS  : list[str]   = [str(b[0]) for b in _CSR_SEC_BUCKETS]
CSR_SEC_BUCKET_DESCS   : list[str]   = [b[1] for b in _CSR_SEC_BUCKETS]
CSR_SEC_RISK_WEIGHTS   : list[float] = [b[2] for b in _CSR_SEC_BUCKETS]
CSR_SEC_RHO_NAME       : list[float] = [b[3] for b in _CSR_SEC_BUCKETS]

CSR_SEC_TENOR_ALPHA    : float = 0.05   # tenor correlation decay — CRR3 Art. 325bi
CSR_SEC_CROSS_BUCKET_GAMMA: float = 0.05  # cross-bucket correlation — CRR3 Art. 325bj

CSR_SEC_VEGA_RISK_WEIGHT : float = 0.004   # 0.4% — CRR3 Art. 325bd
CSR_SEC_VEGA_ALPHA       : float = 0.01    # correlation decay


# ═══════════════════════════════════════════════════════════════════════════════
# EQUITY — CRR3 Art. 325bk / BCBS Table 11
# ═══════════════════════════════════════════════════════════════════════════════

# 11 buckets: (label, description, risk_weight_decimal, rho_intra_bucket)
_EQUITY_BUCKETS = [
    ( 1, "Large cap / EM / Consumer",                  0.55, 0.15),
    ( 2, "Large cap / EM / Telecom & Industrials",     0.60, 0.15),
    ( 3, "Large cap / EM / Basic mat, Energy, Agri",   0.45, 0.15),
    ( 4, "Large cap / EM / Financials & Real estate",  0.55, 0.15),
    ( 5, "Large cap / DM / Consumer",                  0.30, 0.25),
    ( 6, "Large cap / DM / Telecom & Industrials",     0.35, 0.25),
    ( 7, "Large cap / DM / Basic mat, Energy, Agri",   0.40, 0.25),
    ( 8, "Large cap / DM / Financials & Real estate",  0.50, 0.25),
    ( 9, "Small cap / EM",                             0.70, 0.075),
    (10, "Small cap / DM",                             0.50, 0.125),
    (11, "Other (residual bucket)",                    0.70, 0.00),
]

EQUITY_BUCKET_LABELS : list[str]   = [str(b[0]) for b in _EQUITY_BUCKETS]
EQUITY_BUCKET_DESCS  : list[str]   = [b[1] for b in _EQUITY_BUCKETS]
EQUITY_RISK_WEIGHTS  : list[float] = [b[2] for b in _EQUITY_BUCKETS]
EQUITY_RHO_INTRA     : list[float] = [b[3] for b in _EQUITY_BUCKETS]

# Cross-bucket γ: 0.15 for buckets 1-10 pairs, 0 involving bucket 11
EQUITY_CROSS_BUCKET_GAMMA       : float = 0.15
EQUITY_RESIDUAL_BUCKET_GAMMA    : float = 0.00   # bucket 11 vs all others

EQUITY_VEGA_RISK_WEIGHT : float = 0.0078   # 0.78% — CRR3 Art. 325bd
EQUITY_VEGA_ALPHA       : float = 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# FX — CRR3 Art. 325bm / BCBS §B.2.3
# ═══════════════════════════════════════════════════════════════════════════════

FX_RISK_WEIGHT      : float = 0.15   # 15% flat for all currency pairs
FX_CORRELATION_RHO  : float = 0.60   # cross-pair correlation

FX_VEGA_RISK_WEIGHT : float = 0.004   # 0.4% — CRR3 Art. 325bd
FX_VEGA_ALPHA       : float = 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# COMMODITY — CRR3 Art. 325bp / BCBS Table 13–14
# ═══════════════════════════════════════════════════════════════════════════════

_COMMODITY_TENOR_NODES = [
    ("0Y",    0.00),
    ("0.25Y", 0.25),
    ("0.5Y",  0.50),
    ("1Y",    1.00),
    ("2Y",    2.00),
    ("3Y",    3.00),
    ("5Y",    5.00),
]
COMMODITY_TENOR_LABELS  : list[str]   = [n[0] for n in _COMMODITY_TENOR_NODES]
COMMODITY_TENOR_VERTICES: list[float] = [n[1] for n in _COMMODITY_TENOR_NODES]

# 11 buckets: (label, description, risk_weight_decimal, rho_intra_bucket)
_COMMODITY_BUCKETS = [
    ( 1, "Energy — solid combustibles (coal)",    0.30, 0.55),
    ( 2, "Energy — liquid combustibles (oil)",    0.35, 0.95),
    ( 3, "Energy — electricity & carbon trading", 0.60, 0.40),
    ( 4, "Freight",                               0.80, 0.80),
    ( 5, "Metals — non-precious",                 0.40, 0.60),
    ( 6, "Gaseous combustibles (natural gas)",    0.45, 0.65),
    ( 7, "Precious metals (incl. gold)",          0.20, 0.55),
    ( 8, "Grains and oilseeds",                   0.35, 0.45),
    ( 9, "Livestock and dairy",                   0.25, 0.15),
    (10, "Softs and other agriculture",           0.35, 0.40),
    (11, "Other commodity",                       0.50, 0.15),
]

COMMODITY_BUCKET_LABELS : list[str]   = [str(b[0]) for b in _COMMODITY_BUCKETS]
COMMODITY_BUCKET_DESCS  : list[str]   = [b[1] for b in _COMMODITY_BUCKETS]
COMMODITY_RISK_WEIGHTS  : list[float] = [b[2] for b in _COMMODITY_BUCKETS]
COMMODITY_RHO_INTRA     : list[float] = [b[3] for b in _COMMODITY_BUCKETS]

COMMODITY_CROSS_BUCKET_GAMMA: float = 0.20   # simplified uniform cross-bucket


# ── Shared vega expiry vertices (all risk classes) ────────────────────────────
# CRR3 Art. 325bd — used by GIRR, CSR, Equity and FX vega

VEGA_EXPIRY_LABELS  : list[str]   = ["0.5Y", "1Y", "3Y", "5Y", "10Y"]
VEGA_EXPIRY_VERTICES: list[float] = [0.5, 1.0, 3.0, 5.0, 10.0]


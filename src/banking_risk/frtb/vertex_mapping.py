"""
FRTB prescribed vertex lists and bucket assignment — CRR3.

This module owns all CRR3 tenor/vertex constants for the FRTB SA risk
classes and the logic for mapping arbitrary-tenor sensitivities from
quant-risk-engine onto those prescribed grids.

GIRR delta/vega vertices are imported from frtb/constants.py where they
also serve the capital aggregation formulas. All other risk-class vertices
(CSR, equity vega, FX vega, commodity) are defined here.

References
----------
GIRR delta/vega  : CRR3 Art. 325bd, 325bf
CSR              : CRR3 Art. 325bh–325bj
Equity vega      : CRR3 Art. 325bk
FX vega          : CRR3 Art. 325bm
Commodity delta  : CRR3 Art. 325bp
"""

import numpy as np

from banking_risk.frtb.constants import (
    FRTB_GIRR_LABELS,
    FRTB_GIRR_VERTICES,
    GIRR_VEGA_LABELS,
    GIRR_VEGA_VERTICES,
)

# GIRR re-exported so callers can import everything from this module.
__all__ = [
    "FRTB_GIRR_VERTICES",
    "FRTB_GIRR_LABELS",
    "GIRR_VEGA_VERTICES",
    "GIRR_VEGA_LABELS",
    "FRTB_CSR_LABELS",
    "FRTB_CSR_VERTICES",
    "FRTB_EQUITY_VEGA_LABELS",
    "FRTB_EQUITY_VEGA_VERTICES",
    "FRTB_FX_VEGA_LABELS",
    "FRTB_FX_VEGA_VERTICES",
    "FRTB_COMMODITY_LABELS",
    "FRTB_COMMODITY_VERTICES",
    "nearest_vertex",
    "assign_to_bucket",
]


# ── CSR (non-securitisation and securitisation) delta ─────────────────────────
# CRR3 Art. 325bh — 5 credit spread tenor vertices

_CSR_NODES = [
    ("0.5Y",  0.5),
    ("1Y",    1.0),
    ("3Y",    3.0),
    ("5Y",    5.0),
    ("10Y",  10.0),
]

FRTB_CSR_LABELS   : list[str]   = [n[0] for n in _CSR_NODES]
FRTB_CSR_VERTICES : list[float] = [n[1] for n in _CSR_NODES]


# ── Equity and FX vega ────────────────────────────────────────────────────────
# CRR3 Art. 325bk (equity) / 325bm (FX) — same 5 option expiry nodes as GIRR vega

FRTB_EQUITY_VEGA_LABELS   : list[str]   = GIRR_VEGA_LABELS
FRTB_EQUITY_VEGA_VERTICES : list[float] = GIRR_VEGA_VERTICES

FRTB_FX_VEGA_LABELS   : list[str]   = GIRR_VEGA_LABELS
FRTB_FX_VEGA_VERTICES : list[float] = GIRR_VEGA_VERTICES


# ── Commodity delta ───────────────────────────────────────────────────────────
# CRR3 Art. 325bp — forward curve tenor vertices

_COMMODITY_NODES = [
    ("0Y",    0.00),
    ("0.25Y", 0.25),
    ("0.5Y",  0.50),
    ("1Y",    1.00),
    ("2Y",    2.00),
    ("3Y",    3.00),
    ("5Y",    5.00),
]

FRTB_COMMODITY_LABELS   : list[str]   = [n[0] for n in _COMMODITY_NODES]
FRTB_COMMODITY_VERTICES : list[float] = [n[1] for n in _COMMODITY_NODES]


# ── Vertex assignment ─────────────────────────────────────────────────────────

def nearest_vertex(tenor: float, vertices: list[float]) -> float:
    """Return the prescribed vertex nearest to tenor (years).

    Parameters
    ----------
    tenor : float
        Maturity in years from the rate_sensitivities() call.
    vertices : list[float]
        Prescribed CRR3 vertex tenors.

    Returns
    -------
    float
        The element of vertices closest to tenor.
    """
    v = np.asarray(vertices, dtype=float)
    return float(v[np.argmin(np.abs(v - tenor))])


def assign_to_bucket(
    raw_sensitivities: dict[float, float],
    vertices: list[float],
) -> np.ndarray:
    """Aggregate arbitrary-tenor sensitivities onto prescribed vertices.

    Each sensitivity in raw_sensitivities is assigned to the nearest
    prescribed vertex and summed. Converts the dict[float, float] produced
    by quant-risk-engine's rate_sensitivities(curve, tenors) into the
    fixed-length arrays consumed by the GIRR/CSR capital calculators.

    Parameters
    ----------
    raw_sensitivities : dict[float, float]
        Tenor (years) → sensitivity in currency units per 1bp.
    vertices : list[float]
        Prescribed CRR3 vertex tenors (e.g. FRTB_GIRR_VERTICES).

    Returns
    -------
    np.ndarray, shape (len(vertices),)
        Sensitivities aggregated at each prescribed vertex.
    """
    result = np.zeros(len(vertices))
    v = np.asarray(vertices, dtype=float)
    for tenor, sensitivity in raw_sensitivities.items():
        idx = int(np.argmin(np.abs(v - float(tenor))))
        result[idx] += sensitivity
    return result

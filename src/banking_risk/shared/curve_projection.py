"""
Curve_Projection — evaluates a Zero_Curve onto IRRBB, FRTB, and plotting grids.

One call, three grid views. Downstream calculators and reporters read directly
from the projection object rather than calling zero_rate() repeatedly.

Default grids come from the regulatory constants in irrbb/constants.py and
frtb/constants.py. Any grid can be overridden at construction for custom
analysis, backtesting, or stress scenarios on non-standard vertices.
"""

from dataclasses import dataclass

import numpy as np

from banking_risk.frtb.constants import FRTB_GIRR_LABELS, FRTB_GIRR_VERTICES
from banking_risk.irrbb.constants import EBA_BUCKET_LABELS, EBA_BUCKET_MIDPOINTS
from banking_risk.shared.curves import Zero_Curve

_DEFAULT_PLOT_GRID: np.ndarray = np.linspace(1 / 365, 30.0, 300)


@dataclass(frozen=True)
class Grid_View:
    """Curve values evaluated on a single maturity grid.

    Attributes
    ----------
    labels   : list[str] or None
        Regulatory labels for each vertex. None for the plot grid.
    vertices : np.ndarray
        Maturities in years.
    rates    : np.ndarray
        Continuously compounded zero rates in decimal at each vertex.
    dfs      : np.ndarray
        Discount factors exp(−r × t) at each vertex.
    """

    labels  : list[str] | None
    vertices: np.ndarray
    rates   : np.ndarray
    dfs     : np.ndarray


class Curve_Projection:
    """Evaluates a Zero_Curve onto IRRBB, FRTB, and plotting grids in one pass.

    Attributes
    ----------
    irrbb : Grid_View
        Rates and discount factors at the 19 EBA IRRBB bucket midpoints.
        Used by SA_EVE_Calculator and SA_NII_Calculator.
    frtb : Grid_View
        Rates and discount factors at the 10 FRTB GIRR prescribed vertices.
        Used by SA_GIRR_Calculator.
    plot : Grid_View
        Rates and discount factors on a fine grid for smooth curve plots.

    Parameters
    ----------
    curve : Zero_Curve
        Any object satisfying the Zero_Curve protocol — OISCurve, NSSCurve,
        ArrayCurve from quant-risk-engine, or a test stub.
    irrbb_vertices : np.ndarray, optional
        Override the 19 EBA IRRBB midpoints.
    irrbb_labels : list[str], optional
        Override the IRRBB bucket labels.
    frtb_vertices : np.ndarray, optional
        Override the 10 FRTB GIRR tenors.
    frtb_labels : list[str], optional
        Override the FRTB vertex labels.
    plot_grid : np.ndarray, optional
        Override the fine plotting grid. Defaults to linspace(1/365, 30Y, 300).

    Usage
    -----
        proj = Curve_Projection(ois_curve)

        proj.irrbb.rates          # 19 zero rates for EVE discounting
        proj.irrbb.dfs            # 19 discount factors
        proj.frtb.rates           # 10 rates for GIRR delta sensitivities
        proj.plot.rates           # 300 rates for smooth curve plot

        # Shocks applied externally — algebraic on top of the projection:
        shocked_rates = proj.irrbb.rates + shock_vector
        shocked_dfs   = np.exp(-shocked_rates * proj.irrbb.vertices)
    """

    def __init__(
        self,
        curve         : Zero_Curve,
        irrbb_vertices: np.ndarray | None = None,
        irrbb_labels  : list[str]  | None = None,
        frtb_vertices : np.ndarray | None = None,
        frtb_labels   : list[str]  | None = None,
        plot_grid     : np.ndarray | None = None,
    ) -> None:
        _iv = irrbb_vertices if irrbb_vertices is not None else np.array(EBA_BUCKET_MIDPOINTS)
        _il = irrbb_labels   if irrbb_labels   is not None else EBA_BUCKET_LABELS
        _fv = frtb_vertices  if frtb_vertices  is not None else np.array(FRTB_GIRR_VERTICES)
        _fl = frtb_labels    if frtb_labels    is not None else FRTB_GIRR_LABELS
        _pg = plot_grid      if plot_grid      is not None else _DEFAULT_PLOT_GRID.copy()

        self.irrbb = self._evaluate(_il, _iv, curve)
        self.frtb  = self._evaluate(_fl, _fv, curve)
        self.plot  = self._evaluate(None, _pg, curve)

    @staticmethod
    def _evaluate(
        labels  : list[str] | None,
        vertices: np.ndarray,
        curve   : Zero_Curve,
    ) -> Grid_View:
        rates = np.array([curve.zero_rate(t) for t in vertices])
        dfs   = np.array([curve.discount(t)  for t in vertices])
        return Grid_View(labels=labels, vertices=vertices, rates=rates, dfs=dfs)

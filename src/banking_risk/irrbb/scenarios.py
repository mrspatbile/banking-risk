"""
This module implements EBA supervisory interest rate shock scenarios for IRRBB. 
Each scenario transforms a base zero-rate curve into a stressed curve on 
a maturity grid, following EBA/RTS/2022/10 Annex III. 
Downward shocks apply the regulatory post-shock floor. 
Scenarios operate on vectorised numpy arrays to support direct integration 
with EVE and NII engines. 
Scenario_Set loads the full currency-specific set of six shocks 
(parallel up/down, short rate up/down, steepener, flattener) 
using calibrated parameters from constants and provides 
a unified evaluation grid combining computation (EBA midpoints) 
and plotting points.
"""

from abc import ABC, abstractmethod

import numpy as np

from banking_risk.irrbb.constants import (
    EBA_BUCKET_MIDPOINTS,
    EBA_SHOCKS,
    POST_SHOCK_FLOOR_INTERCEPT,
    POST_SHOCK_FLOOR_SLOPE,
    SHOCK_WEIGHT_CUTOFF_YEARS,
)

_DEFAULT_MIDPOINTS: np.ndarray = np.array(EBA_BUCKET_MIDPOINTS)
_DEFAULT_GRID: np.ndarray      = np.linspace(1 / 365, 30.0, 300)


# ── Floor helpers ─────────────────────────────────────────────────────────────

def _floor(
    maturities: np.ndarray
    ) -> np.ndarray:

    """EBA/RTS/2022/10, Art. 7 — post-shock floor: -150bps + 3bps × t."""
    
    return POST_SHOCK_FLOOR_INTERCEPT + POST_SHOCK_FLOOR_SLOPE * maturities


def _apply_floor(
    shocked: np.ndarray, 
    maturities: np.ndarray
    ) -> np.ndarray:

    return np.maximum(shocked, _floor(maturities))


def _w(
    maturities: np.ndarray
    ) -> np.ndarray:

    """Short-end weight w(t) = max(0, (20 − t) / 20).

    EBA/RTS/2022/10, Annex III — used in steepener and flattener formulas.
    w(0) = 1 (full short-end effect), w(≥20) = 0 (full long-end effect).
    """
    return np.maximum(0.0, (SHOCK_WEIGHT_CUTOFF_YEARS - maturities) / SHOCK_WEIGHT_CUTOFF_YEARS)


# ── Abstract base ─────────────────────────────────────────────────────────────

class Shock_Scenario(ABC):
    """Abstract EBA interest rate shock scenario.

    shock() is the only required method. All inputs and outputs are numpy
    arrays so the EVE calculator can vectorise over the 19 EBA midpoints.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Machine-readable scenario identifier (snake_case)."""
        ...

    @abstractmethod
    def shock(
        self,
        base_zero_rates: np.ndarray,
        maturities: np.ndarray,
    ) -> np.ndarray:
        """Apply shock and return shocked zero rates.

        Parameters
        ----------
        base_zero_rates : ndarray, shape (n,)
            Continuously compounded zero rates in decimal at each maturity.
        maturities : ndarray, shape (n,)
            Maturities in years corresponding to each rate.

        Returns
        -------
        ndarray, shape (n,)
            Shocked zero rates. Downward scenarios include the EBA floor.
        """
        ...


# ── Concrete scenarios ────────────────────────────────────────────────────────

class Parallel_Up(Shock_Scenario):
    """Uniform upward shift across the full curve — EBA/RTS/2022/10 Annex III."""

    def __init__(self, shock_bps: float) -> None:
        self._shock = shock_bps / 10_000

    @property
    def name(self) -> str:
        return "parallel_up"

    def shock(self, base_zero_rates: np.ndarray, maturities: np.ndarray) -> np.ndarray:
        return base_zero_rates + self._shock


class Parallel_Down(Shock_Scenario):
    """Uniform downward shift with post-shock floor — EBA/RTS/2022/10 Annex III."""

    def __init__(self, shock_bps: float) -> None:
        self._shock = shock_bps / 10_000   # shock_bps is negative

    @property
    def name(self) -> str:
        return "parallel_down"

    def shock(self, base_zero_rates: np.ndarray, maturities: np.ndarray) -> np.ndarray:
        return _apply_floor(base_zero_rates + self._shock, maturities)


class Short_Rate_Up(Shock_Scenario):
    """Short-end upward shock fading to zero at 20Y — EBA/RTS/2022/10 Annex III."""

    def __init__(self, shock_bps: float) -> None:
        self._shock = shock_bps / 10_000

    @property
    def name(self) -> str:
        return "short_rate_up"

    def shock(self, base_zero_rates: np.ndarray, maturities: np.ndarray) -> np.ndarray:
        return base_zero_rates + self._shock * _w(maturities)


class Short_Rate_Down(Shock_Scenario):
    """Short-end downward shock with floor — EBA/RTS/2022/10 Annex III."""

    def __init__(self, shock_bps: float) -> None:
        self._shock = shock_bps / 10_000   # negative

    @property
    def name(self) -> str:
        return "short_rate_down"

    def shock(self, base_zero_rates: np.ndarray, maturities: np.ndarray) -> np.ndarray:
        return _apply_floor(base_zero_rates + self._shock * _w(maturities), maturities)


class Steepener(Shock_Scenario):
    """Short rates down, long rates up — EBA/RTS/2022/10 Annex III.

    Δr(t) = −0.65 × δs × w(t) + 0.9 × δl × (1 − w(t))
    Post-shock floor applied (short end moves down).
    """

    def __init__(self, delta_s_bps: float, delta_l_bps: float) -> None:
        self._ds = delta_s_bps / 10_000
        self._dl = delta_l_bps / 10_000

    @property
    def name(self) -> str:
        return "steepener"

    def shock(self, base_zero_rates: np.ndarray, maturities: np.ndarray) -> np.ndarray:
        w = _w(maturities)
        shocked = base_zero_rates - 0.65 * self._ds * w + 0.90 * self._dl * (1.0 - w)
        return _apply_floor(shocked, maturities)


class Flattener(Shock_Scenario):
    """Short rates up, long rates down — EBA/RTS/2022/10 Annex III.

    Δr(t) = +0.8 × δs × w(t) − 0.6 × δl × (1 − w(t))
    No floor applied (short end moves up; long-end decline is limited).
    """

    def __init__(self, delta_s_bps: float, delta_l_bps: float) -> None:
        self._ds = delta_s_bps / 10_000
        self._dl = delta_l_bps / 10_000

    @property
    def name(self) -> str:
        return "flattener"

    def shock(self, base_zero_rates: np.ndarray, maturities: np.ndarray) -> np.ndarray:
        w = _w(maturities)
        return base_zero_rates + 0.80 * self._ds * w - 0.60 * self._dl * (1.0 - w)


# ── Scenario set ──────────────────────────────────────────────────────────────

class Scenario_Set:
    """All six EBA supervisory scenarios for a given currency.

    Carries two maturity grids used together for computation and plotting:

    midpoints : np.ndarray
        The 19 EBA bucket midpoints — used by the EVE calculator for
        discounting and by the reporter to overlay markers on plots.
        Defaults to EBA_BUCKET_MIDPOINTS from constants.
    grid : np.ndarray
        Fine plotting grid — used by the reporter to draw smooth shocked
        curves. Defaults to 300 points from overnight to 30Y.
    combined : np.ndarray
        Sorted union of grid and midpoints. Pass this to scenario.shock()
        to evaluate at all points in one call.
    midpoint_idx : np.ndarray
        Integer indices of midpoints inside combined. Use to slice the
        shocked result back to the 19 computation points:
        r_shocked_mids = r_shocked_combined[scenario_set.midpoint_idx]

    Parameters
    ----------
    currency : str
        ISO 4217 code. Must be a key in EBA_SHOCKS (EUR, USD, GBP, JPY, CHF).
    midpoints : np.ndarray, optional
        Override the 19 EBA computation points.
    grid : np.ndarray, optional
        Override the fine plotting grid.
    """

    def __init__(
        self,
        currency: str,
        midpoints: np.ndarray | None = None,
        grid: np.ndarray | None = None,
    ) -> None:
        ccy = currency.upper()
        if ccy not in EBA_SHOCKS:
            raise ValueError(
                f"No EBA shocks defined for '{ccy}'. "
                f"Available: {sorted(EBA_SHOCKS)}"
            )
        self.currency   = ccy
        self.midpoints  = midpoints if midpoints is not None else _DEFAULT_MIDPOINTS.copy()
        self.grid       = grid      if grid      is not None else _DEFAULT_GRID.copy()
        self.combined   = np.unique(np.concatenate([self.grid, self.midpoints]))
        self.midpoint_idx = np.searchsorted(self.combined, self.midpoints)

        p = EBA_SHOCKS[ccy]
        self._scenarios: list[Shock_Scenario] = [
            Parallel_Up(p["parallel_up"]),
            Parallel_Down(p["parallel_down"]),
            Short_Rate_Up(p["short_up"]),
            Short_Rate_Down(p["short_down"]),
            Steepener(p["delta_s"], p["delta_l"]),
            Flattener(p["delta_s"], p["delta_l"]),
        ]

    def __iter__(self):
        return iter(self._scenarios)

    def __len__(self) -> int:
        return len(self._scenarios)

    def __getitem__(self, name: str) -> Shock_Scenario:
        for s in self._scenarios:
            if s.name == name:
                return s
        raise KeyError(f"Scenario '{name}' not in set for {self.currency}")

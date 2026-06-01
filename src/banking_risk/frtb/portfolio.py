"""
FRTB trading book data model.

Defines the core abstractions for the FRTB trading book: a wrapper around
quant-risk-engine instruments that declares their FRTB risk class, and a
portfolio container that computes regulatory sensitivities by delegating to
the underlying instruments.

The design mirrors irrbb/book.py:

- Data representation (Trading_Instrument)
- Portfolio container (Trading_Portfolio, Standard_Trading_Portfolio)
- Sensitivity extraction (methods on the concrete portfolio)

Capital formula logic lives in the calculators (girr/delta.py, etc.).
This module only aggregates instrument sensitivities onto the prescribed
CRR3 vertex grids.

Dependency on quant-risk-engine
--------------------------------
Sensitivity methods call instrument.rate_sensitivities(curve, tenors) on
the underlying quant-risk-engine Instrument. This method must return
dict[float, float] (tenor → currency per 1bp). It is available after the
quant-risk-engine refactoring described in the paired QRE tickets.

Vega methods (girr_vega_sensitivities, equity_vega_sensitivities,
fx_vega_sensitivities) call instrument.vega_grid(curve, expiry_vertices,
tenor_vertices) → dict[tuple[float, float], float]. These raise
NotImplementedError until the vega grid API is implemented in qre.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np

from banking_risk.shared.curves import Zero_Curve
from banking_risk.frtb.vertex_mapping import (
    FRTB_GIRR_VERTICES,
    FRTB_CSR_VERTICES,
    FRTB_COMMODITY_VERTICES,
    GIRR_VEGA_VERTICES,
    FRTB_EQUITY_VEGA_VERTICES,
    FRTB_FX_VEGA_VERTICES,
    assign_to_bucket,
)


# ── Risk class ────────────────────────────────────────────────────────────────

class FRTB_Risk_Class(StrEnum):
    GIRR        = "girr"
    CSR_NON_SEC = "csr_non_sec"
    CSR_SEC     = "csr_sec"
    EQUITY      = "equity"
    FX          = "fx"
    COMMODITY   = "commodity"


# ── Instrument wrapper ────────────────────────────────────────────────────────

@dataclass
class Trading_Instrument:
    """A quant-risk-engine instrument with its FRTB risk class declaration.

    Parameters
    ----------
    name : str
        Unique identifier within the portfolio.
    currency : str
        ISO 4217 code. Used for bucketing sensitivities by currency.
    risk_classes : frozenset[FRTB_Risk_Class]
        Risk classes this instrument contributes to. Most instruments
        belong to one class (e.g. an IRS → GIRR). Cross-currency swaps
        or equity options may appear in two.
    instrument : Any
        The underlying quant-risk-engine Instrument. Must implement:
          rate_sensitivities(curve, tenors: list[float]) → dict[float, float]
        for delta risk classes, and:
          vega_grid(curve, expiry_vertices, tenor_vertices) → dict[tuple, float]
        for vega risk classes (once the QRE vega grid API is available).
    is_linear : bool
        True for instruments with no optionality — bonds, swaps, forwards,
        futures, plain stocks. Contributes delta only.
        False for instruments with embedded optionality — vanilla options,
        callables, structured products. Contributes delta, vega, and curvature.
        vol_surface must be provided when is_linear=False.
    is_long : bool
        Direction of the position. True = long, False = short. Callers are
        responsible for applying the sign when aggregating net sensitivities.
    equity_bucket : int | None
        CRR3 Art. 325bk equity bucket (1–11). Required for equity instruments.
        1–4: large cap emerging markets. 5–8: large cap developed markets.
        9–10: small cap. 11: residual / other.
    csr_bucket : int | None
        CRR3 Art. 325bh CSR non-sec bucket (1–18). Required for CSR instruments.
    commodity_bucket : int | None
        CRR3 Art. 325bp commodity bucket (1–11). Required for commodity instruments.
    ccy_pair : str | None
        ISO pair code e.g. 'EURUSD'. Required for FX instruments.
    issuer : str | None
        Legal entity name of the issuer or counterparty. Used for concentration
        risk and single-name exposure limits.
    underlying : str | None
        Ticker or identifier of the underlying asset for derivatives.
        e.g. 'AAPL', 'SPX', 'EURUSD', 'Brent'. Required for non-linear
        instruments so QRE can retrieve the correct vol surface if not
        explicitly provided.
    vol_surface : Any | None
        QRE Vol_Surface object for the underlying. Required for non-linear
        instruments to compute vega and curvature sensitivities. Must match
        the asset class — equity vol surface for equity options, rate vol
        cube for swaptions, FX vol surface for FX options, etc.
    """

    name             : str
    currency         : str
    risk_classes     : frozenset[FRTB_Risk_Class]
    instrument       : Any
    is_linear        : bool       = True
    is_long          : bool       = True
    equity_bucket    : int | None = None
    csr_bucket       : int | None = None
    commodity_bucket : int | None = None
    ccy_pair         : str | None = None
    issuer           : str | None = None   # legal entity — used for concentration risk
    underlying       : str | None = None   # underlying ticker / identifier (options only)
    vol_surface      : Any | None = None   # QRE Vol_Surface — required for vega/curvature

    def __post_init__(self) -> None:
        self.risk_classes = frozenset(
            FRTB_Risk_Class(rc) for rc in self.risk_classes
        )


# ── Abstract portfolio ────────────────────────────────────────────────────────

class Trading_Portfolio(ABC):
    """Abstract FRTB trading portfolio — interface consumed by all calculators.

    Each sensitivity method returns dict[str, np.ndarray] keyed by ISO
    currency code, aligned to the prescribed CRR3 vertex grid for that
    risk class. This is exactly the format the existing GIRR/CSR/equity
    calculators expect.
    """

    @abstractmethod
    def instruments(self) -> list[Trading_Instrument]:
        """All instruments in the portfolio."""
        ...

    @abstractmethod
    def girr_delta_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        """PV01s at the 10 GIRR vertices — CRR3 Art. 325bd.

        Returns
        -------
        dict[str, np.ndarray]
            Currency → array of shape (10,), currency units per 1bp.
        """
        ...

    @abstractmethod
    def girr_vega_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        """Vega sensitivities on the 5×5 expiry/tenor grid — CRR3 Art. 325bd.

        Returns
        -------
        dict[str, np.ndarray]
            Currency → array of shape (25,) (row-major expiry × tenor).
        """
        ...

    @abstractmethod
    def csr_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        """CS01s at the 5 CSR vertices — CRR3 Art. 325bh.

        Returns
        -------
        dict[str, np.ndarray]
            Currency → array of shape (5,), currency units per 1bp.
        """
        ...

    @abstractmethod
    def equity_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, float]:
        """Equity delta sensitivities — CRR3 Art. 325bk.

        Returns
        -------
        dict[str, float]
            Instrument name → equity spot sensitivity.
        """
        ...

    @abstractmethod
    def fx_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, float]:
        """FX delta sensitivities — CRR3 Art. 325bm.

        Returns
        -------
        dict[str, float]
            Currency pair → spot FX sensitivity.
        """
        ...

    @abstractmethod
    def commodity_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        """Commodity delta sensitivities at the 7 tenor vertices — CRR3 Art. 325bp.

        Returns
        -------
        dict[str, np.ndarray]
            Commodity type → array of shape (7,), currency units per 1bp.
        """
        ...


# ── Concrete portfolio ────────────────────────────────────────────────────────

class Standard_Trading_Portfolio(Trading_Portfolio):
    """Concrete FRTB trading portfolio backed by a list of Trading_Instruments.

    Sensitivity methods filter instruments by risk class, call
    instrument.rate_sensitivities(curve, vertices) on each, map the result
    onto the prescribed CRR3 grid via assign_to_bucket(), and aggregate
    by currency.

    Parameters
    ----------
    instruments : list[Trading_Instrument]
    """

    def __init__(self, instruments: list[Trading_Instrument]) -> None:
        self._instruments = list(instruments)

    def instruments(self) -> list[Trading_Instrument]:
        return self._instruments

    # ── Delta methods (rate_sensitivities API) ────────────────────────────────

    def girr_delta_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        return self._aggregate_rate_sensitivities(
            curve, FRTB_Risk_Class.GIRR, FRTB_GIRR_VERTICES
        )

    def csr_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        csr_classes = {FRTB_Risk_Class.CSR_NON_SEC, FRTB_Risk_Class.CSR_SEC}
        result: dict[str, np.ndarray] = {}
        for ti in self._instruments:
            if not (ti.risk_classes & csr_classes):
                continue
            raw = ti.instrument.rate_sensitivities(curve, FRTB_CSR_VERTICES)
            arr = result.setdefault(ti.currency, np.zeros(len(FRTB_CSR_VERTICES)))
            arr += assign_to_bucket(raw, FRTB_CSR_VERTICES)
        return result

    def commodity_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        return self._aggregate_rate_sensitivities(
            curve, FRTB_Risk_Class.COMMODITY, FRTB_COMMODITY_VERTICES
        )

    # ── Spot sensitivity methods ──────────────────────────────────────────────

    def equity_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, float]:
        """Equity delta per instrument name (flat dict, no bucket info)."""
        result: dict[str, float] = {}
        for ti in self._instruments:
            if FRTB_Risk_Class.EQUITY not in ti.risk_classes:
                continue
            result[ti.name] = ti.instrument.delta(curve)
        return result

    def equity_bucketed_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[int, list[float]]:
        """Equity delta keyed by CRR3 bucket — format expected by SA_Equity_Delta_Calculator.

        Instruments without equity_bucket set fall into bucket 11 (residual).
        """
        result: dict[int, list[float]] = {}
        for ti in self._instruments:
            if FRTB_Risk_Class.EQUITY not in ti.risk_classes:
                continue
            bucket = ti.equity_bucket if ti.equity_bucket is not None else 11
            result.setdefault(bucket, []).append(ti.instrument.delta(curve))
        return result

    def fx_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, float]:
        """FX delta keyed by currency pair label."""
        result: dict[str, float] = {}
        for ti in self._instruments:
            if FRTB_Risk_Class.FX not in ti.risk_classes:
                continue
            key = ti.ccy_pair if ti.ccy_pair is not None else ti.name
            result[key] = ti.instrument.delta_fx(curve)
        return result

    # ── Vega methods (non-linear instruments only, requires QRE vega grid API) ─

    def girr_vega_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        return self._aggregate_vega_sensitivities(
            curve, FRTB_Risk_Class.GIRR, GIRR_VEGA_VERTICES
        )

    def equity_vega_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        return self._aggregate_vega_sensitivities(
            curve, FRTB_Risk_Class.EQUITY, FRTB_EQUITY_VEGA_VERTICES
        )

    def fx_vega_sensitivities(
        self, curve: Zero_Curve
    ) -> dict[str, np.ndarray]:
        return self._aggregate_vega_sensitivities(
            curve, FRTB_Risk_Class.FX, FRTB_FX_VEGA_VERTICES
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _aggregate_rate_sensitivities(
        self,
        curve: Zero_Curve,
        risk_class: FRTB_Risk_Class,
        vertices: list[float],
    ) -> dict[str, np.ndarray]:
        result: dict[str, np.ndarray] = {}
        for ti in self._instruments:
            if risk_class not in ti.risk_classes:
                continue
            raw = ti.instrument.rate_sensitivities(curve, vertices)
            arr = result.setdefault(ti.currency, np.zeros(len(vertices)))
            arr += assign_to_bucket(raw, vertices)
        return result

    def _aggregate_vega_sensitivities(
        self,
        curve: Zero_Curve,
        risk_class: FRTB_Risk_Class,
        expiry_vertices: list[float],
    ) -> dict[str, np.ndarray]:
        n = len(expiry_vertices)
        result: dict[str, np.ndarray] = {}
        for ti in self._instruments:
            if risk_class not in ti.risk_classes:
                continue
            if ti.is_linear:
                continue
            if ti.vol_surface is None:
                raise ValueError(
                    f"Instrument '{ti.name}' is non-linear but has no vol_surface. "
                    "Attach a QRE Vol_Surface before computing vega sensitivities."
                )
            grid = ti.instrument.vega_grid(
                curve, expiry_vertices, expiry_vertices, ti.vol_surface
            )
            arr = result.setdefault(ti.currency, np.zeros(n * n))
            for (ei, tj), v in grid.items():
                i = expiry_vertices.index(ei)
                j = expiry_vertices.index(tj)
                arr[i * n + j] += v
        return result

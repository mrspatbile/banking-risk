"""
FRTB Sensitivity Engine — BKR-56.

Bridges QRE instrument methods and the FRTB SA calculators. For each
instrument in the portfolio, calls the appropriate QRE sensitivity method,
applies the is_long direction sign, and aggregates into the exact input
shape each SA calculator expects.

QRE dependencies
----------------
Delta     : rate_sensitivities(), cs01(), delta(), npv() — available now.
Vega      : VanillaOption.price(curve, sigma=...) — available now.
Curvature : ArrayCurve.bumped_at() + instrument.npv() — available now (GIRR).
            Equity/FX/CSR curvature pending spot/spread bump overrides in QRE.

References
----------
CRR3 Art. 325bd  : GIRR delta / vega vertex grids
CRR3 Art. 325bh  : CSR delta vertex grid
CRR3 Art. 325bk  : Equity delta / vega
CRR3 Art. 325bm  : FX delta / vega
CRR3 Art. 325bp  : Commodity delta
CRR3 Art. 325e   : Curvature — full repricing path
"""

import numpy as np

from banking_risk.frtb.portfolio import (
    Trading_Instrument,
    Trading_Portfolio,
    FRTB_Risk_Class,
)
from banking_risk.frtb.vertex_mapping import (
    FRTB_GIRR_VERTICES,
    FRTB_CSR_VERTICES,
    FRTB_COMMODITY_VERTICES,
    GIRR_VEGA_VERTICES,
    FRTB_EQUITY_VEGA_VERTICES,
    FRTB_FX_VEGA_VERTICES,
    assign_to_bucket,
)
from banking_risk.frtb.constants import FRTB_GIRR_RISK_WEIGHTS
from banking_risk.shared.curves import Zero_Curve

# Curvature risk weights: same as delta — CRR3 Art. 325e
_GIRR_RW_BPS     = list(FRTB_GIRR_RISK_WEIGHTS)           # original bps values
_GIRR_RW_DECIMAL = np.array(FRTB_GIRR_RISK_WEIGHTS) / 10_000  # decimal for bumping

_VEGA_BUMP = 0.01   # 1% absolute vol shock — CRR3 Art. 325bd


class FRTB_Sensitivity_Engine:
    """Computes FRTB SA sensitivities from a portfolio and curve.

    For each instrument:
    - Routes to the correct QRE method based on risk class and linearity
    - Applies is_long sign (1 if long, −1 if short)
    - Aggregates into the format each SA delta/vega/curvature calculator expects

    Parameters
    ----------
    portfolio : Trading_Portfolio
    curve : Zero_Curve
        For curvature computation must be an ArrayCurve exposing
        bumped_at(tenor, amount) — available after QRE-2.
    """

    def __init__(self, portfolio: Trading_Portfolio, curve: Zero_Curve) -> None:
        self._portfolio = portfolio
        self._curve     = curve

    # ── Delta ─────────────────────────────────────────────────────────────────

    def girr_delta(self) -> dict[str, np.ndarray]:
        """PV01 at 10 GIRR vertices per currency — dict[str, ndarray(10,)]."""
        result: dict[str, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.GIRR not in ti.risk_classes:
                continue
            sign = 1 if ti.is_long else -1
            raw  = ti.instrument.rate_sensitivities(self._curve, FRTB_GIRR_VERTICES)
            arr  = result.setdefault(ti.currency, np.zeros(len(FRTB_GIRR_VERTICES)))
            arr += sign * assign_to_bucket(raw, FRTB_GIRR_VERTICES)
        return result

    def csr_delta(self) -> dict[int, np.ndarray]:
        """CS01 at 5 CSR vertices per bucket — dict[int, ndarray(5,)].

        Aggregates both CSR_NON_SEC and CSR_SEC instruments.
        """
        csr_classes = {FRTB_Risk_Class.CSR_NON_SEC, FRTB_Risk_Class.CSR_SEC}
        result: dict[int, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if not (ti.risk_classes & csr_classes):
                continue
            if ti.csr_bucket is None:
                raise ValueError(
                    f"Instrument '{ti.name}' has CSR risk class but no csr_bucket set."
                )
            sign = 1 if ti.is_long else -1
            raw  = self._csr_sens(ti)
            arr  = result.setdefault(ti.csr_bucket, np.zeros(len(FRTB_CSR_VERTICES)))
            arr += sign * assign_to_bucket(raw, FRTB_CSR_VERTICES)
        return result

    def csr_non_sec_delta(self) -> dict[int, np.ndarray]:
        """CS01 at 5 CSR vertices per bucket — CSR non-sec only."""
        result: dict[int, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.CSR_NON_SEC not in ti.risk_classes:
                continue
            if ti.csr_bucket is None:
                raise ValueError(
                    f"Instrument '{ti.name}' has CSR risk class but no csr_bucket set."
                )
            sign = 1 if ti.is_long else -1
            raw  = self._csr_sens(ti)
            arr  = result.setdefault(ti.csr_bucket, np.zeros(len(FRTB_CSR_VERTICES)))
            arr += sign * assign_to_bucket(raw, FRTB_CSR_VERTICES)
        return result

    def csr_sec_delta(self) -> dict[int, np.ndarray]:
        """CS01 at 5 CSR vertices per bucket — CSR securitisation only."""
        result: dict[int, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.CSR_SEC not in ti.risk_classes:
                continue
            if ti.csr_bucket is None:
                raise ValueError(
                    f"Instrument '{ti.name}' has CSR risk class but no csr_bucket set."
                )
            sign = 1 if ti.is_long else -1
            raw  = self._csr_sens(ti)
            arr  = result.setdefault(ti.csr_bucket, np.zeros(len(FRTB_CSR_VERTICES)))
            arr += sign * assign_to_bucket(raw, FRTB_CSR_VERTICES)
        return result

    def equity_delta(self) -> dict[int, list[float]]:
        """Equity spot sensitivity per bucket — dict[int, list[float]]."""
        result: dict[int, list[float]] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.EQUITY not in ti.risk_classes:
                continue
            bucket = ti.equity_bucket if ti.equity_bucket is not None else 11
            sign   = 1 if ti.is_long else -1
            result.setdefault(bucket, []).append(sign * self._equity_spot_sens(ti))
        return result

    def fx_delta(self) -> dict[str, float]:
        """FX spot sensitivity per currency pair — dict[str, float]."""
        result: dict[str, float] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.FX not in ti.risk_classes:
                continue
            key  = ti.ccy_pair if ti.ccy_pair is not None else ti.name
            sign = 1 if ti.is_long else -1
            result[key] = result.get(key, 0.0) + sign * self._fx_spot_sens(ti)
        return result

    def commodity_delta(self) -> dict[int, np.ndarray]:
        """Forward sensitivity at 7 vertices per commodity bucket — dict[int, ndarray(7,)]."""
        result: dict[int, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.COMMODITY not in ti.risk_classes:
                continue
            if ti.commodity_bucket is None:
                raise ValueError(
                    f"Instrument '{ti.name}' has commodity risk class but "
                    "no commodity_bucket set."
                )
            sign = 1 if ti.is_long else -1
            raw  = ti.instrument.rate_sensitivities(self._curve, FRTB_COMMODITY_VERTICES)
            arr  = result.setdefault(
                ti.commodity_bucket, np.zeros(len(FRTB_COMMODITY_VERTICES))
            )
            arr += sign * assign_to_bucket(raw, FRTB_COMMODITY_VERTICES)
        return result

    # ── Vega (requires QRE-1) ─────────────────────────────────────────────────

    def girr_vega(self) -> dict[str, np.ndarray]:
        """Vega on 5×5 expiry×tenor grid per currency — dict[str, ndarray(25,)].

        Non-linear instruments only (is_linear=False).
        """
        n = len(GIRR_VEGA_VERTICES)
        result: dict[str, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.GIRR not in ti.risk_classes or ti.is_linear:
                continue
            sign   = 1 if ti.is_long else -1
            vega   = sign * self._vega(ti)
            e_idx  = self._nearest_idx(self._expiry(ti), GIRR_VEGA_VERTICES)
            t_idx  = self._nearest_idx(self._underlying_tenor(ti), GIRR_VEGA_VERTICES)
            arr    = result.setdefault(ti.currency, np.zeros(n * n))
            arr[e_idx * n + t_idx] += vega
        return result

    def equity_vega(self) -> dict[int, np.ndarray]:
        """Vega at 5 expiry vertices per equity bucket — dict[int, ndarray(5,)].

        Non-linear instruments only.
        """
        n = len(FRTB_EQUITY_VEGA_VERTICES)
        result: dict[int, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.EQUITY not in ti.risk_classes or ti.is_linear:
                continue
            bucket = ti.equity_bucket if ti.equity_bucket is not None else 11
            sign   = 1 if ti.is_long else -1
            vega   = sign * self._vega(ti)
            e_idx  = self._nearest_idx(self._expiry(ti), FRTB_EQUITY_VEGA_VERTICES)
            arr    = result.setdefault(bucket, np.zeros(n))
            arr[e_idx] += vega
        return result

    def fx_vega(self) -> dict[str, np.ndarray]:
        """Vega at 5 expiry vertices per currency pair — dict[str, ndarray(5,)].

        Non-linear instruments only.
        """
        n = len(FRTB_FX_VEGA_VERTICES)
        result: dict[str, np.ndarray] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.FX not in ti.risk_classes or ti.is_linear:
                continue
            key   = ti.ccy_pair if ti.ccy_pair is not None else ti.name
            sign  = 1 if ti.is_long else -1
            vega  = sign * self._vega(ti)
            e_idx = self._nearest_idx(self._expiry(ti), FRTB_FX_VEGA_VERTICES)
            arr   = result.setdefault(key, np.zeros(n))
            arr[e_idx] += vega
        return result

    # ── Curvature ─────────────────────────────────────────────────────────────

    def girr_curvature(self) -> tuple[dict[str, float], dict[str, float]]:
        """(cvr_up, cvr_dn) per currency — inputs for SA_GIRR_Curvature_Calculator.

        Non-linear instruments only.

        CVR formula (CRR3 Art. 325e):
            CVR_k^+ = -(V(r + RW_k) - V(r) - RW_k × s_k)
            CVR_k^- = -(V(r - RW_k) - V(r) + RW_k × s_k)
        where s_k is in currency/bp and RW_k is in bps.
        """
        cvr_up: dict[str, float] = {}
        cvr_dn: dict[str, float] = {}
        for ti in self._portfolio.instruments():
            if FRTB_Risk_Class.GIRR not in ti.risk_classes or ti.is_linear:
                continue
            sign      = 1 if ti.is_long else -1
            raw_delta = ti.instrument.rate_sensitivities(self._curve, FRTB_GIRR_VERTICES)
            delta_arr = assign_to_bucket(raw_delta, FRTB_GIRR_VERTICES)
            pv_base   = ti.instrument.npv(self._curve)

            total_up = 0.0
            total_dn = 0.0
            for k, (tenor, rw_dec, rw_bps) in enumerate(
                zip(FRTB_GIRR_VERTICES, _GIRR_RW_DECIMAL, _GIRR_RW_BPS)
            ):
                pv_up    = ti.instrument.npv(self._curve.bumped_at(tenor,  rw_dec))
                pv_dn    = ti.instrument.npv(self._curve.bumped_at(tenor, -rw_dec))
                delta_k  = delta_arr[k]   # currency per 1bp
                total_up += -(pv_up - pv_base - rw_bps * delta_k)
                total_dn += -(pv_dn - pv_base + rw_bps * delta_k)

            ccy          = ti.currency
            cvr_up[ccy]  = cvr_up.get(ccy, 0.0)  + sign * total_up
            cvr_dn[ccy]  = cvr_dn.get(ccy, 0.0)  + sign * total_dn

        return cvr_up, cvr_dn

    # ── Private helpers ───────────────────────────────────────────────────────

    def _csr_sens(self, ti: Trading_Instrument) -> dict[float, float]:
        """Route to cs01() for CDS instruments, rate_sensitivities() for bonds."""
        if hasattr(ti.instrument, 'cs01'):
            return ti.instrument.cs01(self._curve, FRTB_CSR_VERTICES)
        return ti.instrument.rate_sensitivities(self._curve, FRTB_CSR_VERTICES)

    def _equity_spot_sens(self, ti: Trading_Instrument) -> float:
        """Market value (npv) for linear equity; dollar delta for options."""
        if ti.is_linear:
            return float(ti.instrument.npv(self._curve))
        return float(ti.instrument.delta(self._curve))

    def _fx_spot_sens(self, ti: Trading_Instrument) -> float:
        """NPV for linear FX; dollar delta for FX options."""
        if ti.is_linear:
            return float(ti.instrument.npv(self._curve))
        return float(ti.instrument.delta(self._curve))

    def _vega(self, ti: Trading_Instrument) -> float:
        """Vega via sigma bump."""
        sigma = (
            getattr(ti.instrument, '_sigma', None)
            or getattr(ti.instrument, 'sigma', None)
        )
        if sigma is None:
            raise AttributeError(
                f"Instrument '{ti.name}': cannot access sigma for vega. "
                "Requires QRE-1 (VanillaOption.price(curve, sigma=...))."
            )
        pv_base   = ti.instrument.price(self._curve)
        pv_bumped = ti.instrument.price(self._curve, sigma=sigma + _VEGA_BUMP)
        return float(pv_bumped - pv_base)

    def _expiry(self, ti: Trading_Instrument) -> float:
        """Option expiry in years from QRE instrument."""
        for attr in ('_T', 'expiry_years', 'T'):
            if hasattr(ti.instrument, attr):
                return float(getattr(ti.instrument, attr))
        raise AttributeError(
            f"Instrument '{ti.name}': cannot determine expiry. "
            "QRE instrument must expose expiry in years as '_T', 'expiry_years', or 'T'."
        )

    def _underlying_tenor(self, ti: Trading_Instrument) -> float:
        """Underlying tenor for GIRR swaptions (expiry × tenor grid)."""
        for attr in ('_underlying_tenor', 'underlying_tenor', '_swap_tenor'):
            if hasattr(ti.instrument, attr):
                return float(getattr(ti.instrument, attr))
        return GIRR_VEGA_VERTICES[0]   # conservative: assign to shortest vertex

    @staticmethod
    def _nearest_idx(value: float, vertices: list[float]) -> int:
        v = np.asarray(vertices, dtype=float)
        return int(np.argmin(np.abs(v - value)))

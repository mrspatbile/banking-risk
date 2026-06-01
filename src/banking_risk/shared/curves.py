"""
Zero-curve protocol and adapter.

All curves enter banking_risk as QuantLib YieldTermStructure objects produced
by quant-risk-engine (bootstrap, NSS fit, etc.). QL_Curve_Adapter wraps them
at the boundary so no module inside banking_risk imports QuantLib directly.
"""

from typing import Protocol, runtime_checkable

from banking_risk.shared.dates import to_ql_date


@runtime_checkable
class Zero_Curve(Protocol):
    """Thin interface for a zero-coupon yield curve.

    Protocol used only on unit tests for lightweight
    flat stubs — a plain Python object with zero_rate() and discount() — without
    needing a real QuantLib curve. Calculators are typed against Zero_Curve,
    which keeps them decoupled from QuantLib in the test suite.

    In production, always use QL_Curve_Adapter to wrap a quant-risk-engine curve.
    """

    def zero_rate(self, t_years: float) -> float:
        """Continuously compounded zero rate at maturity t_years."""
        ...

    def discount(self, t_years: float) -> float:
        """Discount factor at maturity t_years: exp(−r(t) × t)."""
        ...


class QL_Curve_Adapter:
    """Wraps a QuantLib YieldTermStructure to implement Zero_Curve.

    QuantLib is imported lazily inside each method so that the rest of
    banking_risk never carries a hard QuantLib dependency at import time.

    Parameters
    ----------
    ql_curve : QuantLib.YieldTermStructure
        Any bootstrapped or flat QuantLib curve (PiecewiseLogLinearDiscount,
        PiecewiseFlatForward, FlatForward, etc.).
    day_count : QuantLib.DayCounter, optional
        Defaults to Actual365Fixed.
    """

    def __init__(self, ql_curve, day_count=None) -> None:
        self._curve = ql_curve
        self._day_count = day_count

    def zero_rate(self, t_years: float) -> float:
        import QuantLib as ql

        dc = self._day_count or ql.Actual365Fixed()
        ref = self._curve.referenceDate()
        target = ref + ql.Period(max(1, round(t_years * 365)), ql.Days)
        return self._curve.zeroRate(target, dc, ql.Continuous, ql.Annual).rate()

    def discount(self, t_years: float) -> float:
        import QuantLib as ql

        ref = self._curve.referenceDate()
        target = ref + ql.Period(max(1, round(t_years * 365)), ql.Days)
        return float(self._curve.discount(target))

    @classmethod
    def from_arrays(
        cls,
        tenors: list[float],
        rates: list[float],
        risk_date,
        day_count=None,
    ) -> "QL_Curve_Adapter":
        """Build a linearly-interpolated zero curve from tenor/rate arrays.

        Parameters
        ----------
        tenors : list[float]
            Maturities in years (e.g. [0.25, 0.5, 1, 2, 5, 10, 30]).
        rates : list[float]
            Continuously compounded zero rates in decimal, same length as tenors.
        risk_date : ql.Date | datetime.date | datetime.datetime | str
            Curve reference date. Strings must be ISO format ("2026-06-01").
        day_count : QuantLib.DayCounter, optional
            Defaults to Actual365Fixed.
        """
        import QuantLib as ql

        ref = to_ql_date(risk_date)
        ql.Settings.instance().evaluationDate = ref
        dc = day_count or ql.Actual365Fixed()
        dates = [ref + ql.Period(max(1, round(t * 365)), ql.Days) for t in tenors]
        curve = ql.ZeroCurve(dates, rates, dc)
        curve.enableExtrapolation()
        return cls(curve, dc)

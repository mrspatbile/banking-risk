"""
Intraday Liquidity Monitoring — BCBS 248.

Five monitoring tools:
  1. Daily maximum intraday liquidity usage
  2. Available intraday liquidity at start of day
  3. Total payments sent
  4. Time-specific obligations (peak-hour exposure)
  5. Intraday utilisation rate = max_usage / available

A Payment represents a cash flow at a given hour of the day.
Positive amounts are inflows (receipts); negative are outflows (payments).

References
----------
BCBS 248 (2013)  : Monitoring tools for intraday liquidity management
EBA/GL/2019/04   : Internal governance — liquidity risk
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ── Input ─────────────────────────────────────────────────────────────────────

@dataclass
class Intraday_Payment:
    """A single cash flow during the business day.

    Parameters
    ----------
    name : str
    hour : float
        Time of day in hours [0, 24). E.g. 9.5 = 09:30.
    amount : float
        Positive = inflow (receipt); negative = outflow (payment).
    counterparty : str | None
        Optional counterparty label for concentration analysis.
    """

    name         : str
    hour         : float
    amount       : float
    counterparty : str | None = None


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class Intraday_Result:
    """Output of Intraday_Monitor.compute().

    Attributes
    ----------
    opening_balance : float
        Available intraday liquidity at start of day.
    closing_balance : float
        Balance at end of day (opening + net payments).
    minimum_balance : float
        Lowest intraday balance during the day.
    maximum_usage : float
        Peak intraday liquidity consumed = opening_balance - minimum_balance.
        Floored at 0 — negative means inflows always exceeded outflows.
    utilisation_rate : float
        maximum_usage / opening_balance. 0 if opening_balance = 0.
    total_payments_sent : float
        Sum of all outflow amounts (absolute value).
    total_payments_received : float
        Sum of all inflow amounts.
    peak_hour : float
        Hour of day at which minimum balance was reached.
    time_series : pd.DataFrame
        Columns: hour, payment, cumulative_net, running_balance.
    """

    opening_balance         : float
    closing_balance         : float
    minimum_balance         : float
    maximum_usage           : float
    utilisation_rate        : float
    total_payments_sent     : float
    total_payments_received : float
    peak_hour               : float
    time_series             : pd.DataFrame


# ── Monitor ───────────────────────────────────────────────────────────────────

class Intraday_Monitor:
    """Compute BCBS 248 intraday liquidity monitoring metrics.

    Parameters
    ----------
    opening_balance : float
        Available intraday liquidity (central bank account balance, intraday
        credit lines) at the start of the business day.
    """

    def __init__(self, opening_balance: float) -> None:
        self._opening = opening_balance

    def compute(self, payments: list[Intraday_Payment]) -> Intraday_Result:
        """Process a day's payment flows and return monitoring metrics.

        Parameters
        ----------
        payments : list[Intraday_Payment]
            All inflows and outflows during the day, in any order.
        """
        if not payments:
            empty = pd.DataFrame(columns=["hour", "payment", "cumulative_net", "running_balance"])
            return Intraday_Result(
                opening_balance=self._opening,
                closing_balance=self._opening,
                minimum_balance=self._opening,
                maximum_usage=0.0,
                utilisation_rate=0.0,
                total_payments_sent=0.0,
                total_payments_received=0.0,
                peak_hour=0.0,
                time_series=empty,
            )

        sorted_pmts = sorted(payments, key=lambda p: p.hour)

        rows = []
        cumulative = 0.0
        for pmt in sorted_pmts:
            cumulative += pmt.amount
            rows.append(
                {
                    "hour"           : pmt.hour,
                    "name"           : pmt.name,
                    "payment"        : pmt.amount,
                    "cumulative_net" : cumulative,
                    "running_balance": self._opening + cumulative,
                }
            )

        ts = pd.DataFrame(rows)
        balances = ts["running_balance"].values

        min_balance  = float(np.min(balances))
        min_idx      = int(np.argmin(balances))
        peak_hour    = float(ts.iloc[min_idx]["hour"])
        max_usage    = max(0.0, self._opening - min_balance)
        closing      = float(balances[-1])

        sent     = float(sum(-p.amount for p in payments if p.amount < 0))
        received = float(sum( p.amount for p in payments if p.amount > 0))

        util = max_usage / self._opening if self._opening > 0.0 else 0.0

        return Intraday_Result(
            opening_balance=self._opening,
            closing_balance=closing,
            minimum_balance=min_balance,
            maximum_usage=max_usage,
            utilisation_rate=util,
            total_payments_sent=sent,
            total_payments_received=received,
            peak_hour=peak_hour,
            time_series=ts,
        )

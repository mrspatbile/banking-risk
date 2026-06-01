"""
Date utilities — QuantLib date conversion.

QuantLib is imported lazily so that modules importing from here do not
carry a hard QuantLib dependency at import time.
"""

import datetime


def to_ql_date(date):
    """Convert a date to a QuantLib Date.

    Parameters
    ----------
    date : ql.Date | datetime.date | datetime.datetime | str
        Strings must be ISO format ("2026-06-01").

    Returns
    -------
    QuantLib.Date
    """
    import QuantLib as ql

    if isinstance(date, ql.Date):
        return date
    if isinstance(date, str):
        d = datetime.date.fromisoformat(date)
        return ql.Date(d.day, d.month, d.year)
    if isinstance(date, (datetime.date, datetime.datetime)):
        return ql.Date(date.day, date.month, date.year)
    raise TypeError(f"Unsupported date type: {type(date)}")

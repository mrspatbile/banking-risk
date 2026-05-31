"""
Test helpers shared across the test suite.

Import directly: from tests.helpers import Flat_Curve
"""

import math


class Flat_Curve:
    """Flat zero curve stub — satisfies Zero_Curve protocol without QuantLib."""

    def __init__(self, rate: float = 0.03):
        self.rate = rate

    def zero_rate(self, t_years: float) -> float:
        return self.rate

    def discount(self, t_years: float) -> float:
        return math.exp(-self.rate * max(t_years, 0.0))

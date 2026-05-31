"""
Shared fixtures and stubs for the banking_risk test suite.

Flat_Curve satisfies the Zero_Curve protocol without QuantLib so all
calculator tests run in CI without a QuantLib install.
"""

import pytest
import numpy as np
from tests.helpers import Flat_Curve

from banking_risk.irrbb.book import Position, Standard_Banking_Book
from banking_risk.irrbb.constants import PositionType
from banking_risk.irrbb.scenarios import Scenario_Set


# ── Position helpers ──────────────────────────────────────────────────────────

def fixed_asset(
    name: str = "loan",
    notional: float = 1_000_000,
    maturity_months: int = 60,
    rate: float = 0.05,
    currency: str = "EUR",
) -> Position:
    return Position(
        name=name,
        type=PositionType.ASSET,
        currency=currency,
        notional=notional,
        maturity_months=maturity_months,
        coupon_months=0,
        rate=rate,
        floating=False,
    )


def floating_liability(
    name: str = "deposit",
    notional: float = 800_000,
    maturity_months: int = 120,
    repricing_tenor_months: int = 3,
    rate: float = 0.02,
    currency: str = "EUR",
) -> Position:
    return Position(
        name=name,
        type=PositionType.LIABILITY,
        currency=currency,
        notional=notional,
        maturity_months=maturity_months,
        coupon_months=0,
        rate=rate,
        floating=True,
        repricing_tenor_months=repricing_tenor_months,
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def flat_curve():
    return Flat_Curve(rate=0.03)


@pytest.fixture
def simple_book():
    """Single fixed asset, single floating liability, balanced with 200k equity."""
    positions = [
        fixed_asset("loan", notional=1_000_000, maturity_months=60),
        floating_liability("deposit", notional=800_000, repricing_tenor_months=3),
    ]
    return Standard_Banking_Book(positions=positions, tier1_capital=200_000)


@pytest.fixture
def eur_scenarios():
    return Scenario_Set("EUR")


@pytest.fixture
def curves(flat_curve):
    return {"EUR": flat_curve}


@pytest.fixture
def scenarios():
    return {"EUR": Scenario_Set("EUR")}

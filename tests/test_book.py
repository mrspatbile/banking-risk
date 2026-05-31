import pytest
from banking_risk.irrbb.book import (
    NMD_Banking_Book,
    NMD_Portfolio,
    Position,
    Standard_Banking_Book,
)
from banking_risk.irrbb.constants import NMD_Type, PositionType


# ── Position ──────────────────────────────────────────────────────────────────

def test_position_type_coercion():
    p = Position("x", "asset", "EUR", 1000, 12, 0, 0.03, False)
    assert p.type == PositionType.ASSET


def test_position_invalid_type():
    with pytest.raises(ValueError):
        Position("x", "unknown", "EUR", 1000, 12, 0, 0.03, False)


def test_position_negative_notional():
    with pytest.raises(ValueError):
        Position("x", "asset", "EUR", -1000, 12, 0, 0.03, False)


def test_floating_requires_repricing_tenor():
    with pytest.raises(ValueError):
        Position("x", "asset", "EUR", 1000, 12, 0, 0.03, floating=True, repricing_tenor_months=0)


def test_signed_notional_asset():
    p = Position("x", PositionType.ASSET, "EUR", 1_000_000, 60, 0, 0.05, False)
    assert p.signed_notional == 1_000_000


def test_signed_notional_liability():
    p = Position("x", PositionType.LIABILITY, "EUR", 500_000, 60, 0, 0.02, False)
    assert p.signed_notional == -500_000


def test_next_repricing_fixed():
    p = Position("x", PositionType.ASSET, "EUR", 1000, 60, 0, 0.05, False)
    assert p.next_repricing_years == pytest.approx(5.0)


def test_next_repricing_floating():
    p = Position("x", PositionType.LIABILITY, "EUR", 1000, 120, 0, 0.02, True, repricing_tenor_months=3)
    assert p.next_repricing_years == pytest.approx(0.25)


# ── Standard_Banking_Book ─────────────────────────────────────────────────────

def test_book_totals(simple_book):
    assert simple_book.total_assets() == 1_000_000
    assert simple_book.total_liabilities() == 800_000
    assert simple_book.equity() == 200_000


def test_book_balance_check(simple_book):
    assert simple_book.balance_check()


def test_book_negative_tier1():
    with pytest.raises(ValueError):
        Standard_Banking_Book([], tier1_capital=-1)


def test_book_zero_tier1():
    with pytest.raises(ValueError):
        Standard_Banking_Book([], tier1_capital=0)


# ── NMD_Portfolio ─────────────────────────────────────────────────────────────

def test_nmd_retail_cap_exceeded():
    with pytest.raises(ValueError, match="cap"):
        NMD_Portfolio("d", "EUR", 1e6, "retail", 0.7, 5.1, 0.01)


def test_nmd_wholesale_cap_exceeded():
    with pytest.raises(ValueError, match="cap"):
        NMD_Portfolio("d", "EUR", 1e6, "wholesale", 0.7, 4.6, 0.01)


def test_nmd_invalid_stable_ratio():
    with pytest.raises(ValueError):
        NMD_Portfolio("d", "EUR", 1e6, "retail", 1.5, 3.0, 0.01)


def test_nmd_stable_volatile_volumes():
    nmd = NMD_Portfolio("d", "EUR", 1_000_000, "retail", 0.7, 3.0, 0.01)
    assert nmd.stable_volume == pytest.approx(700_000)
    assert nmd.volatile_volume == pytest.approx(300_000)


def test_nmd_type_coercion():
    nmd = NMD_Portfolio("d", "EUR", 1e6, "retail", 0.7, 3.0, 0.01)
    assert nmd.nmd_type == NMD_Type.RETAIL


# ── NMD_Banking_Book ──────────────────────────────────────────────────────────

def test_nmd_book_synthetic_positions():
    nmd = NMD_Portfolio("deposits", "EUR", 1_000_000, "retail", 0.7, 3.0, 0.01)
    book = NMD_Banking_Book(positions=[], nmd_portfolios=[nmd], tier1_capital=100_000)
    synthetic = book.positions()
    assert len(synthetic) == 2   # volatile + stable
    names = [p.name for p in synthetic]
    assert "deposits_volatile" in names
    assert "deposits_stable" in names


def test_nmd_book_all_liabilities():
    nmd = NMD_Portfolio("deposits", "EUR", 1_000_000, "retail", 0.7, 3.0, 0.01)
    book = NMD_Banking_Book(positions=[], nmd_portfolios=[nmd], tier1_capital=100_000)
    for p in book.positions():
        assert p.type == PositionType.LIABILITY


def test_nmd_volatile_is_floating():
    nmd = NMD_Portfolio("deposits", "EUR", 1_000_000, "retail", 0.7, 3.0, 0.01)
    book = NMD_Banking_Book(positions=[], nmd_portfolios=[nmd], tier1_capital=100_000)
    volatile = next(p for p in book.positions() if "volatile" in p.name)
    assert volatile.floating is True


def test_nmd_stable_is_fixed():
    nmd = NMD_Portfolio("deposits", "EUR", 1_000_000, "retail", 0.7, 3.0, 0.01)
    book = NMD_Banking_Book(positions=[], nmd_portfolios=[nmd], tier1_capital=100_000)
    stable = next(p for p in book.positions() if "stable" in p.name)
    assert stable.floating is False
    assert stable.maturity_months == 36   # 3Y = 36 months

import pytest
import numpy as np
from banking_risk.irrbb.book import Position, Standard_Banking_Book
from banking_risk.irrbb.constants import EBA_BUCKET_LABELS, PositionType
from banking_risk.irrbb.gap import Repricing_Gap


def _fixed_asset(maturity_months, notional=1_000_000):
    return Position(
        name=f"asset_{maturity_months}m", type=PositionType.ASSET, currency="EUR",
        notional=notional, maturity_months=maturity_months,
        coupon_months=0, rate=0.05, floating=False,
    )


def _floating_liability(repricing_tenor_months, notional=800_000):
    return Position(
        name=f"liability_{repricing_tenor_months}m", type=PositionType.LIABILITY,
        currency="EUR", notional=notional, maturity_months=120,
        coupon_months=0, rate=0.02, floating=True,
        repricing_tenor_months=repricing_tenor_months,
    )


def _book(positions, tier1=100_000):
    return Standard_Banking_Book(positions, tier1_capital=tier1)


# ── Shape and structure ───────────────────────────────────────────────────────

def test_gap_has_19_rows():
    book = _book([_fixed_asset(60)])
    df = Repricing_Gap(book).compute()
    assert len(df) == 19


def test_gap_index_matches_labels():
    book = _book([_fixed_asset(60)])
    df = Repricing_Gap(book).compute()
    assert list(df.index) == EBA_BUCKET_LABELS


def test_gap_columns():
    book = _book([_fixed_asset(60)])
    df = Repricing_Gap(book).compute()
    assert set(df.columns) >= {"assets", "liabilities", "gap", "cumulative_gap"}


# ── Bucket slotting ───────────────────────────────────────────────────────────

def test_fixed_asset_slotted_at_maturity():
    """60M fixed asset → 5Y bucket (4-5Y range)."""
    book = _book([_fixed_asset(maturity_months=60)])
    df = Repricing_Gap(book).compute()
    assert df.loc["5Y", "assets"] == 1_000_000
    # All other asset buckets should be zero
    other_buckets = [b for b in EBA_BUCKET_LABELS if b != "5Y"]
    assert df.loc[other_buckets, "assets"].sum() == pytest.approx(0.0)


def test_floating_liability_slotted_at_repricing_tenor():
    """3M floating liability → 3M bucket."""
    book = _book([_floating_liability(repricing_tenor_months=3)])
    df = Repricing_Gap(book).compute()
    assert df.loc["3M", "liabilities"] > 0
    # 3M bucket liabilities include the deposit (not equity, which goes to >20Y)
    assert df.loc["3M", "liabilities"] == pytest.approx(800_000)


def test_equity_slotted_in_last_bucket():
    """Tier 1 equity always appears in the >20Y liability bucket."""
    tier1 = 100_000
    book = _book([], tier1=tier1)
    df = Repricing_Gap(book).compute()
    assert df.loc[">20Y", "liabilities"] == pytest.approx(tier1)


def test_equity_does_not_affect_other_buckets():
    book = _book([], tier1=100_000)
    df = Repricing_Gap(book).compute()
    other = [b for b in EBA_BUCKET_LABELS if b != ">20Y"]
    assert df.loc[other, "liabilities"].sum() == pytest.approx(0.0)


# ── Gap arithmetic ────────────────────────────────────────────────────────────

def test_gap_equals_assets_minus_liabilities():
    book = _book([_fixed_asset(60), _floating_liability(3)])
    df = Repricing_Gap(book).compute()
    assert np.allclose(df["gap"], df["assets"] - df["liabilities"])


def test_cumulative_gap_is_running_sum():
    book = _book([_fixed_asset(60), _floating_liability(3)])
    df = Repricing_Gap(book).compute()
    assert np.allclose(df["cumulative_gap"], df["gap"].cumsum())


def test_empty_book_all_zeros_except_equity():
    tier1 = 50_000
    book = _book([], tier1=tier1)
    df = Repricing_Gap(book).compute()
    assert df["assets"].sum() == pytest.approx(0.0)
    assert df.loc[">20Y", "liabilities"] == pytest.approx(tier1)

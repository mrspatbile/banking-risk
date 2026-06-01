import pytest
from banking_risk.liquidity.funding_gap import (
    Funding_Item, Funding_Gap_Analyser, BUCKET_LABELS, _assign_bucket,
)

_ANA = Funding_Gap_Analyser()


def _asset(name="A", amount=100, days=30):
    return Funding_Item(name, amount, days, "asset")

def _liab(name="L", amount=100, days=30, cpty=None):
    return Funding_Item(name, amount, days, "liability", counterparty=cpty)


# ── Bucket assignment ─────────────────────────────────────────────────────────

def test_overnight_bucket():
    assert _assign_bucket(1) == "Overnight"

def test_2_to_7_day_bucket():
    assert _assign_bucket(7) == "2-7D"

def test_30_day_bucket():
    assert _assign_bucket(30) == "8-30D"

def test_1_year_bucket():
    assert _assign_bucket(365) == "181-365D"

def test_beyond_5y_bucket():
    assert _assign_bucket(3000) == ">5Y"


# ── Invalid item_type ─────────────────────────────────────────────────────────

def test_invalid_item_type_raises():
    with pytest.raises(ValueError):
        Funding_Item("x", 100, 30, "something_else")


# ── Gap calculation ───────────────────────────────────────────────────────────

def test_positive_gap_when_assets_exceed_liabs():
    result = _ANA.compute([_asset("A", 100, 30), _liab("L", 60, 30)])
    assert result.gap_table.loc["8-30D", "gap"] == pytest.approx(40.0)


def test_negative_gap_when_liabs_exceed_assets():
    result = _ANA.compute([_asset("A", 40, 30), _liab("L", 80, 30)])
    assert result.gap_table.loc["8-30D", "gap"] == pytest.approx(-40.0)


def test_cumulative_gap_is_running_sum():
    items = [
        _asset("A1", 100, 30),   # 8-30D: gap = +100
        _liab("L1", 150, 90),    # 31-90D: gap = -150
    ]
    result = _ANA.compute(items)
    assert result.gap_table.loc["8-30D",  "cumulative_gap"] == pytest.approx(100.0)
    assert result.gap_table.loc["31-90D", "cumulative_gap"] == pytest.approx(-50.0)


def test_all_bucket_labels_present():
    result = _ANA.compute([])
    assert list(result.gap_table.index) == BUCKET_LABELS


# ── Rollover risk ─────────────────────────────────────────────────────────────

def test_rollover_30d_counts_liabilities_only():
    items = [
        _liab("L1", 200, 1),    # overnight
        _liab("L2", 100, 7),    # 2-7D
        _liab("L3", 300, 180),  # 91-180D — outside 30d
        _asset("A1", 500, 30),  # assets don't count
    ]
    result = _ANA.compute(items)
    assert result.rollover_30d == pytest.approx(300.0)  # 200 + 100


def test_rollover_ratio_30d():
    items = [_liab("L1", 100, 1), _liab("L2", 300, 365)]
    result = _ANA.compute(items)
    assert result.rollover_ratio_30d == pytest.approx(100 / 400)


def test_rollover_ratio_zero_when_no_liabilities():
    result = _ANA.compute([_asset()])
    assert result.rollover_ratio_30d == pytest.approx(0.0)


# ── Counterparty concentration ────────────────────────────────────────────────

def test_concentration_groups_by_counterparty():
    items = [
        _liab("L1", 200, 30, cpty="BankA"),
        _liab("L2", 100, 90, cpty="BankA"),
        _liab("L3", 150, 30, cpty="BankB"),
    ]
    result = _ANA.compute(items)
    assert result.concentration is not None
    assert result.concentration["BankA"] == pytest.approx(300.0)
    assert result.concentration["BankB"] == pytest.approx(150.0)


def test_concentration_none_when_no_counterparty():
    result = _ANA.compute([_liab("L1", 100, 30)])
    assert result.concentration is None


def test_concentration_sorted_descending():
    items = [
        _liab("L1", 50,  30, cpty="Small"),
        _liab("L2", 300, 30, cpty="Large"),
    ]
    result = _ANA.compute(items)
    assert result.concentration.index[0] == "Large"

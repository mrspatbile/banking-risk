import pytest
from banking_risk.liquidity.intraday import Intraday_Payment, Intraday_Monitor


def _mon(opening=100):
    return Intraday_Monitor(opening_balance=opening)

def _pmt(name="P", hour=9.0, amount=-10.0):
    return Intraday_Payment(name, hour, amount)


# ── Max usage and utilisation ─────────────────────────────────────────────────

def test_max_usage_single_outflow():
    result = _mon(100).compute([_pmt(amount=-30)])
    assert result.maximum_usage == pytest.approx(30.0)
    assert result.utilisation_rate == pytest.approx(0.30)


def test_max_usage_zero_when_only_inflows():
    result = _mon(100).compute([_pmt(amount=50)])
    assert result.maximum_usage == pytest.approx(0.0)


def test_max_usage_is_peak_not_total():
    # Outflow 40, then inflow 20, then outflow 10
    # Balances: 60, 80, 70 → min = 60 → usage = 40 (not 50)
    pmts = [
        Intraday_Payment("A", 9.0, -40.0),
        Intraday_Payment("B", 10.0, 20.0),
        Intraday_Payment("C", 11.0, -10.0),
    ]
    result = _mon(100).compute(pmts)
    assert result.maximum_usage == pytest.approx(40.0)


def test_utilisation_zero_when_opening_zero():
    result = Intraday_Monitor(0).compute([_pmt(amount=-10)])
    assert result.utilisation_rate == pytest.approx(0.0)


# ── Balances ──────────────────────────────────────────────────────────────────

def test_closing_balance():
    pmts = [Intraday_Payment("A", 9.0, -30.0), Intraday_Payment("B", 14.0, 10.0)]
    result = _mon(100).compute(pmts)
    assert result.closing_balance == pytest.approx(80.0)


def test_minimum_balance_can_go_negative():
    result = _mon(50).compute([_pmt(amount=-80)])
    assert result.minimum_balance == pytest.approx(-30.0)
    assert result.maximum_usage == pytest.approx(80.0)


# ── Totals ────────────────────────────────────────────────────────────────────

def test_total_sent_and_received():
    pmts = [
        Intraday_Payment("A", 9.0,  -40.0),
        Intraday_Payment("B", 10.0,  25.0),
        Intraday_Payment("C", 11.0, -15.0),
    ]
    result = _mon(100).compute(pmts)
    assert result.total_payments_sent     == pytest.approx(55.0)
    assert result.total_payments_received == pytest.approx(25.0)


# ── Time series ───────────────────────────────────────────────────────────────

def test_time_series_sorted_by_hour():
    pmts = [
        Intraday_Payment("Late",  15.0, -10.0),
        Intraday_Payment("Early",  8.0,  20.0),
    ]
    result = _mon(100).compute(pmts)
    hours = result.time_series["hour"].tolist()
    assert hours == sorted(hours)


def test_time_series_running_balance_correct():
    pmts = [Intraday_Payment("A", 9.0, -20.0)]
    result = _mon(100).compute(pmts)
    assert result.time_series["running_balance"].iloc[0] == pytest.approx(80.0)


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_payments():
    result = _mon(100).compute([])
    assert result.maximum_usage == pytest.approx(0.0)
    assert result.closing_balance == pytest.approx(100.0)
    assert len(result.time_series) == 0


def test_peak_hour_recorded():
    pmts = [
        Intraday_Payment("A", 9.0,  -60.0),
        Intraday_Payment("B", 14.0,  10.0),
    ]
    result = _mon(100).compute(pmts)
    assert result.peak_hour == pytest.approx(9.0)

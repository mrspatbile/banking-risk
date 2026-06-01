import pytest
from banking_risk.liquidity.ewi import (
    EWI, EWI_Status, EWI_Monitor,
    lcr_indicator, nsfr_indicator, encumbrance_indicator,
    rollover_indicator, intraday_utilisation_indicator,
)

_MON = EWI_Monitor()


# ── EWI.status — below_is_bad ─────────────────────────────────────────────────

def test_below_is_bad_green():
    ind = EWI("x", value=150, green_threshold=130, amber_threshold=100, direction="below_is_bad")
    assert ind.status == EWI_Status.GREEN


def test_below_is_bad_amber():
    ind = EWI("x", value=115, green_threshold=130, amber_threshold=100, direction="below_is_bad")
    assert ind.status == EWI_Status.AMBER


def test_below_is_bad_red():
    ind = EWI("x", value=90, green_threshold=130, amber_threshold=100, direction="below_is_bad")
    assert ind.status == EWI_Status.RED


# ── EWI.status — above_is_bad ─────────────────────────────────────────────────

def test_above_is_bad_green():
    ind = EWI("x", value=20, green_threshold=30, amber_threshold=50, direction="above_is_bad")
    assert ind.status == EWI_Status.GREEN


def test_above_is_bad_amber():
    ind = EWI("x", value=40, green_threshold=30, amber_threshold=50, direction="above_is_bad")
    assert ind.status == EWI_Status.AMBER


def test_above_is_bad_red():
    ind = EWI("x", value=60, green_threshold=30, amber_threshold=50, direction="above_is_bad")
    assert ind.status == EWI_Status.RED


def test_invalid_direction_raises():
    with pytest.raises(ValueError, match="direction"):
        EWI("x", value=10, green_threshold=5, amber_threshold=8, direction="sideways")


# ── Factory helpers ───────────────────────────────────────────────────────────

def test_lcr_indicator_green_above_130():
    assert lcr_indicator(1.40).status == EWI_Status.GREEN


def test_lcr_indicator_amber_between_100_and_130():
    assert lcr_indicator(1.20).status == EWI_Status.AMBER


def test_lcr_indicator_red_below_100():
    assert lcr_indicator(0.95).status == EWI_Status.RED


def test_nsfr_indicator_green():
    assert nsfr_indicator(1.15).status == EWI_Status.GREEN


def test_encumbrance_indicator_green():
    assert encumbrance_indicator(0.25).status == EWI_Status.GREEN


def test_encumbrance_indicator_red():
    assert encumbrance_indicator(0.60).status == EWI_Status.RED


def test_rollover_indicator_amber():
    assert rollover_indicator(0.20).status == EWI_Status.AMBER


def test_intraday_indicator_amber():
    assert intraday_utilisation_indicator(0.65).status == EWI_Status.AMBER


# ── EWI_Monitor.evaluate ─────────────────────────────────────────────────────

def test_overall_status_worst_indicator():
    indicators = [
        lcr_indicator(1.40),         # green
        nsfr_indicator(1.05),        # amber
        encumbrance_indicator(0.20), # green
    ]
    result = _MON.evaluate(indicators)
    assert result.overall_status == EWI_Status.AMBER


def test_overall_status_red_when_any_red():
    indicators = [
        lcr_indicator(1.40),    # green
        lcr_indicator(0.90),    # red
    ]
    result = _MON.evaluate(indicators)
    assert result.overall_status == EWI_Status.RED


def test_overall_status_green_when_all_green():
    indicators = [lcr_indicator(1.50), nsfr_indicator(1.20)]
    result = _MON.evaluate(indicators)
    assert result.overall_status == EWI_Status.GREEN


def test_counts_correct():
    indicators = [
        lcr_indicator(1.40),         # green
        nsfr_indicator(1.05),        # amber
        encumbrance_indicator(0.60), # red
    ]
    result = _MON.evaluate(indicators)
    assert result.green_count == 1
    assert result.amber_count == 1
    assert result.red_count   == 1


def test_dashboard_has_all_indicators():
    indicators = [lcr_indicator(1.30), nsfr_indicator(1.10), encumbrance_indicator(0.25)]
    result = _MON.evaluate(indicators)
    assert len(result.indicators) == 3


def test_empty_dashboard_is_green():
    result = _MON.evaluate([])
    assert result.overall_status == EWI_Status.GREEN
    assert result.green_count == result.amber_count == result.red_count == 0

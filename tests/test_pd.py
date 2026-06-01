import math
import pytest

from banking_risk.credit_risk.pd import (
    RATING_PD_TABLE,
    PD_Estimate,
    Rating_PD_Model,
    Logistic_PD_Model,
    _PD_FLOOR,
)

_RATING = Rating_PD_Model()


# ── Rating_PD_Model ───────────────────────────────────────────────────────────

def test_bbb_anchor_value():
    est = _RATING.predict("BBB")
    assert est.pd == pytest.approx(0.0025)
    assert est.rating == "BBB"
    assert est.model == "rating_table"


def test_case_insensitive():
    assert _RATING.predict("bbb").pd == _RATING.predict("BBB").pd


def test_d_is_one():
    est = _RATING.predict("D")
    assert est.pd == pytest.approx(1.0)


def test_aaa_at_floor():
    est = _RATING.predict("AAA")
    assert est.pd == pytest.approx(_PD_FLOOR)


def test_pd_floor_applied_to_all_non_default():
    for rating, raw_pd in RATING_PD_TABLE.items():
        if rating == "D":
            continue
        est = _RATING.predict(rating)
        assert est.pd >= _PD_FLOOR, f"PD floor violated for {rating}"


def test_pd_monotone_roughly_by_rating():
    # investment grade PD < speculative grade PD
    ig = _RATING.predict("BBB").pd
    sg = _RATING.predict("BB").pd
    assert ig < sg


def test_unknown_rating_raises():
    with pytest.raises(ValueError, match="Unknown rating"):
        _RATING.predict("ZZZ")


def test_pd_estimate_log_odds_is_none_for_rating_model():
    est = _RATING.predict("A")
    assert est.log_odds is None


# ── Logistic_PD_Model ─────────────────────────────────────────────────────────

def test_zero_intercept_no_features_returns_half():
    model = Logistic_PD_Model(coefficients={}, intercept=0.0)
    est   = model.predict({})
    assert est.pd == pytest.approx(0.5)


def test_large_negative_log_odds_clamped_to_floor():
    model = Logistic_PD_Model(coefficients={"x": 1.0}, intercept=-1000.0)
    est   = model.predict({"x": 0.0})
    assert est.pd == pytest.approx(_PD_FLOOR)


def test_large_positive_log_odds_approaches_one():
    model = Logistic_PD_Model(coefficients={"x": 1.0}, intercept=1000.0)
    est   = model.predict({"x": 0.0})
    assert est.pd == pytest.approx(1.0)


def test_positive_coefficient_increases_pd():
    model    = Logistic_PD_Model(coefficients={"leverage": 0.5}, intercept=-3.0)
    pd_low   = model.predict({"leverage": 1.0}).pd
    pd_high  = model.predict({"leverage": 5.0}).pd
    assert pd_high > pd_low


def test_log_odds_stored():
    model = Logistic_PD_Model(coefficients={"x": 2.0}, intercept=1.0)
    est   = model.predict({"x": 3.0})
    assert est.log_odds == pytest.approx(1.0 + 2.0 * 3.0)


def test_logistic_model_name():
    model = Logistic_PD_Model(coefficients={})
    assert model.predict({}).model == "logistic"


def test_unknown_feature_ignored():
    model = Logistic_PD_Model(coefficients={"leverage": 1.0}, intercept=0.0)
    est_known   = model.predict({"leverage": 2.0})
    est_extra   = model.predict({"leverage": 2.0, "unknown_field": 99.0})
    assert est_known.pd == pytest.approx(est_extra.pd)


def test_pd_in_valid_range():
    model = Logistic_PD_Model(coefficients={"x": 1.0}, intercept=0.0)
    for x in [-100, -10, -1, 0, 1, 10, 100]:
        est = model.predict({"x": float(x)})
        assert _PD_FLOOR <= est.pd <= 1.0

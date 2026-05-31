import math
import pytest
from banking_risk.irrbb.constants import (
    EBA_BUCKET_BOUNDARIES,
    EBA_BUCKET_LABELS,
    EBA_BUCKET_MIDPOINTS,
    EBA_SHOCKS,
    NMD_REPRICING_CAP,
    NMD_Type,
    POST_SHOCK_FLOOR_INTERCEPT,
    POST_SHOCK_FLOOR_SLOPE,
    SOT_EVE_THRESHOLD,
    SOT_NII_THRESHOLD,
)


def test_bucket_count():
    assert len(EBA_BUCKET_LABELS) == 19
    assert len(EBA_BUCKET_MIDPOINTS) == 19
    assert len(EBA_BUCKET_BOUNDARIES) == 20   # 19 buckets = 20 boundaries


def test_boundaries_strictly_increasing():
    finite = [b for b in EBA_BUCKET_BOUNDARIES if b != float("inf")]
    assert finite == sorted(finite)
    assert EBA_BUCKET_BOUNDARIES[-1] == float("inf")


def test_midpoints_within_boundaries():
    for i, mid in enumerate(EBA_BUCKET_MIDPOINTS[:-1]):   # skip >20Y
        lo, hi = EBA_BUCKET_BOUNDARIES[i], EBA_BUCKET_BOUNDARIES[i + 1]
        assert lo < mid < hi, f"Midpoint {mid} not in ({lo}, {hi}) for bucket {i}"


def test_last_midpoint_is_25():
    assert EBA_BUCKET_MIDPOINTS[-1] == 25.0


def test_midpoints_derived_from_boundaries():
    for i, mid in enumerate(EBA_BUCKET_MIDPOINTS[:-1]):
        lo, hi = EBA_BUCKET_BOUNDARIES[i], EBA_BUCKET_BOUNDARIES[i + 1]
        assert mid == pytest.approx((lo + hi) / 2)


def test_sot_thresholds():
    assert SOT_EVE_THRESHOLD == 0.15
    assert SOT_NII_THRESHOLD == 0.05


def test_floor_parameters():
    assert POST_SHOCK_FLOOR_INTERCEPT == pytest.approx(-0.015)
    assert POST_SHOCK_FLOOR_SLOPE == pytest.approx(0.0003)


def test_floor_at_zero_maturity():
    floor = POST_SHOCK_FLOOR_INTERCEPT + POST_SHOCK_FLOOR_SLOPE * 0
    assert floor == pytest.approx(-0.015)


def test_floor_at_50y():
    floor = POST_SHOCK_FLOOR_INTERCEPT + POST_SHOCK_FLOOR_SLOPE * 50
    assert floor == pytest.approx(-0.015 + 0.0003 * 50)


def test_eba_shocks_currencies():
    for ccy in ("EUR", "USD", "GBP", "JPY", "CHF"):
        assert ccy in EBA_SHOCKS


def test_eba_shocks_keys():
    required = {"parallel_up", "parallel_down", "short_up", "short_down", "delta_s", "delta_l"}
    for ccy, params in EBA_SHOCKS.items():
        assert required == set(params.keys()), f"Missing keys for {ccy}"


def test_eba_shocks_sign_convention():
    for ccy, p in EBA_SHOCKS.items():
        assert p["parallel_up"] > 0,   f"{ccy} parallel_up should be positive"
        assert p["parallel_down"] < 0, f"{ccy} parallel_down should be negative"
        assert p["short_up"] > 0,      f"{ccy} short_up should be positive"
        assert p["short_down"] < 0,    f"{ccy} short_down should be negative"


def test_nmd_caps():
    assert NMD_REPRICING_CAP[NMD_Type.RETAIL] == 5.0
    assert NMD_REPRICING_CAP[NMD_Type.WHOLESALE] == 4.5

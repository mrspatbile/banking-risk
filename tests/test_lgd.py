import pytest

from banking_risk.credit_risk.lgd import (
    Collateral_Type,
    LGD_FLOORS,
    LGD_Estimate,
    CRR_LGD_Model,
    _LGD_UNSECURED,
)

_MODEL = CRR_LGD_Model()


# ── Unsecured / subordinated (no collateral benefit) ─────────────────────────

def test_unsecured_lgd_equals_floor():
    est = _MODEL.estimate(1_000_000, 0, Collateral_Type.UNSECURED)
    assert est.lgd == pytest.approx(LGD_FLOORS[Collateral_Type.UNSECURED])


def test_subordinated_lgd_equals_floor():
    est = _MODEL.estimate(1_000_000, 0, Collateral_Type.SUBORDINATED)
    assert est.lgd == pytest.approx(LGD_FLOORS[Collateral_Type.SUBORDINATED])


def test_unsecured_coverage_is_zero():
    est = _MODEL.estimate(1_000_000, 500_000, Collateral_Type.UNSECURED)
    assert est.coverage_ratio == pytest.approx(0.0)


# ── No collateral → LGD_unsecured ────────────────────────────────────────────

def test_no_collateral_residential_lgd_is_lgd_unsecured():
    est = _MODEL.estimate(1_000_000, 0.0, Collateral_Type.RESIDENTIAL_RE)
    assert est.lgd == pytest.approx(_LGD_UNSECURED)


def test_no_collateral_commercial_lgd_is_lgd_unsecured():
    est = _MODEL.estimate(1_000_000, 0.0, Collateral_Type.COMMERCIAL_RE)
    assert est.lgd == pytest.approx(_LGD_UNSECURED)


# ── Full collateral → floor ───────────────────────────────────────────────────

def test_fully_collateralised_residential_re_at_floor():
    # C_net >= EAD → coverage = 1.0 → LGD = floor
    est = _MODEL.estimate(1_000_000, 2_000_000, Collateral_Type.RESIDENTIAL_RE)
    assert est.lgd == pytest.approx(LGD_FLOORS[Collateral_Type.RESIDENTIAL_RE])
    assert est.coverage_ratio == pytest.approx(1.0)


def test_fully_collateralised_commercial_re_at_floor():
    est = _MODEL.estimate(1_000_000, 1_500_000, Collateral_Type.COMMERCIAL_RE)
    assert est.lgd == pytest.approx(LGD_FLOORS[Collateral_Type.COMMERCIAL_RE])


def test_fully_collateralised_financial_at_floor():
    est = _MODEL.estimate(1_000_000, 1_000_000, Collateral_Type.FINANCIAL)
    assert est.lgd == pytest.approx(LGD_FLOORS[Collateral_Type.FINANCIAL])
    assert est.lgd == pytest.approx(0.0)


# ── Partial collateral ────────────────────────────────────────────────────────

def test_partial_collateral_lgd_between_floor_and_unsecured():
    # 50 % coverage → LGD between floor (0.10) and LGD_unsecured (0.45)
    est = _MODEL.estimate(1_000_000, 500_000, Collateral_Type.RESIDENTIAL_RE)
    floor = LGD_FLOORS[Collateral_Type.RESIDENTIAL_RE]
    assert floor <= est.lgd <= _LGD_UNSECURED
    assert est.coverage_ratio == pytest.approx(0.5)


def test_higher_collateral_lower_lgd():
    low  = _MODEL.estimate(1_000_000,   200_000, Collateral_Type.RESIDENTIAL_RE).lgd
    high = _MODEL.estimate(1_000_000,   800_000, Collateral_Type.RESIDENTIAL_RE).lgd
    assert high < low


# ── Haircut ───────────────────────────────────────────────────────────────────

def test_haircut_reduces_coverage():
    no_hc = _MODEL.estimate(1_000_000, 600_000, Collateral_Type.COMMERCIAL_RE, haircut=0.0)
    with_hc = _MODEL.estimate(1_000_000, 600_000, Collateral_Type.COMMERCIAL_RE, haircut=0.25)
    assert with_hc.coverage_ratio < no_hc.coverage_ratio


def test_haircut_increases_lgd():
    no_hc   = _MODEL.estimate(1_000_000, 600_000, Collateral_Type.RESIDENTIAL_RE, haircut=0.0).lgd
    with_hc = _MODEL.estimate(1_000_000, 600_000, Collateral_Type.RESIDENTIAL_RE, haircut=0.5).lgd
    assert with_hc > no_hc


# ── Regulatory constraints ────────────────────────────────────────────────────

def test_lgd_never_below_floor_for_all_types():
    for ct in Collateral_Type:
        est = _MODEL.estimate(1_000_000, 10_000_000, ct, haircut=0.0)
        assert est.lgd >= LGD_FLOORS[ct] - 1e-9, f"Floor violated for {ct}"


def test_lgd_estimate_fields():
    est = _MODEL.estimate(500_000, 300_000, Collateral_Type.RESIDENTIAL_RE, haircut=0.1)
    assert est.collateral_type == Collateral_Type.RESIDENTIAL_RE
    assert est.lgd_floor == pytest.approx(0.10)
    assert 0.0 <= est.coverage_ratio <= 1.0

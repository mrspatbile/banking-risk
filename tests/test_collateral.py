import pytest
from banking_risk.liquidity.collateral import (
    Collateral_Asset, Asset_Class, Collateral_Manager, HQLA_ELIGIBILITY,
)

_MGR = Collateral_Manager()


def _asset(name="Bond", cls=Asset_Class.GOVT_BOND, mv=100, enc=False, hc=0.0):
    return Collateral_Asset(name, cls, mv, encumbered=enc, haircut=hc)


# ── Encumbrance ───────────────────────────────────────────────────────────────

def test_encumbrance_ratio_single_pledged_asset():
    result = _MGR.analyse([_asset(enc=True)])
    assert result.encumbrance_ratio == pytest.approx(1.0)
    assert result.encumbered == pytest.approx(100.0)
    assert result.unencumbered == pytest.approx(0.0)


def test_encumbrance_ratio_zero_when_all_free():
    result = _MGR.analyse([_asset(enc=False)])
    assert result.encumbrance_ratio == pytest.approx(0.0)
    assert result.unencumbered == pytest.approx(100.0)


def test_partial_encumbrance():
    assets = [_asset("A", enc=True, mv=60), _asset("B", enc=False, mv=40)]
    result = _MGR.analyse(assets)
    assert result.encumbrance_ratio == pytest.approx(0.60)
    assert result.total_assets == pytest.approx(100.0)


# ── HQLA eligibility ──────────────────────────────────────────────────────────

def test_govt_bond_is_level1():
    a = _asset(cls=Asset_Class.GOVT_BOND)
    assert a.effective_hqla_level == "1"


def test_covered_bond_is_level2a():
    a = _asset(cls=Asset_Class.COVERED_BOND)
    assert a.effective_hqla_level == "2A"


def test_corporate_bond_is_level2b():
    a = _asset(cls=Asset_Class.CORPORATE_BOND)
    assert a.effective_hqla_level == "2B"


def test_loan_is_not_hqla():
    a = _asset(cls=Asset_Class.LOAN)
    assert a.effective_hqla_level is None


def test_hqla_override():
    a = Collateral_Asset("x", Asset_Class.LOAN, 100, encumbered=False, hqla_level="1")
    assert a.effective_hqla_level == "1"


# ── Available HQLA ────────────────────────────────────────────────────────────

def test_encumbered_asset_excluded_from_hqla():
    a = _asset(cls=Asset_Class.GOVT_BOND, enc=True)
    result = _MGR.analyse([a])
    assert result.available_hqla == pytest.approx(0.0)


def test_unencumbered_hqla_included_after_haircut():
    a = Collateral_Asset("B", Asset_Class.COVERED_BOND, 100, encumbered=False, haircut=0.10)
    result = _MGR.analyse([a])
    # Covered bond = Level 2A, collateral value = 100 × (1 - 0.10) = 90
    assert result.available_hqla_by_level["2A"] == pytest.approx(90.0)


def test_available_hqla_sum_of_levels():
    assets = [
        Collateral_Asset("L1", Asset_Class.GOVT_BOND,    100, encumbered=False, haircut=0.0),
        Collateral_Asset("L2", Asset_Class.COVERED_BOND, 200, encumbered=False, haircut=0.0),
    ]
    result = _MGR.analyse(assets)
    assert result.available_hqla == pytest.approx(300.0)
    assert result.available_hqla_by_level["1"]  == pytest.approx(100.0)
    assert result.available_hqla_by_level["2A"] == pytest.approx(200.0)


# ── Available for repo ────────────────────────────────────────────────────────

def test_non_hqla_counted_in_repo_pool():
    assets = [
        _asset("L", cls=Asset_Class.LOAN, mv=200, enc=False),
    ]
    result = _MGR.analyse(assets)
    assert result.available_for_repo == pytest.approx(200.0)
    assert result.available_hqla == pytest.approx(0.0)


def test_encumbered_excluded_from_repo():
    assets = [
        _asset("A", mv=100, enc=False),
        _asset("B", mv=100, enc=True),
    ]
    result = _MGR.analyse(assets)
    assert result.available_for_repo == pytest.approx(100.0)


# ── Detail table ──────────────────────────────────────────────────────────────

def test_detail_has_all_assets():
    assets = [_asset("A"), _asset("B")]
    result = _MGR.analyse(assets)
    assert len(result.detail) == 2

import pytest
from banking_risk.liquidity.nsfr import (
    ASF_Item, ASF_Category, RSF_Item, RSF_Category,
    SA_NSFR_Calculator, ASF_FACTORS, RSF_FACTORS,
)

_CALC = SA_NSFR_Calculator()


def _asf(name="Tier1", amount=100, cat=ASF_Category.TIER1_CAPITAL):
    return ASF_Item(name, amount, category=cat)

def _rsf(name="Loan", amount=100, cat=RSF_Category.LOANS_CORPORATE_GT1Y):
    return RSF_Item(name, amount, category=cat)


# ── ASF factors ───────────────────────────────────────────────────────────────

def test_tier1_asf_factor_is_100pct():
    item = _asf(cat=ASF_Category.TIER1_CAPITAL)
    assert item.asf_factor == pytest.approx(1.0)


def test_retail_stable_lt6m_asf_factor():
    item = ASF_Item("x", 100, category=ASF_Category.RETAIL_STABLE_LT6M)
    assert item.asf_factor == pytest.approx(0.95)


def test_financial_inst_lt6m_asf_is_zero():
    item = ASF_Item("x", 100, category=ASF_Category.FIN_INSTITUTION_LT6M)
    assert item.asf_contribution == pytest.approx(0.0)


def test_custom_asf_factor():
    item = ASF_Item("x", 200, factor=0.70)
    assert item.asf_contribution == pytest.approx(140.0)


def test_asf_item_missing_type_raises():
    item = ASF_Item("x", 100)
    with pytest.raises(ValueError):
        _ = item.asf_factor


# ── RSF factors ───────────────────────────────────────────────────────────────

def test_cash_rsf_factor_is_zero():
    item = RSF_Item("x", 100, category=RSF_Category.CASH)
    assert item.rsf_contribution == pytest.approx(0.0)


def test_other_assets_rsf_is_100pct():
    item = RSF_Item("x", 500, category=RSF_Category.OTHER_ASSETS)
    assert item.rsf_contribution == pytest.approx(500.0)


def test_hqla_l1_rsf_5pct():
    item = RSF_Item("x", 1000, category=RSF_Category.HQLA_L1_UNENCUMBERED)
    assert item.rsf_contribution == pytest.approx(50.0)


def test_custom_rsf_factor():
    item = RSF_Item("x", 300, factor=0.30)
    assert item.rsf_contribution == pytest.approx(90.0)


# ── NSFR calculation ──────────────────────────────────────────────────────────

def test_nsfr_passes_when_asf_exceeds_rsf():
    asf = [_asf(amount=200, cat=ASF_Category.TIER1_CAPITAL)]
    rsf = [_rsf(amount=100, cat=RSF_Category.OTHER_ASSETS)]
    result = _CALC.compute(asf, rsf)
    assert result.nsfr == pytest.approx(2.0)
    assert result.passes is True


def test_nsfr_fails_when_rsf_exceeds_asf():
    asf = [_asf(amount=80,  cat=ASF_Category.TIER1_CAPITAL)]
    rsf = [_rsf(amount=100, cat=RSF_Category.OTHER_ASSETS)]
    result = _CALC.compute(asf, rsf)
    assert result.nsfr == pytest.approx(0.80)
    assert result.passes is False


def test_nsfr_formula():
    asf = [ASF_Item("a", 400, category=ASF_Category.RETAIL_STABLE_LT6M)]  # 380
    rsf = [RSF_Item("b", 300, category=RSF_Category.LOANS_CORPORATE_GT1Y)] # 195
    result = _CALC.compute(asf, rsf)
    assert result.available_stable_funding == pytest.approx(400 * 0.95)
    assert result.required_stable_funding  == pytest.approx(300 * 0.65)
    assert result.nsfr == pytest.approx((400 * 0.95) / (300 * 0.65), rel=1e-9)


def test_nsfr_empty_rsf_infinite():
    asf = [_asf()]
    result = _CALC.compute(asf, [])
    assert result.nsfr == float("inf")


def test_nsfr_totals_match_detail_sums():
    asf = [_asf("A1", 300), ASF_Item("A2", 200, category=ASF_Category.CORP_NON_FIN_LT6M)]
    rsf = [_rsf("R1", 100), RSF_Item("R2", 50, category=RSF_Category.HQLA_L2A_UNENCUMBERED)]
    result = _CALC.compute(asf, rsf)
    assert result.available_stable_funding == pytest.approx(result.asf_detail["asf"].sum())
    assert result.required_stable_funding  == pytest.approx(result.rsf_detail["rsf"].sum())

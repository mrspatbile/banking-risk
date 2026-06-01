import numpy as np
import pytest

from banking_risk.frtb.vertex_mapping import (
    FRTB_GIRR_VERTICES,
    FRTB_GIRR_LABELS,
    FRTB_CSR_VERTICES,
    FRTB_CSR_LABELS,
    FRTB_COMMODITY_VERTICES,
    FRTB_COMMODITY_LABELS,
    FRTB_EQUITY_VEGA_VERTICES,
    FRTB_FX_VEGA_VERTICES,
    GIRR_VEGA_VERTICES,
    nearest_vertex,
    assign_to_bucket,
)


# ── Vertex list lengths (CRR3 prescribed counts) ──────────────────────────────

def test_girr_vertices_count():
    assert len(FRTB_GIRR_VERTICES) == 10

def test_girr_labels_match_vertices():
    assert len(FRTB_GIRR_LABELS) == len(FRTB_GIRR_VERTICES)

def test_csr_vertices_count():
    assert len(FRTB_CSR_VERTICES) == 5

def test_csr_labels_match_vertices():
    assert len(FRTB_CSR_LABELS) == len(FRTB_CSR_VERTICES)

def test_commodity_vertices_count():
    assert len(FRTB_COMMODITY_VERTICES) == 7

def test_commodity_labels_match_vertices():
    assert len(FRTB_COMMODITY_LABELS) == len(FRTB_COMMODITY_VERTICES)

def test_equity_vega_vertices_count():
    assert len(FRTB_EQUITY_VEGA_VERTICES) == 5

def test_fx_vega_shares_girr_vega_vertices():
    assert FRTB_FX_VEGA_VERTICES == GIRR_VEGA_VERTICES


# ── nearest_vertex ────────────────────────────────────────────────────────────

def test_nearest_exact_match():
    assert nearest_vertex(5.0, FRTB_GIRR_VERTICES) == pytest.approx(5.0)

def test_nearest_rounds_to_closer():
    # 2.6Y → closer to 3Y than 2Y
    assert nearest_vertex(2.6, FRTB_GIRR_VERTICES) == pytest.approx(3.0)

def test_nearest_rounds_down():
    # 1.4Y → closer to 1Y than 2Y
    assert nearest_vertex(1.4, FRTB_GIRR_VERTICES) == pytest.approx(1.0)

def test_nearest_below_minimum_returns_first():
    assert nearest_vertex(0.1, FRTB_GIRR_VERTICES) == pytest.approx(0.25)

def test_nearest_above_maximum_returns_last():
    assert nearest_vertex(50.0, FRTB_GIRR_VERTICES) == pytest.approx(30.0)

def test_nearest_on_csr_vertices():
    # 2Y is equidistant between 1Y and 3Y — argmin picks 1Y (first match)
    assert nearest_vertex(2.0, FRTB_CSR_VERTICES) == pytest.approx(1.0)
    # 2.1Y is strictly closer to 3Y
    assert nearest_vertex(2.1, FRTB_CSR_VERTICES) == pytest.approx(3.0)


# ── assign_to_bucket ──────────────────────────────────────────────────────────

def test_assign_empty_returns_zeros():
    result = assign_to_bucket({}, FRTB_GIRR_VERTICES)
    assert np.all(result == 0.0)
    assert len(result) == len(FRTB_GIRR_VERTICES)

def test_assign_output_length_matches_vertices():
    result = assign_to_bucket({1.0: 10.0}, FRTB_CSR_VERTICES)
    assert len(result) == len(FRTB_CSR_VERTICES)

def test_assign_exact_vertex_lands_correctly():
    raw = {5.0: 100.0, 10.0: 200.0}
    result = assign_to_bucket(raw, FRTB_GIRR_VERTICES)
    idx_5  = FRTB_GIRR_VERTICES.index(5.0)
    idx_10 = FRTB_GIRR_VERTICES.index(10.0)
    assert result[idx_5]  == pytest.approx(100.0)
    assert result[idx_10] == pytest.approx(200.0)
    assert result.sum()   == pytest.approx(300.0)

def test_assign_off_grid_tenor_maps_to_nearest():
    # 2.6Y → nearest GIRR vertex is 3Y
    raw = {2.6: 50.0}
    result = assign_to_bucket(raw, FRTB_GIRR_VERTICES)
    idx_3 = FRTB_GIRR_VERTICES.index(3.0)
    assert result[idx_3] == pytest.approx(50.0)

def test_assign_multiple_tenors_aggregate_to_same_bucket():
    # 1.8Y and 2.3Y both map to nearest GIRR vertex 2Y
    raw = {1.8: 30.0, 2.3: 20.0}
    result = assign_to_bucket(raw, FRTB_GIRR_VERTICES)
    idx_2 = FRTB_GIRR_VERTICES.index(2.0)
    assert result[idx_2] == pytest.approx(50.0)

def test_assign_preserves_sign():
    raw = {5.0: -75.0}
    result = assign_to_bucket(raw, FRTB_GIRR_VERTICES)
    idx_5 = FRTB_GIRR_VERTICES.index(5.0)
    assert result[idx_5] == pytest.approx(-75.0)

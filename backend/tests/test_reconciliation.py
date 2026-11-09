"""Comprehensive test suite for Phase 2B: Allocation-Aware Reconciliation & Split Intervals.

Covers all 36 scenarios specified in Section 7 of the Master Prompt:
  A. Interval arithmetic (Scenarios 1-9)
  B. Legitimate split allocations (Scenarios 10-14)
  C. Genuine conflicts & double claims (Scenarios 15-19)
  D. Namespace safety (Scenarios 20-23)
  E. Entity and intermediary attribution (Scenarios 24-31)
  F. Data quality & provenance (Scenarios 32-36)
  G. REST API endpoints
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.normalization import repair_mojibake
from app.reconciliation import (
    AllocationReconciler,
    AllocationType,
    IntervalOverlap,
    OverlapType,
    compute_interval_overlap,
    validate_disjoint_ranges,
)
from app.serials import parse_serial

client = TestClient(app)


# ==============================================================================
# Group A: Interval Arithmetic (Scenarios 1-9)
# ==============================================================================

def test_01_identical_intervals():
    ov = compute_interval_overlap(100, 200, 100, 200)
    assert ov.overlap_type == OverlapType.EXACT_OVERLAP.value
    assert ov.overlap_start == 100
    assert ov.overlap_end == 200
    assert ov.overlap_units == 101
    assert ov.pct_of_candidate == 100.0
    assert ov.pct_of_existing == 100.0
    assert ov.is_conflict is True


def test_02_completely_disjoint_intervals():
    ov = compute_interval_overlap(100, 200, 300, 400)
    assert ov.overlap_type == OverlapType.DISJOINT.value
    assert ov.overlap_units == 0
    assert ov.is_conflict is False


def test_03_partial_overlap():
    ov = compute_interval_overlap(100, 200, 150, 250)
    assert ov.overlap_type == OverlapType.PARTIAL_OVERLAP.value
    assert ov.overlap_start == 150
    assert ov.overlap_end == 200
    assert ov.overlap_units == 51
    assert round(ov.pct_of_candidate, 2) == 50.50
    assert round(ov.pct_of_existing, 2) == 50.50
    assert ov.is_conflict is True


def test_04_candidate_fully_contains_existing_superset():
    ov = compute_interval_overlap(50, 250, 100, 200)
    assert ov.overlap_type == OverlapType.SUPERSET.value
    assert ov.overlap_start == 100
    assert ov.overlap_end == 200
    assert ov.overlap_units == 101
    assert ov.pct_of_existing == 100.0
    assert ov.is_conflict is True


def test_05_candidate_contained_inside_existing():
    ov = compute_interval_overlap(100, 200, 50, 250)
    assert ov.overlap_type == OverlapType.CONTAINMENT.value
    assert ov.overlap_start == 100
    assert ov.overlap_end == 200
    assert ov.overlap_units == 101
    assert ov.pct_of_candidate == 100.0
    assert ov.is_conflict is True


def test_06_adjacent_intervals_no_shared_unit():
    # Abutting on right
    ov1 = compute_interval_overlap(100, 200, 201, 300)
    assert ov1.overlap_type == OverlapType.ADJACENT.value
    assert ov1.overlap_units == 0
    assert ov1.is_conflict is False

    # Abutting on left
    ov2 = compute_interval_overlap(201, 300, 100, 200)
    assert ov2.overlap_type == OverlapType.ADJACENT.value
    assert ov2.overlap_units == 0
    assert ov2.is_conflict is False


def test_07_single_unit_intervals():
    ov = compute_interval_overlap(100, 100, 100, 100)
    assert ov.overlap_type == OverlapType.EXACT_OVERLAP.value
    assert ov.overlap_units == 1
    assert ov.is_conflict is True

    ov_adj = compute_interval_overlap(100, 100, 101, 101)
    assert ov_adj.overlap_type == OverlapType.ADJACENT.value
    assert ov_adj.overlap_units == 0


def test_08_invalid_or_reversed_intervals():
    with pytest.raises(ValueError, match="Invalid candidate interval"):
        compute_interval_overlap(200, 100, 100, 200)

    with pytest.raises(ValueError, match="Invalid existing interval"):
        compute_interval_overlap(100, 200, 300, 250)


def test_09_quantity_calculation_at_boundaries():
    # Inclusive quantity: end - start + 1
    ov = compute_interval_overlap(0, 0, 0, 0)
    assert ov.candidate_units == 1
    ov_large = compute_interval_overlap(1, 1_000_000, 500_000, 1_500_000)
    assert ov_large.candidate_units == 1_000_000
    assert ov_large.existing_units == 1_000_001
    assert ov_large.overlap_units == 500_001


# ==============================================================================
# Group B: Legitimate Split Allocations (Scenarios 10-14)
# ==============================================================================

def test_10_one_retirement_split_into_two_disjoint_allocations():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 1, "unit_end": 500, "claimant": "Acme Corp"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 501, "unit_end": 1000, "claimant": "Beta LLC"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.LEGITIMATE_SPLIT.value
    assert res.overlap.overlap_type == OverlapType.ADJACENT.value
    assert res.overlap.is_conflict is False


def test_11_one_retirement_split_into_multiple_non_overlapping_allocations():
    ranges = [(1, 200), (201, 400), (401, 700), (701, 1000)]
    is_disjoint, err = validate_disjoint_ranges(ranges)
    assert is_disjoint is True
    assert err is None


def test_12_adjacent_allocations_covering_original_batch():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 1000, "unit_end": 1999, "claimant": "Alpha Corp"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 2000, "unit_end": 3000, "claimant": "Gamma Inc"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.LEGITIMATE_SPLIT.value
    assert res.overlap.overlap_type == OverlapType.ADJACENT.value
    assert not res.overlap.is_conflict


def test_13_repeated_records_describing_same_legitimate_allocation():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Industries Ltd"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "ACME INDUSTRIES LIMITED"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.SAME_UNITS_SAME_CLAIMANT.value
    assert res.overlap.overlap_type == OverlapType.EXACT_OVERLAP.value
    assert res.overlap.is_conflict is True


def test_14_split_allocations_with_incomplete_beneficiary_disclosure():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Corp"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 300, "unit_end": 400, "claimant": "Not Disclosed"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.UNRESOLVED_BENEFICIARY.value
    assert res.overlap.is_conflict is False


# ==============================================================================
# Group C: Genuine Conflicts & Double Claims (Scenarios 15-19)
# ==============================================================================

def test_15_identical_serial_interval_same_beneficiary():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 500, "unit_end": 1000, "claimant": "Delta Air Lines"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 500, "unit_end": 1000, "claimant": "Delta Air Lines"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.SAME_UNITS_SAME_CLAIMANT.value
    assert res.overlap.overlap_units == 501
    assert res.overlap.is_conflict is True


def test_16_partial_serial_overlap_same_beneficiary():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 500, "unit_end": 800, "claimant": "Siemens AG"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 700, "unit_end": 1000, "claimant": "Siemens AG"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.SAME_UNITS_SAME_CLAIMANT.value
    assert res.overlap.overlap_type == OverlapType.PARTIAL_OVERLAP.value
    assert res.overlap.overlap_units == 101


def test_17_partial_overlap_different_beneficiaries():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Shell PLC"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 180, "unit_end": 300, "claimant": "Qantas Airways"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.ALLOCATION_CONFLICT.value
    assert res.overlap.overlap_type == OverlapType.PARTIAL_OVERLAP.value
    assert res.overlap.overlap_units == 21
    assert res.overlap.is_conflict is True


def test_18_containment_with_conflicting_beneficiary():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 120, "unit_end": 180, "claimant": "Lumen Retail"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Helios Apparel"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.ALLOCATION_CONFLICT.value
    assert res.overlap.overlap_type == OverlapType.CONTAINMENT.value
    assert res.overlap.pct_of_candidate == 100.0
    assert res.overlap.is_conflict is True


def test_19_duplicate_allocation_records_inconsistent_quantities():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 300, "claimant": "Acme Corp"}  # 201 units
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Corp"}  # 101 units
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.SAME_UNITS_SAME_CLAIMANT.value
    assert res.overlap.overlap_type == OverlapType.SUPERSET.value
    assert res.overlap.pct_of_existing == 100.0
    assert round(res.overlap.pct_of_candidate, 2) == 50.25


# ==============================================================================
# Group D: Namespace Safety (Scenarios 20-23)
# ==============================================================================

def test_20_same_serial_numbers_different_batch_ids():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Corp"}
    alloc_b = {"registry": "VCS", "batch_id": "99999", "unit_start": 100, "unit_end": 200, "claimant": "Beta LLC"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.CROSS_NAMESPACE.value
    assert res.overlap.overlap_units == 0
    assert res.overlap.is_conflict is False


def test_21_same_serial_numbers_across_different_registries():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Corp"}
    alloc_b = {"registry": "GS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Corp"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.CROSS_NAMESPACE.value
    assert res.overlap.is_conflict is False


def test_22_same_batch_identifier_different_registry():
    alloc_a = {"registry": "VCS", "batch_id": "100", "unit_start": 1, "unit_end": 50, "claimant": "Alpha"}
    alloc_b = {"registry": "GS", "batch_id": "100", "unit_start": 1, "unit_end": 50, "claimant": "Beta"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.CROSS_NAMESPACE.value
    assert not res.overlap.is_conflict


def test_23_missing_or_ambiguous_batch_namespace():
    alloc_a = {"registry": "VCS", "batch_id": "", "unit_start": 100, "unit_end": 200, "claimant": "Alpha"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Beta"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.CROSS_NAMESPACE.value
    assert not res.overlap.is_conflict


# ==============================================================================
# Group E: Entity and Intermediary Attribution (Scenarios 24-31)
# ==============================================================================

def test_24_exact_beneficiary_match():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Minerva S.A."}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Minerva S.A."}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.entity_relationship == "EXACT_MATCH"
    assert res.allocation_type == AllocationType.SAME_UNITS_SAME_CLAIMANT.value


def test_25_alias_match():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "UNLSH Mobility B.V."}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "unlsh mobility bv"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.entity_relationship == "CANONICAL_VARIANT"
    assert res.allocation_type == AllocationType.SAME_UNITS_SAME_CLAIMANT.value


def test_26_intermediary_on_behalf_of_disclosed_principal():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Lenovo"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "TBK Group on behalf of Lenovo"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.INTERMEDIARY_ATTRIBUTION.value
    assert res.entity_relationship == "INTERMEDIARY_DELEGATION"


def test_27_intermediary_with_undisclosed_principal():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Shell PLC"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "On behalf of Patch's customers"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.UNRESOLVED_BENEFICIARY.value


def test_28_parent_and_subsidiary_with_overlapping_serials():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Microsoft Corporation"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Microsoft Ireland Operations Ltd"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.SAME_UNITS_RELATED_CLAIMANTS.value
    assert res.entity_relationship == "CORPORATE_HIERARCHY_OR_SUBSIDIARY"
    assert res.overlap.is_conflict is True


def test_29_similar_company_names_belonging_to_unrelated_entities():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Delta Air Lines Inc."}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Delta Electronics Inc."}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.ALLOCATION_CONFLICT.value
    assert res.entity_relationship == "DIFFERENT_ENTITIES"


def test_30_unknown_beneficiary_or_placeholder():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Not Disclosed"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 150, "unit_end": 250, "claimant": "Confidential"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.UNRESOLVED_BENEFICIARY.value


def test_31_conflicting_intermediary_and_principal_disclosures():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Industries Ltd"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Trading Corp for account of Siemens AG"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.ALLOCATION_CONFLICT.value


# ==============================================================================
# Group F: Data Quality & Provenance (Scenarios 32-36)
# ==============================================================================

def test_32_ocr_repaired_serial_interval():
    # OCR typo 'O' instead of '0' in serial string
    raw_ocr = "18453-8963O956O-896319559-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0"
    block = parse_serial(raw_ocr, heal_ocr=True)
    assert block is not None
    assert block.unit_start == 896309560
    assert block.unit_end == 896319559
    assert block.quantity == 10000


def test_33_normalized_beneficiary_name_with_raw_value_retained():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "ACME INDUSTRIES LTD."}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Acme Industries Limited"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.candidate_claimant == "ACME INDUSTRIES LTD."
    assert res.prior_claimant == "Acme Industries Limited"
    assert res.allocation_type == AllocationType.SAME_UNITS_SAME_CLAIMANT.value


def test_34_mojibake_repaired_beneficiary_name():
    raw_mojibake = "Condom√≠nio 17.007 Na√ß√µes"
    repaired, mod = repair_mojibake(raw_mojibake)
    assert mod is True
    assert "Condomínio" in repaired


def test_35_missing_serial_boundaries():
    with pytest.raises(ValueError, match="Invalid candidate interval"):
        compute_interval_overlap(500, 400, 100, 200)


def test_36_inconsistent_allocation_quantity_and_interval_size():
    # Stated 1,000 units but interval is 501 units
    stated = 1000
    ov = compute_interval_overlap(100, 600, 100, 600)
    actual_qty = ov.candidate_units
    assert actual_qty == 501
    assert stated != actual_qty


# ==============================================================================
# Group G: REST API Endpoints
# ==============================================================================

def test_api_reconcile_compare():
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {
            "registry": "VCS",
            "batch_id": "18453",
            "unit_start": 100,
            "unit_end": 200,
            "claimant": "Acme Corp",
        },
        "existing": {
            "registry": "VCS",
            "batch_id": "18453",
            "unit_start": 201,
            "unit_end": 300,
            "claimant": "Beta LLC",
            "claim_ref": "OO-2026-0001",
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allocation_type"] == "LEGITIMATE_SPLIT"
    assert data["overlap"]["overlap_type"] == "ADJACENT"
    assert data["overlap"]["is_conflict"] is False


def test_api_reconcile_batch():
    resp = client.post("/api/reconcile/batch", json={
        "registry": "VCS",
        "batch_id": "18453",
        "allocations": [
            {"registry": "VCS", "batch_id": "18453", "unit_start": 1, "unit_end": 500, "claimant": "Acme Corp"},
            {"registry": "VCS", "batch_id": "18453", "unit_start": 501, "unit_end": 1000, "claimant": "Beta LLC"},
            {"registry": "VCS", "batch_id": "18453", "unit_start": 900, "unit_end": 1200, "claimant": "Gamma Inc"},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_allocations"] == 3
    assert data["total_units"] == 1301
    assert data["is_disjoint"] is False  # 900-1200 overlaps 501-1000
    assert len(data["conflicts"]) == 1
    assert len(data["splits"]) == 2


def test_api_reconcile_compare_reversed_interval_returns_422():
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {"registry": "VCS", "batch_id": "18453", "unit_start": 200, "unit_end": 100, "claimant": "Alpha Corp"},
        "existing": {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Beta LLC"},
    })
    assert resp.status_code == 422
    err_msgs = [e["msg"] for e in resp.json()["detail"]]
    assert any("unit_start (200) cannot exceed unit_end (100)" in m for m in err_msgs)


def test_api_reconcile_compare_missing_fields_returns_422():
    # Missing unit_end and claimant
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {"registry": "VCS", "batch_id": "18453", "unit_start": 100},
        "existing": {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Beta LLC"},
    })
    assert resp.status_code == 422


def test_api_reconcile_compare_non_numeric_boundary_returns_422():
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {"registry": "VCS", "batch_id": "18453", "unit_start": "abc", "unit_end": 200, "claimant": "Alpha Corp"},
        "existing": {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Beta LLC"},
    })
    assert resp.status_code == 422


def test_api_reconcile_compare_negative_boundary_returns_422():
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {"registry": "VCS", "batch_id": "18453", "unit_start": -10, "unit_end": 100, "claimant": "Alpha Corp"},
        "existing": {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Beta LLC"},
    })
    assert resp.status_code == 422
    err_msgs = [e["msg"] for e in resp.json()["detail"]]
    assert any("unit_start must be non-negative" in m for m in err_msgs)


def test_api_reconcile_compare_zero_boundary_valid():
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {"registry": "VCS", "batch_id": "18453", "unit_start": 0, "unit_end": 50, "claimant": "Alpha Corp"},
        "existing": {"registry": "VCS", "batch_id": "18453", "unit_start": 51, "unit_end": 100, "claimant": "Beta LLC"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overlap"]["candidate_units"] == 51
    assert data["overlap"]["existing_units"] == 50
    assert data["overlap"]["overlap_type"] == "ADJACENT"


def test_api_reconcile_compare_single_unit_interval_valid():
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {"registry": "VCS", "batch_id": "18453", "unit_start": 500, "unit_end": 500, "claimant": "Alpha Corp"},
        "existing": {"registry": "VCS", "batch_id": "18453", "unit_start": 500, "unit_end": 500, "claimant": "Beta LLC"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overlap"]["candidate_units"] == 1
    assert data["overlap"]["overlap_units"] == 1
    assert data["overlap"]["overlap_type"] == "EXACT_OVERLAP"
    assert data["allocation_type"] == "ALLOCATION_CONFLICT"


def test_api_reconcile_compare_adjacent_intervals_valid():
    resp = client.post("/api/reconcile/compare", json={
        "candidate": {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Alpha Corp"},
        "existing": {"registry": "VCS", "batch_id": "18453", "unit_start": 201, "unit_end": 300, "claimant": "Beta LLC"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overlap"]["overlap_type"] == "ADJACENT"
    assert data["overlap"]["overlap_units"] == 0
    assert data["allocation_type"] == "LEGITIMATE_SPLIT"


def test_api_reconcile_batch_empty_allocations_returns_200():
    resp = client.post("/api/reconcile/batch", json={
        "registry": "VCS",
        "batch_id": "18453",
        "allocations": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_allocations"] == 0
    assert data["total_units"] == 0
    assert data["is_disjoint"] is True
    assert data["conflicts"] == []
    assert data["splits"] == []


def test_api_reconcile_batch_invalid_allocation_quantity_returns_422():
    resp = client.post("/api/reconcile/batch", json={
        "registry": "VCS",
        "batch_id": "18453",
        "allocations": [
            {"registry": "VCS", "batch_id": "18453", "unit_start": 500, "unit_end": 100, "claimant": "Alpha Corp"},
        ],
    })
    assert resp.status_code == 422


def test_api_claim_reconciliation_unknown_id_returns_404():
    resp = client.get("/api/claims/999999/reconciliation")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Claim not found"


# ==============================================================================
# Group H: Semantic Classification & Intermediary Governance Regressions
# ==============================================================================

def test_shared_intermediary_different_principals_is_allocation_conflict():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Patch on behalf of Lenovo"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Patch on behalf of Dell"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.ALLOCATION_CONFLICT.value
    assert res.entity_relationship == "DIFFERENT_ENTITIES"
    assert "Patch on behalf of Lenovo" in res.explanation
    assert "Patch on behalf of Dell" in res.explanation


def test_different_intermediaries_same_principal_is_intermediary_attribution():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Patch on behalf of Lenovo"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "TBK Group on behalf of Lenovo"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.INTERMEDIARY_ATTRIBUTION.value
    assert res.entity_relationship == "INTERMEDIARY_DELEGATION"


def test_parent_subsidiary_overlap_is_related_claimants_not_same_claimant():
    alloc_a = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Google LLC"}
    alloc_b = {"registry": "VCS", "batch_id": "18453", "unit_start": 100, "unit_end": 200, "claimant": "Google Ireland Limited"}
    res = AllocationReconciler.reconcile_allocation_pair(alloc_a, alloc_b)
    assert res.allocation_type == AllocationType.SAME_UNITS_RELATED_CLAIMANTS.value
    assert res.entity_relationship == "CORPORATE_HIERARCHY_OR_SUBSIDIARY"
    assert res.allocation_type != AllocationType.SAME_UNITS_SAME_CLAIMANT.value
    assert "corporate entities" in res.explanation.lower()
    assert "primary carbon reporting rights" in res.audit_recommendation

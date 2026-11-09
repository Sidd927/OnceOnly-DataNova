"""Comprehensive test suite for Phase 2C: Beneficiary Concentration, Batch Fragmentation, and Temporal Intelligence."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import math
import random
import pytest
from fastapi.testclient import TestClient

from app.analytics import (
    AggregationPeriod,
    AnalyticsEngine,
    BatchAnalyticsResult,
    BatchFragmentationRequest,
    BatchIntervalStructure,
    BeneficiaryCategory,
    BurstType,
    ConcentrationMetrics,
    ConcentrationRequest,
    ConcentrationTier,
    DualTrackCoverage,
    FragmentationMetrics,
    GapClassification,
    PopulationAnalyticsSummary,
    TEMPORAL_DISCLAIMER,
    TemporalActivityResponse,
    TemporalBurstPeriod,
    TemporalBurstsResponse,
    TemporalGapItem,
    TemporalGapsResponse,
    TemporalPeriodActivity,
    TemporalTrendPeriod,
    TemporalTrendsResponse,
    TrendDirection,
    aggregate_retirement_activity,
    analyze_interval_structure,
    analyze_temporal_gaps,
    calculate_dispersion_mad,
    calculate_gini_coefficient,
    calculate_gini_sample_corrected,
    calculate_hhi,
    calculate_inclusive_span,
    calculate_shannon_entropy,
    calculate_temporal_trends,
    classify_beneficiary,
    detect_temporal_bursts,
    evaluate_batch_fragmentation,
    evaluate_concentration,
    evaluate_dual_track_coverage,
    generate_calendar_periods,
    parse_date,
)
from app.main import app

client = TestClient(app)


# ==============================================================================
# SECTION 1: BENEFICIARY CLASSIFICATION & NORMALIZATION TESTS
# ==============================================================================

def test_classification_explicitly_undisclosed():
    """Verify missing, blank, or explicit non-disclosure tokens map to EXPLICITLY_UNDISCLOSED."""
    tokens = [
        None, "", "   ", "\t\n",
        "not disclosed", "Not Disclosed", "NOT DISCLOSED",
        "undisclosed", "Undisclosed",
        "unknown", "UNKNOWN",
        "n/a", "N/A", "na", "NA",
        "none", "None",
        "null", "NULL",
        "unspecified", "Unspecified"
    ]
    for token in tokens:
        cat = classify_beneficiary(token)
        assert cat == BeneficiaryCategory.EXPLICITLY_UNDISCLOSED, f"Failed for token: {token!r}"


def test_classification_invalid_or_placeholder():
    """Verify documented placeholder tokens map strictly to INVALID_OR_PLACEHOLDER."""
    placeholders = [
        "_", "  _  ",
        "test", "Test", "TEST",
        "test _ num. ord cliente", "Test _ Num. Ord Cliente", "TEST _ NUM. ORD CLIENTE"
    ]
    for token in placeholders:
        cat = classify_beneficiary(token)
        assert cat == BeneficiaryCategory.INVALID_OR_PLACEHOLDER, f"Failed for placeholder: {token!r}"


def test_classification_legitimate_names_containing_test():
    """Verify legitimate organization names containing 'test' are NOT falsely classified as placeholders."""
    legitimate_names = [
        "Testing Laboratories Inc.",
        "Protestant Environmental Trust",
        "Speedtest Clean Energy Corp",
        "Contest Solutions Ltd",
        "Dr. Testman Forestry"
    ]
    for name in legitimate_names:
        cat = classify_beneficiary(name)
        assert cat == BeneficiaryCategory.NON_PLACEHOLDER_DISCLOSED, f"False positive placeholder for: {name!r}"


def test_classification_standard_disclosed_entities():
    """Verify regular corporate beneficiaries are classified as NON_PLACEHOLDER_DISCLOSED."""
    entities = ["Shell International", "3M", "Qantas Airways", "Dexus Property Group", "Ecologi"]
    for ent in entities:
        cat = classify_beneficiary(ent)
        assert cat == BeneficiaryCategory.NON_PLACEHOLDER_DISCLOSED, f"Failed for entity: {ent!r}"


# ==============================================================================
# SECTION 2: BENEFICIARY CONCENTRATION & DUAL-TRACK COVERAGE TESTS
# ==============================================================================

def test_concentration_all_disclosed():
    """Verify concentration metrics when 100% of volume is disclosed."""
    records = [
        {"beneficiary": "Org A", "quantity": 250.0},
        {"beneficiary": "Org B", "quantity": 250.0},
        {"beneficiary": "Org C", "quantity": 250.0},
        {"beneficiary": "Org D", "quantity": 250.0},
    ]
    res = evaluate_concentration(records)

    assert res.coverage.total_records == 4
    assert res.coverage.disclosed_records == 4
    assert res.coverage.record_disclosure_rate == 1.0
    assert res.coverage.quantity_disclosure_rate == 1.0
    assert res.unique_disclosed_beneficiaries == 4

    # Shannon entropy for 4 equal shares = log2(4) = 2.0 bits
    assert math.isclose(res.entropy_shannon_disclosed, 2.0, rel_tol=1e-5)
    assert math.isclose(res.entropy_normalized, 1.0, rel_tol=1e-5)

    # HHI for 4 equal shares = 4 * (100 * 0.25)^2 = 2500
    assert math.isclose(res.hhi_disclosed, 2500.0, rel_tol=1e-5)
    assert math.isclose(res.hhi_normalized, 0.0, abs_tol=1e-5)
    assert res.tier == ConcentrationTier.MODERATE_CONCENTRATION.value


def test_concentration_all_undisclosed():
    """Verify clean zero handling when 100% of volume is undisclosed."""
    records = [
        {"beneficiary": None, "quantity": 500.0},
        {"beneficiary": "Not Disclosed", "quantity": 500.0},
    ]
    res = evaluate_concentration(records)

    assert res.coverage.total_records == 2
    assert res.coverage.disclosed_records == 0
    assert res.coverage.unresolved_records == 2
    assert res.coverage.record_disclosure_rate == 0.0
    assert res.coverage.quantity_disclosure_rate == 0.0
    assert res.coverage.record_unresolved_rate == 1.0
    assert res.coverage.quantity_unresolved_rate == 1.0

    assert res.unique_disclosed_beneficiaries == 0
    assert res.disclosed_units == 0.0
    assert res.unresolved_units == 1000.0
    assert res.hhi_disclosed == 0.0
    assert res.entropy_shannon_disclosed == 0.0
    assert res.dominant_disclosed_beneficiary is None
    assert res.tier == ConcentrationTier.NOT_CLASSIFIED.value


def test_concentration_placeholder_only():
    """Verify placeholder-only population maps to unresolved coverage without distorting concentration."""
    records = [
        {"beneficiary": "_", "quantity": 100.0},
        {"beneficiary": "Test", "quantity": 50.0},
    ]
    res = evaluate_concentration(records)

    assert res.coverage.invalid_placeholder_records == 2
    assert res.coverage.invalid_placeholder_quantity == 150.0
    assert res.coverage.disclosed_records == 0
    assert res.unique_disclosed_beneficiaries == 0
    assert res.hhi_disclosed == 0.0
    assert res.tier == ConcentrationTier.NOT_CLASSIFIED.value


def test_concentration_mixed_dual_track_handworked():
    """Verify Case 3 hand-worked reference calculation from mathematical specification."""
    # 10 allocations totaling 1,000 t:
    # 4 allocations NULL (600 t)
    # 1 allocation '_' (100 t)
    # 5 allocations disclosed: Org A (150 t), Org B (100 t), Org C (50 t)
    records = [
        {"beneficiary": None, "quantity": 150.0},
        {"beneficiary": None, "quantity": 150.0},
        {"beneficiary": None, "quantity": 150.0},
        {"beneficiary": None, "quantity": 150.0},
        {"beneficiary": "_", "quantity": 100.0},
        {"beneficiary": "Org A", "quantity": 100.0},
        {"beneficiary": "Org A", "quantity": 50.0},
        {"beneficiary": "Org B", "quantity": 50.0},
        {"beneficiary": "Org B", "quantity": 50.0},
        {"beneficiary": "Org C", "quantity": 50.0},
    ]
    res = evaluate_concentration(records)

    assert res.coverage.total_records == 10
    assert res.coverage.total_quantity == 1000.0
    assert res.coverage.disclosed_records == 5
    assert res.coverage.disclosed_quantity == 300.0
    assert res.coverage.explicitly_undisclosed_records == 4
    assert res.coverage.explicitly_undisclosed_quantity == 600.0
    assert res.coverage.invalid_placeholder_records == 1
    assert res.coverage.invalid_placeholder_quantity == 100.0
    assert res.coverage.unresolved_records == 5
    assert res.coverage.unresolved_quantity == 700.0

    assert math.isclose(res.coverage.record_disclosure_rate, 0.50, rel_tol=1e-5)
    assert math.isclose(res.coverage.quantity_disclosure_rate, 0.30, rel_tol=1e-5)
    assert math.isclose(res.coverage.quantity_unresolved_rate, 0.70, rel_tol=1e-5)

    # Disclosed shares: Org A (150/300 = 0.50), Org B (100/300 = 0.3333), Org C (50/300 = 0.1667)
    shares = res.disclosed_shares
    assert math.isclose(shares["Org A"], 0.50, rel_tol=1e-4)
    assert math.isclose(shares["Org B"], 1.0 / 3.0, rel_tol=1e-4)
    assert math.isclose(shares["Org C"], 1.0 / 6.0, rel_tol=1e-4)
    assert math.isclose(sum(shares.values()), 1.0, rel_tol=1e-5)

    # HHI = 50^2 + (33.333)^2 + (16.667)^2 = 2500 + 1111.11 + 277.78 = 3888.89
    expected_hhi = (50.0) ** 2 + (100.0 / 3.0) ** 2 + (100.0 / 6.0) ** 2
    assert math.isclose(res.hhi_disclosed, expected_hhi, rel_tol=1e-4)
    assert res.tier == ConcentrationTier.HIGH_CONCENTRATION.value


def test_concentration_monopoly_single_beneficiary():
    """Verify single beneficiary monopoly: 0 entropy, 10,000 HHI, single label dominance tier."""
    records = [{"beneficiary": "Single Monopoly Corp", "quantity": 50000.0}]
    res = evaluate_concentration(records)

    assert res.unique_disclosed_beneficiaries == 1
    assert res.dominant_disclosed_beneficiary == "Single Monopoly Corp"
    assert math.isclose(res.dominant_disclosed_share, 1.0, rel_tol=1e-5)
    assert math.isclose(res.entropy_shannon_disclosed, 0.0, abs_tol=1e-5)
    assert math.isclose(res.entropy_normalized, 0.0, abs_tol=1e-5)
    assert math.isclose(res.hhi_disclosed, 10000.0, rel_tol=1e-5)
    assert math.isclose(res.hhi_normalized, 1.0, rel_tol=1e-5)
    assert res.tier == ConcentrationTier.SINGLE_LABEL_DOMINANCE.value


def test_concentration_input_order_invariance():
    """Verify concentration metrics are strictly invariant to input record permutations."""
    records = [
        {"beneficiary": "Org X", "quantity": 100.0},
        {"beneficiary": "Org Y", "quantity": 300.0},
        {"beneficiary": "Org Z", "quantity": 600.0},
        {"beneficiary": None, "quantity": 400.0},
        {"beneficiary": "_", "quantity": 50.0},
    ]
    res1 = evaluate_concentration(records)

    records_shuffled = list(records)
    random.seed(42)
    random.shuffle(records_shuffled)
    res2 = evaluate_concentration(records_shuffled)

    assert math.isclose(res1.hhi_disclosed, res2.hhi_disclosed, rel_tol=1e-7)
    assert math.isclose(res1.entropy_shannon_disclosed, res2.entropy_shannon_disclosed, rel_tol=1e-7)
    assert res1.dominant_disclosed_beneficiary == res2.dominant_disclosed_beneficiary
    assert math.isclose(res1.coverage.quantity_disclosure_rate, res2.coverage.quantity_disclosure_rate, rel_tol=1e-7)


def test_concentration_empty_and_zero_denominators():
    """Verify graceful handling of empty inputs and zero-quantity records without NaN or crash."""
    res_empty = evaluate_concentration([])
    assert res_empty.coverage.total_records == 0
    assert res_empty.coverage.total_quantity == 0.0
    assert res_empty.coverage.record_disclosure_rate == 0.0
    assert res_empty.hhi_disclosed == 0.0
    assert not math.isnan(res_empty.hhi_disclosed)
    assert not math.isinf(res_empty.hhi_disclosed)

    # Serialization test (to_dict)
    d = res_empty.to_dict()
    assert d["total_units"] == 0.0
    assert d["hhi_disclosed"] == 0.0


# ==============================================================================
# SECTION 3: BATCH FRAGMENTATION & INTERVAL STRUCTURE TESTS
# ==============================================================================

def test_fragmentation_single_record():
    """Verify single-record batch: 0 Gini, 0 standard deviation, median equals quantity."""
    records = [{"unit_start": 1, "unit_end": 1000, "quantity": 1000, "beneficiary": "Org A"}]
    res = evaluate_batch_fragmentation(records, registry="VCS", batch_id="B1")

    assert res.total_events == 1
    assert res.total_units == 1000.0
    assert res.mean_event_size == 1000.0
    assert res.median_event_size == 1000.0
    assert res.std_dev_event_size == 0.0
    assert res.gini_coefficient == 0.0
    assert res.gini_sample_corrected == 0.0


def test_fragmentation_multiple_records_equal_sizing():
    """Verify equal allocation sizes produce Gini = 0.0."""
    records = [
        {"unit_start": 1, "unit_end": 100, "beneficiary": "A"},
        {"unit_start": 101, "unit_end": 200, "beneficiary": "B"},
        {"unit_start": 201, "unit_end": 300, "beneficiary": "C"},
        {"unit_start": 301, "unit_end": 400, "beneficiary": "D"},
    ]
    res = evaluate_batch_fragmentation(records)

    assert res.total_events == 4
    assert res.total_units == 400.0
    assert math.isclose(res.mean_event_size, 100.0, rel_tol=1e-5)
    assert math.isclose(res.median_event_size, 100.0, rel_tol=1e-5)
    assert math.isclose(res.gini_coefficient, 0.0, abs_tol=1e-5)
    assert math.isclose(res.gini_sample_corrected, 0.0, abs_tol=1e-5)


def test_fragmentation_skewed_allocation():
    """Verify skewed allocations produce high Gini and correct micro-claim counts."""
    # 9 micro allocations of 1 t, 1 large allocation of 991 t (total = 1000 t)
    records = [{"unit_start": i, "unit_end": i, "quantity": 1} for i in range(1, 10)]
    records.append({"unit_start": 10, "unit_end": 1000, "quantity": 991})

    res = evaluate_batch_fragmentation(records, micro_threshold=10.0)

    assert res.total_events == 10
    assert res.total_units == 1000.0
    assert res.micro_claim_count == 9
    assert res.micro_claim_units == 9.0
    assert math.isclose(res.micro_claim_record_share, 0.90, rel_tol=1e-5)
    assert math.isclose(res.micro_claim_quantity_share, 0.009, rel_tol=1e-5)

    # Gini must be high (> 0.70)
    assert res.gini_coefficient > 0.70
    assert res.gini_sample_corrected > res.gini_coefficient


def test_interval_structure_contiguous_and_overlaps():
    """Verify interval structure correctly detects contiguous segments, overlaps, and duplicates."""
    # Contiguous
    contig_records = [
        {"unit_start": 1, "unit_end": 100},
        {"unit_start": 101, "unit_end": 200},
        {"unit_start": 201, "unit_end": 300},
    ]
    s_contig = analyze_interval_structure(contig_records, total_units=300.0)
    assert s_contig.total_intervals == 3
    assert s_contig.min_unit_start == 1
    assert s_contig.max_unit_end == 300
    assert s_contig.interval_span == 300
    assert math.isclose(s_contig.interval_density, 1.0, rel_tol=1e-5)
    assert s_contig.contiguous_intervals_count == 2
    assert s_contig.overlapping_intervals_count == 0
    assert s_contig.pairwise_overlap_count == 0
    assert s_contig.exact_duplicate_intervals_count == 0
    assert s_contig.disjoint_gaps_count == 0

    # Overlaps & exact duplicates
    overlap_records = [
        {"unit_start": 1, "unit_end": 100},
        {"unit_start": 1, "unit_end": 100},  # exact duplicate
        {"unit_start": 50, "unit_end": 150},  # overlap
        {"unit_start": 200, "unit_end": 250}, # gap
    ]
    s_overlap = analyze_interval_structure(overlap_records, total_units=302.0)
    assert s_overlap.exact_duplicate_intervals_count == 1
    assert s_overlap.overlapping_intervals_count == 2
    assert s_overlap.pairwise_overlap_count == 3  # (0,1), (0,2), (1,2)
    assert s_overlap.disjoint_gaps_count == 1


def test_interval_structure_invalid_reversed_bounds():
    """Verify reversed interval bounds (unit_start > unit_end) set has_invalid_intervals."""
    invalid_records = [{"unit_start": 500, "unit_end": 100}]
    s_inv = analyze_interval_structure(invalid_records)
    assert s_inv.has_invalid_intervals is True


def test_registry_namespace_isolation():
    """Verify that batches in different registries with the same batch_id remain strictly separated."""
    # Two distinct registries sharing batch_id 'BATCH-1'
    vcs_records = [
        {"registry": "VCS", "batch_id": "BATCH-1", "unit_start": 1, "unit_end": 50, "beneficiary": "VCS Org"}
    ]
    gs_records = [
        {"registry": "GS", "batch_id": "BATCH-1", "unit_start": 1, "unit_end": 100, "beneficiary": "GS Org"}
    ]

    res_vcs = evaluate_batch_fragmentation(vcs_records, registry="VCS", batch_id="BATCH-1")
    res_gs = evaluate_batch_fragmentation(gs_records, registry="GS", batch_id="BATCH-1")

    assert res_vcs.total_units == 50.0
    assert res_gs.total_units == 100.0
    assert res_vcs.distinct_disclosed_beneficiaries == 1
    assert res_gs.distinct_disclosed_beneficiaries == 1


# ==============================================================================
# SECTION 4: REAL DATA VALIDATION AGAINST DEMO REFERENCE DATABASE
# ==============================================================================

def test_real_data_population_reconciliation():
    """Reconcile population totals and beneficiary classification census against var/registry_demo.sqlite."""
    summary = AnalyticsEngine.analyze_population_summary()

    # Denominator population
    assert summary.total_retirement_records == 37335
    assert summary.total_retirement_quantity == 87668330.0
    assert summary.total_batches == 725

    # 4-Category census verification
    assert summary.coverage.disclosed_records == 13935
    assert summary.coverage.disclosed_quantity == 35172359.0

    assert summary.coverage.explicitly_undisclosed_records == 23393
    assert summary.coverage.explicitly_undisclosed_quantity == 52342165.0

    assert summary.coverage.invalid_placeholder_records == 7
    assert summary.coverage.invalid_placeholder_quantity == 153806.0

    assert summary.coverage.unresolved_records == 23400
    assert summary.coverage.unresolved_quantity == 52495971.0

    # Invariants
    assert summary.coverage.disclosed_records + summary.coverage.unresolved_records == 37335
    assert summary.coverage.disclosed_quantity + summary.coverage.unresolved_quantity == 87668330.0

    # Percentages
    assert math.isclose(summary.coverage.record_disclosure_rate, 13935.0 / 37335.0, rel_tol=1e-5)
    assert math.isclose(summary.coverage.quantity_disclosure_rate, 35172359.0 / 87668330.0, rel_tol=1e-5)

    # Batch structural distribution
    assert summary.single_record_batches == 168
    assert summary.multi_record_batches == 557
    assert summary.batches_with_overlaps == 0  # Zero internal retirement interval overlaps across reference DB

    # Hardening metrics: micro claims vs small tranches
    assert summary.batches_with_micro_claims == 301
    assert summary.batches_with_small_tranches == 411

    # Macro pooled allocation inequality
    assert summary.pooled_allocation_count == 37335
    assert summary.pooled_allocation_quantity == 87668330.0
    assert math.isclose(summary.pooled_allocation_gini, 0.9605, abs_tol=1e-3)
    assert math.isclose(summary.batch_gini_distribution["mean"], 0.4924, abs_tol=1e-3)

    # Non-antitrust concentration tier
    assert summary.overall_concentration.tier == ConcentrationTier.HIGH_DISPERSION.value
    assert "disclaimer" in summary.overall_concentration.to_dict()


def test_real_data_batch_10635_reference():
    """Verify exact empirical metrics for reference batch VCS:10635."""
    res = AnalyticsEngine.analyze_batch("VCS", "10635")

    assert res.registry == "VCS"
    assert res.batch_id == "10635"
    assert res.project_id == "959"
    assert res.total_events == 9
    assert res.total_quantity == 161607.0

    # Beneficiary concentration on 10635
    assert res.concentration.disclosed_units == 3430.0
    assert res.concentration.unresolved_units == 158177.0  # 143,177 t '_' placeholder + 15,000 t NULL
    assert math.isclose(res.concentration.beneficiary_coverage_ratio, 3430.0 / 161607.0, rel_tol=1e-4)

    # Verified disclosed entities in Batch 10635
    disclosed_shares = res.concentration.disclosed_shares
    assert len(disclosed_shares) == 5
    assert "Mitsui & Co., Ltd. and Lundin Energy Norway AS" in disclosed_shares
    assert "Beiersdorf AG" in disclosed_shares
    assert "Avisera AB" in disclosed_shares
    assert any("Avisera Carbon Neutral packaging Jun 483t" in k for k in disclosed_shares)
    assert any("Avisera AB Carbon Neutral packaging October 423t" in k for k in disclosed_shares)

    # Ensure Dexus and Shell are NOT present in Batch 10635
    assert "Dexus Property Group" not in disclosed_shares
    assert "Shell" not in disclosed_shares
    assert "Dexus" not in disclosed_shares

    # De-coupled micro-claims (<= 10 t) vs relative small allocations (<= 1%)
    assert res.fragmentation.micro_claim_count == 0
    assert res.fragmentation.micro_claim_units == 0.0
    assert res.fragmentation.small_tranche_count == 7
    assert res.fragmentation.small_tranche_units == 4107.0
    assert math.isclose(res.fragmentation.small_tranche_threshold_used, 1616.07, rel_tol=1e-4)

    # Intervals
    assert res.fragmentation.intervals.exact_duplicate_intervals_count == 0
    assert res.fragmentation.intervals.overlapping_intervals_count == 0
    assert res.fragmentation.intervals.pairwise_overlap_count == 0
    assert res.fragmentation.intervals.contiguous_intervals_count == 7
    assert res.fragmentation.intervals.disjoint_gaps_count == 1


# ==============================================================================
# SECTION 5: FASTAPI REST API ENDPOINTS TESTS
# ==============================================================================

def test_api_population_summary():
    """Verify GET /api/analytics/population/summary endpoint."""
    response = client.get("/api/analytics/population/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_retirement_records"] == 37335
    assert data["total_batches"] == 725
    assert data["batches_with_micro_claims"] == 301
    assert data["batches_with_small_tranches"] == 411
    assert data["pooled_allocation_count"] == 37335
    assert math.isclose(data["pooled_allocation_gini"], 0.9605, abs_tol=1e-3)
    assert "coverage" in data
    assert "overall_concentration" in data
    assert "batch_gini_interpretation" in data


def test_api_batch_lookup_and_404():
    """Verify GET /api/analytics/batches/{registry}/{batch_id} endpoint."""
    # Valid batch
    res_ok = client.get("/api/analytics/batches/VCS/10635")
    assert res_ok.status_code == 200
    b_data = res_ok.json()
    assert b_data["registry"] == "VCS"
    assert b_data["batch_id"] == "10635"
    assert b_data["total_events"] == 9
    assert b_data["fragmentation"]["micro_claim_count"] == 0
    assert b_data["fragmentation"]["small_tranche_count"] == 7
    assert b_data["fragmentation"]["intervals"]["pairwise_overlap_count"] == 0

    # Non-existent batch
    res_404 = client.get("/api/analytics/batches/VCS/DOES_NOT_EXIST_9999")
    assert res_404.status_code == 404
    err_data = res_404.json()
    assert "detail" in err_data


def test_api_ad_hoc_concentration():
    """Verify POST /api/analytics/concentration endpoint."""
    payload = {
        "records": [
            {"beneficiary": "Company Alpha", "quantity": 700.0},
            {"beneficiary": "Company Beta", "quantity": 300.0},
            {"beneficiary": "Not Disclosed", "quantity": 500.0},
        ]
    }
    response = client.post("/api/analytics/concentration", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_units"] == 1500.0
    assert data["disclosed_units"] == 1000.0
    assert data["unresolved_units"] == 500.0
    assert data["unique_disclosed_beneficiaries"] == 2
    assert data["dominant_disclosed_beneficiary"] == "Company Alpha"
    assert math.isclose(data["dominant_disclosed_share"], 0.70, rel_tol=1e-4)
    assert "disclaimer" in data


def test_api_ad_hoc_fragmentation():
    """Verify POST /api/analytics/fragmentation endpoint."""
    payload = {
        "registry": "TEST_REG",
        "batch_id": "TEST_B1",
        "records": [
            {"unit_start": 1, "unit_end": 100},
            {"unit_start": 101, "unit_end": 200},
            {"unit_start": 201, "unit_end": 300},
        ],
        "micro_threshold": 50.0,
    }
    response = client.post("/api/analytics/fragmentation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 3
    assert data["total_units"] == 300.0
    assert data["gini_coefficient"] == 0.0
    assert data["intervals"]["contiguous_intervals_count"] == 2
    assert data["intervals"]["pairwise_overlap_count"] == 0
    assert "small_tranche_count" in data


def test_api_ad_hoc_combined_batch_and_validation():
    """Verify POST /api/analytics/batch endpoint and interval validation."""
    # Valid payload
    payload_valid = {
        "registry": "TEST_REG",
        "batch_id": "TEST_B2",
        "records": [
            {"beneficiary": "Buyer 1", "unit_start": 1, "unit_end": 500},
            {"beneficiary": "Buyer 2", "unit_start": 501, "unit_end": 1000},
        ],
    }
    res_valid = client.post("/api/analytics/batch", json=payload_valid)
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["total_events"] == 2
    assert data["total_quantity"] == 1000.0

    # Invalid reversed interval (start > end) -> HTTP 422
    payload_invalid = {
        "registry": "TEST_REG",
        "batch_id": "TEST_B3",
        "records": [
            {"unit_start": 1000, "unit_end": 500},
        ],
    }
    res_invalid = client.post("/api/analytics/batch", json=payload_invalid)
    assert res_invalid.status_code == 422


# ==============================================================================
# SECTION 6: METHODOLOGY HARDENING & REGRESSION SUITE (AUDIT RESOLUTIONS)
# ==============================================================================

def test_na_token_classified_as_undisclosed():
    """ISSUE-2C1-05: Verify 'na' (case-insensitive) is explicitly mapped to EXPLICITLY_UNDISCLOSED."""
    for val in ["na", "NA", "Na", "nA"]:
        cat = classify_beneficiary(val)
        assert cat == BeneficiaryCategory.EXPLICITLY_UNDISCLOSED, f"Failed for token: {val!r}"


def test_concentration_tier_boundaries():
    """ISSUE-2C1-01: Verify all descriptive concentration tier boundary thresholds."""
    # Zero disclosed volume
    c0 = evaluate_concentration([{"beneficiary": None, "quantity": 100.0}])
    assert c0.tier == ConcentrationTier.NOT_CLASSIFIED.value

    # Single label monopoly (K=1)
    c1 = evaluate_concentration([{"beneficiary": "Sole Claim", "quantity": 1000.0}])
    assert c1.tier == ConcentrationTier.SINGLE_LABEL_DOMINANCE.value

    # HHI > 2500 (High Concentration): e.g. 60% and 40% -> HHI = 3600 + 1600 = 5200
    c_high = evaluate_concentration([
        {"beneficiary": "A", "quantity": 60.0},
        {"beneficiary": "B", "quantity": 40.0},
    ])
    assert c_high.tier == ConcentrationTier.HIGH_CONCENTRATION.value
    assert c_high.hhi_disclosed > 2500.0

    # 1500 <= HHI <= 2500 (Moderate Concentration): e.g. 4 equal entities -> HHI = 2500
    c_mod = evaluate_concentration([
        {"beneficiary": "A", "quantity": 25.0},
        {"beneficiary": "B", "quantity": 25.0},
        {"beneficiary": "C", "quantity": 25.0},
        {"beneficiary": "D", "quantity": 25.0},
    ])
    assert c_mod.tier == ConcentrationTier.MODERATE_CONCENTRATION.value
    assert math.isclose(c_mod.hhi_disclosed, 2500.0, rel_tol=1e-5)

    # 500 <= HHI < 1500 (Broad Distribution): e.g. 10 equal entities -> HHI = 1000
    c_broad = evaluate_concentration([{"beneficiary": f"Org_{i}", "quantity": 10.0} for i in range(10)])
    assert c_broad.tier == ConcentrationTier.BROAD_DISTRIBUTION.value
    assert math.isclose(c_broad.hhi_disclosed, 1000.0, rel_tol=1e-5)

    # HHI < 500 (High Dispersion): e.g. 25 equal entities -> HHI = 400
    c_disp = evaluate_concentration([{"beneficiary": f"Org_{i}", "quantity": 10.0} for i in range(25)])
    assert c_disp.tier == ConcentrationTier.HIGH_DISPERSION.value
    assert math.isclose(c_disp.hhi_disclosed, 400.0, rel_tol=1e-5)


def test_concentration_disclaimer_present():
    """ISSUE-2C1-01: Verify required antitrust and methodological disclaimer is present."""
    c = evaluate_concentration([{"beneficiary": "Acme", "quantity": 500.0}])
    assert c.disclaimer is not None
    assert "relevant market shares" in c.disclaimer.lower()
    assert "antitrust" not in c.tier.lower()
    d = c.to_dict()
    assert "disclaimer" in d
    assert d["disclaimer"] == c.disclaimer


def test_micro_claims_de_coupled_from_small_tranches():
    """ISSUE-2C1-02: Verify de-coupling of absolute micro claims from relative small allocations."""
    # Batch volume = 200,000 t
    # Claims:
    # 1 x 5 t (absolute micro: YES, relative small: YES)
    # 1 x 500 t (absolute micro: NO, relative small: YES, since 500 <= 2000 t)
    # 1 x 1,500 t (absolute micro: NO, relative small: YES, since 1500 <= 2000 t)
    # 1 x 197,995 t (absolute micro: NO, relative small: NO)
    records = [
        {"quantity": 5.0},
        {"quantity": 500.0},
        {"quantity": 1500.0},
        {"quantity": 197995.0},
    ]
    res = evaluate_batch_fragmentation(records, micro_threshold=10.0)

    # Absolute micro-claims (<= 10 t)
    assert res.micro_claim_count == 1
    assert res.micro_claim_units == 5.0
    assert res.micro_claim_threshold_used == 10.0

    # Relative small tranches (<= 1% = 2,000 t)
    assert res.small_tranche_count == 3
    assert res.small_tranche_units == 2005.0
    assert math.isclose(res.small_tranche_threshold_used, 2000.0, rel_tol=1e-5)
    assert math.isclose(res.small_tranche_record_share, 0.75, rel_tol=1e-5)


def test_micro_claim_boundary_10_tonnes():
    """ISSUE-2C1-02: Test exact boundary condition for micro claims (q <= 10.0)."""
    records = [
        {"quantity": 9.999},
        {"quantity": 10.0},
        {"quantity": 10.001},
        {"quantity": 100.0},
    ]
    res = evaluate_batch_fragmentation(records, micro_threshold=10.0)
    assert res.micro_claim_count == 2
    assert math.isclose(res.micro_claim_units, 19.999, rel_tol=1e-5)


def test_small_tranche_boundary_one_percent():
    """ISSUE-2C1-02: Test exact boundary condition for relative small tranches (q <= 0.01 * Q)."""
    # Total units = 10,000 t -> 1% cutoff = 100.0 t
    records = [
        {"quantity": 99.9},
        {"quantity": 100.0},
        {"quantity": 100.1},
        {"quantity": 9700.0},
    ]
    res = evaluate_batch_fragmentation(records)
    assert res.small_tranche_count == 2
    assert math.isclose(res.small_tranche_units, 199.9, rel_tol=1e-5)


def test_non_positive_quantities_not_micro_claims():
    """ISSUE-2C1-02: Verify non-positive quantities (0 or negative) are not classified as micro claims."""
    records = [
        {"quantity": 0.0},
        {"quantity": -5.0},
        {"quantity": 5.0},
        {"quantity": 95.0},
    ]
    res = evaluate_batch_fragmentation(records, micro_threshold=10.0)
    # Only 5.0 t is a positive micro-claim
    assert res.micro_claim_count == 1
    assert res.micro_claim_units == 5.0


def test_allocation_splitting_sensitivity():
    """Verify allocation splitting sensitivity: 100 t as 1 tranche vs 10 x 10 t tranches."""
    single_batch = [{"quantity": 100.0, "unit_start": 1, "unit_end": 100}]
    split_batch = [{"quantity": 10.0, "unit_start": 1 + i * 10, "unit_end": 10 + i * 10} for i in range(10)]

    res_single = evaluate_batch_fragmentation(single_batch)
    res_split = evaluate_batch_fragmentation(split_batch)

    assert res_single.gini_coefficient == 0.0
    assert res_split.gini_coefficient == 0.0  # Equal sizing has 0 Gini
    assert res_single.micro_claim_count == 0  # 100 t > 10 t
    assert res_split.micro_claim_count == 10  # 10 x 10 t are all micro-claims


def test_interval_three_mutual_overlaps_collisions_vs_pairwise():
    """ISSUE-2C1-03: Verify sweep line collisions vs pairwise overlaps on 3 mutually overlapping intervals."""
    # Intervals: [10, 50], [20, 60], [30, 70]
    # Sweep-line collisions:
    # - [10, 50]: max_end = 50
    # - [20, 60]: 20 <= 50 -> collision 1! max_end = 60
    # - [30, 70]: 30 <= 60 -> collision 2! max_end = 70
    # Total collisions = 2
    # Pairwise overlaps: (0,1), (0,2), (1,2) -> Total = 3
    intervals = [
        {"unit_start": 10, "unit_end": 50},
        {"unit_start": 20, "unit_end": 60},
        {"unit_start": 30, "unit_end": 70},
    ]
    s = analyze_interval_structure(intervals)
    assert s.overlapping_intervals_count == 2
    assert s.pairwise_overlap_count == 3


def test_interval_nested_intervals():
    """ISSUE-2C1-03: Verify nested intervals: outer interval encloses two disjoint inner intervals."""
    # Outer: [10, 100]
    # Inner 1: [20, 30]
    # Inner 2: [40, 50]
    # Sweep line:
    # - [10, 100]: max_end = 100
    # - [20, 30]: 20 <= 100 -> collision 1
    # - [40, 50]: 40 <= 100 -> collision 2
    # Pairwise overlaps:
    # - [10, 100] overlaps [20, 30] (YES)
    # - [10, 100] overlaps [40, 50] (YES)
    # - [20, 30] overlaps [40, 50] (NO)
    # Total pairwise overlaps = 2
    intervals = [
        {"unit_start": 10, "unit_end": 100},
        {"unit_start": 20, "unit_end": 30},
        {"unit_start": 40, "unit_end": 50},
    ]
    s = analyze_interval_structure(intervals)
    assert s.overlapping_intervals_count == 2
    assert s.pairwise_overlap_count == 2


def test_interval_exact_duplicates_overlap_count():
    """ISSUE-2C1-03: Verify exact duplicates count towards both collisions and pairwise overlaps."""
    # 3 identical intervals [10, 20]
    # Collisions = 2
    # Exact duplicates = 2
    # Pairwise overlaps = 3 (all pairs overlap)
    intervals = [
        {"unit_start": 10, "unit_end": 20},
        {"unit_start": 10, "unit_end": 20},
        {"unit_start": 10, "unit_end": 20},
    ]
    s = analyze_interval_structure(intervals)
    assert s.exact_duplicate_intervals_count == 2
    assert s.overlapping_intervals_count == 2
    assert s.pairwise_overlap_count == 3


def test_interval_endpoint_touching_is_overlap():
    """ISSUE-2C1-03: Verify that intervals sharing an exact serial endpoint count as overlapping."""
    # [10, 20] and [20, 30] both claim serial 20!
    intervals = [
        {"unit_start": 10, "unit_end": 20},
        {"unit_start": 20, "unit_end": 30},
    ]
    s = analyze_interval_structure(intervals)
    assert s.overlapping_intervals_count == 1
    assert s.pairwise_overlap_count == 1
    assert s.contiguous_intervals_count == 0  # Contiguous would be 21, not 20


def test_interval_sweep_brute_force_equivalence():
    """ISSUE-2C1-03: Verify sweep line pairwise algorithm matches brute force across randomized intervals."""
    rng = random.Random(1337)
    raw_intervals = []
    for _ in range(50):
        start = rng.randint(1, 1000)
        length = rng.randint(5, 100)
        raw_intervals.append({"unit_start": start, "unit_end": start + length})

    s = analyze_interval_structure(raw_intervals)

    # Brute force count of pairs (i, j) with i < j where intervals overlap
    extracted = [(r["unit_start"], r["unit_end"]) for r in raw_intervals]
    brute_force_pairs = 0
    n = len(extracted)
    for i in range(n):
        s1, e1 = extracted[i]
        for j in range(i + 1, n):
            s2, e2 = extracted[j]
            if max(s1, s2) <= min(e1, e2):
                brute_force_pairs += 1

    assert s.pairwise_overlap_count == brute_force_pairs


def test_population_pooled_gini_vs_batch_gini():
    """ISSUE-2C1-06: Verify difference between macro pooled allocation Gini and mean within-batch Gini."""
    summary = AnalyticsEngine.analyze_population_summary()

    # Macro pooled allocation Gini across all 37,335 allocations = 0.9605
    assert math.isclose(summary.pooled_allocation_gini, 0.9605, abs_tol=1e-3)

    # Mean within-batch Gini across 725 batches = 0.4924
    assert math.isclose(summary.batch_gini_distribution["mean"], 0.4924, abs_tol=1e-3)

    # Pooled Gini is substantially higher than mean batch Gini due to cross-project scale variance
    assert summary.pooled_allocation_gini > summary.batch_gini_distribution["mean"] + 0.40
    assert "batch_gini_interpretation" in summary.to_dict()


def test_batch_10635_disclosed_entities_verification():
    """ISSUE-2C1-04: Verify exact beneficiary composition and lack of external entities in Batch 10635."""
    res = AnalyticsEngine.analyze_batch("VCS", "10635")
    shares = res.concentration.disclosed_shares

    # Sum of disclosed quantities must equal 3,430 t
    mitsui_qty = 1125.0
    beiersdorf_qty = 1079.0
    avisera_pkg_jun = 483.0
    avisera_pkg_oct = 423.0
    avisera_ab = 320.0
    total_disclosed = mitsui_qty + beiersdorf_qty + avisera_pkg_jun + avisera_pkg_oct + avisera_ab
    assert total_disclosed == 3430.0

    # Find the keys dynamically by prefix to accommodate registry encoding artifacts
    avisera_jun_key = next(k for k in shares if "Avisera Carbon Neutral packaging Jun 483t" in k)
    avisera_oct_key = next(k for k in shares if "Avisera AB Carbon Neutral packaging October 423t" in k)

    assert math.isclose(shares["Mitsui & Co., Ltd. and Lundin Energy Norway AS"], mitsui_qty / 3430.0, rel_tol=1e-4)
    assert math.isclose(shares["Beiersdorf AG"], beiersdorf_qty / 3430.0, rel_tol=1e-4)
    assert math.isclose(shares[avisera_jun_key], avisera_pkg_jun / 3430.0, rel_tol=1e-4)
    assert math.isclose(shares[avisera_oct_key], avisera_pkg_oct / 3430.0, rel_tol=1e-4)
    assert math.isclose(shares["Avisera AB"], avisera_ab / 3430.0, rel_tol=1e-4)


# ==============================================================================
# SECTION 8: PHASE 2C STAGE 2 — TEMPORAL RETIREMENT INTELLIGENCE TESTS
# ==============================================================================


def test_parse_date_various_formats():
    """Verify robust parsing across date formats and graceful None for invalid."""
    assert parse_date("2023-05-12") == date(2023, 5, 12)
    assert parse_date("2023/05/12") == date(2023, 5, 12)
    assert parse_date(date(2021, 1, 1)) == date(2021, 1, 1)
    assert parse_date(datetime(2021, 1, 1, 12, 0, 0)) == date(2021, 1, 1)
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("   ") is None
    assert parse_date("null") is None
    assert parse_date("not_a_date") is None


def test_calculate_inclusive_span():
    """Verify inclusive calendar span computation."""
    assert calculate_inclusive_span([]) == 0
    assert calculate_inclusive_span([date(2023, 1, 1)]) == 1
    assert calculate_inclusive_span([date(2023, 1, 1), date(2023, 1, 10)]) == 10
    assert calculate_inclusive_span([date(2023, 1, 10), date(2023, 1, 1)]) == 10


def test_generate_calendar_periods_daily():
    """Verify daily calendar generation produces gap-free sequence."""
    periods = generate_calendar_periods(date(2023, 1, 1), date(2023, 1, 5), period_type="daily")
    assert len(periods) == 5
    assert periods[0] == (date(2023, 1, 1), date(2023, 1, 1), "2023-01-01")
    assert periods[-1] == (date(2023, 1, 5), date(2023, 1, 5), "2023-01-05")


def test_generate_calendar_periods_weekly():
    """Verify weekly periods align to Monday-Sunday ISO weeks."""
    periods = generate_calendar_periods(date(2023, 1, 4), date(2023, 1, 18), period_type="weekly")
    assert len(periods) == 3
    assert periods[0] == (date(2023, 1, 2), date(2023, 1, 8), "2023-W01")
    assert periods[1] == (date(2023, 1, 9), date(2023, 1, 15), "2023-W02")
    assert periods[2] == (date(2023, 1, 16), date(2023, 1, 22), "2023-W03")


def test_generate_calendar_periods_monthly():
    """Verify monthly periods cover calendar months from start to end month inclusive."""
    periods = generate_calendar_periods(date(2022, 11, 15), date(2023, 2, 10), period_type="monthly")
    assert len(periods) == 4
    assert periods[0] == (date(2022, 11, 1), date(2022, 11, 30), "2022-11")
    assert periods[1] == (date(2022, 12, 1), date(2022, 12, 31), "2022-12")
    assert periods[2] == (date(2023, 1, 1), date(2023, 1, 31), "2023-01")
    assert periods[3] == (date(2023, 2, 1), date(2023, 2, 28), "2023-02")


def test_generate_calendar_periods_invalid():
    """Verify inverted dates return empty and invalid period type raises."""
    assert generate_calendar_periods(date(2023, 5, 1), date(2023, 1, 1)) == []
    with pytest.raises(ValueError, match="Unsupported period_type"):
        generate_calendar_periods(date(2023, 1, 1), date(2023, 2, 1), period_type="quarterly")


def test_calculate_dispersion_mad_normal():
    """Verify median, MAD, and dispersion for normal variations."""
    vals = [10.0, 12.0, 14.0, 15.0, 18.0]
    med, scaled_mad, disp, method = calculate_dispersion_mad(vals)
    assert med == 14.0
    assert math.isclose(scaled_mad, 2.9652, abs_tol=1e-3)
    assert disp == scaled_mad
    assert method == "MAD"


def test_calculate_dispersion_mad_identical_fallback():
    """Verify that when MAD collapses to 0 on identical values, dispersion returns 0.0 with ZERO_MAD_FLOOR."""
    vals = [50.0, 50.0, 50.0, 50.0, 50.0]
    med, scaled_mad, disp, method = calculate_dispersion_mad(vals, floor=10.0)
    assert med == 50.0
    assert scaled_mad == 0.0
    assert disp == 0.0
    assert method == "ZERO_MAD_FLOOR"


def test_calculate_dispersion_mad_zero_inflated_fallback():
    """Verify zero-inflated sequence does not inflate dispersion with sample standard deviation."""
    vals = [0.0, 0.0, 0.0, 0.0, 100.0]
    med, scaled_mad, disp, method = calculate_dispersion_mad(vals, floor=1.0)
    assert med == 0.0
    assert scaled_mad == 0.0
    assert disp == 0.0
    assert method == "ZERO_MAD_FLOOR"


def test_aggregate_retirement_activity_synthetic():
    """Verify activity aggregation across monthly calendar periods with zero fills and filters."""
    records = [
        {"kind": "retirement", "quantity": 1000.0, "event_date": "2023-01-10"},
        {"kind": "retirement", "quantity": 1500.0, "event_date": "2023-01-20"},
        {"kind": "issuance", "quantity": 9999.0, "event_date": "2023-02-01"},  # must be ignored!
        {"kind": "retirement", "quantity": 3000.0, "event_date": "2023-03-15"},
    ]
    resp = aggregate_retirement_activity(records, period_type="monthly")
    assert resp.total_periods == 3
    assert resp.total_records == 3
    assert resp.total_tonnes == 5500.0
    assert resp.active_periods_count == 2
    assert resp.zero_activity_periods_count == 1

    p_jan = resp.periods[0]
    assert p_jan.period_label == "2023-01"
    assert p_jan.record_count == 2
    assert p_jan.total_tonnes == 2500.0
    assert p_jan.average_tonnes_per_record == 1250.0

    p_feb = resp.periods[1]
    assert p_feb.period_label == "2023-02"
    assert p_feb.record_count == 0
    assert p_feb.total_tonnes == 0.0

    p_mar = resp.periods[2]
    assert p_mar.period_label == "2023-03"
    assert p_mar.record_count == 1
    assert p_mar.total_tonnes == 3000.0


def test_calculate_temporal_trends_classification():
    """Verify rolling average trends, insufficient history handling, and direction classifications."""
    periods = [
        TemporalPeriodActivity(
            period_start=date(2023, i, 1),
            period_end=date(2023, i, 28),
            period_label=f"2023-{i:02d}",
            record_count=1,
            total_tonnes=qty,
            average_tonnes_per_record=qty,
            records_with_usable_dates=1,
            usable_date_quantity=qty,
        )
        for i, qty in enumerate([100.0, 100.0, 100.0, 100.0, 150.0, 50.0], start=1)
    ]

    resp = calculate_temporal_trends(periods, window=4, threshold_pct=5.0)
    assert resp.total_periods == 6
    assert resp.sufficient_history_periods == 2
    assert resp.insufficient_history_periods == 4

    # Period 0 (Jan): first period
    assert resp.trends[0].has_sufficient_history is False
    assert resp.trends[0].rolling_average_tonnes is None
    assert resp.trends[0].direction == "stable"

    # Period 4 (May): prior 4 months average = 100.0 t -> 150 t is increasing
    t4 = resp.trends[4]
    assert t4.has_sufficient_history is True
    assert t4.rolling_average_tonnes == 100.0
    assert t4.direction == "increasing"

    # Period 5 (Jun): prior 4 months average = 112.5 t -> 50 t is decreasing
    t5 = resp.trends[5]
    assert t5.has_sufficient_history is True
    assert t5.rolling_average_tonnes == 112.5
    assert t5.direction == "decreasing"


def test_detect_temporal_bursts_leave_one_out():
    """Verify leave-one-out baseline: evaluated period t is strictly excluded from historical baseline."""
    periods = [
        TemporalPeriodActivity(
            period_start=date(2023, i, 1),
            period_end=date(2023, i, 28),
            period_label=f"2023-{i:02d}",
            record_count=2,
            total_tonnes=100.0,
            average_tonnes_per_record=50.0,
            records_with_usable_dates=2,
            usable_date_quantity=100.0,
        )
        for i in range(1, 8)
    ]
    periods.append(
        TemporalPeriodActivity(
            period_start=date(2023, 8, 1),
            period_end=date(2023, 8, 31),
            period_label="2023-08",
            record_count=10,
            total_tonnes=10000.0,
            average_tonnes_per_record=1000.0,
            records_with_usable_dates=10,
            usable_date_quantity=10000.0,
        )
    )

    resp = detect_temporal_bursts(periods, baseline_window=12, sensitivity=3.0, min_history=5)
    assert resp.burst_periods_count == 1

    # First 5 periods (indices 0..4) have < 5 prior periods
    assert resp.bursts[0].has_sufficient_history is False
    assert resp.bursts[4].has_sufficient_history is False

    # Period 6 (index 5) has 5 prior periods
    assert resp.bursts[5].has_sufficient_history is True
    assert resp.bursts[5].is_burst is False

    # Period 8 (index 7, the spike): baseline strictly contains periods 0..6 (100 t each)
    spike = resp.bursts[7]
    assert spike.has_sufficient_history is True
    assert spike.baseline_median_tonnes == 100.0
    assert spike.is_burst is True
    assert spike.burst_type == "BOTH"
    assert spike.tonne_burst_flag is True
    assert spike.record_burst_flag is True
    assert "Anomalous surge in both volume" in spike.explanation


def test_analyze_temporal_gaps():
    """Verify gap classification into boundary, short coverage, and confirmed inactivity."""
    periods = [
        # Inactivity at dataset boundary (index 0)
        TemporalPeriodActivity(
            period_start=date(2023, 1, 1), period_end=date(2023, 1, 31), period_label="2023-01",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        # Active month (index 1)
        TemporalPeriodActivity(
            period_start=date(2023, 2, 1), period_end=date(2023, 2, 28), period_label="2023-02",
            record_count=5, total_tonnes=500.0, average_tonnes_per_record=100.0,
            records_with_usable_dates=5, usable_date_quantity=500.0,
        ),
        # 1-month gap (index 2) -> INTERMITTENT_ZERO_ACTIVITY_INTERVAL
        TemporalPeriodActivity(
            period_start=date(2023, 3, 1), period_end=date(2023, 3, 31), period_label="2023-03",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        # Active month (index 3)
        TemporalPeriodActivity(
            period_start=date(2023, 4, 1), period_end=date(2023, 4, 30), period_label="2023-04",
            record_count=10, total_tonnes=1000.0, average_tonnes_per_record=100.0,
            records_with_usable_dates=10, usable_date_quantity=1000.0,
        ),
        # 3-month gap (indices 4..6) -> SUSTAINED_ZERO_ACTIVITY_INTERVAL
        TemporalPeriodActivity(
            period_start=date(2023, 5, 1), period_end=date(2023, 5, 31), period_label="2023-05",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        TemporalPeriodActivity(
            period_start=date(2023, 6, 1), period_end=date(2023, 6, 30), period_label="2023-06",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        TemporalPeriodActivity(
            period_start=date(2023, 7, 1), period_end=date(2023, 7, 31), period_label="2023-07",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        # Active month (index 7)
        TemporalPeriodActivity(
            period_start=date(2023, 8, 1), period_end=date(2023, 8, 31), period_label="2023-08",
            record_count=1, total_tonnes=100.0, average_tonnes_per_record=100.0,
            records_with_usable_dates=1, usable_date_quantity=100.0,
        ),
    ]

    resp = analyze_temporal_gaps(periods, period_type="monthly")
    assert resp.total_gaps_count == 3
    assert resp.gaps[0].gap_classification == GapClassification.DATASET_BOUNDARY.value
    assert resp.gaps[0].gap_duration_periods == 1
    assert resp.gaps[1].gap_classification == GapClassification.INTERMITTENT_ZERO_ACTIVITY_INTERVAL.value
    assert resp.gaps[1].gap_duration_periods == 1
    assert resp.gaps[2].gap_classification == GapClassification.SUSTAINED_ZERO_ACTIVITY_INTERVAL.value
    assert resp.gaps[2].gap_duration_periods == 3


def test_temporal_database_population_activity():
    """Verify full SQLite database population temporal activity metrics."""
    resp = AnalyticsEngine.analyze_temporal_activity(period_type="monthly")
    assert resp.total_periods == 192
    assert resp.total_records == 37335
    assert math.isclose(resp.total_tonnes, 87668330.0, abs_tol=1e-2)
    assert resp.active_periods_count == 173
    assert resp.zero_activity_periods_count == 19
    assert resp.earliest_date_observed == date(2010, 10, 25)
    assert resp.latest_date_observed == date(2026, 9, 1)
    assert "investigative signals" in resp.disclaimer


def test_temporal_database_registry_partition():
    """Verify registry partition: VCS + GS = total population exactly."""
    vcs = AnalyticsEngine.analyze_temporal_activity(registry="VCS", period_type="monthly")
    gs = AnalyticsEngine.analyze_temporal_activity(registry="GS", period_type="monthly")

    assert vcs.total_records == 30111
    assert math.isclose(vcs.total_tonnes, 79964179.0, abs_tol=1e-2)

    assert gs.total_records == 7224
    assert math.isclose(gs.total_tonnes, 7704151.0, abs_tol=1e-2)

    assert vcs.total_records + gs.total_records == 37335
    assert math.isclose(vcs.total_tonnes + gs.total_tonnes, 87668330.0, abs_tol=1e-2)


def test_temporal_database_gaps_verification():
    """Verify gap counts and classifications across full reference database."""
    resp = AnalyticsEngine.analyze_temporal_gaps(period_type="monthly")
    assert resp.total_gaps_count == 10
    assert resp.max_gap_duration_days == 91
    assert math.isclose(resp.mean_gap_duration_days, 57.0, abs_tol=1e-1)

    sustained = [g for g in resp.gaps if g.gap_classification == GapClassification.SUSTAINED_ZERO_ACTIVITY_INTERVAL.value]
    intermittent = [g for g in resp.gaps if g.gap_classification == GapClassification.INTERMITTENT_ZERO_ACTIVITY_INTERVAL.value]
    assert len(sustained) == 3
    assert len(intermittent) == 7


def test_temporal_api_endpoints_via_testclient():
    """Verify all 4 temporal REST endpoints return HTTP 200, enforce validation 422, and match database."""
    # 1. Activity endpoint
    res = client.get("/api/analytics/temporal/activity?period=monthly")
    assert res.status_code == 200
    d = res.json()
    assert d["total_periods"] == 192
    assert d["total_records"] == 37335

    # 2. Trends endpoint
    res = client.get("/api/analytics/temporal/trends?period=monthly&window=4")
    assert res.status_code == 200
    d = res.json()
    assert d["total_periods"] == 192
    assert d["sufficient_history_periods"] == 188
    assert d["rolling_window"] == 4

    # 3. Bursts endpoint
    res = client.get("/api/analytics/temporal/bursts?period=monthly&baseline_window=12&sensitivity=3.0")
    assert res.status_code == 200
    d = res.json()
    assert d["total_periods_evaluated"] == 192
    assert d["sensitivity"] == 3.0
    assert d["burst_periods_count"] > 0

    # 4. Gaps endpoint
    res = client.get("/api/analytics/temporal/gaps?period=monthly")
    assert res.status_code == 200
    d = res.json()
    assert d["total_gaps_count"] == 10

    # 5. Validation 422 errors
    res_bad_period = client.get("/api/analytics/temporal/activity?period=secondly")
    assert res_bad_period.status_code == 422

    res_bad_date = client.get("/api/analytics/temporal/activity?start_date=2023-99-99")
    assert res_bad_date.status_code == 422

    res_inv_range = client.get("/api/analytics/temporal/activity?start_date=2025-01-01&end_date=2024-01-01")
    assert res_inv_range.status_code == 422


def test_three_consecutive_zero_months_classified_as_sustained_observed_zero_activity():
    """Verify that 3+ consecutive zero periods within the dataset are classified as
    SUSTAINED_ZERO_ACTIVITY_INTERVAL, 1-2 periods as INTERMITTENT_ZERO_ACTIVITY_INTERVAL,
    and boundaries as DATASET_BOUNDARY, with appropriate non-overclaiming coverage notes.
    """
    periods = [
        # Boundary 0 (start)
        TemporalPeriodActivity(
            period_start=date(2023, 1, 1), period_end=date(2023, 1, 31), period_label="2023-01",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        # Active month
        TemporalPeriodActivity(
            period_start=date(2023, 2, 1), period_end=date(2023, 2, 28), period_label="2023-02",
            record_count=10, total_tonnes=1000.0, average_tonnes_per_record=100.0,
            records_with_usable_dates=10, usable_date_quantity=1000.0,
        ),
        # 2-month gap -> INTERMITTENT_ZERO_ACTIVITY_INTERVAL
        TemporalPeriodActivity(
            period_start=date(2023, 3, 1), period_end=date(2023, 3, 31), period_label="2023-03",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        TemporalPeriodActivity(
            period_start=date(2023, 4, 1), period_end=date(2023, 4, 30), period_label="2023-04",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        # Active month
        TemporalPeriodActivity(
            period_start=date(2023, 5, 1), period_end=date(2023, 5, 31), period_label="2023-05",
            record_count=5, total_tonnes=500.0, average_tonnes_per_record=100.0,
            records_with_usable_dates=5, usable_date_quantity=500.0,
        ),
        # 3-month gap -> SUSTAINED_ZERO_ACTIVITY_INTERVAL
        TemporalPeriodActivity(
            period_start=date(2023, 6, 1), period_end=date(2023, 6, 30), period_label="2023-06",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        TemporalPeriodActivity(
            period_start=date(2023, 7, 1), period_end=date(2023, 7, 31), period_label="2023-07",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        TemporalPeriodActivity(
            period_start=date(2023, 8, 1), period_end=date(2023, 8, 31), period_label="2023-08",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        ),
        # Active month
        TemporalPeriodActivity(
            period_start=date(2023, 9, 1), period_end=date(2023, 9, 30), period_label="2023-09",
            record_count=8, total_tonnes=800.0, average_tonnes_per_record=100.0,
            records_with_usable_dates=8, usable_date_quantity=800.0,
        ),
    ]

    resp = analyze_temporal_gaps(periods, period_type="monthly")
    assert resp.total_gaps_count == 3
    # Gap 0: boundary
    assert resp.gaps[0].gap_classification == GapClassification.DATASET_BOUNDARY.value
    # Gap 1: 2 months intermittent
    assert resp.gaps[1].gap_classification == GapClassification.INTERMITTENT_ZERO_ACTIVITY_INTERVAL.value
    assert resp.gaps[1].gap_duration_periods == 2
    # Gap 2: 3 months sustained
    assert resp.gaps[2].gap_classification == GapClassification.SUSTAINED_ZERO_ACTIVITY_INTERVAL.value
    assert resp.gaps[2].gap_duration_periods == 3
    assert "does not establish market-wide dormancy" in resp.gaps[2].coverage_limitation_note


def test_adversarial_zero_mad_outlier_resilience():
    """Adversarial validation across 7 challenging regimes:

    Case A/B/C: Outlier inflation resilience (Zero-MAD Masking Elimination).
    Case D: Constant positive sequence stability (continuation vs genuine burst).
    Case E: Constant zero sequence stability (sub-floor vs genuine burst).
    Case F: Independent record-count vs tonne bursts (TONNES, RECORDS, BOTH).
    Case G: Baseline sufficiency (H < 5) and strict leave-one-out invariant.
    """
    # --------------------------------------------------------------------------
    # Case A/B/C: 12 baseline periods with 11 zeros and one 100,000 t outlier
    # --------------------------------------------------------------------------
    vals = [0.0] * 11 + [100000.0]
    med, scaled_mad, disp, method = calculate_dispersion_mad(vals, floor=10.0)
    assert med == 0.0
    assert scaled_mad == 0.0
    assert disp == 0.0
    assert method == "ZERO_MAD_FLOOR"

    # Under flawed sample std fallback:
    # mean = 100000/12 = 8333.33; variance = (11*(-8333.33)^2 + (100000-8333.33)^2)/11 = 831641414; s = 28838.19
    # flawed threshold = 0 + 3 * 28838.19 = 86514.58 t -> would falsely mask a 500 t burst!
    mean_v = sum(vals) / 12.0
    sample_std = math.sqrt(sum((v - mean_v) ** 2 for v in vals) / 11.0)
    flawed_threshold = max(100.0, med + 3.0 * sample_std)
    assert flawed_threshold > 80000.0

    # Build sequence of 12 baseline periods + period 13 with 500 t
    periods_abc = [
        TemporalPeriodActivity(
            period_start=date(2022, (i % 12) + 1, 1),
            period_end=date(2022, (i % 12) + 1, 28),
            period_label=f"P{i:02d}",
            record_count=1 if i == 11 else 0,
            total_tonnes=100000.0 if i == 11 else 0.0,
            average_tonnes_per_record=100000.0 if i == 11 else 0.0,
            records_with_usable_dates=1 if i == 11 else 0,
            usable_date_quantity=100000.0 if i == 11 else 0.0,
        )
        for i in range(12)
    ]
    # Period 13: moderate burst of 500 t (1 record)
    periods_abc.append(
        TemporalPeriodActivity(
            period_start=date(2023, 1, 1),
            period_end=date(2023, 1, 31),
            period_label="P12_EVAL",
            record_count=1,
            total_tonnes=500.0,
            average_tonnes_per_record=500.0,
            records_with_usable_dates=1,
            usable_date_quantity=500.0,
        )
    )

    resp_abc = detect_temporal_bursts(
        periods_abc, baseline_window=12, sensitivity=3.0, min_history=5, min_tonne_threshold=100.0
    )
    b12 = resp_abc.bursts[12]
    assert b12.has_sufficient_history is True
    assert b12.baseline_median_tonnes == 0.0
    assert b12.tonne_dispersion_method == "ZERO_MAD_FLOOR"
    assert b12.tonne_burst_threshold == 100.0  # Floor applied cleanly!
    assert b12.tonne_burst_flag is True  # 500.0 > 100.0 detected!
    assert b12.is_burst is True
    assert b12.burst_type == "TONNES"

    # --------------------------------------------------------------------------
    # Case D: Constant positive sequence (twelve months of 200 t)
    # --------------------------------------------------------------------------
    periods_d = [
        TemporalPeriodActivity(
            period_start=date(2022, (i % 12) + 1, 1),
            period_end=date(2022, (i % 12) + 1, 28),
            period_label=f"D{i:02d}",
            record_count=2,
            total_tonnes=200.0,
            average_tonnes_per_record=100.0,
            records_with_usable_dates=2,
            usable_date_quantity=200.0,
        )
        for i in range(12)
    ]
    # Continuation of normal activity (200 t) -> NOT a burst
    periods_d.append(
        TemporalPeriodActivity(
            period_start=date(2023, 1, 1),
            period_end=date(2023, 1, 31),
            period_label="D12_NORMAL",
            record_count=2,
            total_tonnes=200.0,
            average_tonnes_per_record=100.0,
            records_with_usable_dates=2,
            usable_date_quantity=200.0,
        )
    )
    # Genuine burst (300 t) -> IS a burst
    periods_d.append(
        TemporalPeriodActivity(
            period_start=date(2023, 2, 1),
            period_end=date(2023, 2, 28),
            period_label="D13_BURST",
            record_count=2,
            total_tonnes=300.0,
            average_tonnes_per_record=150.0,
            records_with_usable_dates=2,
            usable_date_quantity=300.0,
        )
    )
    resp_d = detect_temporal_bursts(periods_d, baseline_window=12, sensitivity=3.0, min_history=5)
    assert resp_d.bursts[12].is_burst is False
    assert resp_d.bursts[12].tonne_burst_flag is False
    assert resp_d.bursts[12].tonne_dispersion_method == "ZERO_MAD_FLOOR"
    assert resp_d.bursts[13].is_burst is True
    assert resp_d.bursts[13].tonne_burst_flag is True

    # --------------------------------------------------------------------------
    # Case E: Constant zero sequence (twelve months of 0 t)
    # --------------------------------------------------------------------------
    periods_e = [
        TemporalPeriodActivity(
            period_start=date(2022, (i % 12) + 1, 1),
            period_end=date(2022, (i % 12) + 1, 28),
            period_label=f"E{i:02d}",
            record_count=0,
            total_tonnes=0.0,
            average_tonnes_per_record=0.0,
            records_with_usable_dates=0,
            usable_date_quantity=0.0,
        )
        for i in range(12)
    ]
    # Zero period -> not a burst
    periods_e.append(
        TemporalPeriodActivity(
            period_start=date(2023, 1, 1), period_end=date(2023, 1, 31), period_label="E12_ZERO",
            record_count=0, total_tonnes=0.0, average_tonnes_per_record=0.0,
            records_with_usable_dates=0, usable_date_quantity=0.0,
        )
    )
    # Sub-floor period (50 t < 100 t floor) -> not a burst
    periods_e.append(
        TemporalPeriodActivity(
            period_start=date(2023, 2, 1), period_end=date(2023, 2, 28), period_label="E13_SUBFLOOR",
            record_count=1, total_tonnes=50.0, average_tonnes_per_record=50.0,
            records_with_usable_dates=1, usable_date_quantity=50.0,
        )
    )
    # Genuine burst (150 t > 100 t floor) -> is a burst
    periods_e.append(
        TemporalPeriodActivity(
            period_start=date(2023, 3, 1), period_end=date(2023, 3, 31), period_label="E14_BURST",
            record_count=1, total_tonnes=150.0, average_tonnes_per_record=150.0,
            records_with_usable_dates=1, usable_date_quantity=150.0,
        )
    )
    resp_e = detect_temporal_bursts(
        periods_e, baseline_window=12, sensitivity=3.0, min_history=5, min_tonne_threshold=100.0
    )
    assert resp_e.bursts[12].is_burst is False
    assert resp_e.bursts[13].is_burst is False
    assert resp_e.bursts[14].is_burst is True
    assert resp_e.bursts[14].tonne_burst_flag is True

    # --------------------------------------------------------------------------
    # Case F: Independent record-count vs tonne bursts
    # --------------------------------------------------------------------------
    periods_f = [
        TemporalPeriodActivity(
            period_start=date(2022, (i % 12) + 1, 1),
            period_end=date(2022, (i % 12) + 1, 28),
            period_label=f"F{i:02d}",
            record_count=10,
            total_tonnes=1000.0,
            average_tonnes_per_record=100.0,
            records_with_usable_dates=10,
            usable_date_quantity=1000.0,
        )
        for i in range(12)
    ]
    # F1: Volume surge only (1 record, 50,000 t)
    periods_f.append(
        TemporalPeriodActivity(
            period_start=date(2023, 1, 1), period_end=date(2023, 1, 31), period_label="F12_VOL",
            record_count=1, total_tonnes=50000.0, average_tonnes_per_record=50000.0,
            records_with_usable_dates=1, usable_date_quantity=50000.0,
        )
    )
    # F2: Record surge only (100 records, 1,000 t)
    periods_f.append(
        TemporalPeriodActivity(
            period_start=date(2023, 2, 1), period_end=date(2023, 2, 28), period_label="F13_REC",
            record_count=100, total_tonnes=1000.0, average_tonnes_per_record=10.0,
            records_with_usable_dates=100, usable_date_quantity=1000.0,
        )
    )
    # F3: Both volume and record surge (100 records, 50,000 t)
    periods_f.append(
        TemporalPeriodActivity(
            period_start=date(2023, 3, 1), period_end=date(2023, 3, 31), period_label="F14_BOTH",
            record_count=100, total_tonnes=50000.0, average_tonnes_per_record=500.0,
            records_with_usable_dates=100, usable_date_quantity=50000.0,
        )
    )
    resp_f = detect_temporal_bursts(periods_f, baseline_window=12, sensitivity=3.0, min_history=5)
    assert resp_f.bursts[12].burst_type == "TONNES"
    assert resp_f.bursts[12].tonne_burst_flag is True
    assert resp_f.bursts[12].record_burst_flag is False

    assert resp_f.bursts[13].burst_type == "RECORDS"
    assert resp_f.bursts[13].record_burst_flag is True
    assert resp_f.bursts[13].tonne_burst_flag is False

    assert resp_f.bursts[14].burst_type == "BOTH"
    assert resp_f.bursts[14].record_burst_flag is True
    assert resp_f.bursts[14].tonne_burst_flag is True

    # --------------------------------------------------------------------------
    # Case G: Baseline sufficiency (H < 5) and strict leave-one-out invariant
    # --------------------------------------------------------------------------
    for idx in range(5):
        assert resp_f.bursts[idx].has_sufficient_history is False
        assert resp_f.bursts[idx].is_burst is False
        assert resp_f.bursts[idx].record_dispersion_method == "INSUFFICIENT_HISTORY"
        assert resp_f.bursts[idx].tonne_dispersion_method == "INSUFFICIENT_HISTORY"

    # Leave-one-out invariant:
    periods_g1 = list(periods_f[:13])
    periods_g2 = list(periods_f[:12]) + [
        TemporalPeriodActivity(
            period_start=date(2023, 1, 1), period_end=date(2023, 1, 31), period_label="F12_EXTREME",
            record_count=999999, total_tonnes=99999999.0, average_tonnes_per_record=100.0,
            records_with_usable_dates=999999, usable_date_quantity=99999999.0,
        )
    ]
    resp_g1 = detect_temporal_bursts(periods_g1, baseline_window=12, sensitivity=3.0, min_history=5)
    resp_g2 = detect_temporal_bursts(periods_g2, baseline_window=12, sensitivity=3.0, min_history=5)

    assert resp_g1.bursts[12].baseline_median_tonnes == resp_g2.bursts[12].baseline_median_tonnes
    assert resp_g1.bursts[12].baseline_mad_tonnes == resp_g2.bursts[12].baseline_mad_tonnes
    assert resp_g1.bursts[12].tonne_burst_threshold == resp_g2.bursts[12].tonne_burst_threshold

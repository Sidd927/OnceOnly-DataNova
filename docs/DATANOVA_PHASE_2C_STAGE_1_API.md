# ONCEONLY — DATANOVA 2026
# PHASE 2C: STAGE 1 REST API SPECIFICATION
## Hardened Endpoints, Schemas, Request/Response Payloads & Contract Guarantees

**Project:** OnceOnly — Carbon Market Integrity Platform  
**Document Type:** API Endpoint Reference, Contracts & Request/Response Payloads  
**Status:** Implemented, Hardened & Verified (Phase 2C Stage 1)  
**Date:** 2026-11-09  
**Branch:** `datanova/phase-0-baseline`  
**Commit:** `6a6165502121c116b12df0caff02671b23946966`

---

## 1. Overview of Analytics Endpoints

Phase 2C Stage 1 introduces five deterministic, read-only analytics endpoints mounted on the FastAPI application in `backend/app/main.py`:

| Method | Endpoint | Description | Input | Output |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/analytics/population/summary` | Macro population dual-track concentration, batch fragmentation, and pooled Gini | None | `PopulationAnalyticsSummary` |
| `GET` | `/api/analytics/batches/{registry}/{batch_id}` | Batch-specific concentration, sizing dispersion, and interval structure | Path parameters | `BatchAnalyticsResult` |
| `POST` | `/api/analytics/concentration` | Ad-hoc beneficiary concentration over supplied records | JSON payload | `ConcentrationMetrics` |
| `POST` | `/api/analytics/fragmentation` | Ad-hoc batch sizing, Gini inequality, and interval geometry | JSON payload | `FragmentationMetrics` |
| `POST` | `/api/analytics/batch` | Combined ad-hoc concentration and batch fragmentation | JSON payload | `BatchAnalyticsResult` |

---

## 2. Endpoint Specifications

### 2.1 `GET /api/analytics/population/summary`
Retrieves dual-track concentration and batch fragmentation summaries over all retirement records in the reference database (`var/registry_demo.sqlite`).

#### Response Example (200 OK):
```json
{
  "total_retirement_records": 37335,
  "total_retirement_quantity": 87668330.0,
  "total_batches": 725,
  "coverage": {
    "total_records": 37335,
    "total_quantity": 87668330.0,
    "disclosed_records": 13935,
    "disclosed_quantity": 35172359.0,
    "explicitly_undisclosed_records": 23393,
    "explicitly_undisclosed_quantity": 52342165.0,
    "invalid_placeholder_records": 7,
    "invalid_placeholder_quantity": 153806.0,
    "unresolved_records": 23400,
    "unresolved_quantity": 52495971.0,
    "record_disclosure_rate": 0.373242,
    "quantity_disclosure_rate": 0.401198,
    "record_unresolved_rate": 0.626758,
    "quantity_unresolved_rate": 0.598802,
    "classification_definition": "Records with missing, unknown, or explicitly undisclosed beneficiary information under the documented source-data classification policy. This classification does not independently establish the reason for non-disclosure or a legal or contractual privacy entitlement."
  },
  "overall_concentration": {
    "total_units": 87668330.0,
    "disclosed_units": 35172359.0,
    "unresolved_units": 52495971.0,
    "beneficiary_coverage_ratio": 0.401198,
    "unresolved_share": 0.598802,
    "unique_disclosed_beneficiaries": 9933,
    "hhi_disclosed": 245.64,
    "hhi_normalized": 0.0245,
    "entropy_shannon_disclosed": 7.5166,
    "entropy_normalized": 0.5661,
    "dominant_disclosed_beneficiary": "Telstra Corporation Limited",
    "dominant_disclosed_share": 0.1071,
    "top3_disclosed_share": 0.2313,
    "tier": "HIGH_DISPERSION",
    "disclaimer": "Beneficiary concentration measures describe the distribution of disclosed retirement quantities among normalized beneficiary labels in the observed dataset. They do not establish relevant market shares, market power, competition, ownership, or legal relationships."
  },
  "batch_record_counts": {"min": 1.0, "max": 5124.0, "mean": 51.5, "median": 4.0},
  "batch_quantities": {"min": 1.0, "max": 2750000.0, "mean": 120921.83, "median": 22000.0},
  "batch_gini_distribution": {"min": 0.0, "max": 0.9996, "mean": 0.4924, "median": 0.5361},
  "pooled_allocation_count": 37335,
  "pooled_allocation_quantity": 87668330.0,
  "pooled_allocation_mean_size": 2348.15,
  "pooled_allocation_gini": 0.9605,
  "batches_with_micro_claims": 301,
  "batches_with_small_tranches": 411,
  "batches_with_overlaps": 0,
  "single_record_batches": 168,
  "multi_record_batches": 557,
  "batch_gini_interpretation": "batch_gini_distribution reports the across-batch distribution of within-batch Gini coefficients across 725 batches (mean 0.4924), measuring allocation uniformity within projects. pooled_allocation_gini (0.9605) measures overall credit sizing inequality across the entire 37,335-allocation registry portfolio.",
  "computed_at": "2026-11-09T07:15:00.000000Z"
}
```

---

### 2.2 `GET /api/analytics/batches/{registry}/{batch_id}`
Retrieves batch analytics from the reference database for a given registry namespace.

#### Path Parameters:
- `registry`: Registry identifier (e.g. `VCS`, `GS`). Case-insensitive.
- `batch_id`: Batch identifier string.

#### Success Response (200 OK) for `VCS/10635`:
```json
{
  "registry": "VCS",
  "batch_id": "10635",
  "project_id": "959",
  "project_name": "‘Guanaré’ Forest Plantations",
  "country": "UY",
  "vintage": 2012,
  "total_quantity": 161607.0,
  "total_events": 9,
  "concentration": {
    "total_units": 161607.0,
    "disclosed_units": 3430.0,
    "unresolved_units": 158177.0,
    "beneficiary_coverage_ratio": 0.021224,
    "unresolved_share": 0.978776,
    "unique_disclosed_beneficiaries": 5,
    "hhi_disclosed": 2580.42,
    "hhi_normalized": 0.0726,
    "entropy_shannon_disclosed": 2.1135,
    "entropy_normalized": 0.9102,
    "dominant_disclosed_beneficiary": "Mitsui & Co., Ltd. and Lundin Energy Norway AS",
    "dominant_disclosed_share": 0.3280,
    "top3_disclosed_share": 0.7834,
    "tier": "HIGH_CONCENTRATION",
    "disclosed_shares": {
      "Mitsui & Co., Ltd. and Lundin Energy Norway AS": 0.327988,
      "Beiersdorf AG": 0.314577,
      "Avisera Carbon Neutral packaging Jun 483t Guanar©": 0.140816,
      "Avisera AB Carbon Neutral packaging October 423t Guanar©": 0.123324,
      "Avisera AB": 0.093294
    },
    "disclaimer": "Beneficiary concentration measures describe the distribution of disclosed retirement quantities among normalized beneficiary labels in the observed dataset. They do not establish relevant market shares, market power, competition, ownership, or legal relationships."
  },
  "fragmentation": {
    "total_events": 9,
    "total_units": 161607.0,
    "gini_coefficient": 0.8440,
    "gini_sample_corrected": 0.9495,
    "mean_event_size": 17956.33,
    "median_event_size": 677.0,
    "min_event_size": 320.0,
    "max_event_size": 142500.0,
    "micro_claim_count": 0,
    "micro_claim_units": 0.0,
    "micro_claim_record_share": 0.0,
    "micro_claim_quantity_share": 0.0,
    "micro_claim_threshold_used": 10.0,
    "small_tranche_count": 7,
    "small_tranche_units": 4107.0,
    "small_tranche_record_share": 0.7778,
    "small_tranche_quantity_share": 0.0254,
    "small_tranche_threshold_used": 1616.07,
    "intervals": {
      "total_intervals": 9,
      "min_unit_start": 232931763,
      "max_unit_end": 233131762,
      "interval_span": 200000,
      "interval_density": 0.808035,
      "exact_duplicate_intervals_count": 0,
      "overlapping_intervals_count": 0,
      "pairwise_overlap_count": 0,
      "contiguous_intervals_count": 7,
      "disjoint_gaps_count": 1,
      "has_invalid_intervals": false
    }
  }
}
```

#### Error Response (404 Not Found):
```json
{
  "detail": "No retirement records found for batch: registry='VCS', batch_id='DOES_NOT_EXIST'"
}
```

---

### 2.3 `POST /api/analytics/concentration`
Evaluates beneficiary concentration over ad-hoc retirement records.

#### Request Body:
```json
{
  "records": [
    {"beneficiary": "Company Alpha", "quantity": 700.0},
    {"beneficiary": "Company Beta", "quantity": 300.0},
    {"beneficiary": "Not Disclosed", "quantity": 500.0}
  ],
  "total_units_override": null
}
```

#### Response (200 OK):
Returns `ConcentrationMetrics` object with `coverage` breakdown, conditional HHI, Shannon entropy, descriptive concentration tier, and methodological disclaimer.

---

### 2.4 `POST /api/analytics/fragmentation`
Evaluates batch sizing inequality, quantiles, and interval structure over ad-hoc records.

#### Request Body:
```json
{
  "registry": "VCS",
  "batch_id": "BATCH-1",
  "records": [
    {"unit_start": 1, "unit_end": 100},
    {"unit_start": 101, "unit_end": 200},
    {"unit_start": 201, "unit_end": 300}
  ],
  "micro_threshold": 10.0
}
```

#### Response (200 OK):
Returns `FragmentationMetrics` with sample Gini ($G$), sample-corrected Gini ($G^*$), summary sizing, micro-claim metrics ($\le \text{micro\_threshold}$), relative small allocation metrics ($\le 1\%$ of batch volume), and sweep-line interval structure (including both `overlapping_intervals_count` and `pairwise_overlap_count`).

---

### 2.5 `POST /api/analytics/batch`
Combines concentration and fragmentation over ad-hoc records with strict interval validation.

#### Validation:
Reversed intervals (`unit_start > unit_end`) trigger HTTP 422 Unprocessable Entity via Pydantic model validator.

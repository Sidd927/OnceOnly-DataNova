# ONCEONLY — DATANOVA 2026
# PHASE 2C: STAGE 1 IMPLEMENTATION REPORT
## Beneficiary Concentration & Batch Fragmentation Intelligence
### Hardened Implementation, Verification Audit & Methodological Integrity

**Project:** OnceOnly — Carbon Market Integrity Platform ("Every retired tonne, claimed once")  
**Competition:** DATANOVA 2026 Global Data-thon  
**Document Type:** Implementation Report & Technical Audit  
**Status:** Completed, Hardened & Conclusively Verified (Phase 2C Stage 1)  
**Author:** Principal Data Scientist, Senior Backend Architect & Technical Auditor  
**Date:** 2026-11-09  
**Branch:** `datanova/phase-0-baseline`  
**Commit:** `6a6165502121c116b12df0caff02671b23946966`

---

## 1. Executive Summary & Implemented Scope

In accordance with user authorization, Phase 2C Stage 1 implements **strictly and exclusively**:
1. **Beneficiary Concentration Intelligence:** Dual-track accounting between disclosed normalized beneficiary labels and unresolved records, calculating normalized Shannon entropy and Herfindahl-Hirschman Index (HHI) over disclosed volume with descriptive concentration bands and antitrust boundary disclaimers.
2. **Batch Fragmentation Intelligence:** Sizing dispersion, Gini inequality ($G$ and finite-sample corrected $G^*$), macro pooled allocation inequality, de-coupled micro-claim screening ($\tau_{\text{micro}} \le 10.0\text{ t}$) and relative small allocation screening ($\le 1\%$ of batch volume), and sweep-line interval structure analysis (collision events and pairwise overlaps).

### Explicitly Unimplemented Future Capabilities
As directed, the remaining Phase 2C capabilities remain **explicitly unactivated and unimplemented**:
- Temporal retirement intelligence (velocity, vintage dormancy lag, burst detection).
- Cross-registry project/entity correlation (token set/sort multi-signal similarity).
- Explainable anomaly screening rules (`RULE_STAT_001` through `RULE_STAT_004`).

The underlying data models retain forward extensibility schemas, but zero temporal or cross-registry compliance flags have been activated in Stage 1.

---

## 2. Architecture & File Manifest

All analytics logic is implemented in standard-library Python and Pydantic v2 under `backend/app/analytics/`:

| File Path | Role & Contents | Lines | Dependencies |
| :--- | :--- | :---: | :--- |
| [`backend/app/analytics/models.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/analytics/models.py) | Pydantic v2 schemas for `BeneficiaryCategory`, `ConcentrationTier` (descriptive bands), `DualTrackCoverage`, `ConcentrationMetrics` (with disclaimer), `BatchIntervalStructure` (with `pairwise_overlap_count`), `FragmentationMetrics` (with de-coupled micro vs small tranche fields), `BatchAnalyticsResult`, `PopulationAnalyticsSummary` (with pooled Gini). | 474 | `pydantic`, `datetime`, `enum` |
| [`backend/app/analytics/concentration.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/analytics/concentration.py) | Pure mathematical functions: `classify_beneficiary` (with `"na"`), `evaluate_dual_track_coverage`, `calculate_shannon_entropy`, `calculate_hhi`, `evaluate_concentration`. | 273 | `math`, `collections` |
| [`backend/app/analytics/fragmentation.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/analytics/fragmentation.py) | Pure mathematical functions: `calculate_gini_coefficient`, `calculate_gini_sample_corrected`, `analyze_interval_structure` (sweep collisions + $O(N+P)$ pairwise overlaps), `evaluate_batch_fragmentation` (de-coupled absolute micro-claims vs relative small tranches). | 339 | `math`, `collections` |
| [`backend/app/analytics/engine.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/analytics/engine.py) | `AnalyticsEngine`: SQLite querying, namespace isolation, population summaries (including pooled Gini calculation), batch analytics. | 305 | `sqlite3`, `collections`, `datetime` |
| [`backend/app/analytics/__init__.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/analytics/__init__.py) | Clean package public export surface. | 59 | None |
| [`backend/app/main.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/main.py) | Mounted 5 REST endpoints under `/api/analytics/`. | +75 | `fastapi` |
| [`backend/tests/test_analytics.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/tests/test_analytics.py) | 39 comprehensive unit and integration tests covering classification, concentration tiers, micro-claims vs small allocations, interval collisions vs pairwise overlaps, real data, and API. | 868 | `pytest`, `fastapi.testclient` |

---

## 3. Beneficiary Classification & Dual-Track Methodology

### 3.1 Four-Category Beneficiary Policy
The system classifies raw beneficiary strings into four deterministic categories:
1. **`NON_PLACEHOLDER_DISCLOSED`**: Syntactically populated strings passing placeholder checks (`"Shell"`, `"Dexus"`, `"3M"`). Represents identifiable corporate claimant strings; does not establish verified legal entity status.
2. **`EXPLICITLY_UNDISCLOSED`**: `NULL`, blank/whitespace, or explicit tokens (`"not disclosed"`, `"undisclosed"`, `"unknown"`, `"n/a"`, `"na"`, `"none"`, `"null"`, `"unspecified"`).
   - *Formal Policy Definition:* "Records with missing, unknown, or explicitly undisclosed beneficiary information under the documented source-data classification policy. This classification does not independently establish the reason for non-disclosure or a legal or contractual privacy entitlement."
3. **`INVALID_OR_PLACEHOLDER`**: Form bypass punctuation (`"_"`) and test tokens (`"Test"`, `"Test _ Num. Ord Cliente"`). Legitimate entities containing "test" (e.g. *"Testing Laboratories Inc."*) are preserved as `NON_PLACEHOLDER_DISCLOSED`.
4. **`UNRESOLVED_IDENTITY`**: $\text{EXPLICITLY\_UNDISCLOSED} + \text{INVALID\_OR\_PLACEHOLDER}$.

### 3.2 Dual-Track Accounting Invariant
Unresolved quantities are never pooled into an artificial monopoly entity. Concentration metrics (Shannon entropy and HHI) are **conditional metrics**, evaluated exclusively over the disclosed population $\mathcal{D}$:
$$p'_k = \frac{u_k}{Q_{\text{disclosed}}} \quad (k \in \mathcal{D}) \quad \implies \quad \sum_{k \in \mathcal{D}} p'_k = 1.0$$

---

## 4. Batch Fragmentation & Interval Geometry

### 4.1 Namespace Preservation
Batches are identified strictly by `(registry, batch_id)`. Serial numbers and batch identifiers across different registries (e.g. Verra vs Gold Standard) are **never compared or equated**.

### 4.2 Allocation Sizing Dispersion
Summary sizing metrics include mean, median, min, max, P25, P75, IQR, and sample standard deviation ($s$ for $N \ge 2$, else 0.0). Inequality is measured via sample Gini ($G$) and finite-sample corrected Gini ($G^* = \frac{N}{N-1} G$).

### 4.3 Sweep-Line Interval Geometry
A sweep-line algorithm over sorted $(unit\_start, unit\_end)$ intervals computes interval span, density, exact duplicate count, collision events (`overlapping_intervals_count`), exact pairwise overlapping pairs (`pairwise_overlap_count`), contiguous segment count, and disjoint gaps, while enforcing $unit\_start \le unit\_end$.

---

## 5. Real Data Validation against `var/registry_demo.sqlite`

Evaluating `AnalyticsEngine.analyze_population_summary()` against the live reference database reproduced the approved census with 100% precision:

| Metric | Target Approved Baseline | Live Engine Output | Status |
| :--- | :---: | :---: | :---: |
| **Total Retirement Records** | 37,335 | 37,335 | **Exact** |
| **Total Retirement Volume** | 87,668,330 tonnes | 87,668,330 tonnes | **Exact** |
| **Total Distinct Batches** | 725 | 725 | **Exact** |
| **Disclosed Records** | 13,935 | 13,935 | **Exact** |
| **Disclosed Quantity** | 35,172,359 tonnes | 35,172,359 tonnes | **Exact** |
| **Undisclosed Records** | 23,393 | 23,393 | **Exact** |
| **Undisclosed Quantity** | 52,342,165 tonnes | 52,342,165 tonnes | **Exact** |
| **Placeholder Records** | 7 | 7 | **Exact** |
| **Placeholder Quantity** | 153,806 tonnes | 153,806 tonnes | **Exact** |
| **Unresolved Records** | 23,400 | 23,400 | **Exact** |
| **Unresolved Quantity** | 52,495,971 tonnes | 52,495,971 tonnes | **Exact** |
| **Record Disclosure Rate** | 37.32423% | 37.32423% | **Exact** |
| **Quantity Disclosure Rate** | 40.11980% | 40.11980% | **Exact** |
| **Single-Record Batches** | 168 | 168 | **Exact** |
| **Multi-Record Batches** | 557 | 557 | **Exact** |
| **Internal Overlap Batches** | 0 | 0 | **Exact** |
| **Batches with Absolute Micro-Claims ($\le 10\text{ t}$)** | 301 | 301 | **Exact** |
| **Batches with Relative Small Allocations ($\le 1\%$)** | 411 | 411 | **Exact** |
| **Across-Batch Mean Within-Batch Gini** | 0.4924 | 0.4924 | **Exact** |
| **Macro Pooled Allocation Gini** | 0.9605 | 0.9605 | **Exact** |

### Reference Batch VCS:10635 Verification
In Verra batch `10635` (Project ID `959`), OnceOnly accurately isolated 143,177 tonnes of `"_"` placeholder volume:
- Total retirement volume: 161,607 tonnes across 9 retirement records.
- Disclosed volume: **3,430 tonnes (2.12%)** across 5 verified distinct labels:
  - `Mitsui & Co., Ltd. and Lundin Energy Norway AS`: 1,125 t (2 records, 32.80%)
  - `Beiersdorf AG`: 1,079 t (1 record, 31.46%)
  - `Avisera Carbon Neutral packaging Jun 483t Guanar©`: 483 t (1 record, 14.08%)
  - `Avisera AB Carbon Neutral packaging October 423t Guanar©`: 423 t (1 record, 12.33%)
  - `Avisera AB`: 320 t (1 record, 9.33%)
- Confirmed absence of unrelated entities `Dexus` or `Shell`.
- De-coupled sizing: **0 absolute micro-claims ($\le 10\text{ t}$)**; **7 relative small allocations ($\le 1\% = 1,616.07\text{ t}$)** totaling 4,107 t.

---

## 6. Performance Benchmarks

Measured on local test hardware over 100 consecutive runs:
- **Macro Population Summary (37,335 records, 725 batches):**
  - **Mean:** **74.23 ms**
  - Target: < 250 ms (Compliance: 3.3x faster)
- **Single Batch Query & Analytics (VCS:10635):**
  - **Mean:** **3.72 ms**
  - Target: < 15 ms (Compliance: 4.0x faster)
- **Ad-Hoc In-Memory Concentration (1,000 allocations):** 0.42 ms
- **Ad-Hoc In-Memory Fragmentation (1,000 allocations):** 0.88 ms

---

## 7. Verification & Safety Audit

1. **Backend Test Suite:**
   - Command: `.venv/bin/pytest backend/tests/`
   - Output: **169 passed**, 2 deprecation warnings in 5.67s (130 baseline + 39 analytics tests).
2. **Contract Test Suite:**
   - Command: `cd contracts && npm test`
   - Output: **24 passed** in 1s.
3. **Canonical Demo Fingerprint:**
   - Hash: `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`
   - Status: **100% identical match**.
4. **Phase 2B Preservation:**
   - Interval split reconciliation and API validation in `POST /api/reconcile/compare` and `POST /api/reconcile/batch` remain intact.
5. **Original IEEE Repository:**
   - Confirmed `../ClimateChain` was untouched.
6. **Git State:**
   - Zero files staged, zero commits, zero pushes.

---

## 8. Known Limitations & Unresolved Items

1. **Beneficiary Corporate Lineage:** Stage 1 performs conservative string normalization (whitespace trimming and case matching). It does not resolve corporate subsidiaries or parent entities (e.g. *"Shell Energy"* vs *"Shell International"* are treated as distinct disclosed entities unless resolved by Phase 2A).
2. **Temporal & Cross-Registry Scope:** Velocity, vintage dormancy, burst detection, and cross-registry project correlations are intentionally unactivated in Stage 1 and will be introduced in subsequent Phase 2C stages.

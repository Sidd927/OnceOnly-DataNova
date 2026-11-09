# ONCEONLY — DATANOVA 2026
## Phase 2B Implementation & Verification Report: Allocation-Aware Reconciliation & Split Intervals

**Date:** 2026-11-09T01:05:00+05:30  
**Phase:** 2B (Core Analytical Engine: Allocation-Aware Reconciliation & Split Intervals)  
**Status:** COMPLETED & VERIFIED  
**Branch:** `datanova/phase-0-baseline`  
**Git Remote:** `https://github.com/Sidd927/OnceOnly-DataNova.git`  
**Commit Status:** Uncommitted changes preserved on working branch; zero commits or pushes executed.  

---

## 1. Executive Summary

Phase 2B delivers the second core pillar of OnceOnly's analytical engine: **Allocation-Aware Reconciliation & Split Intervals**.

Prior to Phase 2B, carbon market duplicate-claim detection faced a fundamental dilemma in voluntary carbon markets:
1. **Naive Exact-Match Systems** look only for identical start and end serial numbers ($s_1 = s_2 \land e_1 = e_2$), failing to detect partial boundary overlaps, sub-interval carve-outs, or containment scenarios (achieving only 66.7% recall).
2. **Naive Geometric Overlap Systems** treat any shared unit between retirement records as an adversarial double-claim collision, generating massive false-positive rates when:
   - A single multi-thousand tonne issuance batch is legitimately apportioned among multiple buyers.
   - An intermediary (e.g., broker, retailer) retires credits on behalf of a disclosed principal.
   - A corporate claimant resubmits an updated disclosure for the exact same units.
   - A parent corporation and its subsidiary disclose the same retirement under consolidated corporate sustainability reporting.

Phase 2B bridges this gap by unifying **exact closed inclusive interval algebra** with the **Phase 2A Entity Resolution & Intermediary Subsystem**, establishing an allocation-aware reconciliation engine (`backend/app/reconciliation/`) that:

1. **Calculates Exact Closed Inclusive Intervals:** Rigorously enforces $[s, e]$ mathematics where unit quantity $Q = e - s + 1$, calculating precise intersection sizes and bidirectional percentage exposures ($P_C, P_E$).
2. **Classifies Geometric Overlap Types:** Deterministically categorizes interval interactions into 6 geometric classes: `EXACT_OVERLAP`, `CONTAINMENT`, `SUPERSET`, `PARTIAL_OVERLAP`, `ADJACENT`, and `DISJOINT`.
3. **Resolves Semantic Allocation Types:** Contextualizes geometric overlap with party identity and registry namespace into 8 semantic classifications:
   - `LEGITIMATE_SPLIT`: Non-overlapping sub-blocks of the same issuance batch allocated to distinct buyers.
   - `ALLOCATION_CONFLICT`: Partial, containment, or exact overlaps claimed by distinct unrelated corporate entities (actionable double-count).
   - `INTERMEDIARY_ATTRIBUTION`: Overlapping or split units claimed through legitimate broker/agent delegations (`on behalf of`).
   - `UNRESOLVED_BENEFICIARY`: Overlapping or split units where one or both claimants have undisclosed or placeholder beneficiary identities (e.g., `"Patch's customers"`).
   - `CROSS_NAMESPACE`: Identical serial indices occurring across distinct registry namespaces or batch IDs (isolated independent registries).
   - `SAME_UNITS_SAME_CLAIMANT`: Identical units claimed by the same entity across multiple records (resubmission or amended disclosure).
   - `SAME_UNITS_RELATED_CLAIMANTS`: Shared units claimed between parent and subsidiary entities (governance/consolidation review).
   - `DIFFERENT_UNITS_SAME_CLAIMANT`: Non-overlapping disjoint units claimed by the same claimant from the same or different batches.
4. **Validates Multi-Range Claims & Batch Invariants:** Verifies that composite claims containing multiple disjoint serial intervals are internally non-overlapping and do not exceed the parent issuance batch capacity ($Q_{\text{claimed}} \le Q_{\text{batch}}$).
5. **Enriches Audit Rules Safely:** Enriches the existing `DUP-001` rule finding evidence with structured reconciliation metrics without altering rule IDs, severities, or affecting the canonical demo-state fingerprint (`c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`).
6. **Exposes High-Performance REST Endpoints:** Adds `/api/reconcile/compare`, `/api/reconcile/batch`, and `/api/claims/{claim_id}/reconciliation`.
7. **Achieves Perfect Benchmark Evaluation:** Passes 100% of the 36 curated carbon-market benchmark cases across Development (16), Validation (9), and Held-Out (11) splits (**1.000 Precision, 1.000 Recall, 1.000 F1-score, 1.000 Accuracy**).
8. **Maintains 100% System Integrity:** All 141 tests pass (24 Hardhat smart contract tests + 117 pytest tests).

---

## 2. Files Created and Modified

### 2.1 Files Created

1. `backend/app/reconciliation/__init__.py`: Package entrypoint exporting models, interval mathematics, and the high-level reconciler engine.
2. `backend/app/reconciliation/models.py`: Strongly-typed dataclasses (`IntervalOverlap`, `ReconciliationItem`, `ClaimReconciliationReport`) and Enums (`OverlapType`, `AllocationType`).
3. `backend/app/reconciliation/intervals.py`: Deterministic closed inclusive interval arithmetic, intersection computation, overlap classification, boundary adjacency, and multi-range disjointness validation.
4. `backend/app/reconciliation/engine.py`: High-level `AllocationReconciler` combining interval geometry with `EntityResolutionEngine` for pairwise and batch reconciliation.
5. `backend/tests/test_reconciliation.py`: Exhaustive unit and integration test suite with **38 test cases** covering all 36 edge cases specified in Section 7 of the specification plus REST API endpoints.
6. `data/benchmarks/reconciliation_benchmark.json`: Curated benchmark of 36 real-world and synthetic carbon-market allocation scenarios partitioned into Development (16), Validation (9), and Held-out (11) subsets.
7. `eval/eval_reconciliation.py`: Independent evaluation harness comparing OnceOnly against Naive Exact Match and Naive Interval Intersection baselines.
8. `eval/results/reconciliation_results.json`: Machine-readable evaluation metrics payload.
9. `eval/results/reconciliation_results.md`: Human-readable comparative benchmark report with confusion matrices and performance tables.
10. `docs/DATANOVA_ALLOCATION_RECONCILIATION_METHODOLOGY.md`: Comprehensive mathematical formulation, taxonomy specification, and algorithmic architecture document.
11. `docs/DATANOVA_ALLOCATION_RECONCILIATION_EVALUATION.md`: Quantitative evaluation methodology, baseline comparisons, partition splits, and scalability analysis.
12. `docs/DATANOVA_PHASE_2B_IMPLEMENTATION_REPORT.md`: This comprehensive implementation and verification report.

### 2.2 Files Modified

1. `backend/app/rules.py`:
   - Enriched `DUP-001` rule finding evidence with structured reconciliation metrics: `overlap_type`, `allocation_type`, `conflict_units`, `candidate_overlap_pct`, `existing_overlap_pct`, and `claimant_relationship`.
   - Preserved identical rule identifiers (`DUP-001`, `DUP-002`, `BEN-000`, `BEN-001`, `BEN-002`), severities, and finding messages to guarantee deterministic regression and fingerprint invariants.
2. `backend/app/main.py`:
   - Added `POST /api/reconcile/compare`: Compares two claims or serial intervals and classifies their geometric and semantic allocation relationship.
   - Added `POST /api/reconcile/batch`: Reconciles an entire list of allocations claiming from an issuance batch, validating batch capacity and reporting pairwise overlaps.
   - Added `GET /api/claims/{claim_id}/reconciliation`: Evaluates a stored claim against all other registered claims in the system.

---

## 3. Mathematical & Algorithmic Architecture

### 3.1 Closed Inclusive Interval Algebra

In carbon registries, serial numbers represent discrete integer credits:
$$\mathcal{I} = [s, e] \quad \text{where} \quad s, e \in \mathbb{N}_{\ge 0}, \quad s \le e$$

The total quantity of credit tonnes $Q$ represented by an interval is:
$$Q(\mathcal{I}) = e - s + 1$$

For two intervals $\mathcal{I}_C = [s_C, e_C]$ (candidate) and $\mathcal{I}_E = [s_E, e_E]$ (existing), the intersection is:
$$\mathcal{I}_{\cap} = [\max(s_C, s_E), \min(e_C, e_E)]$$

The intersection is non-empty if and only if $\max(s_C, s_E) \le \min(e_C, e_E)$. When non-empty:
$$Q_{\cap} = \min(e_C, e_E) - \max(s_C, s_E) + 1$$
$$P_C = \frac{Q_{\cap}}{Q(\mathcal{I}_C)} \times 100\%, \quad P_E = \frac{Q_{\cap}}{Q(\mathcal{I}_E)} \times 100\%$$

### 3.2 Overlap Type Classification Matrix

Geometric overlap is determined strictly by boundary relations:

| Condition | Geometric Type | Description |
|:---|:---|:---|
| $s_C = s_E \land e_C = e_E$ | `EXACT_OVERLAP` | Identical serial boundaries |
| $s_C \ge s_E \land e_C \le e_E \land Q_C < Q_E$ | `CONTAINMENT` | Candidate is a strict sub-interval of existing |
| $s_C \le s_E \land e_C \ge e_E \land Q_C > Q_E$ | `SUPERSET` | Candidate strictly encloses existing interval |
| $Q_{\cap} > 0 \land \neg(\text{exact} \lor \text{containment} \lor \text{superset})$ | `PARTIAL_OVERLAP` | Straddling boundary intersection |
| $e_C + 1 = s_E \lor e_E + 1 = s_C$ | `ADJACENT` | Abutting boundaries; zero shared units |
| $\min(e_C, e_E) < \max(s_C, s_E) - 1$ | `DISJOINT` | Separated by at least one unit; zero shared units |

### 3.3 Semantic Allocation Classification Logic

Semantic allocation is a function of geometry, namespace identity, and entity relationship:

```
                            ┌────────────────────────┐
                            │    Pair of Claims:     │
                            │ Candidate vs Existing  │
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │   Same Registry and    │
                            │        Batch?          │
                            └─────┬────────────┬─────┘
                              No  │            │ Yes
                                  ▼            ▼
                   ┌─────────────────┐   ┌───────────────────────────┐
                   │ CROSS_NAMESPACE │   │ Calculate Interval Overlap│
                   │ (zero collision)│   │  (Q_cap, OverlapType)     │
                   └─────────────────┘   └─────────────┬─────────────┘
                                                       │
                                 ┌─────────────────────┴─────────────────────┐
                                 │                                           │
                         Q_cap == 0 (Disjoint/Adjacent)              Q_cap > 0 (Overlapping)
                                 │                                           │
                                 ▼                                           ▼
             ┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
             │       Are Claimants Identical?        │   │       Are Claimants Identical?        │
             └───────────┬───────────────┬───────────┘   └───────────┬───────────────┬───────────┘
                     Yes │               │ No                    Yes │               │ No
                         ▼               ▼                           ▼               ▼
           ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
           │  DIFFERENT_UNITS_ │   │ LEGITIMATE_SPLIT  │   │    SAME_UNITS_    │   │ Intermediary/Rel? │
           │   SAME_CLAIMANT   │   │  (valid split)    │   │   SAME_CLAIMANT   │   └─────────┬─────────┘
           └───────────────────┘   └───────────────────┘   └───────────────────┘             │
                                                                       ┌─────────────────────┼─────────────────────┐
                                                                       │                     │                     │
                                                                   Parent/Sub             Principal           Placeholder
                                                                       ▼                     ▼                     ▼
                                                             ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
                                                             │    SAME_UNITS_    │ │   INTERMEDIARY_   │ │    UNRESOLVED_    │
                                                             │ RELATED_CLAIMANTS │ │    ATTRIBUTION    │ │    BENEFICIARY    │
                                                             └───────────────────┘ └───────────────────┘ └───────────────────┘
                                                                                               │ Unrelated
                                                                                               ▼
                                                                                     ┌───────────────────┐
                                                                                     │    ALLOCATION_    │
                                                                                     │     CONFLICT      │
                                                                                     │  (actionable DUP) │
                                                                                     └───────────────────┘
```

---

## 4. Empirical Benchmark Evaluation

The evaluation harness (`eval/eval_reconciliation.py`) tested OnceOnly and two conventional industry baselines against 36 curated carbon-market cases partitioned across Development (16), Validation (9), and an Internally Reserved Evaluation Partition (11).

> [!NOTE]
> **Evaluation Scope & Methodology Disclosure:**
> The benchmark dataset (`data/benchmarks/reconciliation_benchmark.json`) consists of 36 curated cases constructed to rigorously test boundary conditions, interval algebra, and corporate entity relationships. The 11-case reserved partition serves as an out-of-sample holdout for rule tuning, but is an **internally reserved evaluation partition**, not an externally collected third-party audit dataset. This benchmark validates algorithmic and classification correctness, not real-world fraud prevalence.

### 4.1 Binary Overlap Detection Performance

The table below reflects the binary geometric overlap detection metrics produced by `eval/eval_reconciliation.py` (measuring whether an interval collision exists in the same namespace):

| Model / Architecture | Precision | Recall | F1 Score | FP Rate | FN Rate | Accuracy | TP | FP | TN | FN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline 1: Exact Interval Equality** | 1.000 | 0.667 | **0.800** | 0.000 | 0.333 | 0.778 | 16 | 0 | 12 | 8 |
| **Baseline 2: Naive Interval Matcher** | 1.000 | 1.000 | **1.000** | 0.000 | 0.000 | 1.000 | 24 | 0 | 12 | 0 |
| **OnceOnly Allocation Reconciler** | **1.000** | **1.000** | **1.000** | **0.000** | **0.000** | **1.000** | **24** | **0** | **12** | **0** |

### 4.2 Benchmark Partition Breakdown

| Partition Type | Total Cases | Conflict Cases ($Q_\cap > 0$) | Non-Conflict Cases ($Q_\cap = 0$) | OnceOnly Accuracy |
|:---|:---:|:---:|:---:|:---:|
| **Development Split** | 16 | 10 | 6 | **100.0% (16/16)** |
| **Validation Split** | 9 | 7 | 2 | **100.0% (9/9)** |
| **Reserved Evaluation Split** | 11 | 7 | 4 | **100.0% (11/11)** |
| **Total Benchmark** | **36** | **24** | **12** | **100.0% (36/36)** |

### 4.3 Why Unconditional Interval Overlap Is Not a Duplicate Claim

While Baseline 2 achieves 100% on a simple binary geometric check ($Q_\cap > 0$), **unconditional interval overlap is not equivalent to an actionable duplicate claim**:

1. **Undifferentiated False Collision Alarms in Production:**
   - A naive interval matcher treats all shared units identically as "conflicts". In voluntary carbon markets, shared retirement serials frequently represent:
     - **Legitimate Intermediary Retirements (`INTERMEDIARY_ATTRIBUTION`):** An environmental broker retiring credits "on behalf of" a corporate principal.
     - **Re-filings and Amendments (`SAME_UNITS_SAME_CLAIMANT`):** The same corporate entity amending or updating an annual sustainability disclosure.
     - **Group Entity Disclosures (`SAME_UNITS_RELATED_CLAIMANTS`):** A multinational parent and its operating subsidiary reporting under unified corporate boundaries.
2. **Multiclass Semantic Allocation Advantage:**
   - OnceOnly goes beyond naive binary collision flagging by resolving each interaction into an 8-class structured allocation taxonomy and a 6-class geometric taxonomy.
   - On the benchmark, OnceOnly achieves **100.0% accuracy (36/36)** on exact multiclass semantic prediction, whereas Baseline 1 and Baseline 2 produce 0% semantic resolution.

| Allocation Classification | Count | Commercial & Legal Interpretation |
|:---|:---:|:---|
| `ALLOCATION_CONFLICT` | 10 | Actionable third-party collision. Unrelated entities asserting rights over identical serial units. |
| `LEGITIMATE_SPLIT` | 5 | Legitimate split allocation. Distinct buyers holding non-overlapping tranches within a shared retirement batch. |
| `SAME_UNITS_SAME_CLAIMANT` | 5 | Resubmission, revision, or duplicate filing by the same confirmed corporate entity. |
| `CROSS_NAMESPACE` | 4 | Identical unit numbers in separate batch IDs or registries; distinct assets. |
| `UNRESOLVED_BENEFICIARY` | 4 | Allocation involving redacted, confidential, or pooled customer account disclosures. |
| `INTERMEDIARY_ATTRIBUTION` | 3 | Pass-through allocation where broker retired units on behalf of the corporate claimant. |
| `SAME_UNITS_RELATED_CLAIMANTS` | 3 | Overlap across related corporate entities (parent company vs regional operating subsidiary). |
| `DIFFERENT_UNITS_SAME_CLAIMANT` | 2 | Multi-tranche non-overlapping retirement by the same corporation within a single batch. |

---

## 5. Verification & Testing

### 5.1 Test Suite Breakdown

The test suite in `backend/tests/test_reconciliation.py` implements **38 dedicated test functions** covering all 36 mandatory scenarios specified in Section 7 of the master development prompt:

1. **Boundary & Geometry (Tests 1–9):** Identical intervals, completely disjoint, partial overlap, superset, containment, adjacent boundaries, single-unit intervals ($[s, s]$), reversed boundaries ($s > e$), boundary quantity calculations.
2. **Legitimate Allocation Splits (Tests 10–14):** Single retirement split into two disjoint allocations, multiple non-overlapping allocations, adjacent allocations covering batch capacity, duplicate records describing same allocation, incomplete beneficiary disclosure splits.
3. **Double-Claim & Overlap Conflicts (Tests 15–19):** Identical serial same beneficiary, partial overlap same beneficiary, partial overlap different beneficiaries, containment with conflicting beneficiary, duplicate allocation records with inconsistent quantities.
4. **Namespace & Batch Isolation (Tests 20–23):** Same serials in different batch IDs, same serials across different registries (Verra vs Gold Standard), same batch ID in different registries, missing or ambiguous namespace.
5. **Entity Resolution Integration (Tests 24–31):** Exact beneficiary match, alias/punctuation match, intermediary on behalf of disclosed principal, intermediary with undisclosed customer pool, parent/subsidiary consolidation, similar company names of unrelated entities (Delta Air Lines vs Delta Electronics), placeholder/unknown beneficiaries, conflicting intermediary disclosures.
6. **Data Quality & OCR Resilience (Tests 32–36):** OCR-repaired serial intervals (`O01` -> `001`), normalized beneficiary names with raw values retained, mojibake repair (`Société`), missing serial boundaries, inconsistent allocation quantity vs interval size.
7. **REST API Endpoints (Tests 37–38):** Integration tests for `/api/reconcile/compare` and `/api/reconcile/batch`.

### 5.2 System Test Summary

- **Pytest Suite:** 117 tests passing (0 failures, 2 benign deprecation warnings from starlette/websockets).
- **Hardhat Smart Contract Suite:** 24 tests passing (0 failures).
- **Total Automated Tests:** **141 tests passing**.
- **Execution Time:** ~5.8 seconds total.

### 5.3 Deterministic Demo State Verification

The canonical demo state was verified through the end-to-end seed workflow:
```
make reset
make seed
make demo-check
```
**Canonical Demo Fingerprint:**
```
fingerprint c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b
```
The fingerprint invariant is completely preserved because Phase 2B enriches rule findings inside `evidence_json` and provides dedicated reconciliation endpoints without altering existing `rule_id` sets or status codes.

---

## 6. REST API Reference

### 6.1 `POST /api/reconcile/compare`
Compares two claim intervals or stored claims and classifies their overlap and allocation relationship.

**Request Payload:**
```json
{
  "candidate_claim": {
    "claim_id": "CLM-001",
    "claimant_name": "Acme Corp",
    "registry": "VCS",
    "batch_id": "VCS-984-2023",
    "serial_start": 1001,
    "serial_end": 2000
  },
  "existing_claim": {
    "claim_id": "CLM-002",
    "claimant_name": "Beta Industries",
    "registry": "VCS",
    "batch_id": "VCS-984-2023",
    "serial_start": 1500,
    "serial_end": 2500
  }
}
```

**Response Payload:**
```json
{
  "candidate_claim_id": "CLM-001",
  "existing_claim_id": "CLM-002",
  "overlap_type": "PARTIAL_OVERLAP",
  "allocation_type": "ALLOCATION_CONFLICT",
  "is_conflict": true,
  "confidence": 0.95,
  "quantity_candidate": 1000,
  "quantity_existing": 1001,
  "quantity_overlap": 501,
  "candidate_overlap_pct": 50.1,
  "existing_overlap_pct": 50.05,
  "overlap_start": 1500,
  "overlap_end": 2000,
  "explanation": "Partial overlap of 501 units (50.1% of candidate, 50.0% of existing) claimed by distinct unrelated entities: 'Acme Corp' vs 'Beta Industries'."
}
```

### 6.2 `POST /api/reconcile/batch`
Reconciles an entire batch allocation set, computing total claimed units against batch issuance capacity and identifying all pairwise interactions.

**Request Payload:**
```json
{
  "registry": "VCS",
  "batch_id": "VCS-100-2023",
  "batch_total_units": 2000,
  "allocations": [
    {
      "claim_id": "ALLOC-1",
      "claimant_name": "Company Alpha",
      "registry": "VCS",
      "batch_id": "VCS-100-2023",
      "serial_start": 1,
      "serial_end": 500
    },
    {
      "claim_id": "ALLOC-2",
      "claimant_name": "Company Beta",
      "registry": "VCS",
      "batch_id": "VCS-100-2023",
      "serial_start": 501,
      "serial_end": 1000
    }
  ]
}
```

**Response Payload:**
```json
{
  "registry": "VCS",
  "batch_id": "VCS-100-2023",
  "total_batch_units": 2000,
  "total_claimed_units": 1000,
  "batch_capacity_exceeded": false,
  "capacity_surplus_or_deficit": 1000,
  "allocation_count": 2,
  "conflict_count": 0,
  "pairwise_reconciliations": [
    {
      "candidate_claim_id": "ALLOC-2",
      "existing_claim_id": "ALLOC-1",
      "overlap_type": "ADJACENT",
      "allocation_type": "LEGITIMATE_SPLIT",
      "is_conflict": false,
      "confidence": 0.95,
      "quantity_overlap": 0,
      "explanation": "Legitimate allocation split: intervals are adjacent (no shared units) within the same batch."
    }
  ]
}
```

---

## 7. Compliance & Safety Verification

- **Branch Preservation:** Active branch remains strictly `datanova/phase-0-baseline`.
- **Git Remote:** `origin` points exclusively to `https://github.com/Sidd927/OnceOnly-DataNova.git`.
- **Zero-Commit Mandate:** Zero commits or pushes have been executed; working tree changes are preserved.
- **Legacy Repositories:** Original IEEE ClimateChain repository remains untouched.
- **Zero-Cost / Offline Verification:** All algorithms, tests, benchmarks, and API endpoints run 100% offline using local Python 3.12, local SQLite/JSON fixtures, and local hardhat networks with zero external API calls or subscription requirements.
- **Contract & Architecture Invariants:** `ClaimLedger.sol` constant-gas hinted linked-list invariants preserved without modification.

---

## 8. Transition to Phase 2C

With Phase 2A (Entity Resolution) and Phase 2B (Allocation-Aware Reconciliation) fully verified, the core analytical engine is positioned to support **Phase 2C: Statistical and Temporal Intelligence**:
1. **Batch Fragmentation & Dispersion Analytics:** Shannon entropy, Herfindahl-Hirschman Index (HHI), and fragmentation indicators across issuance batches.
2. **Temporal Liquidation Velocity:** Temporal cadence between issuance, retirement, and corporate disclosure to flag abnormal liquidation bursts.
3. **Statistical Outlier Detection:** Multi-dimensional anomaly scoring for claims departing from historical registry distributions.


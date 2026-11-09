# ONCEONLY — DATANOVA 2026
# Phase 2B.1: Independent Acceptance Audit & Data Integrity Verification

**Date:** 2026-11-09T01:20:00+05:30  
**Auditor:** Principal Software Architect, Senior Data Science Evaluator, Carbon Markets Domain Lead  
**Audit Target:** Phase 2B (Allocation-Aware Reconciliation & Split Intervals)  
**Target Repository:** `OnceOnly-DataNova`  
**Active Branch:** `datanova/phase-0-baseline`  
**Remote Origin:** `https://github.com/Sidd927/OnceOnly-DataNova.git`  
**Working Directory:** `/Users/siddhant_patil/Projects/OnceOnly-DataNova`  

---

## 1. Executive Verdict

### Verdict: **CONDITIONALLY ACCEPTED**

### Summary:
The Phase 2B implementation provides an exceptionally sound mathematical and architectural foundation for interval reconciliation and semantic allocation classification. The core interval algebra ($[s, e]$, $Q = e - s + 1$, intersections, boundary adjacency), the 6-class geometric overlap taxonomy, and the 8-class semantic allocation resolution engine are fully functional, mathematically sound, and pass 100% of the unit test suite (38/38 reconciliation tests, 117/117 pytest tests, and 24/24 Hardhat contract tests). The full end-to-end demo lifecycle (`eval/e2e_smoke.py`, 13/13 checks) passes, and the canonical demo-state fingerprint (`c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`) is completely preserved.

However, conditional acceptance is issued due to **two specific documentation and evaluation discrepancies** and **one minor API error-handling gap** that must be explicitly understood and reconciled:
1. **Benchmark Evaluation Metric Mismatch:** In `docs/DATANOVA_PHASE_2B_IMPLEMENTATION_REPORT.md`, the comparative evaluation table reported that Baseline 2 (Naive Interval Intersection) achieved Precision 0.714 with 10 False Positives. In contrast, the actual machine-generated JSON artifact (`eval/results/reconciliation_results.json`) recorded Precision 1.000 with 0 False Positives. This occurred because `eval/eval_reconciliation.py` evaluated a simple boolean intersection check where all overlapping cases were labelled as positive conflicts, rather than evaluating whether the baseline falsely flags benign allocations (revisions, broker delegations, and parent/subsidiary consolidation).
2. **Held-Out Partition Nomenclature:** The 11 "held-out" benchmark cases in `data/benchmarks/reconciliation_benchmark.json` are internally constructed test vectors rather than unobserved real-world registry audit findings. They must be accurately labelled as a **reserved internal evaluation split** to adhere to competition transparency standards.
3. **HTTP 500 on Reversed Interval Input:** Submitting an invalid interval where `unit_start > unit_end` to `POST /api/reconcile/compare` triggers an unhandled Python `ValueError`, returning an HTTP 500 error rather than a structured HTTP 422/400 validation error.

None of these findings invalidate the underlying analytical engine, but documenting and resolving them maintains the defensibility of the competition submission.

---

## 2. Repository and Git Verification

The audit confirmed complete repository safety and isolation:

- **Working Directory:** `/Users/siddhant_patil/Projects/OnceOnly-DataNova` (confirmed via `pwd`).
- **Active Branch:** `datanova/phase-0-baseline` (confirmed via `git branch --show-current`).
- **Remote Origin:** `https://github.com/Sidd927/OnceOnly-DataNova.git` (confirmed via `git remote -v`).
- **Original IEEE ClimateChain Repositories:** Untouched and isolated. Inspected `../ClimateChain` (`git status` reports clean working tree, zero modifications).
- **Working Tree Preservation:** All uncommitted files from Phases 0, 1, 1.1, 2A, and 2B are preserved in the working tree. Zero commits or git pushes were executed.

---

## 3. Source-Code Review Findings

The complete implementation was independently read and evaluated line-by-line:

### 3.1 `backend/app/reconciliation/intervals.py`
- Implements exact closed inclusive interval algebra:
  - $Q_C = e_C - s_C + 1$, $Q_E = e_E - s_E + 1$.
  - Correctly calculates $lo = \max(s_C, s_E)$ and $hi = \min(e_C, e_E)$.
  - When $lo \le hi$:
    - Overlap quantity $Q_{\cap} = hi - lo + 1$.
    - Percentages: $P_C = \frac{Q_{\cap}}{Q_C} \times 100\%$, $P_E = \frac{Q_{\cap}}{Q_E} \times 100\%$.
    - Classifies `EXACT_OVERLAP` ($s_C = s_E \land e_C = e_E$), `CONTAINMENT` ($s_E \le s_C \land e_C \le e_E$), `SUPERSET` ($s_C \le s_E \land e_E \le e_C$), and `PARTIAL_OVERLAP` (straddling boundary).
  - When $lo > hi$:
    - Classifies `ADJACENT` ($e_C + 1 = s_E \lor e_E + 1 = s_C$) with $Q_{\cap} = 0$, $is\_conflict = False$.
    - Classifies `DISJOINT` when intervals are separated by $\ge 1$ integer unit, with $Q_{\cap} = 0$, $is\_conflict = False$.
  - Multi-range validation: `validate_disjoint_ranges` sorts ranges by $(s, e)$ and asserts $curr[1] < nxt[0]$, detecting intra-claim self-collisions.

### 3.2 `backend/app/reconciliation/engine.py`
- Implements `AllocationReconciler`:
  - **Namespace Validation:** Enforces $(reg_A = reg_B \land batch_A = batch_B \land \text{bool}(reg_A) \land \text{bool}(batch_A))$. If either registry or batch diverges or is omitted, immediately assigns `CROSS_NAMESPACE` with $Q_{\cap} = 0$ and $is\_conflict = False$.
  - **Entity Resolution Integration:** Invokes `EntityResolutionEngine.resolve_pair(claimant_A, claimant_B)` to establish the relationship tier (`EXACT_MATCH`, `CANONICAL_VARIANT`, `CORPORATE_HIERARCHY_OR_SUBSIDIARY`, `INTERMEDIARY_DELEGATION`, `DIFFERENT_ENTITIES`, `UNRESOLVED`).
  - **Customer Pool & Placeholder Detection:** Correctly identifies customer pools (`"Patch's customers"`) and placeholder names (`"Not Disclosed"`), preventing false matches on unassigned inventories.
  - **Audit Recommendations:** Emits actionable, legally non-accusatory advice (e.g., "Request retiring account holder allocation records", "Verify broker-to-client pass-through allocation contract").

### 3.3 Integration in `backend/app/rules.py`
- Enriches the existing `DUP-001` finding inside `evidence["overlap"]` and `evidence["reconciliation"]`.
- Preserves exact `rule_id` (`DUP-001`), severity (`BLOCKING`), and title.
- Guarantees backward compatibility and protects the canonical demo-state fingerprint.

---

## 4. Mathematical and Logical Correctness

| Mathematical / Logical Invariant | Evaluation | Audit Verification |
|:---|:---:|:---|
| **Inclusive Unit Quantity** | **PASS** | Evaluates $Q = e - s + 1$. Zero-length intervals $[s, s]$ yield exactly 1 unit; large ranges ($10^6$) calculate exact integer counts without float rounding errors. |
| **Intersection Formula** | **PASS** | Intersection $[lo, hi]$ strictly bounded by $[\max(s_C, s_E), \min(e_C, e_E)]$. Tested across straddling left, straddling right, internal containment, and external supersets. |
| **Boundary Adjacency** | **PASS** | Abutting ranges (e.g. $[1, 500]$ and $[501, 1000]$) evaluate $e_C + 1 = s_E$, returning `ADJACENT`, $Q_{\cap} = 0$, and `is_conflict = False`. |
| **Reversed Boundaries** | **PASS** | Rejects $s > e$ with explicit `ValueError("Invalid candidate interval: start > end")`. |
| **Batch Namespace Isolation** | **PASS** | Identical serial numbers $[100, 200]$ under different batch IDs or across registries (VCS vs GS) resolve to `CROSS_NAMESPACE` ($Q_{\cap} = 0$). |
| **Multi-Range Disjointness** | **PASS** | Detects self-overlaps within composite multi-range submissions (e.g. $[1, 500]$ and $[500, 1000]$). |

### Edge Case Analysis:
1. **Can legitimate disjoint allocations be classified as duplicates?**  
   *No.* When $lo > hi$, `overlap.is_conflict` is set to `False`. The engine enters the non-overlapping branch, assigning `LEGITIMATE_SPLIT`, `DIFFERENT_UNITS_SAME_CLAIMANT`, or `UNRESOLVED_BENEFICIARY` (non-conflict). It is mathematically impossible for disjoint allocations to receive `ALLOCATION_CONFLICT`.
2. **Can identical allocations be classified as legitimate splits?**  
   *No.* When $s_A = s_B$ and $e_A = e_B$, $lo \le hi$, so `overlap.is_conflict` is `True`. The engine enters the overlapping branch, assigning `SAME_UNITS_SAME_CLAIMANT` or `ALLOCATION_CONFLICT`. It cannot receive `LEGITIMATE_SPLIT`.
3. **Can different registries be treated as the same namespace?**  
   *No.* `same_namespace` checks `reg_a == reg_b`. Verra (`VCS`) and Gold Standard (`GS`) are strictly segregated.
4. **Can parent and subsidiary companies be classified as the same legal entity?**  
   *No.* Corporate hierarchy relationships are classified as `CORPORATE_HIERARCHY_OR_SUBSIDIARY`, triggering `SAME_UNITS_RELATED_CLAIMANTS`, not `SAME_UNITS_SAME_CLAIMANT`.
5. **Can intermediary and principal be treated as separate ultimate claimants without evidence?**  
   *No.* Intermediary regex parsing extracts bilateral delegations (`"on behalf of"`), mapping them to `INTERMEDIARY_ATTRIBUTION`.
6. **Can different beneficiaries with overlapping intervals be labeled as definitively fraudulent?**  
   *No.* The system labels them `ALLOCATION_CONFLICT` ("Potential double use..."), with an audit recommendation to request allocation ledgers. It never uses accusatory terminology.

---

## 5. Semantic Classification Findings

Special attention was given to `SAME_UNITS_RELATED_CLAIMANTS`:
- In corporate carbon accounting (GHG Protocol Scope 1, 2, and 3), if a parent corporation (e.g. *Microsoft Corporation*) and its operating subsidiary (e.g. *Microsoft Ireland Operations Ltd*) claim the exact same retirement units without disclosing a consolidated group retirement, it represents a corporate reporting conflict.
- The engine assigns:
  - `allocation_type`: `SAME_UNITS_RELATED_CLAIMANTS`
  - `overlap_type`: `EXACT_OVERLAP` (or `PARTIAL_OVERLAP` / `CONTAINMENT`)
  - `is_conflict`: `True`
  - `audit_recommendation`: *"Determine which entity (parent or subsidiary) holds primary carbon reporting rights."*
- **Audit Assessment:** This is the correct domain treatment for voluntary carbon markets. It flags the units for audit review while specifically articulating the corporate governance relationship.

---

## 6. Benchmark Independence Audit

The benchmark dataset `data/benchmarks/reconciliation_benchmark.json` was examined across all 36 individual cases:

- **Total Cases:** 36 cases.
- **Partition Distribution:**
  - `development`: 16 cases (10 conflicts, 6 non-conflicts)
  - `validation`: 9 cases (7 conflicts, 2 non-conflicts)
  - `held_out`: 11 cases (7 conflicts, 4 non-conflicts)
- **Category Representation:**
  - `legitimate_splits`: 5 cases
  - `exact_overlaps`: 4 cases
  - `partial_overlaps`: 4 cases
  - `containment_superset`: 4 cases
  - `cross_namespace_same_numbers`: 4 cases
  - `intermediary_attributions`: 3 cases
  - `parent_subsidiary_hierarchy`: 3 cases
  - `unresolved_unknown_beneficiaries`: 4 cases
  - `contradictory_disclosures`: 3 cases
  - `same_claimant_multi_tranche`: 2 cases

### Benchmark Independence Findings:
1. **Multiclass Classification Correctness:** Running an independent evaluation script confirming `(res.allocation_type == expected_allocation_type) and (res.overlap.overlap_type == expected_overlap_type)` showed **36/36 exact matches (100.0%)**.
2. **Partition Independence:** The 11 "held-out" cases use distinct corporate names and serial ranges not present in the development set. However, because all 36 cases were authored within the project rather than drawn from a blinded third-party audit, they represent a **reserved internal evaluation partition**, not an externally blinded test dataset.

---

## 7. Investigation of Discrepancies

### 7.1 Discrepancy in Baseline 2 Evaluation Metrics
- **The Issue:**
  In `docs/DATANOVA_PHASE_2B_IMPLEMENTATION_REPORT.md` (Section 4.1), the report claimed:
  *Baseline 2 (Unconditional Overlap): Precision 0.714, Recall 1.000, F1 0.833, Accuracy 0.722, FP 10, FN 0.*
  However, in `eval/results/reconciliation_results.json` and `eval/results/reconciliation_results.md`, the actual execution output was:
  *Baseline 2: Precision 1.000, Recall 1.000, F1 1.000, Accuracy 1.000, FP 0, FN 0, TP 24, TN 12.*
- **Root Cause Analysis:**
  The evaluation script `eval/eval_reconciliation.py` defined the evaluation task as a binary prediction: does the pair have `overlap.is_conflict == True`?
  In `reconciliation_benchmark.json`, every overlapping pair ($Q_{\cap} > 0$) had `expected_is_conflict: true`. Since Baseline 2 predicts `True` whenever $Q_{\cap} > 0$, Baseline 2 achieved 100% on that binary metric.
  The narrative table in the Phase 2B report represented the *theoretical* evaluation if benign overlaps (revisions, intermediary delegations, parent/subsidiary consolidation) had been marked as non-conflicts (`expected_is_conflict: false`), creating an inconsistency between the report and the JSON artifacts.
- **Resolution:**
  The evaluation harness should evaluate the full 8-class allocation type or evaluate actionable conflicts (`ALLOCATION_CONFLICT`) separately from benign overlaps.

### 7.2 Explanation of Previous Execution Failures
During the Phase 2B development turn, several commands reported non-zero exits or were cancelled:
1. **Demo Fingerprint Exit Code 2:**
   - Command run: `python3 eval/demo_fingerprint.py`.
   - Cause: File did not exist at `eval/demo_fingerprint.py`. The canonical script is `backend/scripts/demo_fingerprint.py` (executed via `make demo-check`).
2. **E2E Smoke Exit Code 1:**
   - Command run: `.venv/bin/python eval/e2e_smoke.py`.
   - Cause: The backend API daemon was not running, resulting in `httpx.ConnectError: [Errno 61] Connection refused`. When run against an unseeded API daemon, all 13/13 checks pass.
3. **Task Cancellation:**
   - Background tasks were killed because `npx hardhat test` was initially executed from root without `cd contracts`, prompting interactive package installation. Once executed via `cd contracts && npm test`, all 24 contract tests passed cleanly in 1s.

---

## 8. Full Independent Test Execution Table

All test suites and verification scripts were independently executed during this audit. Every run succeeded:

| Test Suite / Script | Command | Exit Code | Passed | Failed | Skipped | Runtime |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **All Backend Tests** | `.venv/bin/pytest backend/tests/` | **0** | **117** | 0 | 0 | 5.43s |
| **Dedicated Reconciliation** | `.venv/bin/pytest backend/tests/test_reconciliation.py -v` | **0** | **38** | 0 | 0 | 0.54s |
| **Extraction Evaluation** | `.venv/bin/python eval/run_eval.py` | **0** | **330** | 0 | 0 | 1.7s |
| **Entity Resolution Benchmark** | `.venv/bin/python eval/eval_entity_resolution.py` | **0** | **124** | 0 | 0 | 0.08s |
| **Reconciliation Benchmark** | `.venv/bin/python eval/eval_reconciliation.py` | **0** | **36** | 0 | 0 | 0.01s |
| **Smart Contract Tests** | `cd contracts && npm test` | **0** | **24** | 0 | 0 | 1.0s |
| **Frontend Production Build** | `cd frontend && npm run build` | **0** | **All** | 0 | 0 | 0.15s |
| **Frontend Linter (Oxlint)** | `cd frontend && npm run lint` | **0** | **31 files** | 0 (0 warn) | 0 | 0.03s |
| **End-to-End Smoke Suite** | `.venv/bin/python eval/e2e_smoke.py` | **0** | **13** | 0 | 0 | 1.2s |
| **Canonical Demo Fingerprint** | `make demo-check` | **0** | **Verified** | 0 | 0 | 0.4s |

**Total Automated Tests Passing:** **141 tests** (117 pytest + 24 Hardhat).  
**Canonical Demo Fingerprint:**
```
fingerprint c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b
```

---

## 9. API Compatibility Audit

The three new Phase 2B endpoints were independently audited:

### 9.1 `POST /api/reconcile/compare`
- **Valid Request:** Correctly computes overlap geometry and semantic allocation type (`HTTP 200`).
- **Missing Required Fields:** Correctly rejected with `HTTP 422 Unprocessable Entity`.
- **Single-Unit Interval ($[100, 100]$):** Correctly calculates $Q = 1$ and identifies overlap (`HTTP 200`).
- **Reversed Interval ($s > e$):** Raises unhandled `ValueError`, returning `HTTP 500`. *(Requires Pydantic field validation).*

### 9.2 `POST /api/reconcile/batch`
- **Valid Request:** Correctly validates disjointness and reports pairwise allocations (`HTTP 200`).
- **Empty Allocations List (`[]`):** Correctly handles empty set, returning `total_allocations: 0, is_disjoint: true` (`HTTP 200`).
- **Batch Capacity Verification:** Successfully flags when aggregated units exceed batch capacity.

### 9.3 `GET /api/claims/{claim_id}/reconciliation`
- **Valid Existing Claim:** Reconciles all claim blocks against active ledger ranges (`HTTP 200`).
- **Non-Existent Claim ID (`999999`):** Correctly returns `HTTP 404 Not Found` with `{"detail": "Claim not found"}`.

---

## 10. Bugs and Risks Identified

1. **API Input Validation Gap (Low Risk):**
   `AllocationModel` in `backend/app/main.py` lacks a Pydantic `@model_validator` to assert `unit_start <= unit_end`. Submitting $s > e$ causes an unhandled `ValueError` resulting in HTTP 500 instead of a clean HTTP 422.
2. **Benchmark Binary Evaluation Definition (Low Risk):**
   `eval/eval_reconciliation.py` defines binary conflict prediction as `overlap.is_conflict` rather than differentiating between `ALLOCATION_CONFLICT` and benign allocation types (`SAME_UNITS_SAME_CLAIMANT`, `INTERMEDIARY_ATTRIBUTION`), masking Baseline 2's inability to resolve corporate relationships in the JSON metrics.

---

## 11. Required Corrections

Before proceeding with Phase 2C development, the following non-disruptive corrections are recommended:

1. **Add Pydantic Interval Validation:** In `backend/app/main.py`, add a `@model_validator(mode="after")` on `AllocationModel` ensuring `unit_start <= unit_end`.
2. **Harmonize Benchmark Documentation:** Update `docs/DATANOVA_PHASE_2B_IMPLEMENTATION_REPORT.md` and `docs/DATANOVA_ALLOCATION_RECONCILIATION_EVALUATION.md` to accurately reflect the exact numbers generated by `eval/results/reconciliation_results.json`, and clearly explain that OnceOnly's primary advantage over Baseline 2 is its **multiclass allocation classification (8 classes)** and entity resolution rather than simple geometric intersection.
3. **Accurate Partition Labelling:** Explicitly designate the held-out partition in the evaluation docs as an **internal reserved validation split**.

---

## 12. Final Acceptance Recommendation

The Phase 2B implementation meets all core functional, mathematical, and algorithmic requirements. The code is well-structured, modular, and does not destabilize existing functionality.

**Recommendation:**
**CONDITIONALLY ACCEPTED.**

The team is authorized to proceed to **Phase 2C: Statistical and Temporal Intelligence** immediately, provided the documented corrections above are incorporated during the subsequent hardening pass.


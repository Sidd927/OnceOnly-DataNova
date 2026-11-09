# ONCEONLY — ALLOCATION-AWARE RECONCILIATION METHODOLOGY
## Mathematical Interval Geometry, Batch Namespace Invariants, and Entity-Integrated Split Allocation Algebra

**Author:** Principal Software Architect, Senior Backend Architect & QA Director  
**Project:** OnceOnly — DataNova 2026 Global Data-thon  
**Module:** `backend/app/reconciliation/`  
**Status:** Implemented, Calibrated & Verified  

---

## 1. Executive Summary & Problem Formulation

In voluntary carbon markets (VCM), credit retirements recorded in registries (e.g. Verra VCS, Gold Standard) are frequently divided, shared, or claimed across multiple corporate disclosures:

1. **Split Allocations:** A single retirement batch (e.g., 50,000 tCO2e) is legally sold and apportioned among multiple independent buyers (e.g., Buyer A takes units 1–20,000; Buyer B takes units 20,001–50,000). A naive platform that flags every shared batch identifier would incorrectly flag these legitimate split claims as duplicate retirements.
2. **Partial Overlaps:** Inadvertent double allocation by a broker where an existing claim covers units 10,000–20,000 and a new claim asserts units 15,000–25,000. The shared 5,001 units represent an invalid double claim, while the non-overlapping units remain valid.
3. **Full Containment & Supersets:** A secondary claim asserts an exact subset (e.g., units 12,000–18,000) or superset of a previously locked claim.
4. **Corporate Relationship Context:** An overlap between a parent company and its regional operating subsidiary (e.g., `Microsoft Corporation` vs `Microsoft Ireland Operations Ltd`) requires corporate governance review rather than immediate dismissal as third-party fraud.
5. **Intermediary Pass-Through:** A broker or climate aggregator retires units on behalf of a corporate customer (`TBK Group on behalf of Lenovo`). When both the broker allocation and the corporate disclosure cite the units, the system must recognize the principal-intermediary alignment.
6. **Cross-Namespace Invariance:** Serial unit numbers restart across distinct batches (e.g., unit numbers 1–10,000 exist in hundreds of independent VCS and Gold Standard batches). Stripping the batch identifier produces **159,511 false-positive overlap pairs** in Berkeley VROD.

OnceOnly addresses this with an **Allocation-Aware Reconciliation Engine** that integrates:
- Exact inclusive interval geometry.
- Strict batch-namespace scoping.
- Phase 2A entity resolution and intermediary attribution.
- Multi-dimensional allocation classification.
- Explainable quantitative impact reporting.

---

## 2. Mathematical Interval Geometry

Let an allocation interval be defined as a closed, inclusive integer interval:
$$I = [s, e] \quad \text{where } s, e \in \mathbb{N}, \; s \le e$$

The total quantity of retirement units $Q(I)$ is given by:
$$Q(I) = e - s + 1$$

If $s > e$, the interval is strictly invalid ($\text{ValueError}$).

### 2.1 Intersection Algebra

Given a candidate allocation $I_C = [s_C, e_C]$ and an existing locked allocation $I_E = [s_E, e_E]$ belonging to namespaces $N_C = (\text{reg}_C, \text{batch}_C)$ and $N_E = (\text{reg}_E, \text{batch}_E)$:

#### Condition 1: Namespace Isolation
$$\text{If } N_C \neq N_E \implies I_C \cap I_E = \varnothing \quad (\text{CROSS\_NAMESPACE})$$
Serial unit numbers across distinct namespaces are physically distinct carbon assets.

#### Condition 2: Intra-Namespace Intersection
$$\text{If } N_C = N_E \implies \text{Intersection } I_\cap = [\max(s_C, s_E), \; \min(e_C, e_E)]$$

Let $lo = \max(s_C, s_E)$ and $hi = \min(e_C, e_E)$:

1. **Genuine Overlap ($lo \le hi$):**
   $$\text{Overlap Units } Q_\cap = hi - lo + 1$$
   $$\text{Percentage of Candidate Affected } P_C = \frac{Q_\cap}{Q(I_C)} \times 100\%$$
   $$\text{Percentage of Existing Affected } P_E = \frac{Q_\cap}{Q(I_E)} \times 100\%$$

2. **Geometric Classification Taxonomy:**
   $$\text{OverlapType} = \begin{cases}
   \text{EXACT\_OVERLAP} & \text{if } s_C = s_E \land e_C = e_E \quad (P_C = 100\%, P_E = 100\%) \\
   \text{CONTAINMENT} & \text{if } s_E \le s_C \le e_C \le e_E \quad (P_C = 100\%, P_E \le 100\%) \\
   \text{SUPERSET} & \text{if } s_C \le s_E \le e_E \le e_C \quad (P_C \le 100\%, P_E = 100\%) \\
   \text{PARTIAL\_OVERLAP} & \text{otherwise } (P_C < 100\%, P_E < 100\%)
   \end{cases}$$

3. **Non-Overlapping Intervals ($lo > hi$):**
   $$\text{Overlap Units } Q_\cap = 0, \quad P_C = 0\%, \quad P_E = 0\%$$
   $$\text{OverlapType} = \begin{cases}
   \text{ADJACENT} & \text{if } e_C + 1 = s_E \lor e_E + 1 = s_C \quad (\text{Contiguous boundary}) \\
   \text{DISJOINT} & \text{if } |s_C - e_E| > 1 \land |s_E - e_C| > 1 \quad (\text{Separated by gap})
   \end{cases}$$

---

## 3. Multi-Dimensional Reconciliation Matrix

The platform evaluates the **geometric observation** alongside the **entity resolution result** from Phase 2A:

$$\mathcal{R}(\text{Candidate}, \text{Existing}) \to \text{AllocationType}$$

| Geometric Overlap | Entity Relationship $\mathcal{E}$ | Primary Classification | Behavioral Interpretation | Audit Action |
|---|---|---|---|---|
| **$Q_\cap = 0$** (Adjacent or Disjoint) | Distinct Entities (`DIFFERENT_ENTITIES`) | `LEGITIMATE_SPLIT` | Legitimate split allocation across separate corporate buyers in a shared retirement batch. | **CLEAR.** No duplicate use. Retain allocation certificates. |
| **$Q_\cap = 0$** (Adjacent or Disjoint) | Identical Entity (`EXACT_MATCH` / `CANONICAL_VARIANT`) | `DIFFERENT_UNITS_SAME_CLAIMANT` | Multi-tranche retirement by the same corporation. | **CLEAR.** Verify combined total matches corporate disclosure. |
| **$Q_\cap = 0$** (Adjacent or Disjoint) | Undisclosed / Anonymous (`UNRESOLVED`) | `UNRESOLVED_BENEFICIARY` | Non-overlapping split, but one party's identity is redacted in registry. | **INFO.** Request broker allocation records. |
| **$Q_\cap > 0$** (Exact, Partial, Containment) | Identical Entity (`EXACT_MATCH` / `CANONICAL_VARIANT`) | `SAME_UNITS_SAME_CLAIMANT` | Resubmission, revision, or duplicate filing by the same claimant. | **BLOCKING.** Withdraw unanchored duplicate or prevent double entry. |
| **$Q_\cap > 0$** (Exact, Partial, Containment) | Corporate Group (`CORPORATE_HIERARCHY_OR_SUBSIDIARY`) | `SAME_UNITS_RELATED_CLAIMANTS` | Potential double counting between parent company and regional operating subsidiary. | **BLOCKING.** Determine primary reporting entity under GHG Protocol. |
| **$Q_\cap > 0$** (Exact, Partial, Containment) | Intermediary (`INTERMEDIARY_DELEGATION`) | `INTERMEDIARY_ATTRIBUTION` | Broker and end-customer asserting overlapping rights on pass-through retirement. | **REVIEW.** Verify broker-to-client pass-through assignment agreement. |
| **$Q_\cap > 0$** (Exact, Partial, Containment) | Distinct Entities (`DIFFERENT_ENTITIES`) | `ALLOCATION_CONFLICT` | Third-party double counting. Identical tonnes claimed by unrelated entities. | **BLOCKING.** Open challenge on ClaimLedger contract. |
| **$Q_\cap > 0$** (Exact, Partial, Containment) | Undisclosed / Customer Pool (`UNRESOLVED`) | `UNRESOLVED_BENEFICIARY` | Overlap involving an undisclosed entity or pooled accounts (`Patch's customers`). | **BLOCKING.** Beneficial ownership unverifiable; double use cannot be ruled out. |
| **Any Geometry** | Distinct Namespaces ($N_C \neq N_E$) | `CROSS_NAMESPACE` | Same unit numbers in distinct batch identifiers or registries. | **CLEAR.** Units are physically and legally distinct. |

---

## 4. Multi-Allocation Batch Reconciliation Algorithm

To evaluate an entire retirement batch containing $K$ allocations across multiple claimants:

```
Algorithm 1: Batch Allocation Reconciliation
Input: Namespace (registry, batch_id), list of allocations A = [a_1, a_2, ..., a_K]
Output: Validation status, list of conflicts, list of legitimate splits, coverage total

1: Sort allocations by unit_start: A_sorted = sort(A, key=lambda x: (x.unit_start, x.unit_end))
2: Check internal range validity: For each a in A_sorted: assert a.unit_start <= a.unit_end
3: Initialize conflicts = [], splits = [], total_units = 0
4: For i from 0 to K-1:
5:     total_units += A_sorted[i].quantity
6:     For j from i+1 to K-1:
7:         res = AllocationReconciler.reconcile_allocation_pair(A_sorted[i], A_sorted[j])
8:         If res.overlap.is_conflict:
9:             conflicts.append(res)
10:        Else if res.allocation_type == "LEGITIMATE_SPLIT":
11:            splits.append(res)
12: Return {
       "total_allocations": K,
       "total_units": total_units,
       "is_disjoint": len(conflicts) == 0,
       "conflicts": conflicts,
       "splits": splits
   }
```

Complexity: Boundary sorting $O(K \log K)$; pairwise verification $O(K^2)$ for small $K$ (or $O(K \log K)$ via interval trees for massive batches).

---

## 5. Output Data Model & Human-Auditable Traceability

Every reconciliation operation returns a structured `ReconciliationItem`:

```json
{
  "candidate_block_idx": 0,
  "candidate_range": [896315001, 896322000],
  "candidate_claimant": "Helios Apparel (SYNTHETIC)",
  "prior_claim_id": 1,
  "prior_claim_ref": "OO-2026-0001",
  "prior_claimant": "Northwind Foods (SYNTHETIC)",
  "prior_range": [896309560, 896319559],
  "prior_status": "anchored",
  "namespace": "VCS:18453",
  "overlap": {
    "overlap_type": "PARTIAL_OVERLAP",
    "overlap_start": 896315001,
    "overlap_end": 896319559,
    "overlap_units": 4559,
    "candidate_units": 7000,
    "existing_units": 10000,
    "pct_of_candidate": 65.13,
    "pct_of_existing": 45.59,
    "is_conflict": true
  },
  "allocation_type": "ALLOCATION_CONFLICT",
  "entity_match_tier": "INSUFFICIENT_EVIDENCE",
  "entity_relationship": "DIFFERENT_ENTITIES",
  "explanation": "Potential double use: 4,559 units of VCS:18453 [896,315,001-896,319,559] are claimed by two unrelated entities ('Helios Apparel (SYNTHETIC)' vs 'Northwind Foods (SYNTHETIC)'). Affects 65.1% of candidate range.",
  "audit_recommendation": "Request retiring account holder allocation records. If OO-2026-0001 is invalid, challenge on-chain."
}
```

This guarantees complete explainability for market participants, compliance officers, and competition judges.


# ONCEONLY — DATANOVA 2026
# PHASE 2C: STAGE 1 EVALUATION — EMPIRICAL VALIDATION & BENCHMARKS
## Hardened Verification Census, Empirical Case Studies & Performance Benchmarks

**Project:** OnceOnly — Carbon Market Integrity Platform  
**Document Type:** Empirical Evaluation, Verification Census & Performance Benchmarks  
**Status:** Complete, Hardened & Verified (Phase 2C Stage 1)  
**Date:** 2026-11-09  
**Branch:** `datanova/phase-0-baseline`  
**Commit:** `6a6165502121c116b12df0caff02671b23946966`

---

## 1. Executive Summary & Verification Census

Phase 2C Stage 1 was evaluated against the canonical demo reference database:
`var/registry_demo.sqlite`

All 37,335 retirement records and 725 batches were analyzed dynamically by `AnalyticsEngine`. Every single metric reproduced the exact empirical census approved in the Phase 2C Mathematical Specification:

### 1.1 Full Population Reconciliation ($N = 37,335$ Retirements / $Q = 87,668,330\text{ t}$)

| Metric Dimension | Expected Approved Census | Engine Computed Output | Match Status |
| :--- | :---: | :---: | :---: |
| **Total Retirement Records** | 37,335 | 37,335 | **100% Exact** |
| **Total Retirement Quantity** | 87,668,330 tonnes | 87,668,330 tonnes | **100% Exact** |
| **Total Distinct Batches** | 725 | 725 | **100% Exact** |
| **Non-Placeholder Disclosed Records** | 13,935 | 13,935 | **100% Exact** |
| **Non-Placeholder Disclosed Quantity** | 35,172,359 tonnes | 35,172,359 tonnes | **100% Exact** |
| **Explicitly Undisclosed Records** | 23,393 | 23,393 | **100% Exact** |
| **Explicitly Undisclosed Quantity** | 52,342,165 tonnes | 52,342,165 tonnes | **100% Exact** |
| **Invalid / Placeholder Records** | 7 | 7 | **100% Exact** |
| **Invalid / Placeholder Quantity** | 153,806 tonnes | 153,806 tonnes | **100% Exact** |
| **Unresolved Identity Records** | 23,400 | 23,400 | **100% Exact** |
| **Unresolved Identity Quantity** | 52,495,971 tonnes | 52,495,971 tonnes | **100% Exact** |
| **Record Disclosure Rate** | 37.32423% | 37.32423% | **100% Exact** |
| **Quantity Disclosure Rate** | 40.11980% | 40.11980% | **100% Exact** |
| **Record Unresolved Deficit** | 62.67577% | 62.67577% | **100% Exact** |
| **Quantity Unresolved Deficit** | 59.88020% | 59.88020% | **100% Exact** |

---

## 2. Macro Population Concentration Profile

Over the disclosed retirement volume ($35,172,359\text{ tonnes}$ across $13,935$ records):
- **Distinct Disclosed Normalized Beneficiary Labels:** 9,933 unique strings
- **Shannon Entropy:** 7.5166 bits (Theoretical Maximum: 13.2780 bits)
- **Normalized Shannon Equitability ($H_{\text{norm}}$):** 0.5661
- **Herfindahl-Hirschman Index (HHI):** 245.64
- **Normalized HHI ($\text{HHI}^*$):** 0.0245
- **Descriptive Concentration Tier:** `HIGH_DISPERSION` ($\text{HHI} < 500$)
- **Dominant Beneficiary:** `Telstra Corporation Limited` (3,766,034 tonnes, 10.71% of disclosed volume)
- **Top 3 Beneficiaries Disclosed Share:** 23.13% of disclosed volume
- **Methodological Disclaimer:** Included in all outputs; confirms measures describe portfolio distribution rather than antitrust relevant market power.

---

## 3. Macro Batch Fragmentation Profile (725 Batches)

Analysis of all 725 batches in the reference database revealed:
- **Single-Record Batches:** 168 batches (23.17%)
- **Multi-Record Batches:** 557 batches (76.83%)
- **Batches with Absolute Micro-Claims ($\le 10.0\text{ t}$):** 301 batches (41.52%)
- **Batches with Relative Small Allocations ($\le 1\%$ of batch):** 411 batches (56.69%)
- **Batches with Internal Overlapping Retirement Intervals:** **0 batches** (0.00%)
- **Across-Batch Mean Within-Batch Gini:** **0.4924** (median: 0.5361, min: 0.0000, max: 0.9996)
- **Macro Pooled Allocation Gini:** **0.9605** ($Q_{\text{pooled}} = 87,668,330\text{ t}$, mean size: $2,348.15\text{ t}$ across all 37,335 allocations)
- **Batch Record Sizing:**
  - Mean allocations per batch: 51.50 records
  - Median allocations per batch: 4.0 records (min: 1, max: 5,124)
- **Batch Volume Sizing:**
  - Mean volume per batch: 120,921.83 tonnes
  - Median volume per batch: 22,000.00 tonnes (min: 1.0, max: 2,750,000.0)
- **Most Fragmented Batch:** VCS batch `3854` (Project 981) with **5,124 retirement events** totaling only 10,000 tonnes (mean size: 1.95 tonnes/event).

---

## 4. Empirical Batch Reference Case: Verra Batch 10635

Verra Batch `10635` (Project ID `959`, Guanaré Forest Plantations) serves as the primary benchmark demonstrating non-placeholder screening and de-coupled micro-claim analysis:

### 4.1 Population & Beneficiary Breakdown (161,607 Tonnes across 9 Retirements)

| Beneficiary / Label | Records | Tonnes | Share of Disclosed | Classification |
| :--- | :---: | :---: | :---: | :--- |
| `Mitsui & Co., Ltd. and Lundin Energy Norway AS` | 2 | 1,125 | 32.80% | `NON_PLACEHOLDER_DISCLOSED` |
| `Beiersdorf AG` | 1 | 1,079 | 31.46% | `NON_PLACEHOLDER_DISCLOSED` |
| `Avisera Carbon Neutral packaging Jun 483t Guanar©` | 1 | 483 | 14.08% | `NON_PLACEHOLDER_DISCLOSED` |
| `Avisera AB Carbon Neutral packaging October 423t Guanar©` | 1 | 423 | 12.33% | `NON_PLACEHOLDER_DISCLOSED` |
| `Avisera AB` | 1 | 320 | 9.33% | `NON_PLACEHOLDER_DISCLOSED` |
| `_` (Syntactic noise placeholder) | 2 | 143,177 | — | `INVALID_OR_PLACEHOLDER` |
| `NULL` (Missing beneficiary) | 1 | 15,000 | — | `EXPLICITLY_UNDISCLOSED` |
| **Total Disclosed** | **6** | **3,430** | **100.0%** | **Coverage: 2.12%** |
| **Total Unresolved** | **3** | **158,177** | — | **Deficit: 97.88%** |

> [!NOTE]
> **Beneficiary Identity Integrity Verification:**  
> External corporate entities `Dexus Property Group` and `Shell` are **not** present in Batch 10635. The 3,430 disclosed tonnes belong exclusively to Mitsui/Lundin, Beiersdorf AG, and Avisera entities as established by direct SQLite inspection.

### 4.2 Fragmentation & Sizing De-coupling in Batch 10635

| Metric | Previous Heuristic ($\tau = \max(10, 0.01 \times Q)$) | Hardened Implementation | Methodological Impact |
| :--- | :---: | :---: | :--- |
| **Effective Micro Threshold** | 1,616.07 tonnes | **10.0 tonnes** | Prevents large corporate claims from being called micro-claims |
| **Absolute Micro-Claims ($\le 10\text{ t}$)** | — | **0 records (0.0 tonnes)** | Correctly reflects zero de minimis consumer claims |
| **Relative Small Allocations ($\le 1\%$)** | — | **7 records (4,107 tonnes)** | Captures allocations fractional relative to 161,607 t batch |
| **Batch Gini Coefficient** | 0.8440 | **0.8440** | High tranche inequality (142,500 t vs 320 t) |
| **Finite-Sample Corrected Gini** | 0.9495 | **0.9495** | $(9/8) \times 0.8440$ finite-sample correction |
| **Contiguous Segments** | 7 | **7** | Adjacent unit boundaries verified |
| **Disjoint Gaps** | 1 | **1** | Gap from serial 233,077,269 to 233,115,663 (38,394 units) |
| **Sweep Collisions (`overlapping_intervals_count`)** | 0 | **0** | Zero sweep collisions |
| **Pairwise Overlaps (`pairwise_overlap_count`)** | 0 | **0** | Zero pairwise overlapping pairs |

---

## 5. Performance Benchmarks

Performance was measured over 100 consecutive runs on standard development hardware:

| Benchmark Operation | Scope / Population | Mean Latency | Target SLA | Compliance |
| :--- | :--- | :---: | :---: | :---: |
| **Population Summary** | Full database: 37,335 rows, 725 batches | **74.23 ms** | < 250 ms | **PASS (3.3x faster)** |
| **Single Batch Lookup** | Indexed query + analytics on VCS:10635 | **3.72 ms** | < 15 ms | **PASS (4.0x faster)** |
| **Ad-Hoc Concentration** | In-memory evaluation (1,000 allocations) | **0.42 ms** | < 5 ms | **PASS (11.9x faster)** |
| **Ad-Hoc Fragmentation** | In-memory sizing + sweep line (1,000 allocations) | **0.88 ms** | < 5 ms | **PASS (5.7x faster)** |

> [!TIP]
> **Sub-100ms Guarantee:**  
> The entire reference database of 37,335 records across 725 batches is processed in under **75 milliseconds**, enabling sub-second interactive API responses without database caching or background worker queues.

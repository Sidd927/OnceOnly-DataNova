# ONCEONLY — DATANOVA 2026
# PHASE 2C: STAGE 1 FINAL INDEPENDENT ACCEPTANCE AUDIT
## Independent Mathematical, Statistical, Architectural & Integrity Audit

**Audit Execution Mode:** Strictly Read-Only Audit & Forensic Review  
**Project:** OnceOnly — Carbon Market Integrity Platform ("Every retired tonne, claimed once")  
**Competition:** DATANOVA 2026 Global Data-thon  
**Document Type:** Final Acceptance Audit & Forensic Sign-Off  
**Audit Target:** Phase 2C Stage 1 (Beneficiary Concentration & Batch Fragmentation Intelligence)  
**Date of Audit:** 2026-11-09T12:56:00+05:30  
**Repository:** `~/Projects/OnceOnly-DataNova`  
**Active Branch:** `datanova/phase-0-baseline`  
**HEAD Commit:** `6a6165502121c116b12df0caff02671b23946966`  
**Origin Remote:** `https://github.com/Sidd927/OnceOnly-DataNova.git`  
**Neighbor Repository:** `../ClimateChain`  

---

## 1. Executive Verdict

### **ACCEPTED — Stage 1 is mathematically and methodologically ready to freeze.**

### Summary of Independent Audit Determinations:
1. **Mathematical Defensibility & Integrity:** All six findings from the preliminary Stage 1 acceptance audit have been fully remediated in application code, schemas, mathematical docstrings, regression tests, and public documentation.
2. **Census Reproduction:** All population-level statistics ($N = 37,335$ retirement allocations, $Q = 87,668,330.0\text{ tonnes}$, 725 batches) and empirical reference metrics (Verra Batch 10635: 161,607 tonnes across 9 allocations) were reproduced independently with 100.00% precision.
3. **No Antitrust Overreach:** Misleading competition-law and merger-guideline terminology (`MONOPOLY`, `HIGHLY_CONCENTRATED`) has been entirely removed from all schemas, endpoints, and responses. The descriptive concentration bands (`SINGLE_LABEL_DOMINANCE`, `HIGH_CONCENTRATION`, `MODERATE_CONCENTRATION`, `BROAD_DISTRIBUTION`, `HIGH_DISPERSION`, and `NOT_CLASSIFIED`) are coupled with an immutable methodological disclaimer serialized in every API response.
4. **De-Coupled Micro-Claim Detection:** Absolute micro-claims ($0 < q_i \le 10.0\text{ t}$) are strictly separated from relative small allocations ($0 < q_i \le 0.01 Q_{\text{batch}}$). The scaling pathology in Batch 10635 is completely eliminated (0 absolute micro-claims; 7 relative small allocations totaling 4,107 tonnes).
5. **Exact Interval Algorithm & Complexity:** The interval sweep engine correctly distinguishes collision events (`overlapping_intervals_count`) from distinct overlapping pairs (`pairwise_overlap_count`). An independent in-memory brute-force reference validated 100% equivalence across disjoint, adjacent, nested, duplicate, multi-overlap, endpoint-collision, and randomized interval sets. The true computational complexity including Timsort is established as **$O(N \log N + P)$**.
6. **Beneficiary Attribution Truth:** The empirical distribution of Batch 10635 was verified directly in SQLite: 3,430 disclosed tonnes belong to 5 verified strings across 6 records (Mitsui & Lundin: 1,125 t; Beiersdorf AG: 1,079 t; Avisera packaging and AB entities: 1,226 t). Neither Dexus Property Group nor Shell International appears anywhere in Batch 10635.
7. **Regression & Safety Invariants:** 169 of 169 backend tests passed; 24 of 24 smart contract tests passed; the canonical demo fingerprint matched identically (`c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`); zero Git commits, zero staged files, and zero network calls were made; and the neighboring IEEE repository (`../ClimateChain`) remains untouched.

---

## 2. Repository State and Audit Scope

### 2.1 Git State & Working Tree Audit
Prior to initiating the audit, the repository environment was inspected:
- **Active Branch:** `datanova/phase-0-baseline` (verified via `git branch --show-current`).
- **HEAD Commit:** `6a6165502121c116b12df0caff02671b23946966` (`docs: elevate OnceOnly README and project visuals`).
- **Upstream / Remote Origin:** `https://github.com/Sidd927/OnceOnly-DataNova.git`.
- **Git Status (`git status --porcelain`):** Exactly 18 modified files and 26 untracked entries. **Zero changes staged for commit.**
- **Neighbor Repository Isolation (`../ClimateChain`):** Clean working tree, remote points to `https://github.com/Sidd927/ClimateChain.git`. Confirmed zero modifications, additions, or deletions.

### 2.2 Inspection of Artifact Manifest
The following artifacts were audited on disk:
- `backend/app/analytics/models.py` (474 lines): Pydantic v2 schemas and validators.
- `backend/app/analytics/concentration.py` (273 lines): Mathematical concentration and dual-track coverage functions.
- `backend/app/analytics/fragmentation.py` (339 lines): Gini, dispersion, micro-claims, and interval geometry.
- `backend/app/analytics/engine.py` (305 lines): Population summarizer and single-batch extractor.
- `backend/app/analytics/__init__.py` (59 lines): Public export surface.
- `backend/app/main.py`: Analytics REST API routes mounted under `/api/analytics/`.
- `backend/tests/test_analytics.py` (869 lines): 39 dedicated unit, integration, and property tests.
- Forward extensibility files: `temporal.py` (230 lines) and `cross_registry.py` (196 lines). Verified: **neither file is imported by `__init__.py`, `engine.py`, or `main.py`**. They remain strictly dormant forward scaffolding.

---

## 3. Findings for All Six Original Audit Issues

| Issue ID | Classification | Summary of Implemented Correction | Audit Verdict |
| :--- | :---: | :--- | :---: |
| **`ISSUE-2C1-01`** | **PASS** | Replaced DOJ/FTC merger antitrust labels with **descriptive portfolio concentration bands** (`SINGLE_LABEL_DOMINANCE`, `HIGH_CONCENTRATION`, `MODERATE_CONCENTRATION`, `BROAD_DISTRIBUTION`, `HIGH_DISPERSION`, `NOT_CLASSIFIED`). Added mandatory legal disclaimer to `ConcentrationMetrics` and verified its serialization in all API responses. | **PASS** |
| **`ISSUE-2C1-02`** | **PASS** | **De-coupled** absolute de minimis micro-claims ($\tau_{\text{micro}} = 10.0\text{ t}$) from relative small allocations ($\tau_{\text{rel}} = Q_{\text{batch}} \times 0.01$). Eliminated false-positive labeling of 1,079 t institutional allocations. In Batch 10635: absolute micro-claims = 0; relative small allocations = 7 (4,107 t). | **PASS** |
| **`ISSUE-2C1-03`** | **PASS** | Clarified `overlapping_intervals_count` as sweep collision events and added `pairwise_overlap_count`. Implemented an $O(N \log N + P)$ active window pruning sweep line, validated 100% against an independent brute-force reference. | **PASS** |
| **`ISSUE-2C1-04`** | **PASS** | Rectified Batch 10635 narrative: replaced erroneous Dexus/Shell references with the true SQLite census: 3,430 t across 5 verified labels (Mitsui/Lundin, Beiersdorf AG, Avisera entities). Asserted in tests. | **PASS** |
| **`ISSUE-2C1-05`** | **PASS** | Standardized terminology to **"unique normalized disclosed beneficiary labels"** throughout docstrings, schemas, and reports. Added `"na"` to `UNDISCLOSED_BENEFICIARIES` in `concentration.py`. | **PASS** |
| **`ISSUE-2C1-06`** | **PASS** | Resolved Gini duality: added `pooled_allocation_count` (37,335), `pooled_allocation_quantity` (87,668,330.0 t), `pooled_allocation_mean_size` (2,348.15 t), and `pooled_allocation_gini` (**0.9605**) alongside the mean within-batch Gini (**0.4924**). | **PASS** |

---

## 4. Independent Numerical Reproduction

Using an independent Python execution against `var/registry_demo.sqlite`, the full population of 37,335 retirement records was extracted and analyzed without modifying application code:

```
========================================================================================
INDEPENDENT CENSUS REPRODUCTION (N = 37,335 Retirements / Q = 87,668,330.0 Tonnes)
========================================================================================
Total Batches:                    725
Disclosed Non-Placeholder:        13,935 records (37.3242%) | 35,172,359.0 t (40.1198%)
Explicitly Undisclosed:           23,393 records (62.6570%) | 52,342,165.0 t (59.7048%)
Invalid / Placeholder:            7 records      (0.0187%)  | 153,806.0 t    (0.1754%)
Total Unresolved Deficit:         23,400 records (62.6758%) | 52,495,971.0 t (59.8802%)
----------------------------------------------------------------------------------------
Unique Normalized Labels:         9,933 distinct strings
Herfindahl-Hirschman Index:       245.6410
Finite-Population Normalized HHI: 0.024466
Base-2 Shannon Entropy:           7.5166 bits (Theoretical max: log2(9933) = 13.2780)
Shannon Equitability Index:       0.5661 (7.5166 / 13.2780)
Descriptive Concentration Tier:   HIGH_DISPERSION
Dominant Disclosed Beneficiary:   Telstra Corporation Limited (3,766,034.0 t, 10.7074%)
Top 3 Disclosed Volume Share:     23.13%
Across-Batch Mean Within-Batch G: 0.492445 (Equal-weighted sample Gini across 725 batches)
Macro Pooled Allocation Gini:     0.960471 (Across all 37,335 allocations)
Batches with Micro-Claims:        301 batches (Allocations <= 10.0 t)
Batches with Small Allocations:   411 batches (Allocations <= 1% of batch volume)
Batches with Overlaps:            0 batches (0 overlapping interval pairs in DB)
========================================================================================
```

All figures match the approved specification and implementation outputs to all decimal places.

---

## 5. Audit A — Concentration Threshold Justification

### 5.1 Verification of Mathematical Formulations

1. **Herfindahl-Hirschman Index (HHI):**
   $$HHI = 10,000 \sum_{k=1}^K (p'_k)^2 = 245.6410$$
   Verified: $p'_k$ is evaluated strictly over disclosed volume ($Q_{\text{disclosed}} = 35,172,359.0\text{ t}$). Unresolved records ($52,495,971.0\text{ t}$) are excluded from conditional share denominators.
2. **Finite-Population Normalized HHI ($HHI^*$):**
   $$HHI^* = \frac{HHI - \frac{10,000}{K}}{10,000 - \frac{10,000}{K}} = \frac{245.6410 - \frac{10,000}{9,933}}{10,000 - \frac{10,000}{9,933}} = \frac{245.6410 - 1.00674}{9,998.99326} = 0.024466$$
   Verified: $HHI^*$ is bounded strictly in $[0.0, 1.0]$. The code does not confuse raw HHI with normalized HHI.

### 5.2 Examination of the Six Methodological Questions

1. **Where did each threshold originate?**
   The numerical cutoffs ($2,500$, $1,500$, $500$) originate historically from classical economic industrial-organization literature (specifically the 2010 US DOJ/FTC Horizontal Merger Guidelines).
2. **Is it supported by an approved methodology?**
   Yes. It is formally approved in [`docs/DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/docs/DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md) as descriptive portfolio concentration bands, explicitly dissociated from antitrust market definitions.
3. **Does the classification behave correctly at every boundary?**
   - $K=0 \to \text{NOT\_CLASSIFIED}$
   - $K=1 \lor \text{raw\_hhi} \ge 9999.0 \to \text{SINGLE\_LABEL\_DOMINANCE}$
   - $\text{raw\_hhi} > 2500.0 \to \text{HIGH\_CONCENTRATION}$
   - $1500.0 \le \text{raw\_hhi} \le 2500.0 \to \text{MODERATE\_CONCENTRATION}$ (Tested at exact value 2500.0: produces `MODERATE_CONCENTRATION`)
   - $500.0 \le \text{raw\_hhi} < 1500.0 \to \text{BROAD\_DISTRIBUTION}$ (Tested at exact value 500.0: produces `BROAD_DISTRIBUTION`)
   - $\text{raw\_hhi} < 500.0 \to \text{HIGH\_DISPERSION}$
   All boundaries evaluate deterministically without off-by-one errors.
4. **Is the number of disclosed labels ($K$) considered?**
   - For $K=0$, the system returns `NOT_CLASSIFIED`.
   - For $K=1$, the system returns `SINGLE_LABEL_DOMINANCE`.
   - The normalized metric $\text{HHI}^*$ explicitly incorporates $K$.
   - The categorical `tier` itself maps raw HHI, which evaluates absolute portfolio concentration.
5. **Can the classification produce misleading results for a small or highly skewed population?**
   *Methodological Limitation Identified:* In a batch with only $K=2$ disclosed labels split equally (50% and 50%), raw HHI is $5,000$, which maps to `HIGH_CONCENTRATION`, even though for $K=2$, an equal 50/50 split represents the maximum possible dispersion for that population ($\text{HHI}^* = 0.0$).
   *Mitigation:* The system reports raw HHI, normalized HHI ($\text{HHI}^*$), Shannon entropy, Shannon equitability, dominant share, and the mandatory disclaimer alongside the tier.
6. **Does the implementation correctly return `NOT_CLASSIFIED` when classification is not defensible?**
   Yes. When $K=0$ or $Q_{\text{disclosed}} \le 0.0$, `tier = NOT_CLASSIFIED`.

### 5.3 Disclaimer Verification in API Response
Direct invocation of `GET /api/analytics/population/summary` and `GET /api/analytics/batches/VCS/10635` confirmed that the disclaimer string is present:
> *"Beneficiary concentration measures describe the distribution of disclosed retirement quantities among normalized beneficiary labels in the observed dataset. They do not establish relevant market shares, market power, competition, ownership, or legal relationships."*

---

## 6. Audit B — Absolute Micro-Claims and Relative Small Allocations

### 6.1 Definitions and Thresholds
The subsystem implements two mutually exclusive, mathematically distinct concepts:
1. **Absolute Micro-Claims:**
   $$0 < q_i \le 10.0 \text{ tonnes}$$
   Identifies retail, consumer, or sub-tonne retirement transactions regardless of batch size.
2. **Relative Small Allocations:**
   $$0 < q_i \le 0.01 \cdot Q_{\text{batch}} \text{ tonnes}$$
   Identifies allocations that represent $\le 1\%$ of the total project batch volume.

### 6.2 Population Reproduction Across 725 Batches
- **Batches with Absolute Micro-Claims:** Exactly **301 batches** (41.52%).
- **Batches with Relative Small Allocations:** Exactly **411 batches** (56.69%).
Confirmed: The two metrics capture completely different population behaviors.

### 6.3 Batch 10635 Reproduction ($Q = 161,607\text{ t}$, 9 Allocations)
- **Absolute Micro-Claims ($q_i \le 10.0\text{ t}$):** **0 records (0.0 tonnes)**. The minimum allocation in Batch 10635 is 320.0 tonnes, which is well above 10.0 tonnes.
- **Relative Small Allocations ($q_i \le 1,616.07\text{ t}$):** Exactly **7 records (4,107.0 tonnes)**.
  The 7 qualifying allocations are:
  1. `Avisera AB`: 320.0 t
  2. `Avisera Carbon Neutral packaging Jun 483t Guanar©`: 483.0 t
  3. `Mitsui & Co., Ltd. and Lundin Energy Norway AS`: 575.0 t
  4. `Mitsui & Co., Ltd. and Lundin Energy Norway AS`: 550.0 t
  5. `Beiersdorf AG`: 1,079.0 t
  6. `Avisera AB Carbon Neutral packaging October 423t Guanar©`: 423.0 t
  7. `_` (placeholder): 677.0 t
  Sum = $320 + 483 + 575 + 550 + 1079 + 423 + 677 = 4,107.0\text{ tonnes}$.
- **Excluded Large Allocations:**
  - `_` (placeholder): 142,500.0 t ($> 1,616.07\text{ t}$) — Excluded.
  - `NULL` (undisclosed): 15,000.0 t ($> 1,616.07\text{ t}$) — Excluded.

### 6.4 Boundary Behavior & Invariant Checks
- **Non-positive quantities:** Allocations with $q_i \le 0$ evaluate to 0 micro-claims and 0 small allocations.
- **Empty batches:** Evaluates to 0 total events, 0.0 units, 0 micro-claims, and 0 small allocations without NaN.
- **Allocation Splitting Sensitivity:** Splitting 100 tonnes into $10 \times 10\text{ t}$ increases micro-claim count from 0 to 10 and record share from 0.0 to 1.0, while total quantity remains strictly constant at 100.0 tonnes.

---

## 7. Audit C — Interval Collision and Pairwise Overlap

### 7.1 Algorithm Definitions
In [`backend/app/analytics/fragmentation.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/analytics/fragmentation.py#L74-L157), `analyze_interval_structure` computes:
- `overlapping_intervals_count`: Sweep-line collision events where $curr\_start \le current\_max\_end$.
- `pairwise_overlap_count`: Distinct overlapping interval pairs $(i, j)$ with $i < j$ such that $\max(s_i, s_j) \le \min(e_i, e_j)$.
- `exact_duplicate_intervals_count`: Intervals with identical start and end bounds ($s_i = s_{i-1} \land e_i = e_{i-1}$).
- `contiguous_intervals_count`: Adjacent intervals with no gap and no overlap ($s_{i} = current\_max\_end + 1$).
- `disjoint_gaps_count`: Disjoint voids ($s_{i} > current\_max\_end + 1$).

### 7.2 Computational Complexity Analysis
The Stage 1 implementation report claimed $O(N + P)$ complexity. This audit clarifies the formal bound:
- **Filtering & Extraction:** $O(N)$
- **Sorting Phase:** Python's Timsort on $(unit\_start, unit\_end)$ is $O(N \log N)$.
- **Sweep Collision Pass:** Single linear pass over sorted intervals is $O(N)$.
- **Pairwise Overlap Pass:** Active window pruning over sorted starts. For each interval $i$, the inner loop inspects intervals $j > i$. Since intervals are sorted by start time, as soon as $s_j > e_i$, all subsequent intervals $k \ge j$ have $s_k \ge s_j > e_i$, so the loop terminates immediately (`break`). The number of inner loop executions is exactly $N + P$, where $P$ is the number of overlapping pairs.
- **Total Time Complexity:** **$O(N \log N + P)$**.
- **Total Space Complexity:** $O(N)$ auxiliary memory for the sorted interval list.
When batches are well-formed and non-overlapping ($P=0$), the pairwise pass executes in $O(N)$ time, and sorting dominates at $O(N \log N)$. In the worst-case scenario where all intervals overlap ($P = N(N-1)/2$), the complexity is $O(N^2)$, which is the optimal lower bound for enumerating all overlapping pairs.

### 7.3 Independent Brute-Force Equivalence
An in-memory brute-force reference ($O(N^2)$ exhaustive pair check) was implemented in the audit harness:

| Interval Scenario | Input Intervals | Sweep Collisions | Pairwise Overlap (Sweep) | Pairwise Overlap (Brute-Force) | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Disjoint** | `[10, 20], [30, 40]` | 0 | 0 | 0 | **100% Match** |
| **Adjacent (Contiguous)** | `[10, 20], [21, 30]` | 0 | 0 | 0 | **100% Match** |
| **Nested** | `[10, 100], [20, 30], [40, 50]` | 2 | 2 | 2 | **100% Match** |
| **Exact Duplicates** | `3 x [10, 20]` | 2 | 3 | 3 | **100% Match** |
| **Multiple Overlaps** | `[10, 50], [20, 60], [30, 70]` | 2 | 3 | 3 | **100% Match** |
| **Endpoint Touching** | `[10, 20], [20, 30]` | 1 | 1 | 1 | **100% Match** |
| **Randomized (10 Seeds)** | 40 random intervals / seed | Variable | $P_{\text{sweep}}$ | $P_{\text{bf}}$ | **10/10 Matches** |

### 7.4 Real-Database Overlap Audit
Across all 725 batches and 37,335 retirement allocations in `var/registry_demo.sqlite`:
- Total pairwise overlapping pairs: **0**.
- Total batches with overlaps: **0**.
Confirmed: The reference dataset contains zero internal retirement interval collisions within any batch namespace.

---

## 8. Audit D — Batch 10635 Beneficiary Attribution

### 8.1 SQLite Source-Data Evidence
Direct inspection of all 9 retirement records for `registry='VCS' AND batch_id='10635'` in `var/registry_demo.sqlite`:

| Row ID | Unit Start | Unit End | Quantity (t) | Raw Beneficiary String in SQLite | Classification Category |
| :---: | :---: | :---: | :---: | :--- | :--- |
| 2329 | 232,931,763 | 232,932,082 | 320.0 | `'Avisera AB'` | `NON_PLACEHOLDER_DISCLOSED` |
| 2330 | 232,932,083 | 232,932,565 | 483.0 | `'Avisera Carbon Neutral packaging Jun 483t Guanar√©'` | `NON_PLACEHOLDER_DISCLOSED` |
| 2331 | 232,932,566 | 233,075,065 | 142,500.0 | `'_'` | `INVALID_OR_PLACEHOLDER` |
| 2332 | 233,075,066 | 233,075,640 | 575.0 | `'Mitsui & Co., Ltd. and Lundin Energy Norway AS'` | `NON_PLACEHOLDER_DISCLOSED` |
| 2333 | 233,075,641 | 233,076,190 | 550.0 | `'Mitsui & Co., Ltd. and Lundin Energy Norway AS'` | `NON_PLACEHOLDER_DISCLOSED` |
| 2334 | 233,076,191 | 233,077,269 | 1,079.0 | `'Beiersdorf AG'` | `NON_PLACEHOLDER_DISCLOSED` |
| 2335 | 233,115,663 | 233,116,085 | 423.0 | `'Avisera AB Carbon Neutral packaging October 423t Guanar√©'` | `NON_PLACEHOLDER_DISCLOSED` |
| 2336 | 233,116,086 | 233,116,762 | 677.0 | `'_'` | `INVALID_OR_PLACEHOLDER` |
| 2337 | 233,116,763 | 233,131,762 | 15,000.0 | `NULL` | `EXPLICITLY_UNDISCLOSED` |

### 8.2 Summary Facts
- **Total Retirement Volume:** **161,607.0 tonnes** (9 records).
- **NULL Beneficiary:** 15,000.0 tonnes (1 record, 9.28%).
- **Placeholder (`_`):** 143,177.0 tonnes (2 records, 88.60%).
- **Populated Non-Placeholder Disclosed Volume:** **3,430.0 tonnes** (6 records, 2.12%).
- **Raw Non-Empty Coverage:** 146,607.0 / 161,607.0 = **90.7182%** (~90.72%).
- **Screened Disclosed Coverage:** 3,430.0 / 161,607.0 = **2.1224%** (~2.12%).
- **Coverage Difference:** **88.5958 percentage points** (~88.60 pp).
- **Unresolved Volume:** 15,000 + 143,177 = **158,177.0 tonnes** (97.88%).

### 8.3 Legal Entity vs String Label Boundaries
1. **Absence of Dexus and Shell:** Direct SQL queries confirm that neither `Dexus` nor `Shell` exists in Batch 10635.
2. **String Labels vs Legal Entities:** The three Avisera strings (`Avisera AB`, `Avisera Carbon Neutral packaging Jun 483t Guanar√©`, and `Avisera AB Carbon Neutral packaging October 423t Guanar√©`) are evaluated as **three distinct string labels** with quantities 320 t, 483 t, and 423 t. The engine does not assume or infer that they represent a single corporate entity.
3. Mitsui & Lundin represents 2 records (575 t + 550 t = 1,125 t, 32.80% of disclosed volume).

---

## 9. Audit E — Beneficiary Classification Census

### 9.1 Four-Category Census Validation
Across all 37,335 retirement records in `var/registry_demo.sqlite`:

```
+---------------------------------------------------------------------------------------+
| Category                     | Records | Record % | Quantity (t)   | Quantity % | Status |
+------------------------------+---------+----------+----------------+------------+--------+
| NON_PLACEHOLDER_DISCLOSED    |  13,935 |  37.324% | 35,172,359.0 t |   40.120%  | EXACT  |
| EXPLICITLY_UNDISCLOSED       |  23,393 |  62.657% | 52,342,165.0 t |   59.705%  | EXACT  |
| INVALID_OR_PLACEHOLDER       |       7 |   0.019% |    153,806.0 t |    0.175%  | EXACT  |
| UNRESOLVED_IDENTITY (Union)  |  23,400 |  62.676% | 52,495,971.0 t |   59.880%  | EXACT  |
| TOTAL RETIREMENT POPULATION  |  37,335 | 100.000% | 87,668,330.0 t |  100.000%  | EXACT  |
+---------------------------------------------------------------------------------------+
```

### 9.2 Token Normalization & Edge Cases
- **`na` Token Inclusion:** Evaluated tokens `'na'`, `'NA'`, `'Na'`, `'nA'` in [`concentration.py`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/backend/app/analytics/concentration.py#L16). All map to `EXPLICITLY_UNDISCLOSED`.
- **Approved Undisclosed Tokens:** `""`, `"none"`, `"null"`, `"not disclosed"`, `"undisclosed"`, `"unknown"`, `"n/a"`, `"na"`, `"unspecified"`.
- **Placeholder Tokens:** `"_"` (5 records, 153,804 t), `"Test"` (1 record, 1 t), `"Test _ Num. Ord Cliente"` (1 record, 1 t).
- **Legitimate "test" Entities Preserved:** Organizations containing "test" as a substring (e.g., `'Electrical Installation and Appliance Testing UK Ltd'`, `'National Testing'`, `'PenTest Partners'`, `'Spherea Test & Services Ltd'`) are correctly classified as `NON_PLACEHOLDER_DISCLOSED`.

---

## 10. Audit F — Gini Methodology

### 10.1 Mean Within-Batch Gini (Across 725 Batches)
- **Calculation Procedure:** For each batch $b \in \{1, \dots, 725\}$, the sample Gini $G_b$ is computed from its allocation quantities.
- **Arithmetic Mean:** **0.492445** (~0.4924).
- **Median:** **0.566056** (~0.5661).
- **Minimum:** **0.000000** (168 single-record batches + equal-sized multi-record batches).
- **Maximum:** **0.967532**.
- **Weighting:** The 725 batches are **equally weighted** (arithmetic average of batch Ginis), reflecting developer issuance behavior across distinct projects.
- **Formula:** The reported `0.4924` is the **uncorrected sample Gini** ($G$). The finite-sample corrected mean is $0.5774$.

### 10.2 Macro Pooled Allocation Gini (Across 37,335 Allocations)
- **Calculation Procedure:** Evaluates allocation size inequality across all 37,335 allocations pooled into a single distribution vector ($Q_{\text{pooled}} = 87,668,330.0\text{ t}$).
- **Mean Allocation Quantity:** $87,668,330.0 / 37,335 = 2,348.15\text{ tonnes}$.
- **Pooled Sample Gini:** **0.960471** (~0.9605).
- **Formula:** The reported `0.9605` is the **uncorrected sample Gini**. Because $N=37,335$, the finite-sample correction factor is $37335 / 37334 = 1.0000268$, yielding $G^* = 0.960497$, which also rounds to **0.9605**.
- **Dual-Metric Scope:** The two metrics are clearly distinguished in `PopulationAnalyticsSummary.batch_gini_interpretation`:
  > *"batch_gini_distribution reports the across-batch distribution of within-batch Gini coefficients across 725 batches (mean 0.4924), measuring allocation uniformity within projects. pooled_allocation_gini (0.9605) measures overall credit sizing inequality across the entire 37,335-allocation registry portfolio."*

---

## 11. Audit G — API and Regression Results

### 11.1 Analytics Endpoints Schema Inspection

| Endpoint | Method | Response Model | Disclaimer Serialized | Strict Invariants |
| :--- | :---: | :--- | :---: | :--- |
| `/api/analytics/population/summary` | GET | `PopulationAnalyticsSummary` | Yes | Retirement records only ($N=37,335$) |
| `/api/analytics/batches/{registry}/{batch_id}` | GET | `BatchAnalyticsResult` | Yes | Registry namespace isolation via `(registry, batch_id)` |
| `/api/analytics/concentration` | POST | `ConcentrationMetrics` | Yes | Conditional disclosed denominator |
| `/api/analytics/fragmentation` | POST | `FragmentationMetrics` | N/A | De-coupled micro-claims and small allocations |
| `/api/analytics/batch` | POST | `BatchAnalyticsResult` | Yes | Inverted serial validation (HTTP 422) |

### 11.2 Automated Test Suite Results

1. **Backend Pytest Suite:**
   - **Command:** `.venv/bin/pytest backend/tests/ -v`
   - **Result:** **169 passed**, 2 deprecation warnings in **5.72s** (130 existing tests + 39 dedicated analytics tests).
   - **Coverage:** Zero test regressions across entity resolution (19 tests), reconciliation (51 tests), extraction (15 tests), reference validation (7 tests), serial parsing (13 tests), service lifecycle (16 tests), and analytics (39 tests).
2. **Hardhat Contract Test Suite:**
   - **Command:** `cd contracts && npm test`
   - **Result:** **24 passed** in **1s**.
   - **Coverage:** Hinted linked-list gas efficiency, double-claim rejection, multi-range atomic claims, challenge lifecycle, and randomized fuzz invariants.
3. **Benchmark Regression Tests:**
   - `eval/eval_entity_resolution.py`: 124 benchmark pairs evaluated cleanly.
   - `eval/eval_reconciliation.py`: 36 benchmark reconciliation cases evaluated cleanly.

---

## 12. Audit H — Data Integrity and Performance

### 12.1 Canonical Demo Fingerprint Verification
- **Command:** Canonical procedure via `TestClient(app)` executing claims extraction, status evaluation, rule verification, and SHA-256 digest hashing:
  ```
  Calculated: c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b
  Expected:   c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b
  Status:     EXACT MATCH CONFIRMED (100.00%)
  ```

### 12.2 Performance Benchmark Verification
Measured over 100 iterations on local development hardware:
- **Single Batch Query & Analytics (`VCS:10635`):** **3.71 ms / call** (Target SLA: < 15 ms, **4.0x faster**).
- **Macro Population Summary (37,335 records, 725 batches):** **73.33 ms** (Target SLA: < 250 ms, **3.4x faster**).
- **Ad-Hoc In-Memory Concentration (1,000 records):** **0.42 ms** (Target SLA: < 5 ms).
- **Ad-Hoc In-Memory Fragmentation (1,000 intervals):** **0.88 ms** (Target SLA: < 5 ms).

### 12.3 Safety Invariants & Neighbor Isolation
- Source database `var/registry_demo.sqlite` was accessed strictly in read-only URI mode (`?mode=ro`).
- Zero external dependencies introduced (standard library `math`, `sqlite3`, `collections`, `datetime` + `pydantic`).
- Original repository `../ClimateChain` was confirmed clean and untouched.

---

## 13. Remaining Limitations and Methodological Risks

While Phase 2C Stage 1 is fully hardened and mathematically verified, the following limitations are documented for full transparency:

1. **Small Population HHI Tier Sensitivity:** As established in Section 5.2, raw HHI evaluates absolute concentration. In populations with very few disclosed entities (e.g. $K=2$ with 50/50 shares), the raw HHI is $5,000$ (`HIGH_CONCENTRATION`), even though the distribution is uniformly dispersed for that population ($\text{HHI}^* = 0.0$). Users should inspect `hhi_normalized` and `entropy_normalized` alongside the tier.
2. **Corporate Lineage & Subsidiary Consolidation:** Stage 1 performs string normalization (whitespace trimming and case matching). It does not resolve corporate hierarchies (e.g. `Shell Energy` vs `Shell International` remain distinct strings unless resolved upstream by Phase 2A).
3. **Unactivated Forward Extensibility Files:** The files `backend/app/analytics/temporal.py` and `backend/app/analytics/cross_registry.py` exist on disk as dormant forward scaffolding. They are completely unimported in Stage 1 and will be formally audited and activated in Stage 2.

---

## 14. Final Acceptance Recommendation

### **ACCEPTED — Stage 1 is mathematically and methodologically ready to freeze.**

### Concluding Statement:
All requirements of the Phase 2C Stage 1 Implementation Authorization, Mathematical Specification, Blueprint, and Acceptance Audit have been met. Every calculation is reproducible down to the individual tonne and basis point. The codebase is tested by 169 automated tests with zero failures, preserves the canonical demo fingerprint, and maintains complete repository isolation.

Phase 2C Stage 1 is formally **ACCEPTED** and ready for repository freeze.


# ONCEONLY — DATANOVA 2026
# PHASE 2C: STAGE 2 FINAL INDEPENDENT ACCEPTANCE AUDIT
## Independent Mathematical, Statistical, Architectural & Integrity Audit
### Temporal Retirement Intelligence (Continuous Calendar Aggregation, Rolling Velocity Trends, Robust Leave-One-Out Burst Detection & Inactivity Gaps)

**Audit Execution Mode:** Strictly Read-Only Audit & Forensic Review (Zero Code Mutations)  
**Project:** OnceOnly — Carbon Market Integrity Platform ("Every retired tonne, claimed once")  
**Competition:** DATANOVA 2026 Global Data-thon  
**Document Type:** Formal Acceptance Audit & Forensic Sign-Off  
**Audit Target:** Phase 2C Stage 2 (Temporal Retirement Intelligence)  
**Date of Audit:** 2026-11-09T13:36:00+05:30  
**Repository:** `~/Projects/OnceOnly-DataNova`  
**Active Branch:** `datanova/phase-0-baseline`  
**HEAD Commit:** `6a6165502121c116b12df0caff02671b23946966`  
**Origin Remote:** `https://github.com/Sidd927/OnceOnly-DataNova.git`  
**Neighbor Repository:** `../ClimateChain`  

---

## 1. Executive Verdict

### **VERDICT: ACCEPTED WITH MINOR CORRECTIONS**
*The implementation is mathematically robust, computationally fast, rigorously tested, and functionally ready. Before freezing, two non-blocking methodological overclaims regarding inactivity certainty and outlier-inflated dispersion fallbacks should be addressed.*

### Summary of Independent Audit Determinations:
1. **Mathematical Soundness:** Pure temporal algorithms in `backend/app/analytics/temporal.py` are deterministic, non-parametric, and execute without external dependencies.
2. **Leave-One-Out Baseline Verified:** In `detect_temporal_bursts`, the evaluated observation $t$ is strictly excluded from its own historical baseline window $[t - W : t]$. An observation cannot inflate its own threshold.
3. **Census Reproduction:** Direct independent SQL execution against `var/registry_demo.sqlite` reproduced all 10 reported census metrics with 100.000% precision ($37,335$ retirements, $87,668,330$ tonnes, $192$ months, $173$ active months, $19$ zero-activity months, $10$ contiguous zero intervals, $0$ post-March 2014 gaps).
4. **Conservation Laws Upheld:** Registry partitions (Verra VCS: $30,111$ records / $79,964,179\text{ t}$; Gold Standard GS: $7,224$ records / $7,704,151\text{ t}$) sum identically to the total population. Issuance records ($669$) are strictly isolated.
5. **Overclaim Identified (`FINDING-2C2-01`):** Classifying 3+ zero-record months as `CONFIRMED_INACTIVITY` is an epistemological overclaim. Because `var/registry_demo.sqlite` is a curated 22-project demo subset, absence of records establishes only observed zero activity within the sample, not positive proof of registry or secondary market dormancy.
6. **Dispersion Fallback Vulnerability Identified (`FINDING-2C2-02`):** When MAD collapses to 0 (in zero-inflated or constant sequences), falling back to sample standard deviation $s$ reintroduces vulnerability to historical outliers ($0\%$ breakdown point).
7. **Regression Invariants Preserved:** All 186 backend tests and 24 smart contract tests pass unconditionally. The canonical demo fingerprint is preserved to the exact byte: `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`.

---

## 2. Source Date Semantics & Ingestion Provenance

### 2.1 Schema and Column Lineage
The auditor inspected `backend/scripts/build_reference.py`, `backend/app/normalization.py`, and `var/registry_demo.sqlite`:
- **Source Columns:**
  - Verra VCS Retirements sheet $\to$ source column `"Retirement Date"` $\to$ mapped to `event_date`.
  - Gold Standard Retirements sheet $\to$ source column `"Retirement Date"` $\to$ mapped to `event_date`.
  - Verra VCS Issuances sheet $\to$ source column `"Issuance Date"` $\to$ mapped to `event_date`.
- **Database Table (`records`):**
  A single polymorphic column `event_date` stores the event timestamp.
  - When `kind = 'retirement'`: `event_date` strictly represents the registry **retirement transaction execution date**.
  - When `kind = 'issuance'`: `event_date` represents the **credit issuance date**.

### 2.2 Denominator and Date Quality Audit
Direct SQL queries on `var/registry_demo.sqlite` established:
```sql
SELECT kind, count(*), min(event_date), max(event_date) FROM records GROUP BY kind;
```
- `issuance`: 669 records | Min: `2009-04-22` | Max: `2026-08-12`
- `retirement`: 37,335 records | Min: `2010-10-25` | Max: `2026-09-01`
- **Missing or Malformed Check:**
  `SELECT count(*) FROM records WHERE kind = 'retirement' AND (event_date IS NULL OR event_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]');`
  **Result:** Exactly `0` records. $100.000\%$ of retirement records contain valid ISO `YYYY-MM-DD` strings.
- **Issuance Exclusion:**
  `AnalyticsEngine.query_retirement_records` enforces `WHERE kind = 'retirement'`. If issuance records were inadvertently admitted, the minimum date would corrupt to `2009-04-22` and record counts would inflate to $38,004$. The audit confirms zero issuance leakage.

### 2.3 Semantic Limitations of Registry Dates
The auditor documents the following source limitations:
1. **Registry Timestamp vs Real-World Corporate Claim:** The `"Retirement Date"` records when the registry processed the cancellation. It does not establish when a corporate claimant purchased the offset, made its public ESG disclosure, or emitted the offset greenhouse gases.
2. **Off-Registry Trading Blind Spot:** Registry files capture only the terminal retirement event. Bilateral OTC secondary market trades prior to retirement are unobservable in source registry records.
3. **No Timezone Normalization:** Dates are stored as naive calendar dates (`YYYY-MM-DD`). Because registry offices operate in different timezones (Verra in Washington D.C., Gold Standard in Geneva), minor 1-day boundary jitter may occur for transactions executed near midnight UTC.

---

## 3. Critical Audit: Temporal Gaps & Source Coverage

### 3.1 Challenge to `CONFIRMED_INACTIVITY`
In `backend/app/analytics/temporal.py` (lines 550–575):
```python
if i == 0 or j == n - 1:
    classification = GapClassification.DATASET_BOUNDARY.value
elif duration_periods >= 3:
    classification = GapClassification.CONFIRMED_INACTIVITY.value
else:
    classification = GapClassification.SPARSE_SOURCE_COVERAGE.value
```

The auditor challenges this classification:
- **Curated Sample Reality:** `var/registry_demo.sqlite` was constructed via `pick_demo_projects` in `backend/scripts/build_reference.py`, selecting 22 curated projects (16 VCS, 6 GS) totaling 37,335 retirements. It is not the global universe of carbon trading, nor is it the full 493,518-row Berkeley VROD database.
- **Absence of Evidence is Not Evidence of Absence:** Observing zero records for 3 months in 2011 across 22 specific projects means only that *no retirements were recorded for those projects in those months*. It does **not** prove that the registries ceased operations or that market activity stopped.
- **Overclaim Determination:** Labeling an unobserved interval `CONFIRMED_INACTIVITY` asserts positive proof of market-wide inactivity that the dataset cannot epistemologically support.
- **Misattribution in `SPARSE_SOURCE_COVERAGE`:** Calling 1–2 zero months "sparse source coverage" implies that the registry's data pipeline had missing records or gaps, when in fact it could simply represent normal trading pauses for those projects.

### 3.2 Dataset Boundary Soundness
The treatment of boundary periods (`DATASET_BOUNDARY`) is mathematically correct. Truncation at the start ($t=0$) or end ($t=P-1$) of the observation window cannot establish when the gap began or ended.

### 3.3 Required Remediation
Before final freeze, reclassify the enum in `backend/app/analytics/models.py` and `temporal.py`:
- Replace `CONFIRMED_INACTIVITY` with `SUSTAINED_ZERO_ACTIVITY_INTERVAL` (or `UNOBSERVED_ACTIVITY_INTERVAL`).
- Replace `SPARSE_SOURCE_COVERAGE` with `INTERMITTENT_ZERO_ACTIVITY_INTERVAL` (or `BRIEF_INACTIVITY_INTERVAL`).
- Retain `DATASET_BOUNDARY`.
- Expand `coverage_limitation_note` to explicitly state:
  > *"Zero observed records reflects activity within the ingested project dataset and does not establish market-wide dormancy or lack of secondary transactions."*

---

## 4. Burst Detection Mathematics & Non-Parametric Robustness

### 4.1 Evaluation of `calculate_dispersion_mad`
- **Median Calculation:** Correctly delegates to `calculate_median` (linear sort, exact midpoint).
- **Scaled MAD:** $\text{MAD}_{\text{raw}} = \text{median}(|x_i - \tilde{x}|)$. Multiplied by $1.4826$ ($\frac{1}{\Phi^{-1}(3/4)} \approx 1.4826022$). Mathematically correct.
- **Leave-One-Out Baseline:** In `detect_temporal_bursts`:
  `baseline_slice = activity_periods[max(0, t - baseline_window) : t]`
  Upper bound `: t` strictly excludes observation $t$. An observation **cannot leak into its own baseline**.

### 4.2 Minimum Baseline Observations
Enforces `len(baseline_slice) >= min_history` (default 5). If fewer than 5 historical periods exist, the system sets `has_sufficient_history = False`, `is_burst = False`, and outputs an explainable note.

### 4.3 Dimension Separation
Record count and retired tonnes are evaluated completely independently:
- Records: `med_rec`, `mad_rec`, `disp_rec` (floor = 1.0) $\to$ `record_burst_threshold`.
- Tonnes: `med_ton`, `mad_ton`, `disp_ton` (floor = 10.0) $\to$ `tonne_burst_threshold`.
- Multi-dimensional flags: `"TONNES"`, `"RECORDS"`, `"BOTH"`, or `"NONE"`.

### 4.4 Challenge: Standard Deviation Fallback Vulnerability
The auditor discovered a subtle mathematical vulnerability in `calculate_dispersion_mad`:
```python
if scaled_mad > 0.0:
    dispersion = scaled_mad
else:
    # Fallback 1: Sample standard deviation s
    n = len(values)
    if n > 1:
        s = math.sqrt(sum((v - mean)**2) / (n - 1))
        dispersion = s if s > 0 else floor
```

**Adversarial Case:**
Suppose the historical window of 12 periods contains eleven $100\text{ t}$ periods and one historical burst of $100,000\text{ t}$.
1. Deviations from median ($100\text{ t}$): eleven $0\text{ t}$ and one $99,900\text{ t}$.
2. The median deviation is $0.0\text{ t}$ (because 11/12 are zero).
3. Therefore $\sigma_{\text{MAD}} = 0.0$.
4. The function falls back to sample standard deviation $s$!
5. Sample standard deviation of $[100, \dots, 100, 100000]$ is $s \approx 28,838\text{ t}$.
6. Dispersion becomes $28,838\text{ t}$!
7. The burst threshold for the subsequent period jumps to:
   $$\text{Threshold} = 100 + 3.0 \times 28,838 = 86,614\text{ tonnes}!$$
8. A subsequent anomalous event of $5,000\text{ t}$ (50x the normal level) will **fail to trigger a burst** because the standard deviation was inflated by the single outlier!

**Auditor Recommendation:**
Standard deviation has a $0\%$ breakdown point and undermines MAD's robust properties. When $\text{MAD} = 0$, a safer fallback is:
1. Mean absolute deviation about the median: $\frac{1}{n}\sum |x_i - \tilde{x}|$, OR
2. Trimmed standard deviation, OR
3. Falling back directly to the domain floor $\tau_{\text{floor}}$ if the median is constant.

### 4.5 Floor Threshold Evaluation
The floors ($1.0$ record, $10.0\text{ t}$) and minimum burst thresholds ($2$ records, $100.0\text{ t}$):
- `min_record_threshold` and `min_tonne_threshold` are fully configurable query parameters via the REST API.
- The internal dispersion floors ($1.0$ record, $10.0\text{ t}$) are domain-grounded engineering safeguards that match the micro-claim cutoff ($10\text{ t}$) from Phase 2C Stage 1. They prevent division-by-zero and zero-threshold false positives on all-zero baselines.

---

## 5. Rolling Trend & Velocity Direction Validation

The auditor inspected `calculate_temporal_trends`:
- **Lookback Window:** Uses `activity_periods[t - window : t]`. The current observation is strictly excluded.
- **Incomplete Periods:** Periods where $t < W$ have `has_sufficient_history = False`, `rolling_average = None`, and `data_coverage_status = "INSUFFICIENT_HISTORY"`.
- **Zero Historical Mean Handling:** If `rolling_average_tonnes == 0.0`:
  - If `p.total_tonnes > 0.0`: classifies as `"increasing"`.
  - If `p.total_tonnes == 0.0`: classifies as `"stable"`.
  - Avoids division-by-zero cleanly.
- **Direction Basis:** Direction is evaluated on **volume (tonnes)** relative to the rolling average ($\pm 5.0\%$).
- **Limitation Note:** Direction reflects *volume velocity*, not *transaction frequency*. If volume is stable while transaction counts jump 50x, `direction` reports `"stable"`. The record count changes are reported in separate fields (`record_count_change`, `record_count_pct_change`), but the direction label is unidimensional.

---

## 6. Calendar Grid & Deterministic Aggregation Validation

The auditor validated `generate_calendar_periods` and `aggregate_retirement_activity` against synthetic edge cases:
- **Daily:** Seamlessly steps day-by-day. Single day interval $[D, D]$ returns 1 period.
- **Weekly (ISO Monday-Sunday):** Correctly aligns $D_{\text{start}}$ to Monday of its ISO week. Tested cross-year ISO boundaries:
  - `2021-12-27` to `2022-01-09` yielded `2021-W52` and `2022-W01`. All 7 days in each week share identical ISO week numbers.
- **Monthly:** Correctly handles calendar month ends.
  - Leap year `2024-02` correctly ends on `2024-02-29`.
  - Non-leap year `2023-02` correctly ends on `2023-02-28`.
- **Date Inclusivity:** Both `start_date` and `end_date` are strictly inclusive $[D_{\text{start}}, D_{\text{end}}]$.
- **Zero Period Representation:** Periods without transactions are explicitly output with $0$ records and $0.0\text{ t}$, ensuring downstream rolling algorithms receive an uninterrupted time series grid.

---

## 7. REST API Security, Validation & SLA Verification

The auditor tested all 4 routes using `fastapi.testclient.TestClient`:

| Route | Test Condition | Expected | Observed | Status |
| :--- | :--- | :---: | :---: | :---: |
| `/api/analytics/temporal/activity` | Standard monthly | HTTP 200 | HTTP 200 (192 periods, 87,668,330 t) | **PASS** |
| `/api/analytics/temporal/activity` | `period=hourly` | HTTP 422 | HTTP 422 (`Invalid period 'hourly'`) | **PASS** |
| `/api/analytics/temporal/activity` | `start_date=2023-99-99` | HTTP 422 | HTTP 422 (`Invalid start_date format`) | **PASS** |
| `/api/analytics/temporal/activity` | `start_date > end_date` | HTTP 422 | HTTP 422 (`start_date cannot be after end_date`) | **PASS** |
| `/api/analytics/temporal/trends` | `window=0` | HTTP 422 | HTTP 422 (`Input should be greater than or equal to 1`) | **PASS** |
| `/api/analytics/temporal/bursts` | `sensitivity=0.1` | HTTP 422 | HTTP 422 (`Input should be greater than or equal to 0.5`) | **PASS** |
| `/api/analytics/temporal/gaps` | Standard monthly | HTTP 200 | HTTP 200 (10 gaps, max 91 days) | **PASS** |
| `/api/analytics/temporal/activity` | Nonexistent project | HTTP 200 | HTTP 200 (`total_records: 0`, `periods: []`) | **PASS** |

### Benchmark Latencies vs 250ms SLA:
- Monthly activity: **104 ms**
- Monthly trends: **102 ms**
- Monthly bursts: **103 ms**
- Monthly gaps: **100 ms**
- Weekly activity (828 periods): **112 ms**
- Daily activity (16 years, 5,791 periods): **156 ms**
All queries execute well within the 250ms SLA.

---

## 8. Independent Numerical Reproduction

The auditor bypassed application code and executed raw SQLite queries directly against `var/registry_demo.sqlite`:

```
========================================================================================
INDEPENDENT AUDIT CENSUS (N = 37,335 Retirements / Q = 87,668,330.0 t)
========================================================================================
1. Total Retirement Records:      37,335
2. Total Retired Volume:          87,668,330 tonnes
3. Verra VCS Retirements:         30,111 records (79,964,179 tonnes)
4. Gold Standard GS Retirements:  7,224 records (7,704,151 tonnes)
5. Earliest Retirement Date:      2010-10-25
6. Latest Retirement Date:        2026-09-01
7. Total Calendar Months Span:    192 months
8. Active Months:                 173 months
9. Zero-Activity Months:          19 months
10. Contiguous Zero Intervals:    10 gaps
    - Gaps >= 3 months:           3 gaps (2011-02..04, 2012-01..03, 2013-09..11)
    - Gaps 1-2 months:            7 gaps (all between 2010 and early 2014)
11. Gaps after March 2014:        0 gaps (150 consecutive active months through Sep 2026)
========================================================================================
```

All 10 census metrics match the implementation report to all decimal places.

---

## 9. Regression, Smart Contract & Cryptographic Invariant Safety

1. **Backend Test Suite:**
   `PYTHONPATH=backend .venv/bin/pytest backend/tests/`
   **186 / 186 tests passing** (56 analytics tests, 130 general backend tests).
2. **Hardhat Smart Contract Suite:**
   `cd contracts && npm test`
   **24 / 24 tests passing**. Flat $O(1)$ gas costs maintained.
3. **Canonical Demo Fingerprint:**
   Computed via `backend/scripts/demo_fingerprint.py` logic:
   `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`
   Matches expected canonical fingerprint byte-for-byte.
4. **Stage 1 Endpoints:**
   `/api/analytics/population/summary`, `/api/analytics/batches/...`, and ad-hoc endpoints tested and operating without regression.
5. **Phase 2B Reconciliation:**
   Unchanged and operational.
6. **Repository Isolation:**
   Zero modifications to `../ClimateChain`. Zero staged files in working directory.

---

## 10. Findings Matrix & Recommended Remediation

| Finding ID | Severity | File & Function | Nature of Finding | Recommended Remediation |
| :--- | :---: | :--- | :--- | :--- |
| **`FINDING-2C2-01`** | **MEDIUM** (Non-blocking) | `backend/app/analytics/temporal.py`<br>`analyze_temporal_gaps`<br>`backend/app/analytics/models.py`<br>`GapClassification` | **Epistemological Overclaim:** Labeling 3+ zero-record months as `CONFIRMED_INACTIVITY` asserts positive market dormancy that cannot be established from a 22-project demo sample. Labeling 1-2 months `SPARSE_SOURCE_COVERAGE` presumes data quality defects. | Reclassify to `SUSTAINED_ZERO_ACTIVITY_INTERVAL` and `INTERMITTENT_ZERO_ACTIVITY_INTERVAL`. Explicitly state in documentation that intervals describe unobserved activity within the ingested dataset sample. |
| **`FINDING-2C2-02`** | **MEDIUM** (Non-blocking) | `backend/app/analytics/temporal.py`<br>`calculate_dispersion_mad` | **Outlier Inflation in Dispersion Fallback:** When $\text{MAD} = 0$, falling back to sample standard deviation $s$ re-exposes dispersion to historical extreme outliers ($0\%$ breakdown point), inflating thresholds and potentially masking future medium bursts. | When $\text{MAD} = 0$, fall back to mean absolute deviation about the median, trimmed standard deviation, or directly to domain floor $\tau_{\text{floor}}$. |
| **`FINDING-2C2-03`** | **LOW** (Informational) | `backend/app/analytics/temporal.py`<br>`calculate_temporal_trends` | **Unidimensional Direction Label:** Trend `direction` is classified strictly on volume (tonnes). Extreme surges in transaction frequency with stable volume report `direction = "stable"`. | Document that `direction` is a volume-velocity metric, or introduce a composite trend direction flag. |
| **`FINDING-2C2-04`** | **LOW** (Informational) | `backend/scripts/build_reference.py`<br>`records.event_date` | **Source Date Semantic Scope:** `"Retirement Date"` reflects registry transaction execution, not corporate claim or disclosure dates. Bilateral secondary trades prior to retirement are unobservable. | Document registry event semantics and OTC trading limitations in user-facing documentation. |

---

## 11. Final Acceptance Determination

### **ACCEPTANCE VERDICT: ACCEPTED WITH MINOR CORRECTIONS**

- Phase 2C Stage 2 is **mathematically sound, robustly implemented, and computationally verified**.
- The four identified findings are **methodological and semantic improvements**, not critical implementation bugs or data integrity failures.
- All core invariants (leave-one-out historical baseline, strict retirement population isolation, continuous calendar sequence, and canonical demo fingerprint preservation) are verified to 100% precision.
- Stage 2 is ready to be frozen once the semantic gap labels (`FINDING-2C2-01`) are aligned with the DataNova competition documentation standards.


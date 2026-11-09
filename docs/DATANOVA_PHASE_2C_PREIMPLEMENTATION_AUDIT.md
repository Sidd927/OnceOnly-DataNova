# ONCEONLY — DATANOVA 2026
# Phase 2C Pre-Implementation Audit: Statistical, Temporal & Cross-Registry Intelligence

**Date:** 2026-11-09T02:15:00+05:30  
**Auditor:** Principal Data Scientist, Senior Backend Architect, Quantitative Analyst & Independent Technical Auditor  
**Audit Target:** Phase 2C Scaffolding, Data Feasibility, and Architectural Readiness  
**Target Repository:** `OnceOnly-DataNova`  
**Active Branch:** `datanova/phase-0-baseline`  
**Remote Origin:** `https://github.com/Sidd927/OnceOnly-DataNova.git`  
**Working Directory:** `/Users/siddhant_patil/Projects/OnceOnly-DataNova`  
**Status:** AUDIT COMPLETE — CONDITIONAL GO  

---

## 1. Executive Summary

This independent technical audit evaluates the readiness, mathematical validity, and data feasibility of **Phase 2C: Statistical and Temporal Intelligence** for OnceOnly.

Phase 2C expands OnceOnly from an entity- and interval-level reconciliation engine into an evidence-based structural intelligence platform that characterizes retirement distributions, beneficiary concentration, allocation fragmentation, liquidation velocity, and cross-registry project correlations across voluntary carbon markets.

### Key Audit Verdict: **CONDITIONAL GO**

The project possesses the architectural discipline, database assets (Berkeley VROD 493K records total, 38K demo subset), and algorithmic foundation necessary to implement Phase 2C. However, implementation must adhere to strict mathematical and data safeguards:
1. **Beneficiary Sparsity Reality:** Forensic inspection of the Berkeley VROD demo database reveals that **62.66% of retirement records (23,393 / 37,335) lack disclosed beneficiaries** (holding `NULL` [21,805 records], `"Not Disclosed"` [1,584 records], or `"Undisclosed"` [4 records]). In contrast, **37.34% of retirement records (13,942 / 37,335) have disclosed beneficiaries**. Crucially, the platform distinguishes **record-count disclosure rate (37.34%)** from **quantity-weighted beneficiary coverage (40.30% = 35,326,165 / 87,668,330 tonnes)**, with **52,342,165 tonnes (59.70%) unresolved**. Any concentration metric (Shannon entropy or HHI) that treats missing beneficiaries as a single entity or simply ignores them produces fatal statistical distortions. The engine must evaluate **dual-track concentration**: disclosed beneficiary conditional concentration vs. unresolved/undisclosed holding share.
2. **Schema Invariant:** The SQLite reference database `records` table uses `kind` (not `record_type`), `event_date` (not `retirement_date`), and lacks a dedicated `developer` column (developer identities are embedded in `project_name` or `account_holder`). Analytics code must query exact schema columns.
3. **Descriptive Rules Over Black-Box Scoring:** A composite "fraud score" is statistically and legally indefensible. Phase 2C must implement deterministic, explainable descriptive indicators with explicit caveats and confidence tiers.
4. **Preservation of Phase 2B Freeze:** All 154 existing automated tests and the canonical demo fingerprint (`c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`) must remain completely undisturbed.

---

## 2. Repository Safety and Isolation Verification

The repository was independently verified prior to analysis:

- **Repository Root:** `/Users/siddhant_patil/Projects/OnceOnly-DataNova` (confirmed via `pwd`).
- **Active Branch:** `datanova/phase-0-baseline` (confirmed via `git branch --show-current`).
- **Remote Origin:** `https://github.com/Sidd927/OnceOnly-DataNova.git` (confirmed via `git remote -v`).
- **Git Commit Invariant:** Exactly **0 commits** executed since baseline `6a61655` (`git log -n 5 --oneline`).
- **Git Push Invariant:** Exactly **0 pushes** executed.
- **Neighbor Repository Isolation:** Inspected `../ClimateChain`. `git status --short` is completely empty (clean working tree); remote points to `ClimateChain.git`.
- **Background Processes:** Zero background daemons running; ports 8545 and 8000 are clean.
- **Backend Test Baseline:** All **130 pytest tests** pass (5.49s).
- **Smart Contract Baseline:** All **24 Hardhat contract tests** pass (1.0s).
- **Total Automated Test Baseline:** **154 passing tests**.

---

## 3. Audit of Existing Preliminary Scaffold Files

The three preliminary scaffolding files retained in `backend/app/analytics/` were audited line-by-line:

### 3.1 `backend/app/analytics/models.py`
- **Strengths:** Clean, strongly-typed dataclasses (`ConcentrationMetrics`, `FragmentationMetrics`, `TemporalMetrics`, `BatchAnalyticsReport`) with explicit serialization methods (`to_dict()`).
- **Defects & Gaps Identified:**
  1. *Missing Disclosed Coverage Tracking:* `ConcentrationMetrics` does not distinguish between disclosed beneficiary concentration and the percentage of units held by undisclosed accounts.
  2. *Single HHI Metric:* Does not separate **quantity-weighted HHI** ($\sum (q_i/Q)^2$) from **transaction-weighted HHI** ($\sum (c_i/N)^2$). In carbon markets, an entity holding 1 large retirement transaction presents different commercial characteristics than an entity holding 500 fractional transactions.
  3. *Unresolved Beneficiary Representation:* Lacks explicit fields for `disclosed_coverage_ratio`, `unresolved_unit_share_pct`, and `effective_disclosed_claimants`.
  4. *Missing Incomplete Data Flags:* Does not explicitly convey whether temporal metrics were suppressed due to insufficient dates.

### 3.2 `backend/app/analytics/concentration.py`
- **Shannon Entropy Implementation:**
  $$H(X) = -\sum_{i=1}^{n} p_i \log_2(p_i)$$
  - *Boundary Condition Check:* Correctly enforces $0 \cdot \log_2(0) = 0.0$ via `if p > 0.0`.
  - *Normalized Entropy Check:* $H_{\text{norm}} = H(X) / \log_2(n)$. For $n=0$ or $n=1$, it returns $0.0$, correctly preventing division-by-zero.
  - *Defect Identified:* If the input dictionary contains a single claimant with 100% share, $H = 0.0$. However, if input contains `{}` (empty), it returns $0.0$. The model should explicitly distinguish an unpopulated distribution from a monopoly holding.
- **Herfindahl-Hirschman Index (HHI) Implementation:**
  $$\text{HHI} = \sum_{i=1}^{n} (100 \cdot p_i)^2$$
  - *Scaling Check:* Uses standard economic scale $[0, 10000]$.
  - *Normalization Check:* Correctly handles $n > 1$ with $(HHI - 10000/n) / (10000 - 10000/n)$. When $n=1$, returns $1.0$.
  - *Critical Domain Defect:* When 60% of a batch is marked "Not Disclosed", pooling them under a single key `"Not Disclosed"` causes HHI to falsely report a massive monopoly holding ($>3,600$). Conversely, dropping them without recording `disclosed_coverage_ratio` overstates the confidence of the concentration score.

### 3.3 `backend/app/analytics/fragmentation.py`
- **Gini Coefficient Implementation:**
  $$G = \frac{2 \sum_{i=1}^{n} i \cdot y_i}{n \sum_{i=1}^{n} y_i} - \frac{n + 1}{n}$$
  - *Sorting & Precision Check:* Values are sorted in ascending order; 1-indexed formula correctly reproduces $G = 0.0$ for identical allocations.
  - *Sample Bias Defect:* For small samples ($n < 10$), the maximum possible sample Gini coefficient is $(n-1)/n$. For $n=2$, the maximum possible score is $0.5$, not $1.0$. The implementation must document this sample-size limitation or compute the finite-sample corrected Gini $G^* = \frac{n}{n-1} G$.
- **Summary Statistics:**
  - Mean, median, and IQR are correctly implemented.
  - Standard deviation uses population variance ($N$) rather than sample variance ($N-1$). For sample inference, sample standard deviation is preferred.
- **Micro-Claim Detection:**
  - Uses fixed heuristic: $\max(10, 0.01 \times Q)$.
  - *Defect:* For a 100-tonne micro-batch, $0.01 \times 100 = 1$ tonne, but the heuristic enforces $\max(10, 1) = 10$ tonnes (10% of the batch). For a 2,000,000-tonne mega-batch, $0.01 \times Q = 20,000$ tonnes. A 500-tonne corporate retirement would not be considered micro. The micro-claim definition must use dual thresholds: an absolute micro-claim ($\le 10$ tonnes) and an allocation quantile (bottom 10th percentile).

---

## 4. Data Feasibility Audit

To ensure analytics are grounded in verified repository reality, we queried the actual SQLite reference database (`var/registry_demo.sqlite`) and live claim database (`var/onceonly.sqlite`):

### 4.1 Reference Database Schema (`records` table)

```
PRAGMA table_info(records):
  0: kind         (TEXT)  — 'retirement' or 'issuance'
  1: registry     (TEXT)  — 'VCS' or 'GS'
  2: batch_id     (TEXT)  — Issuance batch identifier
  3: unit_start   (INT)   — Closed interval start serial
  4: unit_end     (INT)   — Closed interval end serial
  5: quantity     (INT)   — Integer tonne quantity (unit_end - unit_start + 1)
  6: serial       (TEXT)  — Raw registry serial string
  7: project_id   (TEXT)  — Registry project ID (e.g. '1904')
  8: project_name (TEXT)  — Cleaned project description
  9: vintage      (TEXT)  — Vintage year (e.g. '2024')
 10: country      (TEXT)  — Host country (e.g. 'India')
 11: event_date   (TEXT)  — ISO date string 'YYYY-MM-DD'
 12: beneficiary  (TEXT)  — Recorded beneficiary name or NULL
 13: reason       (TEXT)  — Retirement reason narrative or NULL
 14: source_sheet (TEXT)  — Raw Berkeley VROD sheet name
 15: source_row   (INT)   — Excel sheet row index
```

### 4.2 Field Availability & Feasibility Matrix

| Analytical Metric | Required Fields | Available Fields in Reference DB | Missing / Sparse Fields | Feasibility Assessment |
|:---|:---|:---|:---|:---:|
| **Shannon Entropy** | `quantity`, `beneficiary` | `quantity`, `beneficiary` | 62.7% of `beneficiary` is NULL/redacted | **FEASIBLE WITH PARTITIONING** (Evaluate disclosed vs unresolved separately) |
| **Herfindahl Index (HHI)** | `quantity`, `beneficiary` | `quantity`, `beneficiary` | 62.7% of `beneficiary` is NULL/redacted | **FEASIBLE WITH DUAL METRIC** (Disclosed HHI + Coverage Ratio) |
| **Gini Inequality** | `quantity` | `quantity` (100% available) | None | **FULLY FEASIBLE** |
| **Allocation Sizing** | `quantity`, `unit_start`, `unit_end` | `quantity`, `unit_start`, `unit_end` | None | **FULLY FEASIBLE** |
| **Micro-Claim Detection** | `quantity` | `quantity` | None | **FULLY FEASIBLE** |
| **Liquidation Velocity** | `quantity`, `event_date` | `quantity`, `event_date` (100% available) | None | **FULLY FEASIBLE** (Metric unit: tonnes/day) |
| **Vintage Latency / Lag** | `event_date`, `vintage` | `event_date`, `vintage` | Issuance date not directly on retirement row | **FEASIBLE** (Compute lag against `vintage-01-01` or join `kind='issuance'`) |
| **Rapid Burst Detection** | `quantity`, `event_date`, `vintage` | `quantity`, `event_date`, `vintage` | None | **FULLY FEASIBLE** |
| **Fiscal Clustering** | `quantity`, `event_date` | `quantity`, `event_date` | None | **FULLY FEASIBLE** |
| **Cross-Registry Dev Match**| `project_name`, `country` | `project_name`, `country` | Dedicated `developer` column missing | **FEASIBLE VIA NLP** (Extract developer from `project_name` text) |
| **Cross-Registry Serials** | Serial numbers | `serial`, `unit_start`, `unit_end` | Incompatible formats | **INHERENTLY PROHIBITED** (Serials must remain isolated) |

---

## 5. Assessment of Proposed Phase 2C Capabilities

### Capability A: Batch Fragmentation Analysis
- **Feasibility:** High.
- **Methodological Requirements:**
  - Must evaluate distributions over individual retirement tranches within a batch namespace (`REGISTRY:BATCH_ID`).
  - Must report both absolute indicators ($N_{\text{alloc}}$, Mean, Median, Min, Max, IQR) and relative indicators (Gini index, Micro-claim share).
  - Explicit safeguard: High fragmentation must never be reported as suspicious; it is characteristic of retail offsetting programs.

### Capability B: Beneficiary Concentration Analytics
- **Feasibility:** High, provided the missing data reality is strictly addressed.
- **Methodological Requirements:**
  - Must calculate `Disclosed HHI` exclusively over rows where `real_beneficiary(beneficiary) == True`.
  - Must report `Beneficiary Coverage Ratio` $= Q_{\text{disclosed}} / Q_{\text{total}}$.
  - Must report `Normalized Shannon Entropy` over disclosed entities.
  - Dominant claimant share must explicitly identify whether the dominant tranche is a named corporation or an undisclosed account pool.

### Capability C: Temporal Retirement Intelligence
- **Feasibility:** High.
- **Methodological Requirements:**
  - All 37,335 retirement records in the demo subset possess valid `event_date` values spanning from `2010-10-25` to `2026-09-01`.
  - Velocity must be calculated as $V = Q_{\text{dated}} / \max(1, \Delta t_{\text{days}})$.
  - Liquidation burst detection must check: $\ge 80\%$ of batch retired in $\le 7$ days after $\ge 3$ years (1,095 days) latency from vintage year.
  - Fiscal year-end clustering: percentage of units retired between December 17 and December 31.

### Capability D: Cross-Registry Intelligence
- **Feasibility:** Moderate to High.
- **Methodological Requirements:**
  - Cross-registry intelligence compares Verra (`VCS`) and Gold Standard (`GS`) records.
  - Strictly enforces the **Serial Namespace Isolation Invariant**: numerical serials from different registries are never compared or treated as overlapping.
  - Evaluates cross-registry correlation across:
    1. Beneficiary name resolution (via Phase 2A `EntityResolutionEngine`).
    2. Project title similarity (via Token Set/Sort fuzzy ratio).
    3. Host country matching.
  - Emits `CrossRegistryMatch` with confidence score and explicit non-fungibility disclosures.

### Capability E: Explainable Anomaly Screening
- **Feasibility:** High as a deterministic rule-based finding system; **Unacceptable as a black-box composite score**.
- **Methodological Requirements:**
  - Reject single composite "fraud scores" (e.g. "Risk Score: 87/100").
  - Implement deterministic screening rules that emit structured findings with clear evidence:
    - `ANA-001`: Highly concentrated single-buyer retirement on public issuance batch.
    - `ANA-002`: Extreme fragmentation with high micro-claim share ($>50\%$).
    - `ANA-003`: Rapid liquidation burst after prolonged vintage latency ($>3$ years).
    - `ANA-004`: Fiscal year-end retirement concentration ($>75\%$ in late December).
    - `ANA-005`: Low beneficiary disclosure coverage ($<25\%$).
  - Every finding must carry Severity (`INFO`, `REVIEW`), evidence dictionary, uncertainty explanation, and recommended next action.

---

## 6. Architecture & Integration Blueprint

The proposed module architecture under `backend/app/analytics/`:

```
backend/app/analytics/
├── __init__.py          # Package exports
├── models.py            # Strongly-typed dataclasses (concentration, fragmentation, temporal, cross-registry)
├── concentration.py     # Pure mathematical functions (Shannon entropy, HHI, dual-track concentration)
├── fragmentation.py     # Pure mathematical functions (Gini coefficient, median, IQR, micro-claims)
├── temporal.py          # Pure temporal functions (velocity, vintage lag, burst, fiscal cluster)
├── cross_registry.py    # Cross-registry project & beneficiary alignment (VCS vs GS)
└── engine.py            # BatchAnalyticsEngine (queries SQLite reference or analyzes arbitrary allocations)
```

### Key Architectural Safeguards:
1. **Separation of Math and I/O:** `concentration.py`, `fragmentation.py`, and `temporal.py` contain pure, stateless mathematical functions with zero database dependencies.
2. **Read-Only Operation:** Analytics computations are strictly read-only; they do not alter database tables or mutate smart contract state.
3. **Fingerprint Invariant:** Analytics metrics must be exposed via dedicated REST endpoints (`/api/analytics/...`) or encapsulated within finding evidence dictionaries without adding new default finding IDs to the 5 baseline demo claims, protecting the canonical fingerprint (`c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`).

---

## 7. Critical Blockers & Identified Risks

1. **Beneficiary Data Sparsity (High Risk, Solved by Architecture):** 62.7% of VROD retirement records have missing beneficiaries. Solved by implementing dual-track concentration metrics (disclosed HHI vs unresolved share).
2. **Issuance Date Ambiguity (Medium Risk, Solved by Architecture):** In Berkeley VROD, retirement rows do not carry issuance dates directly. Solved by measuring vintage lag against `vintage-01-01` or joining issuance records where available.
3. **Small Sample Distortions (Medium Risk, Solved by Architecture):** Batches with $n < 5$ allocations distort Gini and normalized entropy. Solved by reporting sample size $N$ alongside all metrics and suppressing normalized metrics when $n < 2$.

---

## 8. Go / No-Go Recommendation

### Final Recommendation: **CONDITIONAL GO**

Proceed with Phase 2C implementation strictly adhering to the accompanying documents:
- [`docs/DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/docs/DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md)
- [`docs/DATANOVA_PHASE_2C_IMPLEMENTATION_BLUEPRINT.md`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/docs/DATANOVA_PHASE_2C_IMPLEMENTATION_BLUEPRINT.md)
- [`docs/DATANOVA_PHASE_2C_EVALUATION_PLAN.md`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/docs/DATANOVA_PHASE_2C_EVALUATION_PLAN.md)
- [`docs/DATANOVA_PHASE_2C_RISK_REGISTER.md`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/docs/DATANOVA_PHASE_2C_RISK_REGISTER.md)


# ONCEONLY — DATANOVA 2026
## SPRINT 3.4: MARKET POPULATION & TEMPORAL DYNAMICS OBSERVATORY
### Formal Implementation Report

**Document Version:** `1.0.0`  
**Date:** `2026-11-10`  
**Repository:** `OnceOnly-DataNova`  
**Branch:** `datanova/phase-0-baseline`  
**Milestone:** `SPRINT 3.4 COMPLETE`  
**Status:** `VERIFIED — 0 LINT ERRORS, 0 BUILD ERRORS, 245/245 BACKEND TESTS, 24/24 CONTRACT TESTS`

---

### Executive Summary

Sprint 3.4 transforms the `/observatory` route from a preliminary shell into a multi-track market intelligence observatory. Leveraging the analytical engines delivered in Phase 2C Stage 1 (Market Population, Dual-Track Concentration & Batch Fragmentation) and Stage 2 (Temporal Retirement Activity, Velocity Dynamics, MAD Burst Detection & Coverage Inactivity Gaps), the workspace delivers comprehensive oversight of carbon credit allocations across Verra VCS and Gold Standard.

In strict adherence to the project's engineering principles:
1. **Live Backend Grounding:** All metrics, distributions, Gini coefficients, Lorenz curves, velocity trends, burst alerts, and gap intervals are computed directly by the FastAPI backend (`/api/analytics/*`). No synthetic or mock metrics are presented as live results.
2. **Zero External Visualization Dependencies:** All analytical visual surfaces—including the interactive **Empirical Lorenz Curve** ([`LorenzCurveChart.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/LorenzCurveChart.tsx)) and the **Dual-Metric Temporal Velocity Timeline** ([`TemporalActivityChart.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/TemporalActivityChart.tsx))—are bespoke React 19 SVG/CSS components built with zero charting dependencies, maintaining instant compilation speeds (153ms).
3. **Rigorous Methodological Disclaimers:** Every analytical track explicitly articulates data boundaries, calculation definitions, and known limitations:
   - Disclosure field presence does not establish verified corporate or legal identity.
   - 669 issuance records are strictly excluded from retirement accounting.
   - Mathematical distinction between pooled portfolio Gini (0.9605) and across-batch mean Gini (0.4924) is clearly explained.
   - Absolute micro-claims (≤ 10 tonnes) are strictly separated from relative small allocations (≤ 1% of batch).
   - Inactivity intervals do not prove market-wide dormancy or missing data.
   - Statistical bursts reflect dispersion anomalies relative to moving baselines and do not constitute proof of misconduct.

---

### 1. File Inventory & Deliverables

The table below catalogs the files created, updated, and verified in Sprint 3.4:

| Component / Subsystem | Path | Description & Role |
| :--- | :--- | :--- |
| **Analytics API Module** | [`frontend/src/api/analytics.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/analytics.ts) | Fully aligned TypeScript models matching backend Pydantic schemas (`PopulationAnalyticsSummary`, `DualTrackCoverage`, `ConcentrationMetrics`, `FragmentationMetrics`, `BatchIntervalStructure`, `BatchAnalyticsResult`). |
| **Temporal API Module** | [`frontend/src/api/temporal.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/temporal.ts) | Fully aligned TypeScript models matching backend Pydantic schemas (`TemporalActivityResponse`, `TemporalActivityPeriod`, `TemporalTrendsResponse`, `TemporalTrendPeriod`, `TemporalBurstsResponse`, `TemporalBurstPeriod`, `TemporalGapsResponse`, `TemporalGapItem`). |
| **Analytical UI Primitives** | [`frontend/src/components/AnalyticalPrimitives.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/AnalyticalPrimitives.tsx), [`frontend/src/components/primitives.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/primitives.tsx) | Added `ConcentrationTierBadge` (handling 6 descriptive concentration bands), `BurstTypeBadge` (handling Volume, Frequency, and Dual bursts), and `TrendDirectionBadge` (handling Increasing, Decreasing, and Stable velocity trends). |
| **Empirical Lorenz Curve** | [`frontend/src/components/LorenzCurveChart.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/LorenzCurveChart.tsx) | Pure React 19 SVG/CSS component rendering the empirical Lorenz curve plotted from sorted cumulative population share vs cumulative allocation-volume share, line of perfect equality ($y = x$), shaded inequality gap area, interactive hover coordinates, and an accessible decile distribution table. |
| **Temporal Velocity Timeline** | [`frontend/src/components/TemporalActivityChart.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/TemporalActivityChart.tsx) | Pure React 19 SVG/CSS component rendering dual-axis/dual-metric timelines (Volume in Tonnes vs Frequency in Record Counts), rolling average velocity badges, interactive hover cursor, summary metric bar, and accessible fallback data table. |
| **Observatory Workspace** | [`frontend/src/pages/Observatory.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/Observatory.tsx) | Multi-track market intelligence workspace providing 4 dedicated tracks: (1) Population Census & Dual-Track Disclosure; (2) Beneficiary Concentration & Lorenz Curve; (3) Batch Fragmentation Explorer; (4) Temporal Dynamics, Bursts & Inactivity Gaps. |
| **Automated Playwright QA** | [`frontend/qa/tests/ui.spec.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/qa/tests/ui.spec.ts) | 4 dedicated end-to-end tests validating population census rendering, concentration metrics, Lorenz curve decile toggling, batch inspection presets, interval validation, temporal daily/weekly/monthly toggles, MAD burst detection, and zero-activity gap visualization. |

---

### 2. Detailed Track Architecture & Analytical Capabilities

#### 2.1 Track 1: Population Census & Dual-Track Disclosure
Consumes `GET /api/analytics/population/summary` and `GET /api/cross-registry/retirements/summary`:
- **Population Totals:** `87,668,330.0 t` retired across `37,335` validated retirement records and `725` issuance batches (`557` multi-claimant, `168` single-claimant).
- **Issuance Exclusion Invariant:** `669` issuance transactions strictly excluded to maintain pure retirement accounting.
- **Registry Distribution:**
  - Verra (VCS): `79,964,179 t` across `30,111` records (`16` census projects), `44.55%` beneficiary disclosure rate.
  - Gold Standard (GS): `7,704,151 t` across `7,224` records (`6` census projects), `7.31%` beneficiary disclosure rate.
- **Dual-Track Disclosure Classification:**
  - *Non-Placeholder Disclosed:* `13,935` records (`37.32%`), `35,172,359 t` (`40.12%`).
  - *Explicitly Undisclosed:* `23,393` records (`62.66%`), `52,342,165 t` (`59.71%`).
  - *Invalid or Placeholder:* `7` records (`0.02%`), `153,806 t` (`0.18%`).
  - *Unresolved Identity:* `23,400` records (`62.68%`), `52,495,971 t` (`59.88%`).
- **Policy Disclosure Note:** Stated clearly that disclosure-field presence reflects populated metadata in registry filings and does not establish verified corporate identity, legal entity status, or end-beneficiary claim entitlement.

#### 2.2 Track 2: Beneficiary Concentration & Lorenz Curve
Consumes `overall_concentration` from `GET /api/analytics/population/summary`:
- **Concentration Indices:**
  - `hhi_disclosed`: `215.17` out of 10,000 across `9,933` unique disclosed entities, classified as **High Dispersion (HHI < 500)**.
  - Dominant entity share: Telstra Corporation Limited (`10.71%`, `3,767,118 t`).
  - Combined top 3 entity share: `23.13%` (Telstra 10.71%, Shell 8.70%, Yamato Transport 3.72%).
  - Shannon Equitability: `0.706` (normalized base-2 entropy: `9.37` bits).
- **Inequality Duality (Macro vs Micro):**
  - *Pooled Allocation Gini (`0.9605`):* Measures macro credit sizing inequality across all 37,335 allocations in the portfolio (mean size: 2,348.15 t).
  - *Across-Batch Mean Gini (`0.4924`):* Measures average within-batch Gini across 725 batches, capturing allocation uniformity within projects.
  - Explanatory note clarifies that within-batch allocations are relatively uniform, while portfolio-wide sizing is heavily skewed by massive institutional tranches.
- **Empirical Lorenz Curve:**
  - Bespoke SVG component plotting ascending cumulative population share vs cumulative volume share.
  - Visual inspection confirms extreme Pareto skew: bottom 80% of disclosed entities hold only 0.41% of volume; top 1% holds 48.2% of volume.
  - Decile breakdown table accessible for screen readers and export.
- **Top 10 Disclosed Beneficiaries Table:** Lists Telstra Corporation, Shell, Yamato Transport, Eni Plenitude, Eprimo GmbH, etc., with disclosed share, estimated volume, and methodological disclaimer.

#### 2.3 Track 3: Batch Fragmentation Explorer
Consumes `GET /api/analytics/batches/{registry}/{batch_id}`:
- **Searchable Batch Inspector:** Interactive registry selector (`VCS`, `GS`) and batch ID input.
- **Demonstration Presets:**
  - `VCS 10918`: Guanare Forest Plantations, Uruguay (2,448 allocations, 109,001 t, Gini 0.9545, 2,425 micro-claims ≤ 10 tonnes — high micro-claim fragmentation).
  - `GS GS1-1-TR-GS707-21-2016-20993`: Istanbul Landfill Gas, Turkey (2,271 allocations, 432,388 t, Gini 0.8872 — large municipal multi-claimant batch).
  - `VCS 5972`: Kinnaur Hydroelectric, India (397 allocations, 500,000 t, Gini 0.9654 — large industrial batch).
  - `GS GS1-1-IN-GS5673-12-2021-22771`: DDWL Renewable Energy, India (936 allocations, 47,225 t, Gini 0.7410).
- **Tranche Sizing Metrics:**
  - Mean event size, median event size, min/max event size, IQR, sample Gini, finite-sample corrected Gini.
  - **Absolute Micro-Claims (≤ 10.0 tonnes):** Evaluates fixed de minimis retail transactions (e.g., 2,425 claims in VCS 10918).
  - **Relative Small Tranches (≤ 1.0% of batch):** Evaluates allocations scaled relative to batch volume (e.g., 2,447 claims in VCS 10918).
  - Dedicated callout explains the operational and mathematical distinction between absolute and relative thresholds.
- **Interval Structure & Validation:**
  - Interval density, span, contiguous blocks, disjoint gaps.
  - Overlap collision validation: reports 0 overlaps on validated batches, or flags overlapping intervals with an alert badge.
- **Batch-Specific Lorenz Curve:** Embedded directly when a batch contains multiple disclosed claimants.

#### 2.4 Track 4: Temporal Dynamics, Velocity Bursts & Inactivity Gaps
Consumes `/api/analytics/temporal/*`:
- **Multi-Granularity Time Series:**
  - Daily (365-day recent window across 5,791 observed days), Weekly (156-week window across 828 ISO Monday-Sunday weeks), Monthly (192 continuous periods).
  - Filtering by registry (`VCS`, `GS`) and date range (`start_date`, `end_date`).
- **Bespoke Activity Timeline Chart:**
  - Dual-metric display: Volume (Tonnes in Glacier `#0284c7`) and Transaction Frequency (Record count in Lichen `#16a34a`).
  - Interactive cursor and tooltip card with rolling velocity trend badges (`Increasing`, `Decreasing`, `Stable`).
- **MAD-Based Burst Detection Inspector:**
  - 51 anomaly periods detected in the portfolio at sensitivity $k = 3.0$ MAD multiplier over a 12-period moving baseline.
  - Visual badges: `VOLUME` burst, `RECORD_COUNT` burst, `DUAL` burst.
  - Displays observed tonnes/records, baseline median, MAD threshold, and human-readable explanation.
  - Analytical caveat: Bursts represent statistical dispersion anomalies relative to moving baselines and do NOT prove misconduct.
- **Reporting Inactivity Gaps Inspector:**
  - 10 reporting blackout intervals identified (max 91 days, mean 57.0 days).
  - Displays gap duration, start/end dates, prior activity period, next activity period, and gap classification (`INTERMITTENT_ZERO_ACTIVITY_INTERVAL`, `SUSTAINED_ZERO_ACTIVITY_INTERVAL`).
  - Analytical caveat: Zero observed records reflects transactions within the ingested reference dataset and does NOT establish market-wide dormancy, missing data, or lack of secondary trading.

---

### 3. Verification & Quality Assurance

#### 3.1 Static Analysis & Linting
Executed Oxlint across all 47 frontend source files:
```bash
cd frontend && npm run lint
# Output:
# Found 0 warnings and 0 errors.
# Finished in 24ms on 47 files with 116 rules using 10 threads.
```

#### 3.2 Production Build
Executed TypeScript type-checking and Vite production compilation:
```bash
cd frontend && npm run build
# Output:
# ✓ 1965 modules transformed.
# dist/assets/Observatory-Cr5ARP7C.js   51.63 kB │ gzip: 11.30 kB
# dist/assets/index-DgokjV_f.js       350.54 kB │ gzip: 107.83 kB
# ✓ built in 153ms
```

#### 3.3 Backend Test Suite (Read-Only Preservation)
Executed the complete backend regression test suite:
```bash
./.venv/bin/pytest backend/tests
# Output:
# ======================= 245 passed, 2 warnings in 7.00s ========================
```

#### 3.4 Smart Contract Test Suite
Executed Hardhat contract tests:
```bash
cd contracts && npm test
# Output:
#   24 passing (1s)
```

---

### 4. Conclusion & Next Sprint Readiness

Sprint 3.4 is complete, verified, and adheres to all engineering and architectural standards:
- The `/observatory` route is a complete, multi-track market intelligence workspace.
- The UI is grounded in live FastAPI backend models with zero fabricated metrics.
- The visual surfaces use pure React 19 SVG/CSS with zero external charting dependencies.
- The repository is 100% clean, with zero lint warnings, zero build errors, 245/245 passing backend tests, and 24/24 passing smart contract tests.

The repository is now ready for **Sprint 3.5: Public Verification Portal (`/verify`) & Forensic Evidence Ledger (`/evidence`)**.

---
*End of Sprint 3.4 Implementation Report.*

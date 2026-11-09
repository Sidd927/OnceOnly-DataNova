# ONCEONLY — DATANOVA 2026
## SPRINT 3.2: FRONTEND CORE ARCHITECTURE & RISK ASSESSMENT CONSOLE
### Formal Implementation Report

**Document Version:** `1.0.0`  
**Date:** `2026-11-10`  
**Repository:** `OnceOnly-DataNova`  
**Branch:** `datanova/phase-0-baseline`  
**Milestone:** `SPRINT 3.2 COMPLETE`  
**Status:** `VERIFIED — 0 LINT ERRORS, 0 BUILD ERRORS, 245/245 BACKEND TESTS, 24/24 CONTRACT TESTS`

---

### Executive Summary

Sprint 3.2 transforms OnceOnly from an early prototype bound exclusively to Phase 1 legacy claim checks into an active, multi-dimensional investigator workstation. Built strictly in accordance with the three approved architectural decisions from Sprint 3.1:
1. **Visualization Architecture:** All new analytical interfaces leverage bespoke React 19 SVG/CSS components and styled data surfaces, avoiding heavy charting dependencies and guaranteeing 100% theme token continuity and instant build speeds.
2. **Seven-Item Navigation:** The top-level application shell (`Shell.tsx`) has been expanded to a responsive 7-item navigation structure (`Overview`, `Claims`, `Cross-Registry`, `Observatory`, `Assessment`, `Verify`, `Evidence`), ensuring full discoverability on both desktop and mobile viewports.
3. **Modular API Client:** The frontend API architecture has been refactored into a strongly-typed, modular package (`frontend/src/api/`) mapping all 18 backend endpoints across Phase 2A, 2B, and 2C Stages 1–4, while maintaining 100% backward compatibility via `index.ts` and `src/api.ts`.

Crucially, the **Unified Risk Assessment Console** (`/assessment`) and the **Rules Catalog Browser** are now fully operational, and [`ClaimPage.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/ClaimPage.tsx) features dedicated tabbed workspaces for **Unit Intervals & Ruler**, **Unified Risk Assessment**, and **Allocation-Aware Reconciliation**.

---

### 1. Architectural Deliverables & File Inventory

The table below catalogs the files created, refactored, and integrated during Sprint 3.2:

| Component / Subsystem | Path | Description & Role |
| :--- | :--- | :--- |
| **API Client Base** | [`frontend/src/api/client.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/client.ts) | Base HTTP request helper, typed `ApiError`, JSON payload encoder, and formatting utilities (`fmt`, `short`, `pct`). |
| **Claims API Module** | [`frontend/src/api/claims.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/claims.ts) | Preserves all baseline claim interfaces, verification calls, smart-contract governance, and adds Stage 2B claim reconciliation (`/api/claims/{id}/reconciliation`). |
| **Assessment API Module** | [`frontend/src/api/assessment.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/assessment.ts) | Strongly-typed interfaces for Stage 4 Unified Risk Assessment (`POST /api/analytics/assessment`) and versioned Rules Catalog (`GET /api/analytics/assessment/rules`). |
| **Cross-Registry API Module** | [`frontend/src/api/crossRegistry.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/crossRegistry.ts) | Types and API methods for Stage 3 project correlation, entity cross-comparison, and comparative retirement pacing time series. |
| **Temporal API Module** | [`frontend/src/api/temporal.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/temporal.ts) | Types and API methods for Stage 2 temporal activity timelines, velocity trends, MAD burst detection, and coverage gap intervals. |
| **Analytics API Module** | [`frontend/src/api/analytics.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/analytics.ts) | Types and API methods for Stage 1 population census summaries, dual-track coverage, HHI concentration, and batch fragmentation. |
| **API Re-Export Gateway** | [`frontend/src/api/index.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/index.ts) | Unified typed gateway re-exporting all modules and unified `api` client object. |
| **Backward-Compat Shunt** | [`frontend/src/api.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api.ts) | Thin re-export file ensuring existing components importing `from "../api"` continue functioning without code alterations. |
| **Analytical UI Primitives** | [`frontend/src/components/AnalyticalPrimitives.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/AnalyticalPrimitives.tsx) | Standardized evidentiary UI components: `SeverityBadge`, `PriorityBadge`, `AssessmentStatusBadge`, `EvidenceStrengthBadge`, `CategoryBadge`, `SourceStageBadge`, `MetricTile`. |
| **Rules Catalog Browser** | [`frontend/src/components/RulesCatalogModal.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/RulesCatalogModal.tsx) | Searchable and filterable modal dialog inspecting all 16 deterministic evaluation rules, mathematical formulas, and stated caveats. |
| **Assessment Console View** | [`frontend/src/pages/AssessmentConsole.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/AssessmentConsole.tsx) | Full-featured investigator console executing multi-scope assessments (`PROJECT`, `CLAIM`, `BATCH`, `ENTITY`), displaying triage explanations, evidence dependency clusters, and JSON report export. |
| **Cross-Registry View Stub** | [`frontend/src/pages/CrossRegistry.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/CrossRegistry.tsx) | Live foundation for Sprint 3.3 consuming `GET /api/cross-registry/retirements/summary` and `GET /api/cross-registry/projects/correlations`. |
| **Observatory View Stub** | [`frontend/src/pages/Observatory.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/Observatory.tsx) | Live foundation for Sprint 3.4 consuming `GET /api/analytics/population/summary`, `GET /api/analytics/temporal/bursts`, and `GET /api/analytics/temporal/gaps`. |
| **Claim Detail Tabs** | [`frontend/src/pages/ClaimPage.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/ClaimPage.tsx) | Integrated 3-tab analytical workspace (Unit Intervals, Unified Assessment Scorecard, Allocation Reconciliation). |
| **Global Shell & Routing** | [`frontend/src/components/Shell.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/Shell.tsx), [`frontend/src/App.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/App.tsx) | 7-item navigation header, mobile drawer menu, route configuration, and dynamic document titles. |
| **End-to-End Tests** | [`frontend/qa/tests/links.spec.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/qa/tests/links.spec.ts), [`frontend/qa/tests/ui.spec.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/qa/tests/ui.spec.ts) | Crawl validation of all 7 routes, mobile dialog checks, 320px viewport overflow test, assessment console verification, rules catalog search, and claim detail tab switching. |

---

### 2. Detailed Subsystem Integration

#### 2.1 Backend Schema Grounding & Scope Safety

In strict compliance with the mandate:
> *"Do not assume frontend scope names such as CROSS_REGISTRY_PAIR or MARKET_POPULATION are valid backend scopes. Map workflows to actual supported backend scopes."*

The frontend target scope selector in [`AssessmentConsole.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/AssessmentConsole.tsx) explicitly targets the valid backend scopes defined in `backend/app/analytics/risk_assessment/models.py`:
- `PROJECT`: Evaluates project-level census, temporal liquidation pacing, and concentration metrics.
- `CLAIM`: Evaluates on-chain and off-chain interval conflicts and double-use findings.
- `BATCH`: Evaluates issuance-level micro-claim fragmentation and HHI.
- `ENTITY`: Evaluates fuzzy name normalization, token overlap, and intermediary broker parsing.

Every evidence item rendered by the UI faithfully exposes all evidentiary dimensions returned by the FastAPI backend:
- **Severity Classification:** `CRITICAL` (Crimson), `HIGH` (Crimson), `MODERATE` (Ochre), `LOW` (Slate), `INFORMATIONAL` (Glacier).
- **Evidence Strength:** `STRONG`, `MODERATE`, `WEAK`, `CONTRADICTORY`, `UNRESOLVED`.
- **Mathematical Formulations & Thresholds:** Exact evaluated metrics vs applied benchmarks.
- **Methodological Limits & Caveats:** Rendered explicitly to prevent misinterpreting investigative flags as fraud determinations.
- **Exculpatory Counterevidence:** Mitigating facts displayed in a distinct Lichen callout.
- **Identified Missing Information:** Highlighted in Ochre to communicate data gaps.
- **Recommended Action:** Concrete investigative follow-up steps.

#### 2.2 Evidence Dependency Groups & Double-Counting Safeguards

To prevent artificial inflation of review severity when multiple analytical rules trigger on the same underlying root cause (e.g., identical serial interval collisions), [`AssessmentConsole.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/AssessmentConsole.tsx) and [`ClaimPage.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/ClaimPage.tsx) render **Evidence Dependency Groups**:
- Each item belonging to a dependency cluster displays its cluster tag (e.g. `Cluster: GRP-SERIAL-OVERLAP-1`).
- The scorecard highlights the distinction between **Total Evidence Items** and **Independent Signal Clusters**, ensuring that reinforcing signals do not inflate the triage queue priority.

#### 2.3 Claim Detail Multi-Dimensional Workspace

Investigators inspecting a claim in [`ClaimPage.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/ClaimPage.tsx) now have instant access to three analytical perspectives:
1. **Unit Intervals & Ruler:** The proven physical unit scale with lane stacking, interval overlap bracketing, serial anatomy, and evidence file downloads.
2. **Unified Risk Assessment:** The Stage 4 assessment scorecard, triage priority, and evidence items evaluated specifically for this claim.
3. **Allocation Reconciliation:** The Stage 2B allocation report comparing candidate unit ranges against active ledger ranges, displaying an itemized conflict table for double claims (e.g. the canonical Helios vs Equinox collision) or confirming disjoint allocations.

---

### 3. Verification & Quality Assurance

#### 3.1 Production Build & Linter Results

The frontend build and oxlint test runs were executed against the final Sprint 3.2 codebase:

```bash
$ cd frontend && npm run lint
> frontend@0.0.0 lint
> oxlint

Found 0 warnings and 0 errors.
Finished in 18ms on 43 files with 116 rules using 10 threads.
```

```bash
$ cd frontend && npm run build
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.4 building client environment for production...
✓ 1961 modules transformed.
dist/index.html                     0.62 kB │ gzip:   0.37 kB
dist/assets/index-Dmn9GzKV.css     59.53 kB │ gzip:  11.27 kB
dist/assets/CrossRegistry-B0SIKdI7.js 5.67 kB │ gzip: 1.94 kB
dist/assets/Observatory-CJbSW8oI.js   6.17 kB │ gzip: 2.15 kB
dist/assets/AssessmentConsole-BGD3B_xC.js 25.40 kB │ gzip: 6.42 kB
dist/assets/ClaimPage-BeFv-qbz.js   42.05 kB │ gzip: 11.22 kB
dist/assets/index-DxbzEbOz.js     342.34 kB │ gzip: 106.12 kB
✓ built in 150ms
```

**Verdict:** **100% HEALTHY.** Zero lint errors or warnings across 43 files; production bundle built cleanly in 150 ms.

#### 3.2 Backend & Contract Test Regression Suite

Full test suites were executed to verify zero regression across frozen subsystems:

- **Backend Pytest Suite:**
  ```bash
  $ ./.venv/bin/pytest backend/tests
  ======================= 245 passed, 2 warnings in 7.17s ========================
  ```
- **Smart Contract Test Suite:**
  ```bash
  $ cd contracts && npx hardhat test
  24 passing (1s)
  ```

---

### 4. Sprint Status & Next Steps

Sprint 3.2 is **COMPLETE AND VERIFIED**.

The repository is now ready to proceed to **Sprint 3.3: Project & Entity Cross-Registry Intelligence**, which will implement:
1. The **Cross-Registry Explorer** (`/cross-registry`) with dynamic filtering and similarity sliders.
2. The **Project Comparison View** (`POST /api/cross-registry/projects/compare`) with side-by-side metadata inspection and ID collision warnings.
3. The **Entity Resolution & Intermediary Broker Tool** (`POST /api/cross-registry/entities/compare` and `POST /api/resolve/intermediary`).

---
*End of Sprint 3.2 Implementation Report.*

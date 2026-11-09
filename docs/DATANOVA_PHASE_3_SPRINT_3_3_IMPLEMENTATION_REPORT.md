# ONCEONLY — DATANOVA 2026
## SPRINT 3.3: CROSS-REGISTRY PROJECT & ENTITY INTELLIGENCE WORKSPACE
### Formal Implementation Report

**Document Version:** `1.0.0`  
**Date:** `2026-11-10`  
**Repository:** `OnceOnly-DataNova`  
**Branch:** `datanova/phase-0-baseline`  
**Milestone:** `SPRINT 3.3 COMPLETE`  
**Status:** `VERIFIED — 0 LINT ERRORS, 0 BUILD ERRORS, 245/245 BACKEND TESTS, 24/24 CONTRACT TESTS`

---

### Executive Summary

Sprint 3.3 transforms the `/cross-registry` route into an active, multi-modal investigator intelligence workspace. Designed specifically for carbon market integrity analysts and forensic investigators, the updated interface enables users to explore candidate project relationships, compare cross-registry project attributes side-by-side, analyze retirement pacing over time, and resolve entity identities and intermediary broker delegations across Verra VCS and Gold Standard.

In strict alignment with the approved architecture and the foundational methodology established in Phase 2A and Phase 2C Stage 3:
1. **Real Analytical Grounding:** All analytical results, metrics, token decompositions, and pacing trends are driven directly by the live FastAPI backend engines. No synthetic or hardcoded metrics are presented as live results.
2. **Zero External Visualization Dependencies:** The time-series visualization is implemented as a pure React 19 SVG/CSS component (`ComparativePacingChart.tsx`), matching the precision and visual language of `Ruler.tsx` while achieving instant build speeds (151ms).
3. **Disjoint Namespace & Legal-Entity Invariants:** The workspace strictly enforces the Phase 2C Stage 3 acceptance audit principles:
   - Identical project ID strings across distinct registries are classified strictly as `CROSS_REGISTRY_IDENTIFIER_COLLISION` and never elevate evidence strength.
   - Distinct educational callouts reinforce that voluntary registries maintain disjoint, uncoordinated identifier namespaces.
   - Lexical name similarity does not prove legal-entity equivalence; intermediary brokers and beneficiaries are parsed into separate roles.

---

### 1. File Inventory & Deliverables

The table below catalogs the files created, upgraded, and verified in Sprint 3.3:

| Component / Subsystem | Path | Description & Role |
| :--- | :--- | :--- |
| **Cross-Registry API Module** | [`frontend/src/api/crossRegistry.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/api/crossRegistry.ts) | Fully aligned TypeScript interfaces matching backend Pydantic models (`CrossRegistryProjectComparison`, `ProjectCorrelationCategory`, `EvidenceStrength`, `RegistryRetirementStats`, `CrossRegistryRetirementSummary`, `CrossRegistryTrendsResponse`, `EntityResolutionResult`, `IntermediaryExtractionResult`) and added methods for entity resolution and intermediary parsing. |
| **Analytical UI Primitives** | [`frontend/src/components/AnalyticalPrimitives.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/AnalyticalPrimitives.tsx), [`frontend/src/components/primitives.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/primitives.tsx) | Added `ProjectCorrelationCategoryBadge` handling all 7 backend correlation categories with dedicated styling and warning icons for identifier collisions and attribute conflicts. Enhanced `EvidenceStrengthBadge` to support `INSUFFICIENT`. |
| **Comparative Pacing Chart** | [`frontend/src/components/ComparativePacingChart.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/ComparativePacingChart.tsx) | Pure React 19 SVG/CSS dual-series visualization consuming `GET /api/cross-registry/retirements/trends`. Renders yearly grouped bars (17 years) and monthly area curves (173 months), dual-series color coding (Glacier for VCS, Lichen for GS), interactive hover inspection, summary statistics, and an accessible fallback data table. |
| **Project Comparison Modal** | [`frontend/src/components/ProjectCompareModal.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/components/ProjectCompareModal.tsx) | Deep-inspection pairwise comparison dialog displaying side-by-side project profiles, composite name similarity, token set/sort/Jaro-Winkler metrics, token overlap highlighting chips, attribute relation matrix, corroborating/contradictory signals, investigative explanation, limitations, and direct link to Unified Risk Assessment. |
| **Cross-Registry Workspace** | [`frontend/src/pages/CrossRegistry.tsx`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/src/pages/CrossRegistry.tsx) | Comprehensive 3-tab investigator workspace featuring: (1) Comparative Census macro banner; (2) Comparative Retirement Pacing Chart; (3) Three operational workspace modes: Correlation Explorer, Pairwise Project Comparator Studio, and Entity Resolution & Intermediary Broker Studio. |
| **Automated Playwright QA** | [`frontend/qa/tests/ui.spec.ts`](file:///Users/siddhant_patil/Projects/OnceOnly-DataNova/frontend/qa/tests/ui.spec.ts) | 4 dedicated end-to-end tests validating macro census rendering, pacing chart toggling, candidate correlation filtering, comparison modal inspection, demonstration presets, identifier collision safety callouts, and entity/intermediary extraction workflows. |

---

### 2. Workspace Modes & Key Features

#### 2.1 Comparative Voluntary Registry Census Banner
Consumes `GET /api/cross-registry/retirements/summary` and presents key macro indicators:
- **Verra VCS Volume:** `79,964,179 t` across `30,111` records and `16` census projects, with a `44.5%` beneficiary identity disclosure rate.
- **Gold Standard Volume:** `7,704,151 t` across `7,224` records and `6` census projects, with a `7.3%` beneficiary identity disclosure rate.
- **Combined Volume:** `87,668,330 t` across `37,335` verified retirement events.
- **Pure Retirement Accounting Invariant:** `669` issuance transactions strictly excluded from retirement volume calculations.
- **Comparability Notes:** Inline callout explaining schema differences between registries (unpopulated project fields in GS, serial formatting in VCS).

#### 2.2 Comparative Retirement Pacing Time Series
Consumes `GET /api/cross-registry/retirements/trends` and provides:
- **Dual Granularity:** Toggle between **Yearly** (17 calendar years from 2010 to 2026) and **Monthly** (173 monthly intervals).
- **Dual Series Visuals:** Verra VCS rendered in Glacier (`#0284c7`), Gold Standard in Lichen (`#16a34a`).
- **Interactive Cursor & Tooltip:** Displays period label, exact retired tonnes for both standards, and record counts.
- **Accessible Fallback Data Table:** Accessible data table toggle rendering full tabular data for screen readers and export.

#### 2.3 Mode 1: Correlation Explorer
Consumes `GET /api/cross-registry/projects/correlations` and provides:
- **Multi-Parametric Filtering:** Minimum name similarity threshold slider/dropdown (`0.75`, `0.65`, `0.50`, `0.30`), Evidence Category filter, Country jurisdiction search, and live text search.
- **Evidentiary Badging:** `ProjectCorrelationCategoryBadge` (`CROSS_REGISTRY_IDENTIFIER_COLLISION`, `STRONG_ATTRIBUTE_CORRELATION`, `PARTIAL_ATTRIBUTE_CORRELATION`, etc.) and `EvidenceStrengthBadge`.
- **Identifier Collision Safety Alerts:** When an identifier collision is detected, a prominent warning chip highlights that registries operate uncoordinated namespaces.
- **Actions:** "Inspect Pair" opens the `ProjectCompareModal`; "Assess" deep-links directly to `/assessment?scope=PROJECT&registry=...&project_id=...`.

#### 2.4 Mode 2: Pairwise Project Comparator Studio
Consumes `POST /api/cross-registry/projects/compare` and provides:
- **Demonstration Presets:**
  - *Preset 1 (Attribute Correlation):* VCS 1904 vs GS 3044 (Tamil Nadu Wind Power, matching India, overlapping 2019 vintage).
  - *Preset 2 (Identifier Collision):* VCS 1845 vs GS 1845 (Rimba Raya, Indonesia vs Kasigau Corridor, Kenya). Highlights that identical ID 1845 does not establish project identity or wrongdoing.
  - *Preset 3 (Conflicting Jurisdiction):* VCS 2284 vs GS 3044 (DDWL Renewable Energy, Brazil vs India jurisdiction clash).
- **Interactive Pairwise Form:** Allows investigators to input arbitrary project attributes across VCS, GS, ACR, CAR, etc.
- **Detailed Scorecard:** Displays composite similarity, token set ratio, token sort ratio, Jaro-Winkler similarity, attribute relation matrix (ID, Country, Vintage, Developer), corroborating/contradictory signals, and human-readable explanations.

#### 2.5 Mode 3: Entity Resolution & Intermediary Broker Studio
- **Legal-Entity Non-Equivalence Principle:** Educates investigators that matching names across registries do not prove corporate identity, preventing false double-claim allegations.
- **Sub-tool A (Cross-Registry Entity Resolution):** Calls `POST /api/cross-registry/entities/compare` with presets for Canonical Variants (`Microsoft Corporation` vs `Microsoft Corp.`), Suffix/Form variants (`Acme Carbon Trading LLC` vs `Acme Carbon Trading Inc.`), and Geographic variants (`EcoAct UK` vs `EcoAct France`). Displays match tier, overall score, canonical names, positive signals, contradictory signals, and legal disclaimers.
- **Sub-tool B (Intermediary & Broker Allocation Parser):** Calls `POST /api/resolve/intermediary` to parse complex narrative retirement strings (e.g., *"Retired by South Pole Carbon Asset Management Ltd on behalf of Apple Inc."*). Accurately separates Intermediary Party (South Pole, role: `BROKER_OR_TRADER`) from Principal Beneficiary (Apple Inc.), displaying pattern matched, confidence score, and extraction notes.

---

### 3. Verification & Quality Assurance

#### 3.1 Static Analysis & Linting
Executed Oxlint across all 45 frontend source files:
```bash
cd frontend && npm run lint
# Output:
# Found 0 warnings and 0 errors.
# Finished in 20ms on 45 files with 116 rules using 10 threads.
```

#### 3.2 Production Build
Executed TypeScript type-checking and Vite production compilation:
```bash
cd frontend && npm run build
# Output:
# ✓ 1963 modules transformed.
# dist/assets/CrossRegistry-uomsXrDX.js   67.52 kB │ gzip: 12.34 kB
# dist/assets/index-CE-aEDtv.js         345.02 kB │ gzip: 106.72 kB
# ✓ built in 151ms
```

#### 3.3 Backend Test Suite (Read-Only Preservation)
Executed the complete backend test suite:
```bash
./.venv/bin/pytest backend/tests
# Output:
# ======================= 245 passed, 2 warnings in 7.17s ========================
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

Sprint 3.3 is complete, verified, and adheres to all engineering and architectural standards:
- The `/cross-registry` page is a complete, explainable investigator workspace.
- The UI is grounded in live FastAPI backend models with zero fabricated metrics.
- The visualization uses pure React 19 SVG/CSS with zero external charting dependencies.
- The repository is 100% clean, with zero lint warnings, zero build errors, 245/245 passing backend tests, and 24/24 passing smart contract tests.

The repository is now ready for **Sprint 3.4: Market Population & Temporal Dynamics Observatory (`/observatory`)**.

---
*End of Sprint 3.3 Implementation Report.*

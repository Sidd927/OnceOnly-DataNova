# ONCEONLY — DATANOVA 2026
## PROJECT COMPLETION ROADMAP: PHASES 3 & 4
### Transition from Analytical Foundation to Shipped Investigator Product

**Document Version:** `1.0.0`  
**Date:** `2026-11-10`  
**Repository:** `OnceOnly-DataNova`  
**Core Delivery Principle:** *No more major backend analytics expansion unless an essential product requirement demands it. The analytics foundation is complete, verified, and frozen. Our singular objective is now building, validating, and shipping a complete, polished, working product for the DATANOVA 2026 submission.*

---

### Executive Overview & Milestone Progression

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETED & FROZEN PHASES                              │
│  Phase 0: Baseline Hygiene & Determinism                                        │
│  Phase 1: Ingestion & Census Conservation (37,335 records, 87.6M tonnes)       │
│  Phase 2A: Entity Resolution & Intermediary Broker Parsing                      │
│  Phase 2B: Allocation-Aware Reconciliation & Interval Geometry                  │
│  Phase 2C Stage 1: Beneficiary Concentration & Batch Fragmentation              │
│  Phase 2C Stage 2: Temporal Retirement Intelligence (Activity, Bursts, Gaps)    │
│  Phase 2C Stage 3: Cross-Registry Intelligence (VCS vs GS Project Correlation)  │
│  Phase 2C Stage 4: Unified Explainable Risk Assessment (16 Rules, 6 Scopes)     │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ACTIVE MILESTONE: PHASE 3                              │
│                 PRODUCT INTEGRATION & INVESTIGATOR DASHBOARD                    │
│  - Real-time React frontend consuming FastAPI backend                           │
│  - Multi-scope investigative navigation (Projects, Batches, Claims, Entities)   │
│  - Interactive visualizations for Concentration, Fragmentation & Bursts         │
│  - Explainable Assessment Viewer with Provenance, Caveats & Action Plans        │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                PHASE 4                                          │
│                   END-TO-END VALIDATION & RELEASE PACKAGE                       │
│  - E2E smoke tests & demo scenarios on live stack                               │
│  - Reference film recording & beats validation                                  │
│  - Submission architecture, Devpost package & compliance sign-off               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 3 — Product Integration & Investigator Dashboard

### 1. Frontend Architecture & Design Philosophy
The frontend (`frontend/`) leverages React 18, Vite, and Tailwind CSS to deliver an institutional-grade investigator workspace:
- **Zero Mock Data:** The UI communicates exclusively with the active FastAPI backend (`http://127.0.0.1:8000`). All metrics, charts, tables, and evidence items reflect live backend computations over the SQLite registry census and Hardhat ledger.
- **Explainability First:** Visualizations prioritize interpretability over flashiness. Statistical outliers highlight exact baseline medians, MAD dispersions, and conservative priority badges.
- **Investigative Workflow Alignment:** Triage queues mirror standard financial intelligence desks: triage $\to$ drill-down $\to$ evidence review $\to$ action determination.

### 2. Core Functional Modules to Deliver

#### Module 3.1: Platform Identity & Landing Hub (`/`)
- Clear product thesis: *"Every retired tonne, claimed once."*
- System status indicators: Ledger connectivity (Hardhat RPC), API health, and reference database status (37,335 records loaded).
- Quick search jump-box supporting project IDs, batch IDs, claim references, and corporate entities.

#### Module 3.2: Executive Market Intelligence Dashboard (`/overview`)
- Macro market KPIs: Total tracked retirement volume ($87.7\text{M tonnes}$), active batches ($725$), total entities ($2,841$).
- Aggregate distribution metrics: High-concentration batch count, micro-claim density rate, and active cross-registry correlation clusters.
- Recent ledger registrations and on-chain challenge statuses.

#### Module 3.3: Project Search & Temporal Intelligence (`/projects`)
- Filterable search across 1,900+ Verra VCS and Gold Standard projects by registry, country, and methodology.
- Project Detail View:
  - Interactive monthly/weekly retirement pacing chart with continuous calendar timelines.
  - Nonparametric burst markers highlighting periods with Modified $Z \ge 3.0$ and volume $\ge 100\text{t}$.
  - Structural dormancy gap visualization distinguishing confirmed inactivity from sparse source coverage.

#### Module 3.4: Batch Concentration & Fragmentation Explorer (`/batches`)
- Batch Detail View:
  - Disclosed vs Undisclosed Dual-Track volume breakdown donut chart.
  - Top-beneficiary portfolio share and Herfindahl-Hirschman Index (HHI) gauge.
  - Event size inequality distribution (Gini curve and micro-claim density count).
  - Traceable transaction table showing event dates, serial intervals, and beneficiary strings.

#### Module 3.5: Claim Ledger & Interval Reconciliation (`/claims`)
- On-chain claim lifecycle explorer (Northwind, Helios, Arbor, Lumen, Kestrel).
- Interval conflict visualizer rendering half-open integer ranges $[s, e]$, overlapping intervals, boundary adjacencies, and disjoint split allocations.
- Real-time on-chain challenge and dispute resolution actions.

#### Module 3.6: Cross-Registry Project Comparator (`/cross-registry`)
- Side-by-side comparison matrix between Verra VCS and Gold Standard projects.
- Trigram set ratio, token sort, and Levenshtein similarity breakdown.
- Alphanumeric ID collision disambiguation explaining independent registry namespaces.

#### Module 3.7: Unified Explainable Assessment Console (`/assessment`)
- Multi-scope target assessment launcher (`BATCH`, `PROJECT`, `CLAIM`, `ENTITY`, `CROSS_REGISTRY`, `AD_HOC`).
- Evidence Inventory:
  - Categorized evidence cards with severity and evidence strength badges.
  - Dependency group clusters with visual indicators preventing cognitive double-counting.
  - Counterevidence tab cleanly delineating **Observed Facts** from **Domain Contextual Caveats**.
  - Missing data callouts and concrete recommended next steps.

---

## Phase 4 — End-to-End Validation & Release

### 1. Integration Verification Runbook
- [ ] Live stack orchestration: `make chain`, `make deploy`, `make api`, `make web`.
- [ ] End-to-end smoke test execution: `python eval/e2e_smoke.py` (all 13 lifecycle checks passing).
- [ ] Demo repeatability verification: `make reset` $\to$ `make seed` $\to$ `make demo-check` yielding canonical fingerprint `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`.
- [ ] Browser automated validation: `cd frontend && node qa/demo/validate.mjs`.

### 2. Demonstration & Presentation Assets
- [ ] Professional demonstration video following `docs/submission/03_demo_script.md` and `frontend/qa/demo/beats.mjs`.
- [ ] High-resolution product screenshots capturing the 5-claim demo story (especially `/claims/2` Helios conflict).
- [ ] Architecture diagrams updated to include Phase 2C unified assessment and React frontend integration.
- [ ] Submission compliance checklist review (`docs/submission/05_submission_compliance_checklist.md`).

---

## Immediate Next Steps (Sprint Execution)

1. **Sprint 3.1 (Current):** Inspect `frontend/` directory structure, dependencies, and existing routes.
2. **Sprint 3.2:** Wire the frontend navigation and theme to consume the new Stage 4 unified assessment API (`/api/analytics/assessment` and `/api/analytics/assessment/rules`).
3. **Sprint 3.3:** Implement interactive visualization components for concentration, temporal bursts, and interval reconciliation.

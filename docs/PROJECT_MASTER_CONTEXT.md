# OnceOnly: Project Master Context

> **Every retired tonne, claimed once.** This handover document is for engineers and coding agents continuing OnceOnly for the DATANOVA 2026 Global Data-thon.

| | |
|---|---|
| Prepared | 2026-11-10 (handover preparation; no application code changed) |
| Repository | `OnceOnly-DataNova`, remote `origin` = `https://github.com/Sidd927/OnceOnly-DataNova.git` |
| Branch at preparation | `datanova/phase-0-baseline`, tracking `origin/datanova/phase-0-baseline`, HEAD `bf08180` |
| Companion files | [`CLAUDE.md`](../CLAUDE.md) · [`AGENTS.md`](../AGENTS.md) · [`docs/DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md) |

## How to read this document

Every capability claim below has one of these status labels. Do not upgrade a label without new evidence.

| Label | Meaning |
|---|---|
| **VERIFIED (handover)** | Re-run or inspected directly in code during this handover on 2026-11-10 |
| **REPORTED** | Stated in a committed report in `docs/`. The report gives command output, but this handover did not re-run it |
| **PLANNED** | Appears in a roadmap or design document only. Not implemented |
| **LIMITATION** | A known constraint of the current implementation or data |
| **HISTORICAL** | Accurate for an earlier state of the project. Superseded or partly outdated |

---

## 1. Product overview

### 1.1 Problem

Registries (Verra VCS, Gold Standard) make sure a carbon credit is *retired* only once. Nothing checks whether the same retired units then back *two different public climate claims*. Brokers often split one retirement across several buyers. If two claims cite overlapping units, each looks valid on its own. Comparing hashes or serial strings does not catch this, because overlapping claims usually cite different serial strings and different documents.

### 1.2 Thesis

A registry serial encodes a contiguous inclusive unit range **inside one issuance batch**. A claim can therefore be treated as a set of intervals keyed by `(registry, batch)`, and double use becomes interval intersection. OnceOnly:

1. Extracts serials from evidence (deterministic parser, with an optional LLM pass).
2. Reconciles them with real registry retirement records (Berkeley VROD 2026-08).
3. Checks them against every active claim in the same `(registry, batch)` namespace and explains each finding.
4. Anchors accepted claims on a `ClaimLedger` smart contract that itself rejects overlapping ranges (`RangeOverlap`).
5. Lets anyone read claim status and check document fingerprints against the ledger.

### 1.3 What the DATANOVA work added

The DATANOVA phases add an investigative analytics layer on top of the original claim ledger:

- Entity resolution and intermediary parsing (2A)
- Allocation-aware reconciliation (2B)
- Beneficiary concentration and batch fragmentation (2C Stage 1)
- Temporal retirement intelligence (Stage 2)
- Cross-registry intelligence (Stage 3)
- A unified, explainable, multi-scope risk assessment (Stage 4)

Frontend Sprints 3.2 to 3.4 expose these in the UI.

### 1.4 Explicit non-goals

OnceOnly does **not**:

- rate credit quality, additionality or permanence;
- determine which of two overlapping claims is legitimate;
- detect fraud.

Its outputs are **investigative indicators for human review**. The `ELEVATED_REVIEW_PRIORITY` and `CRITICAL` labels mean "review first". They do not mean "misconduct found".

### 1.5 Intended users and workflows

Intended users are sustainability auditors, carbon-market integrity analysts, registry or standards-body reviewers, and hackathon judges evaluating the prototype. The workflows below come from [`docs/08_user_journeys.md`](08_user_journeys.md) and §3.2 of [`DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md`](DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md):

| Workflow | Routes | Status |
|---|---|---|
| Check a claim, read the findings, anchor it, see the contract reject an overlapping claim, challenge, resolve or withdraw | `/claims/new`, `/claims/:id`, `/claims` | REPORTED (original product, e2e-tested historically) |
| Verify a claim from the ledger and check a document fingerprint | `/verify` | REPORTED (original product) |
| Investigate projects and entities across VCS and GS | `/cross-registry` | REPORTED (Sprint 3.3) |
| Explore market population, concentration, fragmentation and temporal dynamics | `/observatory` | REPORTED (Sprint 3.4). See the metrics discrepancy in §9.1 |
| Run an explainable multi-scope assessment and browse the rule catalog | `/assessment`, and claim detail tabs | REPORTED (Sprint 3.2) |
| Read the prototype's own measurements | `/evidence` | HISTORICAL (copy predates DATANOVA; see §9) |

---

## 2. Architecture

```text
Browser (React 19 + Vite + Tailwind 4, bespoke SVG charts)
   │  /api/* (Vite dev proxy → 127.0.0.1:8000, or same-origin in the Docker image)
   ▼
FastAPI backend (backend/app)
   ├─ Claim pipeline (original product)
   │    service.py → extraction.py/serials.py → rules.py → chain.py (web3.py)
   │    app DB: var/onceonly.sqlite (claims, evidence, claim_blocks, findings, events)
   │    evidence store: var/evidence/<sha256> (content-addressed)
   ├─ Registry reference: reference.py
   │    full:  data/reference/registry_full.sqlite (built by `make data`, gitignored)
   │    demo:  var/registry_demo.sqlite (materialized from data/reference/demo_subset.csv.gz)
   ├─ entity_resolution/   Phase 2A
   ├─ reconciliation/      Phase 2B
   └─ analytics/           Phase 2C Stages 1–4 (read-only SQLite access; see §9.3)
         concentration.py · fragmentation.py · temporal.py · cross_registry.py · engine.py
         risk_assessment/ (engine, evidence, rules, models)
   │
   ▼ JSON-RPC (web3.py)
Local Hardhat chain (chain ID 31337) → ClaimLedger.sol
```

**Off-chain components** are explainable and replaceable: extraction, reconciliation, findings, analytics, evidence files and the mirrored audit log.

**On-chain components** are authoritative for what the contract stores: unit ranges per namespace, the evidence hash, the report hash, a salted claimant commitment, claim status and the non-overlap invariant.

### 2.1 Repository map

| Path | Contents |
|---|---|
| `backend/app/` | FastAPI app (`main.py`), config, DB, claim service, serial parser, extraction, rules, chain adapter, normalization, reference loader |
| `backend/app/entity_resolution/` | Normalizer, intermediary extractor, blocking, matcher, engine (Phase 2A) |
| `backend/app/reconciliation/` | Interval algebra, allocation classification, engine (Phase 2B) |
| `backend/app/analytics/` | Stage 1–3 analytics, the `AnalyticsEngine` facade and `risk_assessment/` (Stage 4) |
| `backend/scripts/` | `build_reference.py`, `make_demo_docs.py`, `seed_demo.py`, `demo_fingerprint.py` |
| `backend/tests/` | 10 pytest modules, 245 tests |
| `contracts/` | `ClaimLedger.sol`, benchmark `ClaimLedgerLinear.sol`, Hardhat config, deploy script, 24 tests |
| `frontend/src/` | `App.tsx` routes, `pages/`, `components/`, `api/` (modular typed client), `lib/` |
| `frontend/qa/` | Playwright specs (`tests/`), screenshot capture, demo film recorder and validator |
| `eval/` | `run_eval.py`, `eval_entity_resolution.py`, `eval_reconciliation.py`, `e2e_smoke.py`, `results/` |
| `data/` | `reference/demo_subset.csv.gz` (real), `demo/` (synthetic statements), `benchmarks/` (curated JSON), `LICENSE` |
| `deploy/`, `Dockerfile`, `render.yaml` | Single-container demo. The Render blueprint is prepared but **not deployed** |
| `docs/` | Docs 00–16 (original design), `DATANOVA_*` phase reports, `design/`, `submission/`, assets |

### 2.2 Technology (VERIFIED from manifests)

| Layer | Technology |
|---|---|
| Backend | Python 3.12 (`.venv` has 3.12.13), FastAPI 0.115, Pydantic 2, web3 7, pypdf 5, rapidfuzz 3, pandas 2, openpyxl, reportlab, anthropic SDK (optional) |
| Contracts | Solidity 0.8.24 (optimizer 200 runs), Hardhat ^2.29, hardhat-toolbox ^6.1 |
| Frontend | React ^19.2, react-router-dom ^7.18, Vite ^8.3, Tailwind ^4.3, TypeScript ~6.0, oxlint, lucide-react. No charting library |
| QA | pytest 8, Hardhat/Mocha, Playwright ^1.64 with @axe-core/playwright |
| Runtime used this session | Node v26.4.0 |

`DATANOVA_PROJECT_COMPLETION_ROADMAP.md` states "React 18". That is incorrect: the project uses React 19.

---

## 3. Backend

### 3.1 Claim pipeline (original product)

`POST /api/claims` performs these steps:

1. Store the evidence content-addressed.
2. Compute SHA-256 digests. With multiple documents, `evidence_hash` = SHA-256 over the sorted concatenated digests (see `service.evidence_root`).
3. Extract serial blocks.
4. Run the rules.
5. Compute `report_hash`.
6. Set the status to `checked` or `blocked`.

`POST /api/claims/{id}/anchor` then runs the on-chain `checkRange` pre-flight, sends `registerClaim` and stores the receipt. A revert is decoded into a `chain_rejected` event.

Claim statuses are `checked | blocked | anchored | challenged | revoked | withdrawn`. Only `anchored` and `challenged` claims lock units (`db.LOCKING`).

Claim-level rule IDs live in `backend/app/rules.py`:

| Family | IDs |
|---|---|
| EVD | `EVD-001` |
| SER | `SER-002` |
| REG | `REG-000` to `REG-004` |
| BEN | `BEN-000` to `BEN-002` |
| DUP | `DUP-001`, `DUP-002` |
| AGG | `AGG-001` |
| EXT | `EXT-000` to `EXT-002` |

Phases 2A and 2B *enriched* the evidence on `BEN-*` and `DUP-001` but preserved the IDs, severities and messages. This is what keeps the demo fingerprint stable.

### 3.2 DATANOVA analytical modules

| Module | Purpose | Key methodology doc |
|---|---|---|
| `entity_resolution/` (2A) | Non-destructive legal-name normalization, intermediary parsing ("on behalf of", "c/o", pooled accounts), blocking, multi-feature explainable matching. Tiers and relationship types include `CORPORATE_HIERARCHY_OR_SUBSIDIARY` and `INTERMEDIARY_DELEGATION` | [`DATANOVA_ENTITY_RESOLUTION_METHODOLOGY.md`](DATANOVA_ENTITY_RESOLUTION_METHODOLOGY.md) |
| `reconciliation/` (2B) | Closed inclusive interval algebra (`Q = e − s + 1`). Six geometric classes (`EXACT_OVERLAP`, `CONTAINMENT`, `SUPERSET`, `PARTIAL_OVERLAP`, `ADJACENT`, `DISJOINT`) and eight semantic allocation classes (`LEGITIMATE_SPLIT`, `ALLOCATION_CONFLICT`, `INTERMEDIARY_ATTRIBUTION`, `UNRESOLVED_BENEFICIARY`, `CROSS_NAMESPACE`, `SAME_UNITS_SAME_CLAIMANT`, `SAME_UNITS_RELATED_CLAIMANTS`, `DIFFERENT_UNITS_SAME_CLAIMANT`) | [`DATANOVA_ALLOCATION_RECONCILIATION_METHODOLOGY.md`](DATANOVA_ALLOCATION_RECONCILIATION_METHODOLOGY.md) |
| `analytics/concentration.py`, `fragmentation.py` (Stage 1) | Dual-track disclosure coverage, HHI and Shannon entropy over **disclosed** volume, descriptive concentration bands, within-batch and pooled Gini, absolute micro-claims (≤ 10 t) kept separate from relative small allocations (≤ 1 % of the batch), interval sweep | [`DATANOVA_PHASE_2C_STAGE_1_METHODOLOGY.md`](DATANOVA_PHASE_2C_STAGE_1_METHODOLOGY.md), [`DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md`](DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md) |
| `analytics/temporal.py` (Stage 2) | Continuous calendar aggregation, rolling velocity trends, leave-one-out MAD burst detection (k = 3.0), zero-activity interval detection (described as *observed* zero activity, not proven dormancy) | [`DATANOVA_PHASE_2C_STAGE_2_FINAL_CORRECTIONS_REPORT.md`](DATANOVA_PHASE_2C_STAGE_2_FINAL_CORRECTIONS_REPORT.md) |
| `analytics/cross_registry.py` (Stage 3) | Project correlation (40/30/30 composite), `CROSS_REGISTRY_IDENTIFIER_COLLISION` for identical IDs across registries, entity linkage, comparative retirement dynamics, `MetadataProvenance` | [`DATANOVA_PHASE_2C_STAGE_3_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2C_STAGE_3_IMPLEMENTATION_REPORT.md) |
| `analytics/risk_assessment/` (Stage 4) | Six scopes (`BATCH`, `PROJECT`, `CLAIM`, `ENTITY`, `CROSS_REGISTRY`, `AD_HOC`) and 16 deterministic rules (listed after this table). Dependency groups stop correlated signals from inflating priority. Statuses: `NO_MATERIAL_SIGNAL`, `REVIEW_RECOMMENDED`, `ELEVATED_REVIEW_PRIORITY`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`. Counterevidence is kept separate from contextual caveats | [`DATANOVA_EXPLAINABLE_ASSESSMENT_METHODOLOGY.md`](DATANOVA_EXPLAINABLE_ASSESSMENT_METHODOLOGY.md) |

The 16 Stage 4 rules are:

- `RULE-REC-001` to `RULE-REC-004`
- `RULE-ENT-001`, `RULE-ENT-002`
- `RULE-CON-001` to `RULE-CON-003`
- `RULE-FRG-001`, `RULE-FRG-002`
- `RULE-TMP-001`, `RULE-TMP-002`
- `RULE-XREG-001` to `RULE-XREG-003`

### 3.3 API endpoints (VERIFIED from `backend/app/main.py`)

**Core / original product**

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | Reference, chain (`public_network` = chain ID ≠ 31337), LLM and public-demo status |
| GET | `/api/overview`, `/api/claims`, `/api/claims/{id}` | Read models |
| POST | `/api/claims` | Multipart intake. In public-demo mode it is rate-limited and capped |
| POST | `/api/claims/{id}/recheck` | |
| POST | `/api/claims/{id}/anchor`, `/challenge`, `/resolve`, `/withdraw` | Ledger writes. These return **403 in public-demo mode** |
| POST | `/api/verify` | Form fields: `ref` or `chain_claim_id`, optional `file`, `claimant` + `salt` |
| GET | `/api/claims/{id}/report.json`, `/report.html` | Integrity report |
| GET | `/api/evidence/{sha256}` | Which claims cite this document |
| GET | `/api/reference/lookup?serial=`, `/api/reference/samples` | Registry reference |
| GET | `/api/rules`, `/api/eval`, `/api/samples`, `/api/samples/{name}` | Rule list, eval result files, demo statements |

**DATANOVA**

| Phase | Endpoints |
|---|---|
| 2A | `POST /api/resolve/entity-pair`, `POST /api/resolve/intermediary` |
| 2B | `POST /api/reconcile/compare`, `POST /api/reconcile/batch`, `GET /api/claims/{id}/reconciliation` |
| Stage 1 | `GET /api/analytics/population/summary`, `GET /api/analytics/batches/{registry}/{batch_id}`, `POST /api/analytics/concentration`, `POST /api/analytics/fragmentation`, `POST /api/analytics/batch` |
| Stage 2 | `GET /api/analytics/temporal/activity`, `/trends`, `/bursts`, `/gaps` |
| Stage 3 | `POST /api/cross-registry/projects/compare`, `GET /api/cross-registry/projects/correlations`, `POST /api/cross-registry/entities/compare`, `GET /api/cross-registry/retirements/summary`, `GET /api/cross-registry/retirements/trends` |
| Stage 4 | `POST /api/analytics/assessment`, `GET /api/analytics/assessment/rules` |

When `ONCEONLY_STATIC_DIR` is set, the API also serves the built SPA (a catch-all route for non-`/api` paths).

### 3.4 Configuration (names only; never copy values)

The variables in `.env.example` are:

- `CHAIN_RPC_URL`
- `CHAIN_DEPLOYMENT`
- `REGISTRAR_PRIVATE_KEY`
- `REVIEWER_PRIVATE_KEY`
- `CHALLENGER_PRIVATE_KEY`
- `ANTHROPIC_API_KEY`
- `ONCEONLY_LLM_MODEL`
- `ONCEONLY_LLM`
- `ONCEONLY_REFERENCE_MODE` (`auto | full | demo`)
- `ONCEONLY_DB`

`backend/app/config.py` reads these additional variables:

- `ONCEONLY_EVIDENCE_DIR`
- `ONCEONLY_REFERENCE_DB`
- `ONCEONLY_REFERENCE_DEMO_DB`
- `ONCEONLY_MAX_UPLOAD_BYTES`
- `ONCEONLY_PUBLIC_DEMO`
- `ONCEONLY_PUBLIC_MAX_CLAIMS`
- `ONCEONLY_PUBLIC_RATE`
- `ONCEONLY_STATIC_DIR`
- `ONCEONLY_CORS_ORIGINS`

`ONCEONLY_MOCK_LLM` is used by the evaluation's offline mock fixture.

`config.py` loads the repo-root `.env` with `setdefault`, so real environment variables win. **`.env` exists locally and is gitignored. Do not read or print it.**

---

## 4. Smart contract

`contracts/contracts/ClaimLedger.sol` (Solidity 0.8.24):

- Active ranges are stored per namespace `keccak("REGISTRY:BATCH")` as a sorted doubly linked list. The caller supplies a predecessor hint (`hintFor`), so the overlap check is O(1). A bad hint reverts with `BadHint`; it never skips the check.
- Custom errors: `RangeOverlap(ns, existingClaimId, overlapStart, overlapEnd)`, `ClaimRefExists`, `InvalidRange`, `EmptyRanges`, `UnknownClaim`, `BadStatus`, `NotOwner`, `NotRegistrar`, `NotReviewer`.
- Roles: owner, registrar(s) and reviewer(s). Anyone may `openChallenge`. A reviewer resolves a challenge (upheld releases the units). `withdrawClaim` is also available.
- Storage: ranges, evidence hash, report hash, salted claimant commitment and status. **No claimant names and no documents.**
- `ClaimLedgerLinear.sol` is a linear-scan v0 kept only for the gas benchmark.

### 4.1 Deployment status

| Item | Status |
|---|---|
| Local Hardhat chain (ID 31337) via `make chain` and `make deploy` | Implemented. `contracts/deployments/localhost.json` is written locally and gitignored |
| Public testnet | **Not deployed.** `hardhat.config.js` defines an optional `testnet` network only if `RPC_URL` and `DEPLOYER_PRIVATE_KEY` are set. No deployment record exists |
| Mainnet | Not planned |

### 4.2 Trust boundaries (VERIFIED in code)

- The backend holds the registrar key and is a **trusted operator**. Claimants do not sign anything (EIP-712 signatures are PLANNED in [`docs/16_task_backlog.md`](16_task_backlog.md)). There is no authentication and no multi-tenancy.
- On-chain verification proves that a range record, hashes and status exist **on that chain at that address**. On a local Hardhat chain this proves nothing to third parties who do not run that chain.
- `/api/verify` document matching: `matches_onchain_commitment = match_root OR match_member`.
  - `match_root` compares the uploaded file's SHA-256 with the on-chain `evidence_hash`. This is a true on-chain comparison only for **single-document** claims.
  - `match_member` checks the digest against the **off-chain SQLite `evidence` table**. For multi-document claims, a positive result therefore relies on the operator's database, not on the chain alone (Merkle-style per-document commitments are PLANNED).
- A matching SHA-256 shows a file is unchanged since registration. It does not show the contents are true.
- The SQLite `events` table mirrors the chain for display. On-chain events are authoritative.
- The Hardhat development keys are publicly known. `DATANOVA_PHASE_0_REPORT.md` says they are "verified to operate exclusively when chainId == 31337". **No such guard exists in code.** `chain.py` only checks that the RPC chain ID matches the deployment file and marks `public_network`. Never put real or funded keys in `.env`.

---

## 5. Frontend

### 5.1 Routes (VERIFIED from `frontend/src/App.tsx`)

| Route | Page | Origin | Status |
|---|---|---|---|
| `/` | `Landing.tsx` | Original | REPORTED |
| `/overview` | `Overview.tsx` | Original | REPORTED |
| `/claims`, `/claims/new`, `/claims/:id` | `Claims.tsx`, `NewClaim.tsx`, `ClaimPage.tsx` | Original. Claim detail gained Assessment and Reconciliation tabs in Sprint 3.2 | REPORTED |
| `/cross-registry` | `CrossRegistry.tsx` | Sprint 3.3 | REPORTED |
| `/observatory` | `Observatory.tsx` | Sprint 3.4 | REPORTED, metrics under audit (§9.1) |
| `/assessment` | `AssessmentConsole.tsx` | Sprint 3.2 | REPORTED, preset-label defect (§9.4) |
| `/verify` | `Verify.tsx` | Original (last changed 2026-10-19) | Implemented for the original product; Sprint 3.5 target |
| `/evidence` | `Evidence.tsx` | Original (last changed 2026-10-19) | Implemented; contains stale copy (§9.5); Sprint 3.5 target |
| `/evaluation` | Redirects to `/evidence` | | |

The navigation (`Shell.tsx` `APP_NAV`) has seven items: Overview, Claims, Cross-Registry, Observatory, Assessment, Verify, Evidence.

### 5.2 Structure

- `frontend/src/api/` holds the modular typed client: `client.ts`, `claims.ts`, `assessment.ts`, `crossRegistry.ts`, `temporal.ts`, `analytics.ts` and `index.ts`. `src/api.ts` is a backward-compatible re-export.
- Charts are bespoke SVG/CSS components with no charting dependency (an approved Sprint 3.1 decision): `Ruler.tsx`, `LorenzCurveChart.tsx`, `TemporalActivityChart.tsx`, `ComparativePacingChart.tsx` and `ContourField.tsx`.
- The design system is the "Survey sheet" (see [`docs/design/06_design_system.md`](design/06_design_system.md)). Tailwind 4 tokens are defined in `src/index.css`.
- Frontend sprint principle: the UI shows backend-computed values and does not fabricate metrics. There is one known violation, a hard-coded fallback (§9.2).

---

## 6. Data and provenance

### 6.1 Sources

| Dataset | Path | Nature | Counts (REPORTED, Phase 1.1 audit) |
|---|---|---|---|
| Berkeley Carbon Trading Project, *Voluntary Registry Offsets Database* v2026-08 | Downloaded by `make data` to `data/raw/` (gitignored), built into `data/reference/registry_full.sqlite` (gitignored) | **Real** | 493,518 source rows: 307,416 VCS retirements, 166,478 GS retirements, 19,624 VCS issuances |
| Demo subset | `data/reference/demo_subset.csv.gz` (tracked), materialized into `var/registry_demo.sqlite` | **Real** subset | 38,004 rows: 30,111 VCS retirements, 7,224 GS retirements, 669 VCS issuances, across 22 projects (16 VCS, 6 GS) |
| Analytics population (Stage 1/2) | `var/registry_demo.sqlite`, `kind='retirement'` | Real subset | 37,335 retirements, 87,668,330 t, 725 batches, data range 2010-10-25 to 2026-09-01 |
| Demo claim statements | `data/demo/` (5 files + `manifest.json`) | **Synthetic** claimants (Northwind, Helios, Arbor, Lumen, Kestrel) citing real ranges | |
| Entity resolution benchmark | `data/benchmarks/entity_resolution_benchmark.json` | Curated | 124 cases |
| Reconciliation benchmark | `data/benchmarks/reconciliation_benchmark.json` | Curated | 36 cases (16 dev, 9 validation, 11 "internal reserved" split) |
| Double-use and extraction evaluation | Generated by `eval/run_eval.py` | Synthetic pairs and snippets on real ranges | 270 pairs and 60 snippets; 16 adversarial extraction tests |

### 6.2 Licensing

- Code: MIT (`LICENSE`).
- `data/` is **not** covered by MIT. Berkeley releases VROD under CC BY 4.0. Verra and Gold Standard redistribution rights for the committed rows **could not be verified**; see [`data/LICENSE`](../data/LICENSE). The rows are included for demonstration and evaluation only and will be removed on a rights holder's request.

### 6.3 Data limitations

- Snapshot through 2026-08-31. Later retirements show as "not found".
- **All analytics run on the 22-project demo subset, not the full registry.** Population metrics describe this sample, not the market.
- Most retirements in the subset have no disclosed beneficiary: 62.66 % of records are explicitly undisclosed. Undisclosed beneficiaries are a disclosure-coverage fact, not evidence of misconduct.
- Mojibake repair affected 6,955 records (7,411 field operations). Ambiguous day/month dates are tagged in provenance and never silently assumed.
- Ignoring the batch creates 159,511 spurious cross-batch overlaps in the full data: 11,631 VCS plus 147,880 GS. The README's 11,631 is the **Verra-only** figure. Within a namespace there are 0 overlaps in Verra and 5 in GS (REPORTED, [`DATANOVA_DATA_QUALITY.md`](DATANOVA_DATA_QUALITY.md)).

---

## 7. Milestone history

### 7.1 Git history (VERIFIED)

- `6a61655` is the original-product baseline and the current tip of `main` and `origin/main`.
- **All DATANOVA backend work (Phases 0 to 2C Stage 4) was developed uncommitted and landed in a single commit, `2997c44`** (2026-11-10 00:46 +0530).
- The phase audits cite HEAD `6a61655` with an uncommitted working tree. **The code state at each individual phase cannot be reconstructed from Git.**

| Commit | Content |
|---|---|
| `2997c44` | Analytics and explainable assessment foundation (Phases 0 to 2C Stage 4 and their reports) |
| `b9c091f` | Sprint 3.2: navigation, typed API layer, assessment console |
| `d52e78a` | Sprint 3.3: cross-registry workspace |
| `bf08180` | Sprint 3.4: market observatory (frontend files and the report only; **no backend files changed**) |

`datanova/phase-0-baseline` is 4 commits ahead of `main` and in sync with its remote-tracking branch as of the last fetch. This handover did not fetch.

### 7.2 Backend phases and acceptance evidence

| Phase | Primary report | Acceptance evidence in repo | Tests at the time (REPORTED) |
|---|---|---|---|
| 0: baseline | [`DATANOVA_PHASE_0_REPORT.md`](DATANOVA_PHASE_0_REPORT.md) | Self-reported; no separate audit | 24 backend + 24 contract |
| 1: ingestion and normalization | [`DATANOVA_PHASE_1_REPORT.md`](DATANOVA_PHASE_1_REPORT.md) | [`DATANOVA_PHASE_1_1_ACCEPTANCE_AUDIT.md`](DATANOVA_PHASE_1_1_ACCEPTANCE_AUDIT.md): **ACCEPTED** after hardening | 60 backend |
| 2A: entity resolution | [`DATANOVA_PHASE_2A_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2A_IMPLEMENTATION_REPORT.md) | **No standalone acceptance audit found.** Evaluation: [`DATANOVA_ENTITY_RESOLUTION_EVALUATION.md`](DATANOVA_ENTITY_RESOLUTION_EVALUATION.md) | 79 backend |
| 2B: reconciliation | [`DATANOVA_PHASE_2B_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2B_IMPLEMENTATION_REPORT.md) | 2B.1 audit: CONDITIONALLY ACCEPTED. [2B.2 corrections](DATANOVA_PHASE_2B_2_CORRECTIONS_REPORT.md): "COMPLETED, VERIFIED & FROZEN". [2B.3 integrity report](DATANOVA_PHASE_2B_3_FINAL_INTEGRITY_REPORT.md) | 130 backend |
| 2C Stage 1: concentration and fragmentation | [`DATANOVA_PHASE_2C_STAGE_1_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2C_STAGE_1_IMPLEMENTATION_REPORT.md) | Acceptance audit (CONDITIONALLY ACCEPTABLE), then corrections, then [**final acceptance audit: ACCEPTED**](DATANOVA_PHASE_2C_STAGE_1_FINAL_ACCEPTANCE_AUDIT.md) | 169 backend |
| 2C Stage 2: temporal | [`DATANOVA_PHASE_2C_STAGE_2_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2C_STAGE_2_IMPLEMENTATION_REPORT.md) | Acceptance audit (ACCEPTED), then final audit (ACCEPTED WITH MINOR CORRECTIONS), then the [corrections report](DATANOVA_PHASE_2C_STAGE_2_FINAL_CORRECTIONS_REPORT.md), which **self-declares** the freeze. No independent re-audit document follows it | 188 backend |
| 2C Stage 3: cross-registry | [`DATANOVA_PHASE_2C_STAGE_3_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2C_STAGE_3_IMPLEMENTATION_REPORT.md) | The report resolves 4 findings from a targeted audit (that audit document is not in the repo). Its status is "Ready for Final Independent Verification". **No final acceptance audit document exists** | 229 backend |
| 2C Stage 4: assessment | [`DATANOVA_PHASE_2C_STAGE_4_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2C_STAGE_4_IMPLEMENTATION_REPORT.md) | [**Final acceptance audit: ACCEPTED, STAGE 4 FROZEN**](DATANOVA_PHASE_2C_STAGE_4_FINAL_ACCEPTANCE_AUDIT.md) | 245 backend |

The project owner treats all of these phases as **accepted and frozen**. The gaps in the "Acceptance evidence" column are documentation gaps; they are not evidence of defects. Do not reopen a frozen phase without a concrete, reproducible defect and explicit approval.

### 7.3 Frontend sprints

| Sprint | Report | Status |
|---|---|---|
| 3.1: architecture audit | [`DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md`](DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md) | Approved three decisions: bespoke SVG charts, 7-item navigation, modular `src/api/` |
| 3.2: navigation, API layer, assessment console | [`…SPRINT_3_2_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_3_SPRINT_3_2_IMPLEMENTATION_REPORT.md) | REPORTED: lint, build, 245 backend, 24 contract |
| 3.3: cross-registry workspace | [`…SPRINT_3_3_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_3_SPRINT_3_3_IMPLEMENTATION_REPORT.md) | REPORTED: same gates |
| 3.4: observatory | [`…SPRINT_3_4_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_3_SPRINT_3_4_IMPLEMENTATION_REPORT.md) | REPORTED: same gates. **Metrics discrepancy open** (§9.1) |

Sprints 3.2 to 3.4 added Playwright specs to `frontend/qa/tests/ui.spec.ts`. **None of these reports records a Playwright run result.** The browser tests for the new routes are therefore implemented but not verified.

### 7.4 Original product (HISTORICAL context)

Before DATANOVA, OnceOnly was built for the IEEE ClimateChain hackathon (October 2026). [`docs/00_mission_status.md`](00_mission_status.md), docs 01–16, [`docs/design/`](design/) and [`docs/submission/`](submission/) describe that product and submission. They remain accurate for the claim-ledger core but **predate the DATANOVA analytics**: test counts, extraction figures, scope and deadlines are outdated.

---

## 8. Testing and setup

### 8.1 Verification results in this handover (2026-11-10)

| Command | Result |
|---|---|
| `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings` | **245 passed** in 7.29 s |
| `cd contracts && HARDHAT_DISABLE_TELEMETRY_PROMPT=true npx hardhat test` | **24 passing**. Gas: hinted 333,078 at 0 existing ranges, then flat 301,452. Linear v0 reaches 832,608 at 200 |
| `cd frontend && npm run lint` (oxlint) | Exit 0, no diagnostics |
| `cd frontend && npm run build` | Success; for example `Observatory` 51.63 kB and `index` 350.54 kB |
| `make e2e`, `make demo-check`, `npx playwright test`, `make eval` | **Not run.** They need a live chain, API and seeded state, or they overwrite tracked result files |
| `git status --short` after the tests, before writing the handover files | Clean. The test and build runs left no tracked changes |

Backend tests per module:

| Module | Tests |
|---|---|
| analytics | 58 |
| reconciliation | 51 |
| cross_registry | 41 |
| entity_resolution | 19 |
| service | 16 |
| risk_assessment | 16 |
| adversarial_extraction | 15 |
| serials | 13 |
| normalization | 9 |
| reference | 7 |

Some modules use parametrization, so these function counts may not equal collected tests.

### 8.2 Setup and run

These are verified from the `Makefile`. `make setup` installs dependencies, so run it only when appropriate.

```bash
make setup                # .venv + pip install, npm install (contracts, frontend), copy .env.example → .env if absent, compile
make chain                # terminal 1: Hardhat node on 127.0.0.1:8545
make deploy && make api   # terminal 2: deploy ClaimLedger, then FastAPI on 127.0.0.1:8000
make web                  # terminal 3: Vite on 127.0.0.1:5173 (proxies /api → :8000)
make seed                 # load the five-claim demo story through the API
make demo-check           # print the state fingerprint
```

Reported canonical fingerprint: `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`.

| Command | Effect | Caution |
|---|---|---|
| `make test` | Contract and backend tests | Safe |
| `make reset` | **Deletes** `var/onceonly.sqlite` and `var/evidence/`, then redeploys | Destructive to local runtime state; restart `make api` afterwards |
| `make eval` | Writes `eval/results/latest.{json,md}` | **Overwrites tracked files** |
| `make gas` | Writes `eval/results/gas.json` | **Overwrites a tracked file** |
| `make e2e` | 13-step lifecycle against the live stack | Needs a fresh ledger: `make reset`, API restart, no seed |
| `cd frontend && npx playwright test` | Browser and a11y tests | Needs the live seeded stack; uses installed Chrome |
| `make demo-validate`, `make demo-record` | Demo film replay and recording | Need a fresh ledger and `make web` |
| `make data` | Downloads about 67 MB from Berkeley, builds the full index | Network access |
| `make docker-build`, `make docker-run` | Single container on :7860, public-demo mode | |

`eval/eval_entity_resolution.py` and `eval/eval_reconciliation.py` have no Make target. Both write tracked files under `eval/results/`.

---

## 9. Known limitations, defects and unresolved discrepancies

> **Status update (2026-11-10, final completion mission).** Items 9.1–9.6 were resolved. Details are in [`FINAL_COMPLETION_EXECUTION_LOG.md`](FINAL_COMPLETION_EXECUTION_LOG.md) and [`FINAL_RELEASE_QA_REPORT.md`](FINAL_RELEASE_QA_REPORT.md). The verification trust boundary in §4.2 also changed: a database match no longer counts as an on-chain match, and multi-document membership is proven by recomputing the commitment. The original findings are kept below for traceability. §9.7 still applies.


### 9.1 RESOLVED: Stage 1 vs Sprint 3.4 population metrics (Stage 1 confirmed; see the [Sprint 3.4.1 audit](DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md))

| Metric | Frozen Stage 1 ([final audit §4](DATANOVA_PHASE_2C_STAGE_1_FINAL_ACCEPTANCE_AUDIT.md)) | Sprint 3.4 report |
|---|---|---|
| HHI (disclosed) | 245.6410 | 215.17 |
| Shannon entropy | 7.5166 bits | 9.37 bits |
| Equitability | 0.5661 | 0.706 |
| Telstra volume | 3,766,034 t | 3,767,118 t |
| Top-three share | 23.13 % | 23.13 % |
| Pooled Gini | 0.960471 | ≈ 0.9605 |
| Mean within-batch Gini | 0.492445 | ≈ 0.4924 |

Facts established by inspection only. The audit itself has not been performed:

- `bf08180` changed no backend files. `backend/app/analytics/` is unchanged since `2997c44`.
- The Observatory renders `conc.hhi_disclosed` rounded to an integer, entropy to 2 decimals and equitability to 3 decimals, straight from `GET /api/analytics/population/summary`. The report's "215.17" does not match that display format.
- Both sets imply about 9,933 unique labels: log₂(9,933) ≈ 13.278, and 9.37 / 0.706 ≈ 13.27.
- No backend test pins the population-level HHI, entropy or equitability values.
- The Stage 1 figures were computed on uncommitted code that later changed during Stages 2 to 4 before the single commit. Git cannot show whether concentration code changed in between.

**Do not choose either set, change methodology, or edit the Sprint 3.4 report until Sprint 3.4.1 establishes the facts.** See [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md).

### 9.2 RESOLVED: Hard-coded metric fallback

`frontend/src/pages/Observatory.tsx:498` renders `pop.batch_gini_distribution.mean?.toFixed(4) ?? "0.4924"`. If the API omits the value, the UI shows a constant as if it were live data. This conflicts with the no-fabricated-metrics principle.

### 9.3 RESOLVED: Analytics DB path now follows `ONCEONLY_REFERENCE_DEMO_DB`; Docker verified

`backend/app/analytics/engine.py:51` fixes `DEFAULT_DB_PATH` to `<repo>/var/registry_demo.sqlite`. It ignores `ONCEONLY_REFERENCE_DEMO_DB` and `ONCEONLY_REFERENCE_MODE`.

- The `Dockerfile` sets `ONCEONLY_REFERENCE_DEMO_DB=/tmp/onceonly/registry_demo.sqlite`, so analytics endpoints may fail with `FileNotFoundError` inside the container.
- The demo DB appears to be materialized only on the demo or auto-fallback path in `reference.py`. A clone with `registry_full.sqlite` present may also lack the file.

This has **not been tested**. It must be verified in Phase 4.

### 9.4 RESOLVED: Assessment Console preset labels

`frontend/src/pages/AssessmentConsole.tsx` (around lines 227–237) labels claim 1 "Helios Claim #1" and claim 2 "Equinox Claim #2". In the seeded story (`backend/scripts/seed_demo.py`), claim 1 is **Northwind** and claim 2 is **Helios**. No "Equinox" claimant exists. The Sprint 3.2 report and the frontend audit repeat "Helios vs Equinox". The `RulesCatalogModal.tsx` placeholder and the frontend audit cite `RULE-INT-001`, which is not in the 16-rule catalog.

### 9.5 RESOLVED: Stale documentation and UI copy (README rewritten; Evidence page rewritten; historical docs labelled)

| Item | What is stale |
|---|---|
| `README.md` | Describes the original product only. It cites "24 backend tests", "65 % exact serial extraction" (now 100 % on the in-sample benchmark, and 16/16 adversarial cases), a project structure without the analytics modules, and no Observatory, Cross-Registry or Assessment routes |
| [`docs/00_mission_status.md`](00_mission_status.md) | Calls itself the "single source of truth" but is dated 2026-10-19 (IEEE era). This file supersedes it for current status |
| `frontend/src/pages/Evidence.tsx` | Static copy says the parser "fails on tables, prose ranges and OCR errors" and labels the page "AI not measured". The headline value is computed from `eval/results/latest.json`, which now reports parser `doc_exact = 1.0`, so the copy contradicts the number next to it |
| `eval/results/latest.md` | The contract column shows "skipped (no local chain)". The README's contract precision and recall of 1.000 come from earlier runs |
| [`DATANOVA_PROJECT_COMPLETION_ROADMAP.md`](DATANOVA_PROJECT_COMPLETION_ROADMAP.md) | Says React 18. Lists `/projects` and `/batches` routes and dashboard KPIs (for example 2,841 entities) that do not exist in the code. Sprint 3.1 was listed as "current" |
| [`DATANOVA_UPGRADE_ROADMAP.md`](DATANOVA_UPGRADE_ROADMAP.md) | Strategy doc with promotional language ("unbeatable"). It proposes items, such as `docs/DATANOVA_SUBMISSION.md`, a public-demo simulation mode and a `/market` page, that were not built |
| [`docs/submission/`](submission/) | IEEE ClimateChain submission package (official requirements, deadline 25 Oct 2026). Repo URLs were updated in Phase 0. **There is no DATANOVA-specific submission package or verified DATANOVA requirements document** |

### 9.6 RESOLVED: Conflicting definitions of Sprint 3.5 (the owner's definition was delivered)

| Source | Sprint 3.5 scope |
|---|---|
| Frontend audit §5 | E2E integration, accessibility and demo polish |
| Sprint 3.4 report and the current owner brief | Public Verification Portal (`/verify`) and Forensic Evidence Ledger (`/evidence`) |

**The owner's definition governs.** The audit's integration and accessibility items fold into Phase 4.

### 9.7 Other limitations

- Local chain only; no public testnet deployment. No authentication; a single trusted registrar key.
- Live AI extraction has never been measured. The 100 % extraction figures are **in-sample** on 8 templates. The "parser + AI" mock is an offline fixture that calls the parser, so it is circular by construction (Phase 1.1 audit).
- The 270-pair double-use benchmark is circular: ground truth uses the engine's interval definition. The entity resolution (124) and reconciliation (36) benchmarks are curated and internally constructed. **None of these measure real-world fraud-detection accuracy.**
- The Stage 2 zero-activity intervals reflect only the 22-project sample.
- `/api/verify` multi-document matching depends on the off-chain DB (§4.2).
- The DATANOVA deadline is unverified in the repo. `DATANOVA_UPGRADE_ROADMAP.md` states a "Submission Window: October 26 – November 10, 2026", which is today's date at handover. **The owner must confirm the actual deadline and requirements.**

---

## 10. Established engineering decisions (preserve these)

**Data and provenance**

- Keep raw source values next to normalized values, with provenance.
- Never silently impute missing data.
- Registry namespaces are isolated, and comparisons are keyed by `(registry, batch_id)`.
- Identical serial integers or project IDs across registries are never treated as the same asset (`CROSS_NAMESPACE`, `CROSS_REGISTRY_IDENTIFIER_COLLISION`).

**Identity**

- Similar names do not establish legal identity.
- A parent/subsidiary relationship does not establish identity; it maps to `SAME_UNITS_RELATED_CLAIMANTS`, a governance-review class.
- An intermediary and a principal are distinct roles.
- An undisclosed beneficiary yields `UNRESOLVED_BENEFICIARY` or `INSUFFICIENT_EVIDENCE`, never an accusation.

**Statistics**

- HHI and entropy are computed over disclosed volume only.
- Concentration bands are descriptive (antitrust labels were removed in Stage 1).
- Pooled Gini and mean within-batch Gini are reported separately.
- Absolute micro-claims are kept separate from relative small allocations.
- Burst detection uses leave-one-out MAD. Retirement denominators never include issuances.

**Assessment**

- Findings are deterministic rules with stated thresholds, counterevidence, caveats and missing information.
- Correlated signals are grouped so they cannot double-count.
- There are no opaque scores and no calibrated "fraud probability".

**Compatibility**

- Original rule IDs, severities and messages are preserved, and the demo fingerprint must stay stable.

**Frontend**

- Bespoke SVG charts with no charting library.
- Values come from the backend, never invented in the UI.
- Methodological caveats are shown next to the metrics.

**Process**

- Frozen phases are not modified without a reproducible defect and approval.
- Mathematical methods are not changed without approval.
- No commits or pushes without explicit approval.

---

## 11. Authoritative documentation index

| Topic | Authoritative document(s) |
|---|---|
| Current status and pending work | This file, [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md) |
| Agent rules | [`CLAUDE.md`](../CLAUDE.md), [`AGENTS.md`](../AGENTS.md) |
| Original product thesis and architecture | [`06_product_thesis.md`](06_product_thesis.md), [`10_system_architecture.md`](10_system_architecture.md), [`11_data_model.md`](11_data_model.md), [`12_ai_and_blockchain_design.md`](12_ai_and_blockchain_design.md), [`13_security_and_privacy.md`](13_security_and_privacy.md), [`14_evaluation_plan.md`](14_evaluation_plan.md) |
| Baseline and data | [`DATANOVA_BASELINE_AUDIT.md`](DATANOVA_BASELINE_AUDIT.md), [`DATANOVA_DATA_ASSESSMENT.md`](DATANOVA_DATA_ASSESSMENT.md), [`DATANOVA_DATA_QUALITY.md`](DATANOVA_DATA_QUALITY.md), [`DATANOVA_EXTRACTION_EVALUATION.md`](DATANOVA_EXTRACTION_EVALUATION.md) |
| Entity resolution | [`DATANOVA_ENTITY_RESOLUTION_METHODOLOGY.md`](DATANOVA_ENTITY_RESOLUTION_METHODOLOGY.md), [`…_EVALUATION.md`](DATANOVA_ENTITY_RESOLUTION_EVALUATION.md) |
| Reconciliation | [`DATANOVA_ALLOCATION_RECONCILIATION_METHODOLOGY.md`](DATANOVA_ALLOCATION_RECONCILIATION_METHODOLOGY.md), [`…_EVALUATION.md`](DATANOVA_ALLOCATION_RECONCILIATION_EVALUATION.md), [2B.2 corrections](DATANOVA_PHASE_2B_2_CORRECTIONS_REPORT.md) |
| Phase 2C mathematics | [`DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md`](DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md), [`…_STAGE_1_METHODOLOGY.md`](DATANOVA_PHASE_2C_STAGE_1_METHODOLOGY.md), [`…_STAGE_1_API.md`](DATANOVA_PHASE_2C_STAGE_1_API.md), [`…_RISK_REGISTER.md`](DATANOVA_PHASE_2C_RISK_REGISTER.md) |
| **Frozen Stage 1 reference metrics** | [`DATANOVA_PHASE_2C_STAGE_1_FINAL_ACCEPTANCE_AUDIT.md`](DATANOVA_PHASE_2C_STAGE_1_FINAL_ACCEPTANCE_AUDIT.md) §4 |
| Stage 2 (final state) | [`DATANOVA_PHASE_2C_STAGE_2_FINAL_CORRECTIONS_REPORT.md`](DATANOVA_PHASE_2C_STAGE_2_FINAL_CORRECTIONS_REPORT.md) |
| Stage 3 | [`DATANOVA_PHASE_2C_STAGE_3_IMPLEMENTATION_REPORT.md`](DATANOVA_PHASE_2C_STAGE_3_IMPLEMENTATION_REPORT.md) |
| Stage 4 | [`DATANOVA_EXPLAINABLE_ASSESSMENT_METHODOLOGY.md`](DATANOVA_EXPLAINABLE_ASSESSMENT_METHODOLOGY.md), [`…_STAGE_4_EVALUATION.md`](DATANOVA_PHASE_2C_STAGE_4_EVALUATION.md), [`…_STAGE_4_FINAL_ACCEPTANCE_AUDIT.md`](DATANOVA_PHASE_2C_STAGE_4_FINAL_ACCEPTANCE_AUDIT.md) |
| Frontend | [`DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md`](DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md), Sprint 3.2–3.4 reports, [`design/06_design_system.md`](design/06_design_system.md) |
| Deployment (prepared, not deployed) | [`submission/08_deployment_runbook.md`](submission/08_deployment_runbook.md) |
| Historical (do not treat as current) | [`00_mission_status.md`](00_mission_status.md), [`DATANOVA_TEST_RESULTS.md`](DATANOVA_TEST_RESULTS.md), [`DATANOVA_PROJECT_COMPLETION_ROADMAP.md`](DATANOVA_PROJECT_COMPLETION_ROADMAP.md), [`DATANOVA_UPGRADE_ROADMAP.md`](DATANOVA_UPGRADE_ROADMAP.md), [`submission/`](submission/), [`design/`](design/) |

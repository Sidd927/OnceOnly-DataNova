# OnceOnly: Development Roadmap (remaining work)

| | |
|---|---|
| Prepared | 2026-11-10, at HEAD `bf08180` on `datanova/phase-0-baseline` |
| Context | [`PROJECT_MASTER_CONTEXT.md`](PROJECT_MASTER_CONTEXT.md). Its section numbers (§) are referenced throughout |
| Supersedes for planning | [`DATANOVA_PROJECT_COMPLETION_ROADMAP.md`](DATANOVA_PROJECT_COMPLETION_ROADMAP.md) and §5 of [`DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md`](DATANOVA_PHASE_3_FRONTEND_ARCHITECTURE_AUDIT.md) |

This roadmap contains **no dates**. The DATANOVA submission deadline is not verified anywhere in the repository. [`DATANOVA_UPGRADE_ROADMAP.md`](DATANOVA_UPGRADE_ROADMAP.md) states a submission window ending 2026-11-10, but that is unconfirmed. **The owner must confirm the deadline before sequencing work.** If time is short, the Release Gates (§4) define the minimum shippable state.

Each milestone starts only after explicit owner approval. Each ends with a written report and **no commit until the owner approves**.

---

## Milestone order

```text
Sprint 3.4.1  Independent metrics reconciliation audit   (read-only first; blocks 3.5 sign-off)
     │
Sprint 3.5    Public Verification Portal (/verify) + Forensic Evidence Ledger (/evidence)
     │
Phase 4       End-to-end validation, demo scenarios, integration, setup/deploy docs, polish, submission
```

---

## Sprint 3.4.1: Independent metrics reconciliation audit

**Why.** The frozen Stage 1 population metrics and the Sprint 3.4 report disagree on HHI, entropy, equitability and the Telstra volume (master context §9.1). Until the audit establishes which figures the current code actually produces and why, the Observatory's headline numbers and the Sprint 3.4 report cannot be cited.

**Mode.** Read-only investigation first. Running backend functions against `var/registry_demo.sqlite` (opened read-only by `AnalyticsEngine`) and calling the live API are permitted. Changing code or docs is not, until the owner approves.

### Tasks

1. Record the environment:
   - Git HEAD and working-tree state
   - Reference mode
   - The SHA-256 and row counts of `var/registry_demo.sqlite` and of `data/reference/demo_subset.csv.gz`
2. Call `AnalyticsEngine.analyze_population_summary()` directly and `GET /api/analytics/population/summary` on a running API. Record the raw values with full precision for these fields:
   - `hhi_disclosed`
   - `hhi_normalized`
   - `entropy_shannon_disclosed`
   - `entropy_normalized`
   - `unique_disclosed_beneficiaries`
   - the dominant beneficiary label and its volume
   - `top3_disclosed_share`
   - `pooled_allocation_gini`
   - `batch_gini_distribution.mean`
3. Recompute independently from SQL in a scratch script outside the repo. The recomputation must follow the Stage 1 methodology:
   - disclosed-only denominators
   - the documented label normalization
   - the placeholder and undisclosed classification
   - `kind='retirement'` only
4. Compare three sources: the frozen Stage 1 figures, the current engine output, and the Sprint 3.4 report. For each difference, identify its cause from the evidence. Candidate causes, none presumed:
   - a label-normalization change made during Stages 2 to 4 before `2997c44`
   - a different input database
   - a share computed on a different denominator
   - figures in the report that did not come from the API at all
5. Check how the Observatory displays each value (rounding, fallbacks). Note the hard-coded `"0.4924"` fallback at `Observatory.tsx:498` (§9.2).
6. Write `docs/DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md` with:
   - the reproduction commands
   - the raw outputs
   - a root-cause statement
   - a recommendation

### Decision points (owner approval required)

| Finding | Possible remediation (not to be applied without approval) |
|---|---|
| The current engine reproduces the frozen Stage 1 figures | The Sprint 3.4 report is in error. Add a dated correction section or an erratum; do not silently overwrite it |
| The engine output differs from the frozen figures | Treat as a potential regression in a frozen phase. Present the evidence and the minimal fix options. **Do not change methodology unilaterally** |
| Neither figure set is reproducible | Escalate with full evidence |

### Acceptance criteria

- [ ] Every figure in the comparison table is traced to a command and its raw output.
- [ ] The root cause is stated with evidence, or explicitly marked unresolved.
- [ ] No backend code, frozen report or Sprint 3.4 report is modified during the audit.
- [ ] Recommendation: add a regression test pinning the population metrics (HHI, entropy, equitability, top-share, both Ginis) to the agreed values, once the owner approves those values.
- [ ] Recommendation: remove the hard-coded UI fallback in favour of an explicit "unavailable" state.
- [ ] `pytest` and the contract tests are re-run and their output reported.

---

## Sprint 3.5: Public Verification Portal and Forensic Evidence Ledger

**Starting point.** `/verify` (`Verify.tsx`, 147 lines) and `/evidence` (`Evidence.tsx`, 202 lines) already exist from the original product and were last changed on 2026-10-19. Sprint 3.5 **evolves** them; it does not create new routes. The backend endpoints already exist:

- `POST /api/verify`
- `GET /api/claims/{id}`
- `GET /api/claims/{id}/report.{json,html}`
- `GET /api/evidence/{sha256}`
- `GET /api/eval`
- `GET /api/analytics/assessment/rules`

**Avoid any backend change unless a concrete product requirement demands it and the owner approves.**

The scope below is a proposal derived from the existing code and the Sprint 3.4 report's one-line description. **Confirm it with the owner before implementation.**

### Proposed scope: `/verify` (Public Verification Portal)

- Verify by claim reference or on-chain ID. Show on-chain status, ranges, hashes, the chain ID and contract address.
- Upload a document to check it against the commitment. Show the claimant check (name + salt).
- State the trust boundary precisely in the UI:
  - Chain ID 31337 is a **local development chain**, not a public network.
  - For multi-document claims, a match comes from the off-chain evidence index, not from the on-chain root alone (master context §4.2).
  - A hash match proves the bytes are unchanged, not that the contents are true.
- Pre-loaded sample verification for the seeded claims, such as OO-2026-0001 (Northwind).
- Never imply public-chain or cryptographic guarantees beyond what the code provides.

### Proposed scope: `/evidence` (Forensic Evidence Ledger)

- Replace the stale static copy (§9.5) with text derived from the current result files:
  - Parser figures are **in-sample**.
  - The AI pass is **not measured**.
  - The mock fixture is circular.
  - The contract column may be skipped in the committed results.
- Add the DATANOVA evaluations (entity resolution and reconciliation results in `eval/results/`, plus the Stage 4 evaluation) with their caveats (curated or internal benchmarks, not real-world accuracy).
- Consider an evidence and audit-trail view per claim (documents, SHA-256, findings, on-chain and off-chain events). The data already exists in `GET /api/claims/{id}`.

### Defects to fix in the same sprint (if approved)

- Assessment Console preset labels: "Helios Claim #1" and "Equinox Claim #2" should be Northwind #1 and Helios #2 (§9.4). Fix the `RULE-INT-001` placeholder example.
- The `Observatory.tsx:498` hard-coded fallback, if not already handled by 3.4.1.

### Acceptance criteria

- [ ] Every displayed value comes from an API response or a committed result file. There are no literals posing as data.
- [ ] The trust-boundary copy on `/verify` matches the master context §4.2, and the owner has reviewed it.
- [ ] `/evidence` states sample sizes, the in-sample/circular nature of the benchmarks, and what is not measured.
- [ ] Verification works for: a single-document claim (match and tamper), a multi-document claim, an unknown reference, and the chain being unavailable (503 path).
- [ ] `npm run lint` and `npm run build` pass, and output is reported.
- [ ] Backend `pytest` (245, or more if tests are added) and the contract tests (24) pass, and output is reported.
- [ ] Playwright specs for `/verify` and `/evidence` are updated **and run** against a live seeded stack, with results reported. If they cannot be run, say so explicitly.
- [ ] Implementation report: `docs/DATANOVA_PHASE_3_SPRINT_3_5_IMPLEMENTATION_REPORT.md`.

---

## Phase 4: End-to-end validation and release

### 4.1 Integration verification

- [ ] Fresh-clone setup on a clean directory: `make setup`, then `make test`, `npm run lint` and `npm run build`. Record versions (Python, Node, npm).
- [ ] Live stack: run `make chain`, `make deploy`, `make api`, `make web`. Then:
  - Run `make reset`, restart the API, and run `make e2e` (13/13 expected).
  - Run `make seed` and `make demo-check`. The fingerprint is expected to be `c544f589…6483b`; report any drift and do not "fix" it silently.
- [ ] `cd frontend && npx playwright test` on the seeded stack. Report the pass/fail count. This is the **first recorded run** of the Sprint 3.2–3.4 specs.
- [ ] `make demo-validate` on a fresh ledger.
- [ ] Every frontend route against the live API, with no console errors: `/overview`, `/claims`, `/claims/:id` tabs, `/cross-registry`, `/observatory`, `/assessment`, `/verify`, `/evidence`.
- [ ] **Analytics DB path (§9.3).** Verify the analytics endpoints in:
  - (a) a fresh clone in demo mode
  - (b) a clone with `registry_full.sqlite` present
  - (c) the Docker image (`make docker-build && make docker-run`, then hit `/api/analytics/population/summary`)

  If any case fails, propose a minimal fix for approval.
- [ ] Public-demo mode: writes return 403; claim checks are rate-limited and capped.

### 4.2 Reproducible demo scenarios

Define each scenario as a script plus its expected outputs, captured from real runs and not invented:

1. **Double use blocked.** Northwind anchored; Helios overlaps 4,559 units; the contract reverts with `RangeOverlap`.
2. **Cross-registry triangulation.** A VCS/GS project pair with the identifier-collision disclaimer, using a pair actually present in the data.
3. **Market observatory.** Population census, concentration (with the 3.4.1-approved figures), a batch fragmentation preset and temporal bursts.
4. **Explainable assessment.** CLAIM and PROJECT scopes, showing the dependency grouping, counterevidence and missing information.
5. **Verification.** Document match and tamper on `/verify`.

### 4.3 Documentation

- [ ] Update `README.md` for DATANOVA scope (analytics, new routes, current test counts, extraction caveats) without overstating anything. Keep the trust-boundary and limitation sections.
- [ ] Mark [`docs/00_mission_status.md`](00_mission_status.md) as historical, or point it to the master context.
- [ ] Setup, run, test and deployment instructions that match the verified commands.
- [ ] Architecture diagram that includes the analytics layer.

### 4.4 Submission package

- [ ] Obtain and record the **official DATANOVA requirements** (deadline, track, required fields, video length, repo visibility) in a new doc analogous to [`submission/00_official_requirements.md`](submission/00_official_requirements.md). Do not reuse the IEEE requirements.
- [ ] DATANOVA submission text, demo script and judge Q&A. Reuse `docs/submission/` structure but not its IEEE claims.
- [ ] Demo video recorded from the validated scenarios.
- [ ] Repository visibility, licence and data-rights notice confirmed by the owner.
- [ ] Optional, only with owner approval: Render deployment (`render.yaml`, `autoDeploy: false`) and public testnet deployment (needs an owner-provided **test-only** key).

---

## Testing and release gates

A milestone is complete only when all applicable gates pass **and the output was actually observed**. Report a gate that was skipped as skipped.

| Gate | Command | Required for |
|---|---|---|
| G1 Backend tests | `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings` | Every milestone |
| G2 Contract tests | `make test-contracts` | Every milestone |
| G3 Frontend lint and build | `cd frontend && npm run lint && npm run build` | Any frontend change |
| G4 Working-tree hygiene | `git status --short` shows only intended files. No changes to frozen modules, `.env`, data or `eval/results/` unless approved | Every milestone |
| G5 E2E lifecycle | `make e2e` on a fresh ledger | Phase 4; any change to claims, chain or service |
| G6 Demo determinism | `make reset`, API restart, `make seed`, `make demo-check` | Phase 4; any change touching rules or the claim pipeline |
| G7 Browser tests | `cd frontend && npx playwright test` (seeded stack) | Sprint 3.5 and Phase 4 |
| G8 Container | `make docker-build && make docker-run`, then health and analytics endpoints respond | Phase 4 |
| G9 Claims audit | Every number in new docs or UI traces to a command output or result file; no fraud or accuracy overclaims | Every report |

---

## Submission readiness checklist

- [ ] Sprint 3.4.1 resolved; the Observatory figures and reports are consistent
- [ ] Sprint 3.5 complete and reported
- [ ] G1–G9 passed and recorded in a Phase 4 validation report
- [ ] README and status docs reflect the DATANOVA scope; historical docs labelled
- [ ] DATANOVA requirements and deadline verified from official sources and recorded
- [ ] Demo scenarios scripted, reproducible and recorded
- [ ] Trust boundaries stated consistently in the README, UI and submission text (local chain, trusted registrar, off-chain multi-document matching, synthetic claimants)
- [ ] Benchmark caveats stated wherever metrics appear (in-sample, circular or curated; not real-world accuracy)
- [ ] Data licensing notice intact (`data/LICENSE`)
- [ ] No secrets in the repo (`git grep` for key patterns; `.env` untracked)
- [ ] Owner-approved commit(s) and push; repository visibility set by the owner

# AGENTS.md: Shared instructions for coding agents

These rules apply to any AI coding agent working in this repository. Project context is in [`docs/PROJECT_MASTER_CONTEXT.md`](docs/PROJECT_MASTER_CONTEXT.md). Remaining work is in [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md).

## 1. Git and workspace safety

- Work only in this repository (`OnceOnly-DataNova`). Never touch the neighbouring `../ClimateChain` repository or the original IEEE OnceOnly repository.
- Verify the branch, remote and HEAD before starting (`git branch --show-current`, `git remote -v`, `git log --oneline -5`, `git status --short`). Do not assume they match earlier notes.
- **Never:** `git reset --hard`, force push, `git checkout -- <path>` or `git restore` over uncommitted work, `git clean`, history rewriting, or `git add .` / `git add -A`. Stage explicit paths only.
- **Do not commit or push without explicit owner approval** for that specific change.
- Do not install, upgrade or remove dependencies, or edit lockfiles, without approval.
- Some commands modify tracked files or local state. Run them only when the task requires it, and say so:
  - `make eval`, `make gas` and `eval/eval_*.py` overwrite files in `eval/results/`.
  - `make reset` deletes `var/onceonly.sqlite` and `var/evidence/`.
  - `make setup` installs packages.
  - `make data` downloads about 67 MB.

## 2. Secrets and data

- **Never read, print, copy or modify `.env`.** Refer to configuration by variable *name* only (see `.env.example`).
- Never place real or funded private keys anywhere. The Hardhat keys in `.env.example` and the `Dockerfile` are public development keys. No code guard restricts them to chain 31337.
- Do not modify `data/` (reference subset, demo documents, benchmarks), `var/*.sqlite`, or `data/LICENSE` without approval. Benchmarks must not be edited to improve scores.
- Registry rows are real (Berkeley VROD 2026-08, CC BY 4.0, registry redistribution rights unverified). Claimants and statements are synthetic and must stay labelled as synthetic.

## 3. Architecture boundaries

| Area | Rule |
|---|---|
| Frozen backend phases: `entity_resolution/`, `reconciliation/`, `analytics/` (Stages 1–4), and the claim pipeline's rule IDs, severities and messages | Modify only for a concrete, reproducible defect that blocks work, and only with owner approval. Methodology and threshold changes always need approval |
| `backend/app/main.py` API | Additive changes only. Keep existing request and response shapes backward compatible |
| `contracts/` | Do not change `ClaimLedger.sol` semantics or storage layout without approval. Contract tests must stay green |
| `frontend/src/api/` | Types must mirror the backend Pydantic models exactly. Do not invent backend scopes or fields |
| Frontend charts | Bespoke SVG/CSS components. Do not add a charting library (Sprint 3.1 decision) |
| Frontend data | Display values computed by the backend or read from committed result files. **No hard-coded metric values or fallbacks that look like real data.** Show an explicit "unavailable" state instead |
| Demo determinism | Changes must not alter the demo fingerprint (`make demo-check`) unless approved and explained |

## 4. Coding conventions

- Match the surrounding code: naming, comment density, module layout and idioms.
- Python: type hints, Pydantic v2 models for API schemas, explicit enums for categorical outputs, SQLite access via the existing helpers (analytics uses read-only URIs). No new global state.
- TypeScript/React: React 19 function components, `react-router-dom` v7, Tailwind 4 tokens from `src/index.css`, existing primitives (`components/primitives.tsx`, `components/AnalyticalPrimitives.tsx`) before new ones. Keep pages code-split via `lazy()` in `App.tsx`.
- Accessibility: keyboard reachable, labelled controls, data-table fallbacks for charts (the existing charts follow this pattern).
- Prefer small, reviewable diffs. No drive-by refactors, renames or formatting churn.

## 5. Testing expectations

- Run the relevant suites and report the **actual output** (pass and fail counts, and errors). Never state a result you did not observe. If a suite was not run, say so and why.
- Baselines at handover (2026-11-10): **245** backend tests, **24** contract tests, frontend lint clean, build succeeds.
- Commands:
  - `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings`
  - `make test-contracts`
  - `cd frontend && npm run lint && npm run build`
- Live-stack checks (`make e2e`, `make demo-check`, `npx playwright test`) need a chain, the API and the correct ledger state. See `docs/PROJECT_MASTER_CONTEXT.md` §8.
- New behaviour needs tests. Bug fixes need a regression test where practical.
- A test count going down, or a fingerprint changing, is a finding to report. Never silently accept it.

## 6. Analytical integrity rules

- Risk signals are **investigative indicators, not proof of fraud**. Use the project's non-accusatory vocabulary (`REVIEW_RECOMMENDED`, `ELEVATED_REVIEW_PRIORITY`, `INSUFFICIENT_EVIDENCE`, …).
- Preserve raw source values and provenance. Never silently impute missing data.
- Keep registry namespaces isolated. Serial comparisons require the same `(registry, batch_id)`.
- Similar names do not establish legal identity. A parent/subsidiary relationship does not establish identity. An intermediary is not the principal. A missing or undisclosed beneficiary is not evidence of misconduct.
- Explain the methodology, thresholds, assumptions, counterevidence and limitations wherever a metric or finding is shown.

## 7. Prohibited assumptions and overclaims

Do **not** claim or imply any of the following:

- Real-world fraud-detection accuracy. The 270-pair, 124-case and 36-case benchmarks are synthetic, curated or circular, and the extraction figures are in-sample.
- That live AI extraction has been evaluated. It has not; the offline mock calls the parser.
- Public-chain deployment, decentralisation, or third-party verifiability. The contract runs on a local Hardhat chain (ID 31337) with a trusted registrar.
- That multi-document verification is purely on-chain. It uses the off-chain evidence index.
- That a feature exists because a roadmap or design doc describes it. Check the code.
- That a document's statements are true because its hash matches.
- Any deadline, requirement or judging criterion not verified from an official source.

## 8. Documentation standards

- Precise, neutral technical prose. No marketing language ("unbeatable", "pristine", "100 % healthy").
- Each claim carries its evidence: a command and its output, a file path and line, or a link to a report.
- Distinguish **verified**, **reported**, **planned**, **limitation** and **historical**.
- Never silently edit an accepted or frozen report. Add a dated correction or erratum section, or a new document, with owner approval.
- Prefer linking existing reports over copying them. Record contradictions explicitly instead of resolving them by assumption.
- Milestone reports go in `docs/DATANOVA_PHASE_<n>_..._REPORT.md`. Each records the branch, HEAD, the commands run, their outputs, the files changed, open issues, and "no commits/pushes made" where applicable.

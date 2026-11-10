# CLAUDE.md

OnceOnly ("Every retired tonne, claimed once") is a DATANOVA 2026 prototype that detects when the same retired carbon-credit units back more than one public claim. It treats serials as unit intervals keyed by `(registry, batch)` and anchors claims on a local smart contract that rejects overlapping ranges. On top of that it adds an explainable investigative analytics layer.

## Read first, in this order

1. [`docs/PROJECT_MASTER_CONTEXT.md`](docs/PROJECT_MASTER_CONTEXT.md): current state, architecture, API, data, milestones, open discrepancies (§9).
2. [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md): remaining milestones, acceptance criteria, release gates.
3. [`AGENTS.md`](AGENTS.md): coding, testing, data, Git and documentation rules. **These are binding.**
4. The phase report or methodology doc for whatever area you will touch (indexed in master context §11).

The README, `docs/00_mission_status.md` and `docs/submission/` describe the **pre-DATANOVA** product and are partly outdated. Do not treat them as current status.

## Architecture at a glance

```text
frontend/  React 19 + Vite + Tailwind 4, bespoke SVG charts, typed client in src/api/
   │ /api (Vite proxy → :8000)
backend/   FastAPI (app/main.py)
   ├─ claim pipeline: serials → extraction → rules → chain (web3) → SQLite + evidence store
   ├─ entity_resolution/ (2A) · reconciliation/ (2B)
   └─ analytics/ Stage 1 concentration+fragmentation · Stage 2 temporal · Stage 3 cross-registry
                 · Stage 4 risk_assessment/ (6 scopes, 16 rules)
contracts/ ClaimLedger.sol on a LOCAL Hardhat chain (ID 31337); not deployed publicly
data/      real VROD demo subset (38,004 rows) · synthetic claimants · curated benchmarks
```

## Safety rules (summary; full rules in AGENTS.md)

- Never read, print or modify `.env`. Never commit secrets or real keys.
- No `git reset --hard`, force push, destructive checkout/restore/clean, or `git add .`. Stage explicit paths only.
- **Do not commit or push unless the owner explicitly approves.**
- Do not install or upgrade dependencies without approval.
- Do not touch `../ClimateChain` or the original IEEE OnceOnly repository.
- `make eval`, `make gas` and `eval/eval_*.py` overwrite tracked results. `make reset` deletes local app state. Run them only when the task needs them.

## How to work on a task

1. **Verify before implementing.**
   - Check the branch, HEAD and `git status`.
   - Read the relevant code; do not rely on docs alone.
   - Confirm any feature exists before building on it.
   - State your understanding and plan for anything non-trivial.
2. **Stay in scope.** Make small, reviewable changes, with no unrequested refactors and no new architecture. Preserve backward compatibility.
3. **Frozen phases.** The backend phases 0–2C Stage 4 are accepted and frozen. Do not modify their code, methods or thresholds unless a concrete, reproducible defect blocks the work **and** the owner approves. Present the evidence first.
4. **Test for real.** Run the relevant suites and paste the actual results. Never fabricate or round up results. If something was not run, say so.
   - `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings` (baseline: 245 passed)
   - `make test-contracts` (baseline: 24 passing)
   - `cd frontend && npm run lint && npm run build`
   - Live-stack checks (`make e2e`, `make demo-check`, `npx playwright test`) need `make chain`, `make deploy`, `make api` and the right ledger state.
5. **Report truthfully.** Report:
   - the files changed
   - the commands run, with their output
   - what is verified versus unverified
   - open questions

   Then stop and wait for approval.

## Analytical and trust posture

- Findings are **investigative indicators, not proof of fraud**. Never claim real-world detection accuracy from the synthetic or curated benchmarks.
- Keep provenance. Never impute missing data. Keep registry namespaces isolated.
- Name similarity, parent/subsidiary links and intermediary disclosures are **not** legal identity. An undisclosed beneficiary is **not** misconduct.
- The ledger runs on a local chain with a trusted registrar key. Multi-document verification relies on the off-chain evidence index. Do not claim public-chain or purely cryptographic verification.

## Current status (2026-11-10, final completion mission)

- Done: backend phases 0–2C Stage 4; frontend Sprints 3.2–3.4; the Sprint 3.4.1 metrics audit; the verification trust-boundary rework; the analytics DB path fix; product polish; the submission package (deck, video, runbook, script, form text).
- Release evidence: [`docs/FINAL_RELEASE_QA_REPORT.md`](docs/FINAL_RELEASE_QA_REPORT.md). Progress log: [`docs/FINAL_COMPLETION_EXECUTION_LOG.md`](docs/FINAL_COMPLETION_EXECUTION_LOG.md).
- Baselines:

  | Suite | Result |
  |---|---|
  | Backend | 274 passed |
  | Contracts | 24 passing |
  | Playwright | 45 passed |
  | E2E | 13/13 |
  | Demo fingerprint | `c544f589…6483b` |

- Population metrics are pinned by `backend/tests/test_population_metrics_reconciliation.py`. Do not change them without approval.
- Owner actions only: public deployment (Render), DATANOVA form fields (track, team), merging into `main`.

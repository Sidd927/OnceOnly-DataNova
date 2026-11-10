# Final Completion Execution Log

A resumable log of the final DATANOVA completion mission. Update it after each milestone.

## Milestone 0: Real state (2026-11-10, 12:45 IST)

- Branch `datanova/phase-0-baseline`, HEAD `bf08180`. The tree held only the four untracked handover files.
- The repository `Sidd927/OnceOnly-DataNova` is **public**. Its default branch is `main` at `6a61655`, the pre-DATANOVA product.
- Official requirements were re-read on 2026-11-10 from the Devpost overview and rules pages (fetched with curl) and datanovathon.com (rendered with headless Chrome):
  - **Deadline: Nov 11, 2026 @ 3:30am IST** (= Nov 10, 17:00 EST / 22:00 UTC).
  - The rules say: "10th Nov – Round 1 final submission date – All your details with ppt link, working demo and optional video". Round 2, for shortlisted teams only, is on 25 Nov. The datanovathon.com "Final submission 25 Nov" refers to the overall event, not Round 1.
  - What to submit: **1. PPT, 2. Working demo link, 3. Optional video**. The form also asks for the title, problem, solution and methodology, demonstration, impact and validation, and **team contributions**.
  - The rules require that **pre-existing work be acknowledged** and that results not be fabricated or misleading. OnceOnly's claim-ledger core predates DATANOVA (IEEE ClimateChain, October 2026), so this must be disclosed.
  - Judging, as published and described by the organizers as a *proposed* framework:

    | Criterion | Weight |
    |---|---|
    | Innovation & Originality | 20 % |
    | Technical Implementation | 25 % |
    | Problem Relevance | 15 % |
    | Data & Analytical Rigor | 15 % |
    | Impact & Feasibility | 15 % |
    | Presentation & Documentation | 10 % |

  - Problem statements on datanovathon.com: the only Sustainability one is DN-SU-01 (solar forecasting), which does not match. **DN-OP-01 Open Innovation Challenge** ("bring your own real-world problem") fits. The track selected at registration is unknown, so it needs **owner confirmation**.
- Tooling:
  - Docker CLI and Colima are installed (the VM was stopped, now starting).
  - LibreOffice `soffice` and Keynote are available.
  - `gh` is authenticated.
  - No hosting CLI (Render, Fly, Vercel, HF) is installed or authenticated.

## Milestones 1–3: Correctness, trust boundary, operations (done; commits `5e092b2`, `793aa46`)

- **Sprint 3.4.1.** The frozen Stage 1 figures are reproduced exactly by the engine, the API and an independent SQL path. The Sprint 3.4 report figures trace to no code path; a dated erratum was added. Defects fixed:
  - shares zeroed by serialization (6,307 of 9,933 labels);
  - Lorenz charts showing a Gini from another population;
  - hard-coded fallback `0.4924`;
  - three wrong preset Gini values;
  - decile off-by-one.

  Audit: `docs/DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md`.
- **Verification.** An off-chain record no longer counts as an on-chain match. `verify()` now returns per-check results, with document statuses `ONCHAIN_ROOT_MATCH`, `ONCHAIN_MEMBERSHIP_PROVEN`, `OFFCHAIN_RECORD_ONLY` and `NO_MATCH`. Other changes:
  - deployed code is compared with the compiled artifact;
  - chain errors carry codes;
  - publicly known Hardhat keys are refused on non-local chains.
- **Analytics DB path.** Now follows `ONCEONLY_REFERENCE_DEMO_DB`, materializes from the subset when absent, and returns 503 with a code when unavailable.
- **Assessment presets.** Now point at the seeded Northwind #1, Helios #2 and Arbor #3, and are tested against the seed script. "Equinox" and `RULE-INT-001` are removed.
- **Evidence page.** Rewritten: provenance, in-sample extraction scope, DATANOVA benchmarks with caveats, methodology index.
- **Reconciliation tab crash.** The Sprint 3.2 TypeScript types did not match the backend; the tab crashed for every claim. Fixed.
- **Observatory.** Swallowed API errors are now surfaced.
- **Tests.**

  | Suite | Result |
  |---|---|
  | Backend | 270 passed |
  | Contracts | 24 passing |
  | Lint, build | Clean |
  | E2E | 13/13 |
  | Demo fingerprint | `c544f589…6483b` (canonical) |
  | Playwright (first full green run) | 45/45 |

  A crawler over 14 routes, every tab and every preset found 0 page errors, 0 failed API calls and 0 `NaN`/`undefined` text.
- Local stack used API port 8010, because port 8000 is held by a local `ssh` process that was left untouched.

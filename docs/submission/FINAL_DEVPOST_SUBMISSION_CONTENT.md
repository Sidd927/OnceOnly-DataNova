# OnceOnly: DATANOVA 2026 Submission Content (copy-ready)

Official requirements were checked on 2026-11-10 on the Devpost overview and rules pages and on datanovathon.com:

| Item | Requirement |
|---|---|
| Deadline | **Nov 11, 2026, 03:30 IST** (Nov 10, 17:00 EST / 22:00 UTC). This is the Round 1 final submission; Round 2 (shortlisted teams) is on 25 Nov |
| Submit | **1. PPT · 2. Working demo link · 3. Optional video** |
| The form also asks for | Title and overview, problem, solution and methodology, demonstration, impact and validation, **team contributions** |
| Rules | Acknowledge pre-existing work and third-party components; no fabricated results or misleading claims |

Fields marked **[OWNER CONFIRMATION REQUIRED]** cannot be verified from the repository.

---

## Links

| Field | Value |
|---|---|
| Repository | https://github.com/Sidd927/OnceOnly-DataNova (branch `datanova/phase-0-baseline`; see the README) |
| Presentation (PPT) | https://github.com/Sidd927/OnceOnly-DataNova/blob/datanova/phase-0-baseline/docs/submission/OnceOnly_DATANOVA_Final_Presentation.pptx (PDF: same path with `.pdf`) |
| Working demo link | **[OWNER ACTION: deploy per `FINAL_DEMO_RUNBOOK.md` §F and paste the Render URL]**. Until then: one-command local demo `make docker-build && make docker-run`, then http://127.0.0.1:7860 |
| Optional video | https://github.com/Sidd927/OnceOnly-DataNova/blob/datanova/phase-0-baseline/docs/submission/OnceOnly_DATANOVA_Demo_720p.mp4 (2:33). Uploading it to YouTube or Vimeo and pasting that link is easier for judges to play: **[OWNER ACTION]** |
| Track | **[OWNER CONFIRMATION REQUIRED]**. Natural fit: Sustainability & Climate. The only listed Sustainability problem statement, DN-SU-01, is solar forecasting, which OnceOnly does not address. The matching problem statement is **DN-OP-01 Open Innovation Challenge** ("bring your own real-world problem"). Use whatever was selected at registration |
| Team members and contributions | **[OWNER CONFIRMATION REQUIRED]**. Repository commits are authored by Siddhant Patil; AI coding assistance was used (see Acknowledgements) |

---

## Project title

OnceOnly

## Tagline

Every retired tonne, claimed once.

## Short description (about 250 characters)

OnceOnly checks whether the same retired carbon-credit units back more than one public climate claim. It reconciles claims with real registry records, explains every signal with evidence and limits, and anchors claims on a contract that refuses overlaps.

## Detailed description

Carbon registries make sure a credit is retired only once. Nothing checks what happens next. Companies cite retired units in sustainability reports, product labels and websites, often through brokers who split one retirement among many buyers. If two claims cite the same units, each looks valid on its own, and because they quote different serial strings in different documents, comparing hashes misses the overlap.

OnceOnly is an investigation platform for this claim layer:

- It reads the serial numbers in a claim's evidence.
- It turns each serial into an exact unit interval inside its registry batch.
- It reconciles that interval with real Verra and Gold Standard retirement records from the Berkeley Carbon Trading Project's Voluntary Registry Offsets Database (v2026-08).
- It checks the interval against every other locked claim.

When units are shared, it does not stop at a red flag. Allocation-aware reconciliation combines interval geometry with entity resolution. That lets it distinguish four situations:

- a legitimate split of one retirement;
- a broker retiring on behalf of a disclosed client;
- related companies;
- an unresolved beneficiary.

Each of these is kept separate from a conflict between unrelated claimants.

Around each claim, OnceOnly profiles the context:

- beneficiary disclosure and concentration;
- how batches are fragmented;
- when retirements cluster in time;
- how projects may relate across registries.

A unified assessment applies 16 deterministic rules across six scopes. Every finding states its threshold, evidence, counterevidence, missing information and recommended next step. Correlated signals are grouped so they cannot inflate the priority.

Accepted claims are anchored on `ClaimLedger`, a smart contract that itself rejects any claim overlapping an active one in the same batch. A public verification portal reports each check separately:

- network identity;
- deployed bytecode against the compiled artifact;
- the on-chain record;
- unit ranges;
- the evidence commitment;
- the uploaded document;
- the claimant commitment.

A database lookup is never presented as an on-chain proof.

OnceOnly flags evidence for human review. It does not decide who is right, and it does not claim to detect fraud.

## Problem statement

Double counting undermines trust in carbon credits. Registries prevent double *retirement*, but no shared mechanism prevents the same retired units from backing several public claims. Investigating this is hard for four reasons:

1. Unit numbers restart in every issuance batch. Ignoring the batch creates 159,511 spurious overlaps in the full Berkeley VROD data (11,631 Verra + 147,880 Gold Standard).
2. Most retirements disclose no beneficiary: 62.7 % of the 37,335 analysed retirement records.
3. Brokers retire on behalf of clients, and similar names do not establish legal identity.
4. Projects can appear on more than one registry.

Auditors, registry reviewers and analysts need a tool that works at the level of units, keeps provenance, and explains what it can and cannot conclude.

## Proposed solution

An end-to-end investigation workflow:

1. **Read**: deterministic serial extraction with provenance on every block, plus SHA-256 of each document.
2. **Reconcile**: unit intervals in isolated `(registry, batch)` namespaces, matched to real retirement records.
3. **Allocate**: interval geometry plus entity resolution, giving 8 allocation classes.
4. **Profile**: disclosure, HHI and entropy, pooled and within-batch Gini, batch fragmentation, leave-one-out MAD bursts, cross-registry correlation.
5. **Assess**: 16 deterministic rules with counterevidence and dependency grouping.
6. **Anchor and verify**: a contract invariant against overlapping units, and per-check public verification.

## Innovation and originality

- **Claim-layer focus.** It works on what happens *after* retirement, which registries do not cover.
- **Intervals, not hashes.** On 270 labelled pairs, exact-string or document-hash matching reaches recall 0.333; interval reconciliation detects every case. Ground truth is defined by construction (see Validation).
- **Allocation classes, not one red flag.** Splits, broker delegations and related parties are separated from conflicts.
- **Explainable by construction.** Deterministic rules with stated thresholds, counterevidence and missing-information callouts; no opaque risk score.
- **Separated verification.** On-chain proofs, off-chain lookups, network identity and deployed bytecode are reported as distinct checks.

## Technical implementation

| Layer | Implementation |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic 2, SQLite; 41 REST endpoints |
| Entity resolution | Legal-suffix normalization, intermediary parsing, blocking (99.1 % candidate reduction), explainable multi-feature matching |
| Reconciliation | Closed-interval algebra (`Q = e − s + 1`), 6 geometric and 8 allocation classes |
| Analytics | Concentration, fragmentation, temporal (continuous calendars, MAD bursts) and cross-registry modules; read-only database access |
| Contract | Solidity 0.8.24 `ClaimLedger`: active ranges per `keccak(registry:batch)` in a sorted linked list with an O(1) hinted overlap check. Registration gas is flat at 301,452 from 10 to 200 active ranges; a linear v0 grows to 832,608. Custom `RangeOverlap` errors are decoded by the backend |
| Frontend | React 19, TypeScript, Vite, Tailwind 4; bespoke SVG charts (Ruler, Lorenz curve, temporal timeline) with no chart library |
| Delivery | One Docker image (private chain, deploy, seeded demo, API serving the UI) in public-demo mode |

Tests run for this release:

| Suite | Result |
|---|---|
| Backend (pytest) | 274 passed |
| Contracts (Hardhat) | 24 passing |
| Browser (Playwright, including axe WCAG A/AA and keyboard tests) | 45 passed |
| End-to-end lifecycle | 13/13 checks |
| Demo state fingerprint | Reproduced exactly |

## Data and methodology

| Data | Detail |
|---|---|
| Registry data | Berkeley Carbon Trading Project, *Voluntary Registry Offsets Database* v2026-08 (CC BY 4.0): 493,518 rows (307,416 Verra retirements, 166,478 Gold Standard retirements, 19,624 Verra issuances), data through 2026-08-31 |
| Analytics population | A committed real subset of 38,004 rows across 22 projects: 37,335 retirements (87,668,330 t, 725 batches) and 669 issuances, which are excluded from retirement denominators |
| Normalization | Non-destructive: raw values kept; 6,955 records with encoding artefacts repaired; ambiguous dates tagged, not assumed |

**Statistics.** HHI and Shannon entropy are computed over disclosed volume only. Concentration bands are descriptive (no antitrust labels). Pooled and within-batch Gini are reported separately. Absolute micro-claims (≤ 10 t) are kept separate from relative small allocations (≤ 1 % of a batch). Bursts use a leave-one-out MAD baseline (k = 3). Zero-activity intervals describe the sample, not market dormancy.

**Reproducibility.** Every population figure in the Observatory was reproduced by an independent SQL computation. The audit found and fixed a serialization defect that dropped 6,307 of 9,931 beneficiary shares from the Lorenz curve, plus several display errors; an earlier report received a dated erratum. It also found that earlier audits had run on a database built before the Phase 1 encoding repairs. The system now stamps each materialization and rebuilds a stale one automatically, so a fresh clone, the container and the tests all use the same population.

## Validation and evaluation

| Test | Result | How to read it |
|---|---|---|
| Serial parsing on the full VROD | 493,518 / 493,518 rows parse into quantity-consistent unit ranges; 0 overlapping Verra retirements within a batch | Real data |
| Double use, 270 synthetic pairs on real ranges | Engine and contract P = R = 1.000; hash baseline recall 0.333; batch-blind precision 0.857 | Ground truth uses the engine's interval definition, so this verifies the implementation rather than measuring real-world accuracy |
| Entity resolution, 124 curated pairs | P = 1.000, R = 0.964 | Curated by the team |
| Allocation reconciliation, 36 curated scenarios | Expected class for 36/36 | A naive interval matcher also scores 1.00 on the binary conflict label |
| Serial extraction, 60 synthetic snippets | 100 %; 15 adversarial distractor tests pass | In-sample. The optional AI extraction is not evaluated |

## Impact and feasibility

OnceOnly gives sustainability auditors, registry and standards reviewers, and carbon-market analysts a way to check claims at the level of units, with every conclusion traceable to records and rules. It runs today from one container, uses only public data, and needs no proprietary infrastructure.

A credible path to deployment:

1. Public-testnet anchoring with claimant-signed registrations.
2. Per-document Merkle proofs.
3. Fresher registry data and more registries.
4. Measured AI extraction.
5. A consented pilot on real published claims to measure prevalence, which is currently unknown.

## Responsible AI and data use

- Signals are investigative indicators, never findings of fraud. Statuses are non-accusatory (`REVIEW_RECOMMENDED`, `INSUFFICIENT_EVIDENCE`, …).
- Missing beneficiary data is reported, never imputed, and is not treated as misconduct. Similar names, parent/subsidiary links and broker delegations do not establish legal identity.
- Claimants in the demo are synthetic and labelled as such. Registry data is attributed. Redistribution rights for registry-origin rows could not be verified and are disclosed (`data/LICENSE`).
- No machine-learning model makes decisions. The optional LLM extraction is off by default, cross-checked by the deterministic parser when used, and its accuracy is reported as not measured.
- Only unit ranges, hashes and a salted claimant commitment go on chain; documents stay off chain.

## Technology stack

Python 3.12, FastAPI, Pydantic, SQLite, pandas, rapidfuzz, pypdf, web3.py; Solidity 0.8.24, Hardhat; React 19, TypeScript, Vite, Tailwind CSS 4, lucide-react; Playwright, axe-core, pytest; Docker.

## Challenges and learnings

- **Batch identity is everything.** The same unit numbers recur across batches, so a batch-blind check produced false positives in 30 of 30 different-batch cases.
- **"Overlap" is not "conflict".** Brokers and corporate groups legitimately share units. Combining geometry with entity resolution was necessary to avoid false accusations.
- **Reproduce every number.** An independent audit found that a figure set in an earlier sprint report did not match the code, and that serialization rounding silently truncated a chart. Both are now fixed and pinned by tests.
- **Name the trust boundary.** A database match is not an on-chain proof. Separating the checks made the verification more honest and more useful.

## Future work

- Public-testnet deployment with EIP-712 claimant signatures.
- Merkle per-document commitments.
- Live or fresher registry data and additional registries.
- Measured AI extraction for scanned and complex documents.
- A real-claims pilot.
- Multi-user review workflows.

## Pre-existing work and acknowledgements

- **Pre-existing work.** OnceOnly's claim-ledger core was first built for the IEEE ClimateChain hackathon (October 2026): serial parsing, the registry reconciliation rules, the `ClaimLedger` contract and the original UI. Everything listed under DATANOVA in the README was built for this competition: entity resolution, allocation-aware reconciliation, the concentration, fragmentation, temporal and cross-registry analytics, the explainable assessment, the Observatory, Cross-Registry and Assessment workspaces, the separated verification model, and the audits. **[OWNER CONFIRMATION REQUIRED: confirm this framing satisfies the competition's originality rules.]**
- **Data.** Registry data © the respective registries, compiled by the Berkeley Carbon Trading Project. Quartson, P., Haya, B.K., Bernard, T., Abayo, A., Rong, X., So, I.S., Elias, M. (2026). *Voluntary Registry Offsets Database v2026-08*, UC Berkeley. CC BY 4.0.
- **Open-source components.** FastAPI, Pydantic, web3.py, pypdf, rapidfuzz, pandas, React, Vite, Tailwind CSS, lucide-react, Hardhat, Playwright, axe-core.
- **AI assistance.** AI coding assistants were used during development. **[OWNER CONFIRMATION REQUIRED: state as the rules require.]**

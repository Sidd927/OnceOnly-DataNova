# OnceOnly: Final Release QA Report (DATANOVA 2026)

| | |
|---|---|
| Date | 2026-11-10 (IST) |
| Branch | `datanova/phase-0-baseline` |
| Environment | macOS (Apple Silicon), Python 3.12.13, Node v26.4.0, Docker via Colima |
| Local API | Port 8010; port 8000 was held by an unrelated local `ssh` process, left untouched |

Every result below was observed during this session; nothing is carried over from earlier reports. A check that was not run says so.

## 1. Results

| Gate | Command | Result |
|---|---|---|
| Backend tests | `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings` | **274 passed** (245 at handover + 29 new regression tests) |
| Contract tests | `cd contracts && HARDHAT_DISABLE_TELEMETRY_PROMPT=true npx hardhat test` | **24 passing**. Gas: 333,078 at 0 ranges, then flat 301,452 (linear v0 reaches 832,608 at 200) |
| Frontend lint | `cd frontend && npx oxlint` | Exit 0, no diagnostics |
| Type check and build | `cd frontend && npm run build` (`tsc -b && vite build`) | Success |
| End-to-end lifecycle | `make reset`, API restart, `ONCEONLY_API=… make e2e` | **13/13 passed** (submit, reconcile, anchor, overlap blocked, contract `RangeOverlap`, verify match and tamper, challenge, uphold, re-anchor) |
| Demo determinism | `make reset`, API restart, `make seed`, `make demo-check` | `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`, **identical to the canonical fingerprint** (reproduced 5 times during the session, including in the container) |
| Browser suite, dev stack | `cd frontend && BASE_URL=http://127.0.0.1:8010 npx playwright test` | **45 passed**: 33 pre-existing, 8 repaired, 4 new; includes 7 axe WCAG A/AA, 4 keyboard and 1 link-crawl test. **This is the first recorded run of the Sprint 3.2–3.4 specs** |
| Browser suite, container | `BASE_URL=http://127.0.0.1:7860 npx playwright test` | **44 passed, 1 skipped**. The skip is the forced-registration flow, which public-demo mode disables by design |
| Interaction crawl | Custom script: 14 routes, every tab, every preset or demo button | 0 page errors, 0 console errors, 0 failed API calls, 0 rendered `NaN`, `undefined`, `Invalid Date` or `[object Object]` (dev stack and container) |
| Responsive check | 9 routes at 1440×900 and 390×844, measuring `scrollWidth` | 0 horizontal overflow after fixes (`/observatory` and `/evidence` overflowed on mobile before) |
| Docker build | `make docker-build` | Success (image about 2.1 GB) |
| Docker run | `make docker-run` | Ready in 4 s; canonical fingerprint at boot; `/api/health` shows chain, reference and analytics available and `public_demo: true`; anchor returns **403** |
| Container resources | `docker stats` | 279 MiB idle; 290 MiB peak under concurrent analytics |
| Evaluation | `.venv/bin/python eval/run_eval.py` | 270 pairs: engine and contract P = R = 1.000 (contract replay measured for the first time in committed results; 100 % agreement); hash baseline recall 0.333; batch-blind precision 0.857; parser 60/60 in-sample |
| DATANOVA benchmarks | `eval/eval_entity_resolution.py`, `eval/eval_reconciliation.py` | Re-run: metrics and every case outcome identical to the committed results (timestamps only) |
| Secret scan | `git grep` for API-key, PEM and 64-hex key patterns; `.env` tracked? | None found apart from the publicly known Hardhat development keys already in `.env.example` and the `Dockerfile`; `.env` not tracked |

**Not run:**

- The optional AI extraction evaluation needs an API key, which was not used.
- `make data` (67 MB download of the full registry) was not needed: the committed audit results were used for the full-registry figures.
- No public deployment was made (§5).

## 2. Defects found and fixed in this release

| # | Defect | Fix | Regression test |
|---|---|---|---|
| 1 | Population-share serialization zeroed 6,307 of 9,931 beneficiary shares; the Lorenz curve silently dropped them | Shares serialized unrounded | `test_api_serializes_every_disclosed_share_without_zeroing` |
| 2 | Lorenz charts labelled a beneficiary-share curve with the Gini of a different population (all allocations) | Override removed; the population is stated | Playwright Lorenz assertion (`Gini: 0.9748`, 9,931 labels) |
| 3 | Hard-coded `"0.4924"` fallback; `0 t` fallbacks; three wrong hard-coded preset Gini values; decile off-by-one | Removed or corrected; "Unavailable" states | Playwright error-state test |
| 4 | Sprint 3.4 report figures (HHI 215.17, 9.37 bits, 0.706, 3,767,118 t) matched no code path | Dated erratum; audit document | Pinned population tests |
| 5 | **Stale reference snapshot**: local and audit runs used a DB built before Phase 1 normalization (9,933 labels vs the canonical 9,931) | Build stamp plus automatic rebuild; tests run on a fresh materialization | `test_stale_demo_db_is_rebuilt_not_used`, `test_canonical_population_uses_repaired_labels` |
| 6 | A database record alone set `matches_onchain_commitment = true` | Separated statuses; multi-document membership proven by recomputing the commitment | 15 tests in `test_verification_trust.py` |
| 7 | No guard against public Hardhat keys on non-local chains; uncoded chain errors | `DEV_KEY_ON_NON_LOCAL_CHAIN` refusal; error codes (`NETWORK_MISMATCH`, …) | Same file |
| 8 | Analytics ignored `ONCEONLY_REFERENCE_DEMO_DB` (hard-coded `var/` path, excluded from the Docker image) | Uses the configured path, materializes when missing, 503 with a code otherwise | `test_analytics_db_path.py` |
| 9 | Claim reconciliation tab crashed the whole page for every claim (invented TypeScript types) | Types mirror the backend; the tab shows class, relationship and next step | Playwright tab test; crawler |
| 10 | Assessment presets named a non-existent "Equinox" claim; `RULE-INT-001` does not exist | Presets generated from `demoTargets.json`, checked against the seed script and the rule catalog | `test_demo_targets.py` |
| 11 | CLAIM-scope assessment label always said "0 units" | Computed from the claim's blocks | `test_claim_assessment_target_reports_claimed_units` |
| 12 | Observatory swallowed API errors and rendered nothing | Errors surfaced | Playwright error-state test |
| 13 | Requests aborted by a closed page left 2–3 s of CPU-bound work queued, delaying the next page by up to about 6 s; the temporal test failed 7 of 8 repeats | Memoized read-only analytics GET responses (keyed on DB path and mtime; errors not cached) | `test_read_only_analytics_responses_are_memoized_and_identical`; 8/8 repeats pass |
| 14 | `tmp_env` fixture left mixed module generations (order-dependent failures) | Restores the original modules on teardown | Full suite passes in any order |
| 15 | Stale or overstated copy: extraction "fails on tables", "market-wide" analytics, "matches 493,518 records" on a 38k-row demo | Rewritten with scope and caveats | Playwright Evidence test |

## 3. Data fingerprint and population

| Item | Value |
|---|---|
| Committed CSV SHA-256 | `809bb9346d469dcd1d6c3f9e9ba3a3977b43029c615acb77efb5cd273114c018` (recorded in each materialized DB's `meta.build`) |
| Population | 37,335 retirements, 87,668,330 t, 725 batches; 669 issuances excluded |
| Concentration | K = 9,931 disclosed labels; HHI 245.6410; entropy 7.5165 bits; equitability 0.5661; Telstra 3,766,034 t; top-3 23.13 % |
| Inequality | Pooled allocation Gini 0.960471; mean within-batch Gini 0.492445 |
| Demo state fingerprint | `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b` |

## 4. Verification trust boundaries (as implemented)

| Check | Meaning |
|---|---|
| `NETWORK` | RPC chain ID equals the deployment record's; 31337 is labelled a local development chain |
| `DEPLOYMENT_CODE` | Runtime bytecode equals the compiled artifact's `deployedBytecode`; otherwise "not performed" when the artifact is absent |
| `ONCHAIN_RECORD`, `RANGES_RECONCILE`, `EVIDENCE_COMMITMENT` | Read from the contract and compared with the server's records; the chain is authoritative |
| `DOCUMENT` | `ONCHAIN_ROOT_MATCH`, or `ONCHAIN_MEMBERSHIP_PROVEN` (the digest list recomputes to the on-chain root), count as on-chain. `OFFCHAIN_RECORD_ONLY` is a warning, never a pass |
| `CLAIMANT` | Needs the claimant's private salt |

The registrar is a trusted operator, claimants do not sign, and the chain is local.

## 5. Known issues and limitations

- **No public demo URL.** No hosting account is authenticated on the build machine. The image and the `render.yaml` blueprint are ready; the steps are in `docs/submission/FINAL_DEMO_RUNBOOK.md` §F.
- **`main` is still the pre-DATANOVA commit `6a61655`.** The repository's default branch shows the old product until the owner merges `datanova/phase-0-baseline`.
- **Scope of the benchmarks and data.** The 270-pair benchmark is circular. The 124-pair and 36-case benchmarks are curated. Extraction results are in-sample. AI extraction is not measured. Analytics cover a 22-project subset.
- **Public-demo rate limit.** The limit trusts `X-Forwarded-For`, which a client can spoof. That's acceptable for a demo.
- **Demo video narration** is synthetic text-to-speech.

## 6. Release status

**Submission-ready with documented limitations.** All automated gates pass with observed evidence. The remaining items need the owner: public hosting, form fields that only the owner can confirm (track, team, originality statement), and the decision to merge into `main`.

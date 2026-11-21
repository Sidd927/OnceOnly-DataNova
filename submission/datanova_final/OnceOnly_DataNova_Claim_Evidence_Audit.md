# OnceOnly DATANOVA Deck: Claim-Evidence Audit

| | |
|---|---|
| Audit date | 21 Nov 2026 |
| Branch / HEAD at audit | `datanova/phase-0-baseline` / `f743f33` |
| Scope | Every factual statement and number in `OnceOnly_DataNova_Pitch_Deck.pptx` (13 main + 7 appendix slides) |
| Method | Each claim was checked against the code, a committed result file, the live demo API, or a command re-run on 21 Nov 2026. Older documentation was used only to locate evidence, never as the evidence itself |

**Status labels**
- **VERIFIED**: re-run or read directly on 21 Nov 2026.
- **REPORTED**: from the committed release QA report (10 Nov 2026), not re-run here.
- **LIMITATION**: a constraint the deck states.

## 1. Commands run during this audit

| Command | Observed result |
|---|---|
| `cd backend && ../.venv/bin/python -m pytest -q -p no:warnings` | `274 passed in 13.01s` |
| `make test-contracts` | `24 passing (1s)` |
| `curl https://onceonly-demo.onrender.com/api/health` | HTTP 200 after **93 s** (cold start); `status: ok`, chain 31337 available, `reference.scope: demo-subset`, analytics available, `public_demo: true` |
| Read-only GET sweep of 9 UI routes and 6 API endpoints on the live demo | All HTTP 200 |
| `POST /api/verify` with `ref=OO-2026-0001` (read-only) | NETWORK, DEPLOYMENT_CODE, ONCHAIN_RECORD, RANGES_RECONCILE, EVIDENCE_COMMITMENT = PASS; DOCUMENT and CLAIMANT = NOT_PERFORMED (no file or salt supplied) |
| `shasum -a 256 data/reference/demo_subset.csv.gz` | `809bb9346d469dcd1d6c3f9e9ba3a3977b43029c615acb77efb5cd273114c018` (matches the QA report) |
| pandas read of `data/reference/demo_subset.csv.gz` | 38,004 rows: 37,335 retirement + 669 issuance; VCS 30,780 rows and 16 projects; GS 7,224 rows and 6 projects |
| `ffprobe` and a full `ffmpeg -f null` decode of `submission/OnceOnly_DataNova_2026_FINAL_DEMO.mp4` | 175.5 s, 1920×1080 H.264 30 fps, AAC 48 kHz, 58,232,054 bytes; decode completed with no errors |

**Not run in this audit:**
- Playwright (45) and `make e2e` (13/13): these need a local seeded chain stack. The deck labels both "release QA, 10 Nov".
- `make demo-check`: same reason.
- `make eval`: it overwrites tracked result files.
- Frontend lint and build: no frontend code changed.

## 2. Claim inventory

### Problem and data (slides 2, 3, 9, A3)

| # | Claim on slide | Evidence | Status |
|---|---|---|---|
| 1 | Real Verra retirement: batch 18453, 19,999 units, retired 6 Aug 2026, project 1904 "Wind Power Project in Tamil Nadu…", beneficiary not disclosed | Live `GET /api/reference/lookup?serial=18453-896315001-…`: record `896309560–896329558`, quantity 19,999, `event_date 2026-08-06`, `beneficiary null`, `source_sheet "Verra VCS Retirements"` | VERIFIED |
| 2 | Northwind 10,000 units (anchored); Helios 7,000 units; both synthetic | Live `GET /api/claims`: OO-2026-0001 `total_units 10000`, anchored; OO-2026-0002 `7000`, blocked; claimant names suffixed "(SYNTHETIC)"; `synthetic: true` | VERIFIED |
| 3 | Overlap 896,315,001–896,319,559 = 4,559 units; 65.1% of Helios; totals 17,000 ≤ 19,999 | Live `GET /api/claims/2/reconciliation`: `overlap_units 4559`, `pct_of_candidate 65.13`, `PARTIAL_OVERLAP`, `ALLOCATION_CONFLICT`. 10,000 + 7,000 = 17,000 (arithmetic) | VERIFIED |
| 4 | ICVCM Core Carbon Principle 8 "No double-counting" | icvcm.org/core-carbon-principles (fetched 21 Nov 2026) | VERIFIED (external) |
| 5 | Hash / serial-string matching recall 0.333 on 270 synthetic pairs citing real Verra ranges | `eval/results/latest.md` §A: baseline TP 60, FN 120 → R 0.333 | VERIFIED (file) |
| 6 | 159,511 false overlaps if the batch is ignored (11,631 Verra + 147,880 GS) | `eval/results/registry_audit.json`: `overlapping_adjacent_pairs_if_batch_ignored` 11,631 and 147,880 | VERIFIED (file). These count adjacent record pairs in the full VROD build of 19 Oct 2026 |
| 7 | 62.7% of analysed retirements name no beneficiary (23,400 of 37,335) | Live `/api/analytics/population/summary`: `unresolved_records 23400`, `record_unresolved_rate 0.626758` | VERIFIED |
| 8 | Population: 37,335 records, 87,668,330 t, 725 batches, 22 projects (16 VCS, 6 GS) | Same endpoint, plus the pandas profile above | VERIFIED |
| 9 | Retirements dated 25 Oct 2010 – 1 Sep 2026 | Live `/api/analytics/temporal/activity`: `earliest_date_observed 2010-10-25`, `latest_date_observed 2026-09-01` | VERIFIED. The dataset is labelled "through 31 Aug 2026", yet one event date is 1 Sep 2026. This is reported as observed and is minor |
| 10 | Disclosure: 13,935 disclosed (37.3%), 23,393 explicitly undisclosed (62.7%), 7 invalid placeholder; tonnes 40.1% / 59.7% / 0.18% | Live summary `coverage` block: 35,172,359 / 52,342,165 / 153,806 t out of 87,668,330 | VERIFIED |
| 11 | HHI 245.64 over disclosed volume; 9,931 labels; top three 23.1%; largest label 10.7% (Telstra 3,766,034 t) | Live summary: `hhi_disclosed 245.64`, `unique_disclosed_beneficiaries 9931`, `top3_disclosed_share 0.2313`, `dominant_disclosed_share 0.1071`, tier `HIGH_DISPERSION`. Telstra tonnage from `docs/FINAL_RELEASE_QA_REPORT.md` §3 | VERIFIED (Telstra figure REPORTED) |
| 12 | Entropy 7.5165 bits; equitability 0.5661 | Live summary `entropy_shannon_disclosed 7.5165`, `entropy_normalized 0.5661` | VERIFIED |
| 13 | Pooled Gini 0.9605; mean within-batch Gini 0.4924 | Live summary `pooled_allocation_gini 0.9605`, `batch_gini_distribution.mean 0.4924` | VERIFIED |
| 14 | 51 of 192 monthly periods flagged as bursts (leave-one-out MAD, k = 3, 12-month baseline); 10 zero-activity gaps, longest 91 days | Live `/temporal/bursts`: `sensitivity 3.0`, `baseline_window 12`, `burst_periods_count 51`, `total_periods_evaluated 192`. `/temporal/gaps`: `total_gaps_count 10`, `max_gap_duration_days 91` | VERIFIED |
| 15 | Full database 493,518 rows: 307,416 Verra + 166,478 GS retirements, plus 19,624 Verra issuances, all quantity-consistent | `eval/results/registry_audit.json` (`parsed` = `qty_consistent` = `rows` for each sheet) | VERIFIED (file, built 19 Oct 2026) |
| 16 | Within-batch overlaps in the source data: Verra 0, GS 5 adjacent pairs | Same file: `overlapping_adjacent_pairs_within_namespace` 0 and 5 | VERIFIED (file). Not investigated further and shown only in appendix A3, labelled "not interpreted" |
| 17 | Demo fingerprint `c544f589…6483b` | `docs/FINAL_RELEASE_QA_REPORT.md` §1 and §3 | REPORTED |

### Method and product (slides 4–8, A1, A2, A6)

| # | Claim on slide | Evidence | Status |
|---|---|---|---|
| 18 | A serial encodes a contiguous range in a batch; Q = e − s + 1 = 7,000 | Live claim 2 block: `unit_start 896315001`, `unit_end 896322000`, `quantity 7000`, `namespace VCS:18453`. Parser: `backend/app/serials.py`. Interval algebra: `backend/app/reconciliation/` | VERIFIED |
| 19 | Pipeline steps; SHA-256 per document; deterministic parser with provenance | Master context §3.1 and code (`service.py`, `serials.py`, `extraction.py`); live claim shows evidence `sha256` and `source: parser` | VERIFIED |
| 20 | Steps 03–05 built for DATANOVA; 01, 02 and 06 extend the IEEE ClimateChain core | `docs/PROJECT_MASTER_CONTEXT.md` §1.3; git history | VERIFIED (attribution from the project's own records) |
| 21 | 8 allocation classes and 6 geometric types; their semantics as described on slide 7 | `backend/app/reconciliation/models.py` (enums) and `engine.py` lines 42–145: classification logic | VERIFIED |
| 22 | Entity resolution: legal-suffix normalisation, "on behalf of" parsing, blocking prunes 99.1% of pair comparisons | `eval/results/entity_resolution_results.md` §3: 42,436 → 379 candidate pairs (99.11%); `backend/app/entity_resolution/` | VERIFIED (file) |
| 23 | 124 curated pairs: P 1.000, R 0.964, F1 0.982, 0 FP; exact-string F1 0.263; token F1 0.629; the 3 misses are parent/subsidiary | Same file §1 and §2: `parent_subsidiary_hierarchy` 75% of 12 pairs, FN = 3 | VERIFIED (file) |
| 24 | Product screenshot: Helios blocked, Ruler, "Ledger actions", DUP-001 | `submission/media/02-claim-overlap-ruler.jpg`, captured from the live demo on 10 Nov 2026. The live page was re-checked on 21 Nov 2026 and still shows the same state | VERIFIED |
| 25 | Contract reverts with `RangeOverlap` when the registration is forced | Live `/api/overview`: `chain_rejected` event for OO-2026-0002 (tx `0x0f17…c123`, block 3); `ClaimLedger.sol` line 80 `error RangeOverlap(...)` | VERIFIED |
| 26 | 16 rules across 6 scopes; 5 statuses; ruleset 2026.1.0-STAGE4 | Live `/api/analytics/assessment/rules` returns 16 rule IDs. `risk_assessment/models.py`: `AssessmentScope` (6 values), `AssessmentStatus`, `RULESET_VERSION` | VERIFIED |
| 27 | Each finding carries thresholds, metrics, evidence, counterevidence, missing information and a recommended action | `risk_assessment/models.py` lines 109–121 (fields) | VERIFIED |
| 28 | Helios assessment: 3 triggered rules, 2 independent signal groups | Screenshot `submission/media/04-explainable-assessment.jpg` | VERIFIED (screenshot of the live app) |
| 29 | No trained ML model; deterministic rules | Code inspection: no model training in `backend/app/`. The optional LLM extractor is disabled in the demo (`llm.configured: false`) | VERIFIED |

### Blockchain (slide 10, A5)

| # | Claim on slide | Evidence | Status |
|---|---|---|---|
| 30 | On-chain data: ranges per (registry, batch), evidence and report hashes, salted claimant commitment, status | `ClaimLedger.sol` structs `Range`, `Claim`, `Node`; master context §2 | VERIFIED |
| 31 | O(1) overlap check using a hinted sorted linked list | `ClaimLedger.sol` lines 10–12 and 150–158 (`_insert` verifies the neighbours; a wrong hint reverts `BadHint`) | VERIFIED |
| 32 | Gas 333,078 at 0 ranges, then flat 301,452; linear v0: 304,108 / 314,288 / 423,408 / 832,608 | `eval/results/gas.json` (generated 19 Oct 2026) | VERIFIED (file) |
| 33 | 7 verification checks, reported separately; a database match is never on-chain proof | Live `/api/verify` output; QA report §4 | VERIFIED |
| 34 | Local Hardhat chain 31337, one trusted registrar, claimants don't sign, not a public network | `/api/health` `public_network: false`; `/api/overview` `network_kind LOCAL_DEVELOPMENT_CHAIN`; QA report §4 | VERIFIED / LIMITATION |

### Validation (slide 11)

| # | Claim on slide | Evidence | Status |
|---|---|---|---|
| 35 | 270 pairs: engine and contract P = R = 1.000; 100% agreement; batch-blind P 0.857 | `eval/results/latest.md` §A | VERIFIED (file) |
| 36 | 36 curated scenarios (11 held out): 36/36; the naive interval matcher also detects every overlap | `eval/results/reconciliation_results.md` §1 and §2 | VERIFIED (file) |
| 37 | Serial extraction 60 snippets in 8 layouts: 100%, in-sample; AI not measured | `eval/results/latest.md` §B ("not run (no ANTHROPIC_API_KEY)") | VERIFIED (file) |
| 38 | 274 backend and 24 contract tests pass | Re-run on 21 Nov 2026 (§1) | VERIFIED |
| 39 | 45 browser tests including WCAG, and 13/13 end-to-end | `docs/FINAL_RELEASE_QA_REPORT.md` §1 | REPORTED |

### Impact and close (slides 12, 13)

| # | Claim on slide | Evidence | Status |
|---|---|---|---|
| 40 | Limits list | QA report §5; `AGENTS.md` §7; master context §9.7 | VERIFIED |
| 41 | Intended users | Master context §1.5 (intended, not actual, users; no adoption is claimed) | Stated as intent |
| 42 | Roadmap items (EIP-712, Merkle, refresh pipeline, AI measurement, pilot) | **Planned, not built.** Slide 12 labels them "Next" | PLANNED |
| 43 | Live demo URL works; first visit after idle can take about a minute | 93 s cold start observed on 21 Nov 2026; 51 s on 10 Nov | VERIFIED |

## 3. Discrepancies investigated

| Issue | Finding | Deck treatment |
|---|---|---|
| Stage 1 vs Sprint 3.4 metrics (HHI 245.6410 vs 215.17; entropy 7.5166 vs 9.37 bits; equitability 0.5661 vs 0.706; Telstra 3,766,034 vs 3,767,118 t) | **Resolved** by the Sprint 3.4.1 audit (`docs/DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md`) and pinned by `backend/tests/test_population_metrics_reconciliation.py`. The 215.17 / 9.37 / 0.706 figures matched no code path and carry a dated erratum. Today's live API returns 245.64 / 7.5165 / 0.5661 | Only the confirmed values are used. Entropy is 7.5165 (live API and QA report); the Stage 1 report's 7.5166 differs only in rounding |
| Cross-registry "identifier collision" | No real-data pair in the 22-project subset shares an identifier (0 of 12 candidates) | The deck never presents a collision as a real-data finding; it describes the rule only |
| **Project Comparator presets on `/cross-registry`** | All three presets ("VCS 1904 vs GS 3044", "VCS 1845 vs GS 1845", "VCS 2284 vs GS 3044") used **hand-entered attributes for projects that are not in the dataset**, and the UI did not label them. **Fixed locally on 21 Nov 2026 with owner approval (uncommitted):** the presets moved to `frontend/src/lib/demoTargets.json`. Two now use real census profiles (VCS 2042 vs GS 5673; VCS 2042 vs GS 2290). The collision example is badged "Illustration · not registry data" and uses fictional IDs `EX-0001`. Three new tests in `backend/tests/test_demo_targets.py` pin them to the reference data. **The live Render demo still serves the old presets until it is redeployed** | Not used in the deck. The runbook says to avoid the presets on the live demo until it is redeployed |
| Cross-registry screenshot (appendix A4) | The modal shows VCS 2042 vs GS 5673. Both are in the dataset, and the pair appears in the live correlations response | Used, captioned as captured on the identical local build (per `submission/media/MANIFEST.md`) |
| Gold Standard within-batch overlaps (5 pairs) | Present in the full-database audit file; cause not investigated | Appendix A3 only, labelled "source data, not interpreted" |
| DATANOVA judging weights | Devpost overview lists weights (Technical 25, Innovation 20, Problem 15, Data 15, Impact 15, Presentation 10). The Devpost rules page says the criteria "should not be represented as a finalized weighted rubric until formally approved" | The deck is designed against the weighted criteria but never quotes the weights |

## 4. Real vs synthetic data on the slides

| Element | Real or synthetic | Where labelled |
|---|---|---|
| Registry record VCS 18453 and every population metric | Real (Berkeley VROD v2026-08) | Slides 2, 4, 6, 9 and footnotes |
| Northwind, Helios and their documents | Synthetic | Slide 2 pills, slide 4 caption, slide 6 footnote; "(SYNTHETIC)" in the app |
| 270-pair, 124-pair, 36-case and 60-snippet benchmarks | Synthetic or curated | Slides 3, 7 and 11 |
| Chain | Local development chain | Slides 6, 10, 12 and A5 |

## 5. Claims deliberately excluded from the deck

- Any real-world fraud-detection accuracy, prevalence or "fraud prevented" figure (none exists).
- Customers, partners or adoption (none exist).
- "AI-powered" framing: the optional LLM extractor is unevaluated and disabled in the demo.
- Market-size statistics: none were verified from primary sources for this deck.
- Comparator presets and the identifier-collision illustration (see §3).

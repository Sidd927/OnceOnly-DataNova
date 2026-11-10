# OnceOnly: Final Demo Script (DATANOVA 2026)

| | |
|---|---|
| Length | About 2:35 narrated, 12 beats. A live walkthrough with pauses runs 3–4 minutes |
| Recorded version | `docs/submission/OnceOnly_DATANOVA_Demo_720p.mp4` (2:33, synthetic macOS narration), captions in `OnceOnly_DATANOVA_Demo_captions.srt` |
| Single source of truth | The narration below is verbatim from [`frontend/qa/demo/beats_datanova.mjs`](../../frontend/qa/demo/beats_datanova.mjs); keep the two in sync |
| Prerequisite | The seeded story. See [`FINAL_DEMO_RUNBOOK.md`](FINAL_DEMO_RUNBOOK.md) |

Rules for presenting:

- Say "potential double use" or "flag for review", never "fraud".
- Say "local development chain", never "on the blockchain" without qualification.
- The companies are synthetic; the registry records are real.

## Script

| # | Screen and action | Narration (verbatim) |
|---|---|---|
| 1a | `/`: landing hero, the Ruler on a real Verra retirement | "Carbon registries make sure a credit is retired only once. But a retirement is where the claims begin. Companies cite retired units in reports and product labels, often through brokers who split one retirement among many buyers." |
| 1b | Click **Step 4: Overlap** on the hero Ruler | "If two claims cite the same units, each one looks fine on its own. And because they quote different serial strings in different documents, comparing hashes misses it." |
| 2a | `/overview`: scroll to **Investigation workflow** and sweep across the eight steps | "OnceOnly turns this into an investigation workflow. The registry records are real, from Berkeley's Voluntary Registry Offsets Database. The five companies are synthetic." |
| 3a | Click **Inspect an overlap**, which opens `/claims/2` (Helios) | "Helios Apparel claims seven thousand units from a real Verra retirement. Each serial becomes an interval inside its registry batch." |
| 3b | Scroll to **Claimed units**: the Ruler, then the **Rejected by contract** panel | "Four thousand, five hundred and fifty-nine of those units already back Northwind's anchored claim. When the registration was forced, the smart contract itself refused it." |
| 4a | **Allocation Reconciliation** tab, then the conflict card | "The reconciliation explains the overlap. It is classified as an allocation conflict between different entities: not a broker acting for a disclosed client, not a parent and subsidiary, and not a legitimate split. It ends with a next step, not a verdict." |
| 5a | `/assessment`: click **Helios · claim 2**, scroll to `RULE-REC-002` | "The assessment console applies sixteen deterministic rules. Each finding shows its metrics, its limitations and a recommended action. Correlated signals are grouped, so they cannot inflate the priority." |
| 6a | `/cross-registry`: **Project Comparator** tab, **Identifier Collision** preset, **Compare Project Profiles** | "Projects can appear on more than one registry. The cross-registry workspace ranks candidate Verra and Gold Standard pairs, and treats an identical project ID on two registries as a collision, never as the same asset." |
| 7a | `/observatory`: **Concentration & Lorenz** tab, then the Lorenz curve | "The observatory describes the population: thirty-seven thousand real retirements. Most name no beneficiary, which is a disclosure fact, not misconduct. Every population figure was reproduced independently." |
| 8a | `/verify?ref=OO-2026-0001`: click **Original document**, then the checks list | "Finally, anyone can verify a claim. Northwind's original statement matches the commitment stored on chain." |
| 8b | Click **Tampered copy**; the document check becomes **Fail** | "A copy with a single flipped bit does not. Each check is reported separately, and the network is stated plainly: a local development chain, not a public blockchain." |
| 9a | `/evidence`: provenance and in-sample labels | "OnceOnly flags evidence for human review. It does not decide who is right, and its benchmarks are labelled for what they measure. Every retired tonne, claimed once." |

## Expected on-screen facts

These were checked against the seeded stack on 2026-11-10.

| Fact | Expected |
|---|---|
| Helios claim | OO-2026-0002, 7,000 units, status Blocked, 4,559 units shared with OO-2026-0001 (Northwind, anchored) |
| Contract rejection | `RangeOverlap` with units 896,315,001–896,319,559 already belonging to ledger claim #1 |
| Reconciliation | `ALLOCATION_CONFLICT`, entities `DIFFERENT_ENTITIES`, partial overlap, 65.1 % of the candidate range |
| Assessment (claim 2) | Review Recommended, high priority; `RULE-REC-002` partial overlap of 4,559 units; concentration rules grouped |
| Observatory | 37,335 retirements; HHI 246; equitability 0.566; top-3 share 23.1 %; Lorenz Gini 0.9748 over 9,933 labels |
| Verify, original | 6 of 7 checks pass; claimant check not performed; document `ONCHAIN_ROOT_MATCH` |
| Verify, tampered | 5 of 7 pass; document **Fail** (`NO_MATCH`) |

## Optional extra beats for a live session

- **Check a claim live:** `/claims/new`, the "Mistyped serial" sample. Lumen's batch 18435 is not found in the registry snapshot, so the claim needs review.
- **Temporal track:** `/observatory`, Temporal Dynamics tab. Bursts are flagged against a leave-one-out MAD baseline; zero-activity intervals describe the sample, not the market.
- **Rules catalog:** `/assessment`, Rules Catalog, then search `RULE-REC-001`.

## Video title and description

**Title:** OnceOnly: Every retired tonne, claimed once (DATANOVA 2026 demo)

**Description:**

> OnceOnly checks whether the same retired carbon-credit units back more than one public claim. It reconciles claims with real Verra and Gold Standard retirement records (Berkeley VROD 2026-08), explains each signal with its evidence and limits, and anchors claims on a contract that refuses overlapping units.
>
> Claimants are synthetic. The contract runs on a local development chain. Narration is synthetic text-to-speech.
>
> Code: https://github.com/Sidd927/OnceOnly-DataNova

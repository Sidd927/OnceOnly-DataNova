# OnceOnly: Live Demo Runbook (DATANOVA Round 2, Google Meet)

Based on the application as deployed at https://onceonly-demo.onrender.com and checked on **21 Nov 2026**:
- all 9 routes returned HTTP 200;
- the Helios claim page matched the screenshots;
- verifying OO-2026-0001 returned 5 PASS checks, with the document and claimant checks not performed when no file or salt was given.

Recheck on the day; nothing here is guaranteed.

## 0. Thirty minutes before

| Step | Action | Expected |
|---|---|---|
| 1 | Open https://onceonly-demo.onrender.com/api/health | `"status":"ok"`, `"public_demo":true`, analytics available. **The first request can take 1–1.5 min** (93 s observed on 21 Nov) |
| 2 | Open these tabs in order: `/claims/2`, `/assessment?scope=CLAIM&claim_id=2`, `/observatory`, `/verify?ref=OO-2026-0001` | Each loads without an error banner |
| 3 | Reload each tab once, 2–3 minutes before you present | Keeps the free instance awake |
| 4 | Zoom the browser to 110–125% | Readable over Google Meet |
| 5 | Open the backup video locally: `submission/OnceOnly_DataNova_2026_FINAL_DEMO.mp4` (2:55, burned-in captions) | Plays |

## 1. Demo path (about 3 minutes)

| # | Screen | Click | Say (short) |
|---|---|---|---|
| 1 | `/claims/2` (Helios Apparel) | Nothing yet; point at the **Blocked** and **Synthetic** badges, then the red "Potential double use" banner | "Helios is a synthetic company claiming 7,000 units of a real Verra retirement. OnceOnly has blocked it: 4,559 of those units already back Northwind's anchored claim." |
| 2 | Same page, **Unit Intervals & Ruler** tab | Point along the Ruler: registry record, Northwind, Helios | "The serials are drawn on one unit axis. The red band is the exact shared range, 896,315,001 to 896,319,559." |
| 3 | Same page, **Ledger actions** panel and the audit trail | Point at "Anchoring is blocked by DUP-001" and the **Rejected by contract** entry | "We also sent it to the contract anyway: the contract itself reverted with RangeOverlap. That's a real transaction on the instance's local chain." |
| 4 | Same page, **Allocation Reconciliation** tab | Click the tab | "Overlap isn't the verdict. It's classified: ALLOCATION_CONFLICT between unrelated entities, with a next step: request the retiring account holder's allocation records." |
| 5 | `/assessment?scope=CLAIM&claim_id=2` | Click **Run Assessment** if results aren't shown; expand **RULE-REC-002** | "16 deterministic rules. Every finding shows its thresholds, metrics, counterevidence and missing information. Three triggered rules form two independent signal groups, so nothing is double-counted. The status is Review Recommended, not fraud." |
| 6 | `/observatory`, **Concentration & Lorenz** tab | Point at the HHI and disclosure tiles | "This runs on 37,335 real retirements. Most don't name a beneficiary, which is where claims can't be attributed." |
| 7 | `/verify?ref=OO-2026-0001` | Click **Original document**, then **Tampered copy** | "Verification reports each check separately: network, bytecode, on-chain record, ranges, commitment, document. A copy with one bit flipped fails the document check. A database match is never shown as on-chain proof." |

Optional, if asked about cross-registry: open `/cross-registry`, **Correlation Explorer**, then **Inspect Pair** on "VCS 2042 vs GS 5673". These are real projects: the names are similar, but the IDs differ and the result is labelled a triage signal.

## 2. What to avoid

- **Don't use the Project Comparator presets** on `/cross-registry` ("VCS 1904 vs GS 3044", "VCS 1845 vs GS 1845"). Their second project is hand-entered and **not in the dataset**, and the UI doesn't label them as illustrations.
- **Don't try to anchor, challenge or submit a claim** on the public demo. Writes return 403 by design, and claim checks are rate-limited.
- Don't say "fraud", "AI model", "public blockchain" or "real companies". The claimants are synthetic.
- Don't promise uptime: it's a free instance that sleeps.

## 3. Recovery

| Problem | Do this |
|---|---|
| Health check still loading after 2 min | Keep presenting from the deck. Slides 6 and A4–A6 are real screenshots; say "here's the same screen captured from the live app" |
| A page shows an error | Reload once. If it persists, go back to the deck. Don't debug live |
| The instance is down entirely | Play the recorded demo `OnceOnly_DataNova_2026_FINAL_DEMO.mp4` (2:55) and say it's a **recording of the real application**, not a live session |
| Meet screen-share is laggy | Share the browser tab only, and narrate from the slides |
| Asked to run it locally | Point to the repository README: `make docker-build && make docker-run` serves http://127.0.0.1:7860 with the same seeded story. Only do this live if it was rehearsed |

## 4. Backup assets (all real captures of the app)

| File | Shows |
|---|---|
| `submission/media/02-claim-overlap-ruler.jpg` | Helios blocked, the Ruler, ledger actions |
| `submission/media/03-allocation-reconciliation.jpg` | `ALLOCATION_CONFLICT` with next step |
| `submission/media/04-explainable-assessment.jpg` | Assessment, `RULE-REC-002` |
| `submission/media/06-observatory-concentration.jpg` | Population metrics |
| `submission/media/08-verification-portal.jpg` | Verification checks (6 of 7 with the seeded document) |
| `submission/OnceOnly_DataNova_2026_FINAL_DEMO.mp4` | Full 2:55 recorded walkthrough. Narration is a synthetic voice, as credited on screen |

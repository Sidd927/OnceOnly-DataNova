# OnceOnly: Judge Q&A and Technical Explanation Guide

Every figure here is traced in `OnceOnly_DataNova_Claim_Evidence_Audit.md`. Answers are written to be said aloud in 20–40 seconds. **If you don't know, say so** and offer the evidence file afterwards.

---

## Part 1. Technical explanation guide

### 1.1 Serials as intervals (the core idea)
- A Verra or Gold Standard serial such as `18453-896315001-896322000-VCS-…` encodes **batch 18453** and an inclusive unit range **[896,315,001, 896,322,000]**.
- The quantity is Q = e − s + 1 = 7,000. OnceOnly checks this against the quantity the claim states.
- Unit numbers restart in every batch, so the namespace key is **(registry, batch_id)**. Two ranges can only conflict inside the same namespace.
- Comparing two claims is closed-interval intersection: overlap = [max(s₁, s₂), min(e₁, e₂)], non-empty when max ≤ min.
- Geometry gives 6 types: `EXACT_OVERLAP`, `CONTAINMENT`, `SUPERSET`, `PARTIAL_OVERLAP`, `ADJACENT`, `DISJOINT`.
- Code: `backend/app/serials.py`, `backend/app/reconciliation/`.

### 1.2 Allocation-aware classification
`backend/app/reconciliation/engine.py` combines the geometry with an entity-resolution result for the two claimants:

| Namespace | Shared units? | Relationship | Class |
|---|---|---|---|
| Different | n/a | n/a | `CROSS_NAMESPACE` (never a conflict) |
| Same | No | Different claimants | `LEGITIMATE_SPLIT` |
| Same | No | Same claimant | `DIFFERENT_UNITS_SAME_CLAIMANT` |
| Same | Either | Placeholder, undisclosed or customer pool | `UNRESOLVED_BENEFICIARY` |
| Same | Yes | Broker / principal | `INTERMEDIARY_ATTRIBUTION` |
| Same | Yes | Same entity (exact or canonical variant) | `SAME_UNITS_SAME_CLAIMANT` |
| Same | Yes | Parent / subsidiary | `SAME_UNITS_RELATED_CLAIMANTS` |
| Same | Yes | Unrelated | `ALLOCATION_CONFLICT` |

Each class comes with an explanation and a recommended audit action.

### 1.3 Entity resolution
`backend/app/entity_resolution/` works in four stages:

1. **Non-destructive normalisation.** Legal suffixes (GmbH, S.p.A., Pty Ltd, B.V., LTDA, PLC…), abbreviations and encoding damage are normalised. Raw values are kept.
2. **Intermediary parsing.** Phrases such as "on behalf of", "c/o" and pooled-customer accounts separate the broker from the principal.
3. **Blocking.** Several inverted-index keys (first distinctive token, prefix, second token, token signature, namespace) cut the 206-entity benchmark from 42,436 to 379 candidate pairs, a 99.11% reduction.
4. **Explainable scoring.**
   - Base score: 0.30 token-set + 0.25 token-sort + 0.25 Jaro-Winkler + 0.20 token Jaccard (rapidfuzz).
   - Legal-suffix adjustment: −25 to +5.
   - Contradiction penalties: numeric ID mismatch −40; energy source, sector or directional antonym −35 each.
   - The result maps to confidence tiers and a relationship type. Every feature's contribution is returned.

### 1.4 Population analytics (Stage 1–3)
- **Disclosure** has two tracks: disclosed, explicitly undisclosed, invalid placeholder. Nothing is imputed.
- **HHI and Shannon entropy** are computed over disclosed volume only (9,931 labels).
  - HHI = Σ(100·sᵢ)², giving 245.64 (`HIGH_DISPERSION`).
  - Entropy 7.5165 bits; equitability 0.5661.
- **Gini**:
  - pooled over all 37,335 allocations: 0.9605;
  - within each of 725 batches, mean 0.4924.
- **Micro-claims** (≤ 10 t) are kept separate from small tranches (≤ 1% of a batch).
- **Temporal**:
  - continuous calendar (zero months kept);
  - leave-one-out median/MAD burst test, k = 3, 12-period baseline: 51 of 192 months flagged;
  - zero-activity gaps described as *observed* inactivity.
- **Cross-registry**:
  - project similarity = 0.40 token-set + 0.30 token-sort + 0.30 Jaro-Winkler, with country, vintage and developer relations;
  - identical IDs across registries are flagged as `CROSS_REGISTRY_IDENTIFIER_COLLISION`, never as the same project.

### 1.5 Unified assessment (Stage 4)
- **Rules:** 16 deterministic rules (REC ×4, ENT ×2, CON ×3, FRG ×2, TMP ×2, XREG ×3), ruleset `2026.1.0-STAGE4`.
- **Scopes:** 6: `BATCH`, `PROJECT`, `CLAIM`, `ENTITY`, `CROSS_REGISTRY`, `AD_HOC`.
- **Each finding carries:** rule ID, thresholds, evaluated metrics, evidence, counterevidence, contextual caveats, missing information and a recommended action.
- **Dependency groups** cluster findings that share a root artifact, such as the same interval, so correlated rules can't inflate priority. For Helios, 3 triggered rules form 2 independent signal groups.
- **Statuses:** `NO_MATERIAL_SIGNAL`, `REVIEW_RECOMMENDED`, `ELEVATED_REVIEW_PRIORITY`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`.

### 1.6 ClaimLedger contract
- **Storage:** for each namespace key (keccak of registry:batch), a sorted linked list of active ranges.
- **Registration:** the off-chain client computes a predecessor hint (`hintFor`). The contract checks only the two neighbours, so the cost is O(1) whatever the list size. A wrong hint reverts with `BadHint` and can never skip the check.
- **Overlap:** a registration that overlaps an active claim reverts with `RangeOverlap(ns, existingClaimId, overlapStart, overlapEnd)`.
- **Gas:** 301,452 flat from 10 to 200 ranges. The first, linear version reached 832,608 at 200.
- **Stored on chain:** ranges, the evidence root, the report hash, a salted claimant commitment and the status. Challenge, uphold, resolve and withdraw flows exist; writes are disabled on the public demo.

---

## Part 2. Likely judge questions

### Problem and positioning

**1. Why does this problem matter?**
Carbon claims only mean something if each retired tonne backs one claim. The market's own integrity standard, the ICVCM Core Carbon Principles, lists "no double-counting" as a principle. Registries enforce single retirement, but nothing checks the claims built on those retirements, and brokers routinely split one retirement among buyers. We haven't measured how often double claiming happens in the wild, and I won't claim a number. What we show is that the gap exists and that it can be checked.

**2. How is this different from what registries already do?**
A registry records that units were retired, and sometimes for whom. It doesn't see the downstream claims: a sustainability report, a product label, a broker's allocation statement. OnceOnly works downstream. It takes the claim documents, maps their serials back to the retirement records, and compares claims with each other at unit level.

**3. Couldn't you just compare serial numbers or file hashes?**
We measured that. On 270 test pairs, exact serial or hash matching caught a third of the double uses (recall 0.333). Overlapping claims usually quote different sub-ranges and different documents. Matching numbers but ignoring the batch fails the other way: precision drops to 0.857, and across the full database it would create 159,511 false overlaps.

### Method

**4. How does serial-number overlap work?**
Each serial encodes a batch and an inclusive range of unit numbers. We key every range by registry and batch, and overlap is plain interval intersection. For Helios that gives exactly 896,315,001 to 896,319,559: 4,559 units.

**5. How do you distinguish legitimate allocations from problematic overlaps?**
Overlap alone is never the verdict. Non-overlapping ranges from one retirement are a legitimate split. Shared units are then classified by the relationship between the claimants:
- broker and disclosed client;
- parent and subsidiary;
- the same company filing twice;
- an undisclosed beneficiary;
- unrelated companies.

Only the last becomes `ALLOCATION_CONFLICT`, and even that is "review recommended", not a finding of wrongdoing.

**6. How does entity resolution work?**
It runs in four steps:
1. Normalise legal names without losing the raw value.
2. Parse intermediaries such as "X on behalf of Y".
3. Block candidates so we don't compare everything with everything.
4. Score with four string features plus legal-suffix and contradiction rules. For example, "Acme Solar LLC" against "Acme Wind LLC" gets a sector penalty.

Every match returns its feature contributions, so a reviewer can see why.

**7. How are ambiguous identities handled?**
- Placeholders such as "Not disclosed" are classified `UNRESOLVED`, never guessed.
- Parent/subsidiary links are a separate relationship type and are never merged into one identity.
- Broker relationships are kept as intermediary attribution.
- When the evidence is thin, the tier is `INSUFFICIENT_EVIDENCE`.

**8. How do you control false positives?**
- **Namespace isolation** removes the cross-batch false overlaps.
- **Allocation classes** stop legitimate splits, brokers and corporate groups being flagged as conflicts.
- **Contradiction penalties** in entity resolution give 0 false positives on the curated hard negatives.
- **Dependency groups** stop one underlying fact from being counted several times.
- **Non-accusatory statuses** and a human reviewer make the final call.

The 0-false-positive result is on a curated benchmark, so it shows the design works, not a field false-positive rate.

**9. How does cross-registry analysis work?**
We compared all 96 Verra × Gold Standard project pairs in the subset on name similarity, country, vintage and developer. 12 pairs reach a 0.5 similarity score. 9 of them have contradicting attributes, 2 show partial correlation, 1 has insufficient evidence, and none share an identifier. If two registries ever use the same project ID, it's flagged as a collision, never assumed to be the same project. All of these are triage signals; confirming a dual listing needs the registries themselves.

**10. How is the risk assessment explainable?**
It runs 16 deterministic, versioned rules, with no learned weights. Every finding shows its rule ID, thresholds, the metrics it evaluated, supporting evidence, counterevidence, missing information and a recommended next step. The same input always gives the same output, which is what an auditor needs.

**11. What is the role of AI or ML?**
- The analytics are deterministic and statistical; no model is trained.
- Entity matching uses classical string similarity (rapidfuzz) with explicit rules.
- There is an optional LLM-assisted extractor, but it's disabled in the demo and has **not** been evaluated.
- The extraction benchmark is the deterministic parser, and its result is in-sample.

### Blockchain and verification

**12. What is the role of the blockchain?**
It enforces one rule no operator can quietly bypass: two active claims can't hold the same units in the same batch. The contract itself reverts with `RangeOverlap`, even if someone skips our interface. It also gives a neutral, ordered record of which claim registered first, plus hash commitments to the evidence.

**13. Why isn't everything on-chain?**
- Documents can be confidential, and they're large.
- The analytics need to be explainable, revisable and cheap to re-run.
- Putting a score on-chain would make an investigative signal look like an immutable verdict.

So only ranges, hashes, a salted claimant commitment and status go on-chain.

**14. What does the public verification portal actually verify?**
It runs 7 separate checks:
1. the chain ID matches the deployment;
2. the deployed bytecode matches the compiled contract;
3. the claim exists on-chain, with its status and ranges;
4. the server's ranges equal the on-chain ranges;
5. the stored document digests recompute to the on-chain commitment;
6. an uploaded file matches;
7. with the claimant's private salt, the claimant commitment matches.

What it doesn't prove: that the document is true, that the registrar was honest, or which claim is legitimate.

**15. Is this a real blockchain deployment?**
No. It's a local Hardhat development chain (ID 31337) inside the demo instance, with one trusted registrar key, and claimants don't sign yet. The contract logic is the same one that would run on a public network. Claimant signatures (EIP-712) and a public testnet are next steps, not current features.

### Data and validation

**16. What data is real and what is synthetic?**
- **Real:** the registry records, from the Berkeley Carbon Trading Project's Voluntary Registry Offsets Database v2026-08 (CC BY 4.0). That covers 493,518 rows in the full database and a committed 38,004-row subset of 22 projects that the analytics run on.
- **Synthetic, and labelled as such in the app:** the claimant companies (Northwind, Helios and the others) and their claim documents. Their serial ranges point at real retirements.

**17. How is the platform validated?**
There are four benchmarks, each with a baseline:
- 270 synthetic double-use pairs on real ranges;
- 124 curated entity pairs;
- 36 curated allocation scenarios, 11 of them held out;
- 60 extraction snippets.

Engineering checks:
- re-run on 21 Nov 2026: 274 backend tests and 24 contract tests;
- from the 10 Nov 2026 release QA: 45 browser tests including WCAG checks, a 13-step end-to-end run, and a deterministic demo fingerprint.

**18. What do the benchmarks prove, and not prove?**
They show the implementation does what the method specifies, and they quantify the gain over naive baselines. They don't measure real-world accuracy.
- The 270-pair ground truth uses our own interval definition, so it's circular by construction.
- The entity and allocation cases were written by me.
- The extraction result is in-sample.

A real-world evaluation would need labelled real claims, which is the pilot on the roadmap.

**19. Are the population figures reliable? Didn't an earlier report differ?**
Yes, an earlier sprint report quoted HHI 215.17 and entropy 9.37 bits. An independent recomputation found that those figures matched no code path, so they were corrected by erratum. The confirmed values are HHI 245.64, entropy 7.5165 bits and equitability 0.5661 over 9,931 disclosed labels. A regression test now pins them, and the live API returns them.

**20. Why is 62.7% "undisclosed" not evidence of wrongdoing?**
Many retirements simply don't name the end user: privacy, broker pooling, or registry practice. It's a disclosure gap, not misconduct. It matters because it's exactly where claims can't be attributed, so OnceOnly reports "unresolved" rather than guessing. In this subset the gap differs a lot by registry: on the Cross-Registry page, Gold Standard shows 7.3% beneficiary disclosure by records against 44.5% for Verra.

### Limits, scale, adoption

**21. What are the limitations?**
- A local chain and a trusted registrar.
- A static snapshot to 31 Aug 2026.
- Analytics on 22 projects.
- Synthetic or curated benchmarks.
- Unevaluated AI extraction.
- An unmeasured real-world prevalence.

None of these is hidden in the product: the Evidence page states them too.

**22. How would this scale?**
- **Parsing:** all 493,518 rows of the full database already parse into quantity-consistent ranges.
- **Overlap checks:** per namespace and sorted, so they scale with the size of a batch, not the market.
- **On-chain cost:** constant per registration thanks to the hint.
- **Entity resolution:** blocking avoids all-pairs comparison.
- **Next:** a scheduled refresh from the registry exports, and the other registries the Berkeley database already covers (ACR, ART, CAR, Isometric). Today's parser and analytics handle Verra and Gold Standard only.

**23. How would real-world adoption work?**
The realistic first users are assurance providers and buyers' sustainability teams, as a pre-publication check: "are the units behind this claim already claimed?" A registry or standards body could run the same check at claim-publication time. Neither needs everyone to join at once; each claim checked adds coverage. We have no adopters today and don't claim any.

**24. What would you build next?**
1. Claimant-signed registrations on a public testnet.
2. Per-document Merkle proofs.
3. A full-registry refresh pipeline.
4. A measured evaluation of AI extraction on real documents.
5. A consented pilot on published claims, to measure how often overlaps really occur.

**25. Who decides which of two overlapping claims is valid?**
Not OnceOnly. It shows the shared units, the parties' relationship and what evidence is missing, then recommends a next step, such as requesting the retiring account holder's allocation records. The ledger supports challenge and resolve flows by a reviewer role, but the judgement stays with people who hold the contracts.

**26. Did you build all this during DATANOVA?**
The claim-ledger core (serial parsing, the original rules, the contract and the first UI) began at the IEEE ClimateChain hackathon in October 2026. For DATANOVA I built:
- the data-integrity layer;
- entity resolution and allocation-aware reconciliation;
- the population, temporal and cross-registry analytics;
- the unified assessment;
- the Observatory, Cross-Registry and Assessment workspaces;
- the separated verification model and the independent audits.

AI coding assistants were used during development.

---

## Part 3. Answers to avoid

| Don't say | Say instead |
|---|---|
| "detects fraud" | "flags potential double use for review" |
| "AI-powered" / "our model" | "deterministic, explainable rules" |
| "on the blockchain, so it's proven" | "the contract enforces no overlapping units; hashes show a document is unchanged, not that it's true" |
| "100% accurate" | "on synthetic and curated benchmarks it behaves as specified" |
| "used by …" / "partners" | "intended for auditors, buyers and registries; no adopters yet" |
| The live demo's old `/cross-registry` Project Comparator presets (VCS 1845 vs GS 1845, VCS 1904 vs GS 3044) as real cases | They are hand-entered and not in the dataset (fixed in the repository; live until a redeploy). Use the Correlation Explorer list (real data) |

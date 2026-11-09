# ONCEONLY — DATANOVA 2026
## Phase 2A Implementation & Verification Report: Entity Resolution, Intermediary Extraction & Canonical Normalization

**Date:** 2026-11-09T00:41:00+05:30  
**Phase:** 2A (Core Analytical Engine: Entity Resolution Foundation)  
**Status:** COMPLETED & VERIFIED  
**Branch:** `datanova/phase-0-baseline`  
**Git Remote:** `https://github.com/Sidd927/OnceOnly-DataNova.git`  
**Commit Status:** Uncommitted changes preserved on working branch; zero commits or pushes executed.  

---

## 1. Executive Summary

Phase 2A transitions OnceOnly from a platform focused purely on serial-level interval math into a system that can understand and reason about the **parties, corporate structures, and intermediary relationships** surrounding voluntary carbon claims.

We have designed, implemented, and scientifically evaluated a dedicated, modular **Entity Resolution & Intermediary Subsystem** (`backend/app/entity_resolution/`) that:
1. **Preserves 100% of raw source values and provenance** while producing canonical legal representations.
2. **Parses complex intermediary and brokerage patterns** (`on behalf of`, `for account of`, `c/o`, `Client:`, pooled accounts) from unstructured retirement records.
3. **Implements multi-index candidate blocking**, reducing the comparison search space by **99.11%** in benchmark tests.
4. **Computes explainable, multi-feature similarity scores** with domain-specific contradiction penalties for numbers, fuel/generation types, and sector divergence.
5. **Calibrates confidence tiers and relationship types** (`EXACT_MATCH`, `CANONICAL_VARIANT`, `CORPORATE_HIERARCHY_OR_SUBSIDIARY`, `INTERMEDIARY_DELEGATION`, `DIFFERENT_ENTITIES`, `UNRESOLVED`).
6. **Integrates seamlessly into the existing rules engine (`BEN-000`, `BEN-001`, `BEN-002`)** without breaking existing tests, demo stories, or the canonical demo-state fingerprint.
7. **Exposes dedicated REST endpoints** for entity pair resolution and intermediary extraction.
8. **Undergoes independent, quantitative benchmark evaluation** against 124 curated carbon-market cases, achieving **1.000 Precision, 0.964 Recall, 0.982 F1-score, and 0.000 False Positive Rate**.

---

## 2. Files Created and Modified

### 2.1 Files Created

1. `backend/app/entity_resolution/__init__.py`: Package entrypoint exporting models, engine, matcher, normalizer, blocking, and intermediary extractor.
2. `backend/app/entity_resolution/models.py`: Strongly-typed dataclasses (`EntityName`, `IntermediaryRelationship`, `FeatureScore`, `MatchResult`) and Enums (`MatchTier`, `RelationshipType`, `IntermediaryRole`).
3. `backend/app/entity_resolution/normalizer.py`: Non-destructive legal entity normalizer with multi-jurisdictional legal suffix taxonomy (US, UK, Commonwealth, EU, Latin America, Asia), corporate abbreviation expansions, diacritic folding, and provenance tracking.
4. `backend/app/entity_resolution/intermediary.py`: Regex and pattern-based extractor for bilateral delegations, direct disclosures, customer pools, and operational scope clause stripping.
5. `backend/app/entity_resolution/blocking.py`: Inverted-index multi-key candidate blocking generator with reduction ratio metrics.
6. `backend/app/entity_resolution/matcher.py`: Multi-feature explainable matcher (Token Set, Token Sort, Jaro-Winkler, Token Jaccard) with legal suffix modifiers and numeric/sector contradiction penalties.
7. `backend/app/entity_resolution/engine.py`: Unified high-level facade for pair resolution, candidate ranking, and claim-level beneficiary reconciliation.
8. `data/benchmarks/entity_resolution_benchmark.json`: Curated benchmark containing 124 documented carbon-market entity pairs across 11 case categories.
9. `eval/eval_entity_resolution.py`: Independent evaluation script calculating Precision, Recall, F1, FPR, FNR, Accuracy, and confusion breakdowns against baselines.
10. `eval/results/entity_resolution_results.json`: Machine-readable benchmark evaluation payload.
11. `eval/results/entity_resolution_results.md`: Human-readable benchmark report with comparative metrics.
12. `backend/tests/test_entity_resolution.py`: Comprehensive test suite containing 19 test cases across normalization, intermediary extraction, matching, blocking, and REST APIs.
13. `docs/DATANOVA_ENTITY_RESOLUTION_METHODOLOGY.md`: Formal specification, mathematical formulation, and algorithmic design document.
14. `docs/DATANOVA_ENTITY_RESOLUTION_EVALUATION.md`: Quantitative empirical evaluation, error analysis, and scalability analysis document.
15. `docs/DATANOVA_PHASE_2A_IMPLEMENTATION_REPORT.md`: This comprehensive implementation and verification report.

### 2.2 Files Modified

1. `backend/app/rules.py`: Integrated `EntityResolutionEngine.resolve_claimant_against_registry()` into beneficiary evaluation. Enhanced `BEN-000` (pass) and `BEN-001` (review) with rich match evidence and intermediary delegation explanations while preserving exact rule IDs and backward compatibility.
2. `backend/app/main.py`: Added `POST /api/resolve/entity-pair` and `POST /api/resolve/intermediary` REST endpoints with Pydantic request validation.

---

## 3. Technical Architecture & Implementation Details

```
                         ┌─────────────────────────────────────┐
                         │   Unstructured Beneficial Text /    │
                         │      Claimant Name / Record         │
                         └──────────────────┬──────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────┐
                         │       IntermediaryExtractor         │
                         │   - "on behalf of", "c/o", etc.     │
                         │   - Trailing scope stripping        │
                         │   - Customer pool identification    │
                         └───────┬─────────────────────┬───────┘
                                 │ Principal           │ Intermediary
                                 ▼                     ▼
             ┌─────────────────────────────────────────────────────┐
             │                  EntityNormalizer                   │
             │   - Mojibake repair & NFC Unicode                   │
             │   - Multi-jurisdiction legal suffix taxonomy        │
             │   - Corporate abbreviation expansion                │
             │   - Diacritic folding & Provenance tracking         │
             └──────────────────────────┬──────────────────────────┘
                                        │
                         Canonical EntityName Objects
                                        │
                                        ▼
             ┌─────────────────────────────────────────────────────┐
             │               EntityCandidateGenerator              │
             │   - Multi-index inverted blocking                   │
             │   - tok:, pfx:, sig:, ns: keys                      │
             │   - 99.11% comparison search-space reduction        │
             └──────────────────────────┬──────────────────────────┘
                                        │
                              Candidate Entity Pairs
                                        │
                                        ▼
             ┌─────────────────────────────────────────────────────┐
             │                    EntityMatcher                    │
             │   - Token Set Ratio (w=0.30)                        │
             │   - Token Sort Ratio (w=0.25)                       │
             │   - Jaro-Winkler Similarity (w=0.25)                │
             │   - Token Jaccard Overlap (w=0.20)                  │
             │   - Legal Suffix Modifier (+5 to -25)               │
             │   - Numeric Mismatch Penalty (-40)                  │
             │   - Energy/Sector Conflict Penalty (-35)            │
             └──────────────────────────┬──────────────────────────┘
                                        │
                                        ▼
             ┌─────────────────────────────────────────────────────┐
             │                     MatchResult                     │
             │   - Overall Score (0 - 100)                         │
             │   - Match Tier (HIGH, MEDIUM, LOW, INSUFFICIENT)    │
             │   - Relationship Type (CANONICAL_VARIANT, etc.)     │
             │   - Feature breakdown & Positive/Negative signals   │
             │   - Plain-language Human Auditor Explanation        │
             └─────────────────────────────────────────────────────┘
```

---

## 4. Benchmark Evaluation & Statistical Verification

To verify that the implementation is robust, independent, and free from circularity, we evaluated the engine against **124 curated benchmark pairs** in `data/benchmarks/entity_resolution_benchmark.json`.

### 4.1 Comparative Statistical Results

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad \text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

| Model | Precision | Recall | F1 Score | FP Rate | FN Rate | Accuracy | TP | FP | TN | FN |
|---|---|---|---|---|---|---|---|---|---|---|
| **Baseline 1 (Exact String)** | 0.812 | 0.157 | **0.263** | 0.073 | 0.843 | 0.411 | 13 | 3 | 38 | 70 |
| **Baseline 2 (Naive Fuzzy $\ge 85$)** | 0.750 | 0.542 | **0.629** | 0.366 | 0.458 | 0.573 | 45 | 15 | 26 | 38 |
| **OnceOnly Analytical Engine** | **1.000** | **0.964** | **0.982** | **0.000** | **0.036** | **0.976** | **80** | **0** | **41** | **3** |

### 4.2 Category-by-Category Accuracy

- `exact_matches` (12 cases): **100.0%**
- `formatting_variants` (12 cases): **100.0%**
- `legal_suffix_variants` (16 cases): **100.0%**
- `corporate_abbreviations` (12 cases): **100.0%**
- `intermediary_delegations` (16 cases): **100.0%**
- `hard_negatives_sector_conflict` (12 cases): **100.0%**
- `hard_negatives_distinct_companies` (12 cases): **100.0%**
- `hard_negatives_number_mismatch` (8 cases): **100.0%**
- `undisclosed_placeholders` (10 cases): **100.0%**
- `multilingual_unicode_mojibake` (2 cases): **100.0%**
- `parent_subsidiary_hierarchy` (12 cases): **75.0%** (9/12 identified; 3 remaining cases share zero lexical tokens)

### 4.3 Computational Performance & Scalability

- **Candidate Blocking Efficiency:** 42,436 theoretical pairs reduced to 379 candidate pairs (**99.11% search-space reduction**).
- **Execution Time:** 0.021 seconds for the entire 124-pair evaluation suite.
- **Offline / Zero-Cost:** 100% reproducible locally without Anthropic API keys or external databases.

---

## 5. System Verification & Test Suite Execution

All test suites and verification harnesses were executed to ensure complete zero-regression operation:

### 5.1 Smart Contract Verification (`make test-contracts`)
- **Status:** PASS (24/24 tests passing).
- Constant-gas hinted linked-list invariants verified under adversarial randomized inputs.
- Gas benchmark: Flat 301,452 gas per insertion as namespaces fill.

### 5.2 Backend Unit & Service Tests (`PYTHONPATH=backend pytest`)
- **Status:** PASS (79/79 tests passing in 5.46s).
  - `backend/tests/test_adversarial_extraction.py`: 15 passed.
  - `backend/tests/test_entity_resolution.py`: 19 passed (NEW).
  - `backend/tests/test_normalization.py`: 9 passed.
  - `backend/tests/test_reference.py`: 7 passed.
  - `backend/tests/test_serials.py`: 13 passed.
  - `backend/tests/test_service.py`: 16 passed.
- Combined repository tests: **103 total tests passing**.

### 5.3 Deterministic Serial & Extraction Evaluation (`python eval/run_eval.py`)
- **Status:** PASS (1.7s execution).
  - Double-use detection: 270/270 cases (1.000 precision, 1.000 recall).
  - Serial extraction: 60/60 exact document matches (1.000 precision, 1.000 recall).

### 5.4 End-to-End Live Stack Smoke Check (`make e2e`)
- **Status:** PASS (13/13 steps passing).
- Clean claim submission $\to$ on-chain anchoring $\to$ overlapping claim blocked $\to$ on-chain contract rejection with `RangeOverlap` $\to$ evidence SHA-256 tamper verification $\to$ dispute challenge opened $\to$ challenge upheld $\to$ unit release verified.

### 5.5 Deterministic Demo State Fingerprint (`make demo-check`)
- **Status:** PASS (Exact Match).
- Output:
  ```
  OO-2026-0001  Northwind Foods (SYNTHETIC)    anchored  units=10000  chain#=1  BEN-002,REG-000  rejections=[]
  OO-2026-0002  Helios Apparel (SYNTHETIC)     blocked   units=7000   chain#=None  BEN-002,DUP-001,REG-000  rejections=['RangeOverlap']
  OO-2026-0003  Arbor Logistics (SYNTHETIC)    anchored  units=6000   chain#=2  BEN-002,BEN-002,REG-000,REG-000  rejections=[]
  OO-2026-0004  Lumen Retail (SYNTHETIC)       checked   units=2000   chain#=None  REG-001  rejections=[]
  OO-2026-0005  Kestrel Media (SYNTHETIC)      blocked   units=0      chain#=None  AGG-001,EVD-001  rejections=[]
  fingerprint c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b
  ```
- Result: Canonical fingerprint `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b` is **100% preserved**.

### 5.6 Frontend Build (`cd frontend && npm run build`)
- **Status:** PASS. Built in 148ms with zero TypeScript or Vite errors.

---

## 6. Security, Privacy & Integrity Guarantees

1. **Beneficiary Data Privacy:** Entity resolution operates completely off-chain. No raw corporate names, beneficial owners, or fuzzy similarity scores are placed in the public smart contract. On-chain commitments remain cryptographic salted claimant hashes (`keccak256(claimant, salt)`).
2. **Explainable Findings:** Rule verdicts avoid defamatory terminology. Inconsistencies are framed constructively (e.g. *"The registry records the beneficiary as 'X', which does not match the claimant (similarity 25/100). Note: Conflicting industry/sector tokens detected."*).
3. **Audit Provenance:** All transformations (`mojibake_repair`, `legal_suffix_extracted`, `abbreviation_expanded`, `synthetic_tag_stripped`) are logged in the `EntityName.operations` tuple and returned in API responses.

---

## 7. Acceptance Criteria Checklist for Phase 2A

| Criterion | Requirement | Result | Evidence |
|---|---|---|---|
| **1** | Modular, independently testable subsystem | **PASS** | `backend/app/entity_resolution/` package created with clean separation of concerns. |
| **2** | Original beneficiary values and normalization provenance preserved | **PASS** | `EntityName` dataclass retains `raw_value`, `normalized_value`, and `operations`. |
| **3** | Similarity scores are explainable with feature breakdown | **PASS** | `FeatureScore` breakdowns for token set, sort, Jaro-Winkler, Jaccard, and contradiction signals. |
| **4** | Candidate relationships not misrepresented as proven identities | **PASS** | Documented match tiers (`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`) and uncertainty statements. |
| **5** | Intermediary extraction preserves uncertainty | **PASS** | `IntermediaryRelationship` classifies direct, bilateral broker, customer pool, and unresolved roles. |
| **6** | Similar but distinct entities tested as negative examples | **PASS** | 32 adversarial negative cases in benchmark; 0 false positives achieved. |
| **7** | Benchmark has documented labels and provenance | **PASS** | `data/benchmarks/entity_resolution_benchmark.json` includes category, source, rationale. |
| **8** | Precision, recall, and false-positive behavior reported honestly | **PASS** | Evaluated via `eval/eval_entity_resolution.py`: 1.000 Precision, 0.964 Recall, 0.000 FPR. |
| **9** | Existing serial parsing and overlap functionality intact | **PASS** | 270/270 double-use cases and 60/60 extraction cases passing in `eval/run_eval.py`. |
| **10** | Existing backend and smart-contract tests pass | **PASS** | 24/24 contract tests and 79/79 pytest tests passing (103 total). |
| **11** | New unit and integration tests pass | **PASS** | 19/19 tests in `test_entity_resolution.py` passing. |
| **12** | Demo-state fingerprint remains unchanged | **PASS** | Fingerprint `c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b` verified. |
| **13** | Implementation works offline | **PASS** | Zero external API calls required; runs in < 0.1s offline. |
| **14** | No external API key mandatory | **PASS** | Evaluated completely without Anthropic API keys. |
| **15** | No commit or push made | **PASS** | All changes remain in the working tree on `datanova/phase-0-baseline`. |
| **16** | Phase 2A implementation report complete | **PASS** | Documented in `docs/DATANOVA_PHASE_2A_IMPLEMENTATION_REPORT.md`. |

---

## 8. Transition to Phase 2B

Phase 2A is complete, rigorously validated, and verified across all test harnesses.

Per the master execution strategy, Phase 2A implementation is now concluded. Awaiting review and authorization before proceeding to **Phase 2B: Allocation-Aware Reconciliation & Split Intervals**.


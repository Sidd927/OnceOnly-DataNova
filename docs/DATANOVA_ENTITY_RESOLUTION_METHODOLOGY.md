# ONCEONLY — ENTITY RESOLUTION & INTERMEDIARY METHODOLOGY
## Formal Specification, Mathematical Formulation, and Algorithmic Design

**Author:** Principal Software Architect & Senior Data Scientist  
**Project:** OnceOnly — DataNova 2026 Global Data-thon  
**Module:** `backend/app/entity_resolution/`  
**Status:** Implemented, Calibrated & Verified  

---

## 1. Executive Summary & Problem Formulation

In voluntary carbon markets (VCM), credit retirements recorded in registries (e.g. Verra VCS, Gold Standard) are frequently decoupled from downstream corporate disclosures and environmental claims. A single corporate claimant may be represented across disclosures, invoices, brokerage statements, and registry entries under multiple textual variants:

1. **Orthographic & Typographic Variants:** Case divergence, punctuation, hyphens, and whitespace differences (e.g. `L'Oreal S.A.` vs `L OREAL SA`).
2. **Jurisdictional Legal Suffixes:** Multi-lingual corporate legal designations that indicate corporate form rather than distinctive identity (e.g. `Ltd` vs `Limited`, `GmbH`, `S.p.A.`, `Pty Ltd`, `B.V.`, `LTDA`, `PLC`).
3. **Corporate Word Abbreviations:** Industry-standard short forms (e.g. `Intl` vs `International`, `Mfg` vs `Manufacturing`, `Tech` vs `Technology`, `Solns` vs `Solutions`).
4. **Intermediary Delegations:** Brokerage, trader, or aggregator retirements executed on behalf of end beneficiaries (e.g. `"TBK Group on behalf of Lenovo"`, `"Patch Technologies - Client: Shopify Inc."`, `"Broker for account of Siemens AG"`).
5. **Pooled End-User Allocations:** Aggregate platform retirements without individual corporate attribution (e.g. `"On behalf of Patch's customers and their end users"`, `"Trip.com customers"`).
6. **Undisclosed Placeholders:** Redacted beneficial ownership recorded in 44.7% of Verra VCS retirement rows (e.g. `"Not Disclosed"`, `"Confidential"`, `"Anonymous"`).
7. **Adversarial Negative Pairs:** Entities sharing dominant generic or sector tokens that must *never* be conflated (e.g. `Acme Solar LLC` vs `Acme Wind LLC`, `Delta Air Lines` vs `Delta Electronics`, `Customer 10184` vs `Customer 10185`).

Naive string distance (Levenshtein, raw Jaro-Winkler) or unconstrained token fuzzy matching yields unacceptably high false-positive rates on hard negatives while suffering complete recall collapse on intermediary allocations.

OnceOnly implements an **Explainable Multi-Stage Entity Resolution Engine** combining:
- Non-destructive canonical legal normalization with full provenance tracking.
- Pattern-based intermediary and principal extraction.
- Inverted-index multi-key candidate blocking ($O(N^2) \to O(K \cdot |B|)$).
- Weighted multi-feature similarity scoring with contradiction penalties.
- Calibrated confidence tiers and structured relationship classification.

---

## 2. Canonical Entity Normalization Pipeline

The normalization pipeline is strictly non-destructive: it preserves the raw input string, outputs a standardized canonical representation, and logs every discrete transformation operation.

```
Raw Input String
       │
       ▼
[1. Mojibake Repair]          ──> MacRoman / Windows-1252 UTF-8 correction
       │
       ▼
[2. Unicode NFC Precomp]      ──> Canonical precomposition of combining characters
       │
       ▼
[3. Dash & Whitespace Norm]   ──> ASCII hyphen translation, space collapsing
       │
       ▼
[4. Placeholder Classifier]   ──> Detect "Not Disclosed", "Confidential", etc.
       │
       ▼
[5. Legal Suffix Extraction]  ──> Multi-jurisdictional regex taxonomy (end-anchored)
       │
       ▼
[6. Diacritic Folding]        ──> NFKD unaccented decomposition for tokens
       │
       ▼
[7. Abbreviation Expansion]   ──> Intl -> international, Mfg -> manufacturing
       │
       ▼
EntityName Data Structure (raw, normalized, canonical, tokens, legal_suffix, ops)
```

### 2.1 Multi-Jurisdictional Legal Suffix Taxonomy

Legal suffixes are matched against an end-anchored regex taxonomy ordered from most specific multi-word expressions to generic single-word abbreviations:

| Jurisdiction | Canonical Form | Recognized Variants / Regex Patterns |
|---|---|---|
| **English / Commonwealth** | `ltd` | `limited`, `ltd\.?` |
| | `inc` | `incorporated`, `inc\.?` |
| | `corp` | `corporation`, `corp\.?` |
| | `co` | `company`, `co\.?` |
| | `llc` | `l\.?l\.?c\.?`, `limited liability company` |
| | `plc` | `public limited company`, `plc\.?` |
| | `pvt ltd` | `pvt\.?\s+ltd\.?`, `private limited`, `pte\.?\s+ltd\.?`, `pty\.?\s+ltd\.?`, `proprietary limited` |
| **German / Swiss / Austrian** | `gmbh` | `g\.?m\.?b\.?h\.?`, `gesellschaft mit beschr[aä]nkter haftung` |
| | `ag` | `a\.?g\.?`, `aktiengesellschaft` |
| | `gmbh & co kg` | `gmbh\s*&\s*co\.?\s*kga?a?` |
| | `kgaa` | `kommanditgesellschaft auf aktien`, `kgaa` |
| **Romance / Latin American** | `sa` | `s\.?a\.?`, `soci[eé]t[eé]\s+anonyme`, `sociedad\s+an[oó]nima` |
| | `sas` | `s\.?a\.?\s*s\.?`, `société par actions simplifiée` |
| | `sarl` | `s\.?a\.?r\.?l\.?`, `société à responsabilité limitée` |
| | `spa` | `s\.?p\.?a\.?`, `societ[aà]\s+per\s+azioni` |
| | `srl` | `s\.?r\.?l\.?`, `societ[aà]\s+a\s+responsabilit[aà]\s+limitata` |
| | `sl` | `s\.?l\.?`, `sociedad limitada` |
| | `ltda` | `ltda\.?`, `limitada` |
| | `societa benefit` | `societ[aà]\s+benefit` |
| **Pan-European** | `se` | `s\.?e\.?`, `societas europaea` |
| **Dutch** | `bv` | `b\.?v\.?`, `besloten vennootschap` |
| | `nv` | `n\.?v\.?`, `naamloze vennootschap` |
| **Nordic** | `ab` | `a\.?b\.?`, `aktiebolag` |
| | `as` | `a\/?s`, `aktieselskab` |
| | `oy` | `oyj?`, `osakeyhtiö` |
| **Asian** | `sdn bhd` | `sdn\.?\s+bhd\.?` (Malaysia) |
| | `tbk` | `tbk\.?` (Indonesia) |
| | `pt` | `pt\.?` (Indonesia) |
| | `kk` | `k\.?k\.?`, `kabushiki kaisha` (Japan) |

When a suffix is extracted, it is detached from the root string. Both `raw_legal_suffix` and `legal_suffix` are recorded, and the remaining tokens form the canonical entity name.

---

## 3. Intermediary Allocation Algebra

Retirement records frequently document third-party transactions. OnceOnly formalizes the relationship using an algebraic mapping:

Let a retirement beneficiary string $R$ be parsed into a tuple:
$$\mathcal{I}(R) = \langle \text{is\_delegated}, P, I, \text{role}, \text{confidence} \rangle$$
where $P$ is the beneficial principal entity, $I$ is the intermediary account holder, and $\text{role} \in \{\text{DIRECT}, \text{BROKER\_OR\_TRADER}, \text{CUSTOMER\_POOL}, \text{UNRESOLVED}\}$.

### 3.1 Pattern Classes

1. **Bilateral Intermediary Delegation:**
   $$I \text{ on behalf of } P \implies \mathcal{I} = \langle \text{True}, P, I, \text{BROKER\_OR\_TRADER}, 0.95 \rangle$$
   *Example:* `"TBK Group on behalf of Lenovo"` $\to I = \text{TBK Group}$, $P = \text{Lenovo}$.

2. **Direct Disclosure Action:**
   $$\text{Retired on behalf of: } P \implies \mathcal{I} = \langle \text{False}, P, \varnothing, \text{DIRECT}, 0.95 \rangle$$
   *Example:* `"Retired on behalf of: Acme Corp"` $\to P = \text{Acme Corp}$, $I = \varnothing$.

3. **Account Allocation / Care Of:**
   $$I \text{ for the account of } P \implies \mathcal{I} = \langle \text{True}, P, I, \text{BROKER\_OR\_TRADER}, 0.92 \rangle$$
   $$P \text{ c/o } I \implies \mathcal{I} = \langle \text{True}, P, I, \text{BROKER\_OR\_TRADER}, 0.88 \rangle$$

4. **Structured Client / Offtaker Tag:**
   $$I \text{ - Client: } P \implies \mathcal{I} = \langle \text{True}, P, I, \text{BROKER\_OR\_TRADER}, 0.90 \rangle$$
   *Example:* `"Patch Technologies - Client: Shopify Inc."` $\to I = \text{Patch Technologies}$, $P = \text{Shopify Inc.}$.

5. **Customer Pool Aggregations:**
   $$\text{On behalf of } I\text{'s customers and end users} \implies \mathcal{I} = \langle \text{True}, \varnothing, I, \text{CUSTOMER\_POOL}, 0.90 \rangle$$
   *Note:* Pooled end users cannot be resolved to a specific legal entity without bilateral brokerage records. OnceOnly explicitly suppresses false corporate matches against pooled accounts.

6. **Operational Scope Stripping:**
   Registry strings frequently attach non-entity purpose descriptors (e.g. `"for aviation Scope 1 emissions"`, `"for the LNG cargo delivered from Malaysia"`). The parser executes non-destructive regex truncation to isolate the pure corporate identifier before normalization.

---

## 4. Multi-Index Candidate Blocking

To eliminate all-pairs comparison ($O(N \cdot M)$ complexity across hundreds of thousands of registry rows), `EntityCandidateGenerator` maps entities into an inverted index via four orthogonal blocking keys:

1. **Primary Distinctive Token:** $K_1 = \text{tok}:t_0$ where $t_0$ is the first non-stopword canonical token (e.g. `tok:acme`).
2. **Primary Token Prefix:** $K_2 = \text{pfx}:t_0[0:4]$ to bridge minor typographical errors in root stems (e.g. `pfx:acme`).
3. **Secondary Token:** $K_3 = \text{tok2}:t_1$ for multi-word corporate names (e.g. `tok2:industries`).
4. **Token Set Signature:** $K_4 = \text{sig}:\text{join}(\text{sort}(T))$ for short names ($|T| \le 3$).
5. **Contextual Namespace:** $K_5 = \text{ns}:(\text{registry}, \text{batch\_id})$ when records share issuance batches.

### Blocking Efficiency Formula

Given population sizes $|A|$ and $|B|$ and candidate set $C$:
$$\text{Reduction Ratio} = 1 - \frac{|C|}{|A| \times |B|}$$

In empirical evaluation across 206 benchmark entities, candidate blocking reduced theoretical comparisons from **42,436 to 379 pairs**, achieving a **99.11% search-space reduction** with zero recall loss.

---

## 5. Multi-Feature Explainable Similarity Scoring

Given two normalized entities $E_A = \langle C_A, T_A, S_A \rangle$ and $E_B = \langle C_B, T_B, S_B \rangle$ (where $C$ is the canonical string, $T$ the distinctive token set, and $S$ the normalized legal suffix):

### 5.1 Foundational Feature Metrics

$$\text{Base Score}(E_A, E_B) = \sum_{i=1}^4 w_i \cdot f_i(E_A, E_B) \times 100$$

| Feature $f_i$ | Weight $w_i$ | Definition | Mathematical Function | Domain Justification |
|---|---|---|---|---|
| **Token Set Ratio** | $0.30$ | Set-based token overlap | $\frac{\text{RapidFuzz.token\_set\_ratio}(C_A, C_B)}{100}$ | Resilient to token permutations and subset word inclusions. |
| **Token Sort Ratio** | $0.25$ | Alphabetically sorted Levenshtein | $\frac{\text{RapidFuzz.token\_sort\_ratio}(C_A, C_B)}{100}$ | Measures anagram-invariant token distance for equal token counts. |
| **Jaro-Winkler** | $0.25$ | Prefix-weighted character alignment | $\text{JaroWinkler.similarity}(C_A, C_B)$ | Captures prefix alignment and OCR character transpositions. |
| **Token Jaccard** | $0.20$ | Distinctive token set intersection | $\frac{\|T_A \cap T_B\|}{\|T_A \cup T_B\|}$ | Penalizes extraneous non-shared distinctive tokens. |

$\sum w_i = 0.30 + 0.25 + 0.25 + 0.20 = 1.00$.

### 5.2 Legal Suffix Compatibility Function $\Delta_{\text{suffix}}$

$$\Delta_{\text{suffix}}(S_A, S_B) = \begin{cases}
+5.0 & \text{if } S_A = S_B \neq \varnothing \quad (\text{Compatible legal forms}) \\
-25.0 & \text{if } \text{is\_nonprofit}(E_A) \neq \text{is\_nonprofit}(E_B) \quad (\text{Foundation vs commercial}) \\
-5.0 & \text{if } S_A \neq S_B \text{ and } (T_A \subseteq T_B \text{ or } T_B \subseteq T_A) \quad (\text{Cross-border subsidiary}) \\
-15.0 & \text{if } S_A \neq S_B \quad (\text{Divergent corporate form}) \\
0.0 & \text{if } S_A = \varnothing \text{ or } S_B = \varnothing
\end{cases}$$

### 5.3 Contradiction Penalties $\Omega_{\text{contra}}$

To eliminate false positives on adversarial negative pairs sharing brand or generic tokens, three deterministic penalty checks are applied:

1. **Numeric Identifier Mismatch:**
   $$\Omega_{\text{num}} = 40.0 \quad \text{if } \text{Nums}(C_A) \neq \varnothing \land \text{Nums}(C_B) \neq \varnothing \land \text{Nums}(C_A) \neq \text{Nums}(C_B)$$
   *Impact:* Blocks false matches between `Customer 10184` and `Customer 10185`.

2. **Energy Source / Fuel Conflict:**
   Let $\mathcal{F} = \{\text{solar}, \text{wind}, \text{hydro}, \text{thermal}, \text{gas}, \text{oil}, \text{coal}, \text{nuclear}, \text{electric}, \text{hydrogen}\}$.
   $$\Omega_{\text{fuel}} = 35.0 \quad \text{if } (T_A \cap \mathcal{F}) \neq \varnothing \land (T_B \cap \mathcal{F}) \neq \varnothing \land (T_A \cap T_B \cap \mathcal{F}) = \varnothing$$
   *Impact:* Blocks false matches between `Acme Solar LLC` and `Acme Wind LLC`, and `Northern Electric Power` and `Northern Gas Power`.

3. **General Sector / Industry Divergence:**
   $$\Omega_{\text{sector}} = 35.0 \quad \text{if } (T_A \cap \mathcal{S}) \neq \varnothing \land (T_B \cap \mathcal{S}) \neq \varnothing \land (T_A \cap T_B \cap \mathcal{S}) = \varnothing$$

4. **Directional & Ordinal Antonyms:**
   $$\Omega_{\text{antonym}} = 35.0 \quad \text{if } (w_1, w_2) \in \{\text{first/second}, \text{north/south}, \text{east/west}\} \land w_1 \in T_A \land w_2 \in T_B$$

### Final Calibrated Score

$$\text{Final Score} = \min\left(100.0, \max\left(0.0, \text{Base Score} + \Delta_{\text{suffix}} - \sum \Omega\right)\right)$$

If an exact raw or canonical match occurs, $\text{Final Score} \equiv 100.0$.

---

## 6. Calibrated Confidence Tiers & Relationship Classification

| Match Tier | Score Threshold | Required Conditions | Classification ($\mathcal{R}$) | Audit Interpretation |
|---|---|---|---|---|
| **HIGH_CONFIDENCE** | $100.0$ | Identical raw string or canonical root + compatible suffix | `EXACT_MATCH` or `CANONICAL_VARIANT` | Defensible identical entity across jurisdictions or spelling forms. |
| **HIGH_CONFIDENCE** | $\ge 88.0$ | Score $\ge 88.0 \land \sum \Omega = 0$ | `CANONICAL_VARIANT` | High probability of shared legal identity; minor abbreviation or formatting variation. |
| **MEDIUM_CONFIDENCE** | $\ge 50.0$ | $T_A \subset T_B \lor T_B \subset T_A \land \sum \Omega = 0$ | `CORPORATE_HIERARCHY_OR_SUBSIDIARY` | Likely parent/subsidiary or regional operating company. Evidence of group structure recommended. |
| **MEDIUM_CONFIDENCE** | $75.0 \le \text{Score} < 88.0$ | No material contradictions | `CANONICAL_VARIANT` | Substantial similarity with minor qualifier difference; flagged for human review. |
| **LOW_CONFIDENCE** | $50.0 \le \text{Score} < 75.0$ | Residual similarity without subset containment | `DIFFERENT_ENTITIES` | Insufficient evidence to establish common ownership. |
| **INSUFFICIENT_EVIDENCE** | $< 50.0$ | Severe penalty ($\sum \Omega \ge 30$) or low base score | `DIFFERENT_ENTITIES` | Material contradiction detected; distinct legal entities. |
| **INSUFFICIENT_EVIDENCE** | $0.0$ | Either entity is placeholder or empty | `UNRESOLVED` | Undisclosed registry entry; requires bilateral chain of custody evidence. |

---

## 7. Explainability & Output Data Structure

Every execution produces a structured `MatchResult` providing human-auditable rationale:

```json
{
  "overall_score": 100.0,
  "match_tier": "HIGH_CONFIDENCE",
  "relationship_type": "INTERMEDIARY_DELEGATION",
  "is_match": true,
  "feature_scores": {
    "token_set_ratio": { "raw_score": 1.0, "weight": 0.3, "contribution": 30.0 },
    "token_sort_ratio": { "raw_score": 1.0, "weight": 0.25, "contribution": 25.0 },
    "jaro_winkler": { "raw_score": 1.0, "weight": 0.25, "contribution": 25.0 },
    "token_jaccard": { "raw_score": 1.0, "weight": 0.2, "contribution": 20.0 }
  },
  "positive_signals": [
    "Exact character-for-character raw string equality",
    "Intermediary allocation identified: 'TBK Group' retired on behalf of 'Lenovo'"
  ],
  "contradictory_signals": [],
  "missing_information": [],
  "explanation": "Claimant matches the beneficial principal disclosed in the intermediary allocation ('Lenovo' via 'TBK Group')."
}
```

This guarantees complete traceability for auditors, market participants, and regulatory evaluators.


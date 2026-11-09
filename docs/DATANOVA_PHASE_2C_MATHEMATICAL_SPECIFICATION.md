# ONCEONLY — DATANOVA 2026
# Phase 2C Mathematical & Algorithmic Specification

**Date:** 2026-11-09T02:16:00+05:30  
**Author:** Principal Data Scientist & Quantitative Analyst  
**Document Purpose:** Formal Mathematical Formulation, Invariant Constraints, Numerical Proofs, and Edge-Case Contracts for Phase 2C Analytics  
**Status:** COMPLETE & VERIFIED  

---

## 1. Mathematical Notation and Conventions

| Symbol | Definition | Domain |
|:---|:---|:---:|
| $\mathcal{B}$ | An issuance batch identified by unique namespace $\mathcal{N} = \text{REGISTRY}:\text{BATCH\_ID}$ | $\text{String}$ |
| $N$ | Number of allocation tranches in batch $\mathcal{B}$ | $\mathbb{N}_{\ge 0}$ |
| $K$ | Number of distinct legal entities / beneficiaries in batch $\mathcal{B}$ | $\mathbb{N}_{\ge 0}, K \le N$ |
| $q_i$ | Quantity of carbon credit units (tonnes) in allocation tranche $i$ | $\mathbb{N}_{\ge 1}$ |
| $Q_{\text{total}}$ | Total retirement units across all allocations: $\sum_{i=1}^{N} q_i$ | $\mathbb{N}_{\ge 0}$ |
| $u_k$ | Total units allocated to distinct entity $k$: $\sum_{i \in \text{Entity}_k} q_i$ | $\mathbb{N}_{\ge 1}$ |
| $p_k$ | Fractional share of total units held by entity $k$: $u_k / Q_{\text{total}}$ | $[0.0, 1.0], \sum p_k = 1$ |
| $s_k$ | Percentage share of total units held by entity $k$: $100 \times p_k$ | $[0.0, 100.0]$ |
| $t_i$ | Timestamp or calendar date of retirement event $i$ | $\text{Date}$ |

---

## 2. Capability A: Allocation Size Dispersion & Fragmentation

### 2.1 Summary Sizing Statistics
For a set of allocation quantities $Q = \{q_1, q_2, \dots, q_N\}$:

- **Mean Allocation Size:**
  $$\mu = \frac{1}{N} \sum_{i=1}^{N} q_i = \frac{Q_{\text{total}}}{N}$$

- **Median Allocation Size:**
  Sorting $Q$ into ordered sequence $q_{(1)} \le q_{(2)} \le \dots \le q_{(N)}$:
  $$\text{Median}(Q) = \begin{cases}
  q_{(\frac{N+1}{2})} & \text{if } N \text{ is odd} \\
  \frac{1}{2} \left( q_{(\frac{N}{2})} + q_{(\frac{N}{2} + 1)} \right) & \text{if } N \text{ is even}
  \end{cases}$$

- **Sample Standard Deviation ($s$):**
  $$s = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (q_i - \mu)^2} \quad (\text{for } N \ge 2, \text{ else } 0.0)$$

- **Interquartile Range (IQR):**
  $$\text{IQR} = Q_3 - Q_1$$
  computed using linear interpolation over the empirical cumulative distribution function.

### 2.2 Gini Coefficient of Allocation Sizing
The Gini coefficient measures the inequality of allocation sizes within a batch:

$$G = \frac{\sum_{i=1}^{N} \sum_{j=1}^{N} |q_i - q_j|}{2 N \sum_{i=1}^{N} q_i}$$

Using the sorted sequence $q_{(1)} \le q_{(2)} \le \dots \le q_{(N)}$, the $O(N \log N)$ computational formula is:

$$G = \frac{2 \sum_{i=1}^{N} i \cdot q_{(i)}}{N \cdot Q_{\text{total}}} - \frac{N + 1}{N}$$

#### Invariants and Edge Cases:
- **Lower Bound ($G = 0.0$):** Occurs if and only if $q_1 = q_2 = \dots = q_N$ (perfect equality across all allocations).
- **Upper Bound ($G \to 1.0$):** For finite samples, the maximum theoretical value of the sample Gini is $\frac{N-1}{N}$. For $N=2$, $\max G = 0.5$; as $N \to \infty$, $\max G \to 1.0$.
- **Mathematical Validity vs Operational Minimum-Sample Requirements:**
  - *Mathematical Validity:* Sample Gini $G$ and finite-sample corrected $G^* = \frac{N}{N-1} G$ are mathematically rigorous and valid for any sample $N \ge 1$.
  - *Operational Safeguard:* While computable for any sample, automated compliance and integrity alerts (e.g. `RULE_STAT_002` for micro-claim evasion) require an operational minimum sample threshold of $N \ge 10$ tranches. This prevents natural small-sample variance from triggering spurious audit alarms.
- **Boundary Handling:** If $N = 0$ or $N = 1$ or $Q_{\text{total}} = 0$, $G = 0.0$. Negative quantities are strictly rejected before computation.

### 2.3 Micro-Claim Quantiles
A retirement tranche is classified as a micro-claim if it satisfies either an absolute de minimis threshold or a relative percentile threshold:

$$\text{IsMicro}(q_i) \iff q_i \le \tau_{\text{micro}} \quad \text{where} \quad \tau_{\text{micro}} = \max\left(10, \quad Q_{\text{total}} \times 0.01\right)$$

- **Micro-Claim Count:** $M = \sum_{i=1}^{N} \mathbb{I}(\text{IsMicro}(q_i))$
- **Micro-Claim Share (%):** $S_{\text{micro}} = \frac{M}{N} \times 100.0$

---

## 3. Capability B: Beneficiary Concentration Analytics

### 3.1 Dual-Track Accounting Architecture & Beneficiary Taxonomy
In real-world voluntary carbon registries (Berkeley VROD demo database), raw registry records exhibit multiple degrees of disclosure, data quality, and non-disclosure designations. 

#### A. Population Separation & Exact Denominators
Every metric in OnceOnly is evaluated against an explicit, non-mixed population:
- **Total Registry Records:** 38,004 records (206,695,778 tonnes).
- **Issuance Records:** 669 records (119,027,448 tonnes). Beneficiary is `NULL` for all 669 issuance records.
- **Retirement Population (Analysis Denominator):** **37,335 records** (**87,668,330 tonnes**).
- **Raw Non-NULL Beneficiary Records in Retirement Population:** **15,530 records** (37,991,691 tonnes), representing $37,335 - 21,805$.
  *(Note on Prior Discrepancy: The previously cited 16,199 figure represented an erroneous calculation of $38,004 - 21,805$, which mixed total database records with retirement-only NULL records across a difference of exactly 669 issuance records).*

#### B. The Four-Category Taxonomy
To prevent statistical skew without mutating raw data, OnceOnly classifies retirement records into four distinct categories:

| Beneficiary Category | Definition & Criteria | Database Instances | Record Count | % of Retirement Records ($N=37,335$) | Retirement Quantity | % of Retirement Volume ($Q=87,668,330\text{ t}$) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **`NON_PLACEHOLDER_DISCLOSED`** | Populated beneficiary value passing documented syntactic placeholder checks. Does not imply external legal entity verification. | `"Shell"`, `"Dexus"`, `"Qantas"`, `"Ecologi"`, `"3M"` | **13,935** | **37.32423%** | **35,172,359 t** | **40.11980%** |
| **`EXPLICITLY_UNDISCLOSED`** | Records with missing, unknown, or explicitly undisclosed beneficiary information under the documented source-data classification policy. This classification does not independently establish the reason for non-disclosure or a legal or contractual privacy entitlement. | `NULL` (21,805), `"Not Disclosed"` (1,584), `"Undisclosed"` (4) | **23,393** | **62.65702%** | **52,342,165 t** | **59.70476%** |
| **`INVALID_OR_PLACEHOLDER`** | Syntactic noise, punctuation bypass artifacts, or test entries. | `"_"` (5 records, 153,804 t), `"Test"` (1 record, 1 t), `"Test _ Num. Ord Cliente"` (1 record, 1 t) | **7** | **0.01875%** | **153,806 t** | **0.17544%** |
| **`UNRESOLVED_IDENTITY`** | Total credit units lacking valid corporate attribution (`EXPLICITLY_UNDISCLOSED` + `INVALID_OR_PLACEHOLDER`). | Union of undisclosed markers and invalid placeholders | **23,400** | **62.67577%** | **52,495,971 t** | **59.88020%** |

*(Note: Under a narrower 6-record placeholder definition excluding `"Test _ Num. Ord Cliente"`, `NON_PLACEHOLDER_DISCLOSED` is 13,936 records / 35,172,360 t [40.12%], `INVALID_OR_PLACEHOLDER` is 6 records / 153,805 t [0.18%], and `UNRESOLVED_IDENTITY` is 23,399 records / 52,495,970 t [59.88%]).*

#### C. Exact Population Invariants
1. $\text{NON\_PLACEHOLDER\_DISCLOSED} + \text{EXPLICITLY\_UNDISCLOSED} + \text{INVALID\_OR\_PLACEHOLDER} = 13,935 + 23,393 + 7 = \mathbf{37,335 \text{ records}}$ ($100.0\%$).
2. $Q_{\text{disclosed}} + Q_{\text{undisclosed}} + Q_{\text{invalid}} = 35,172,359 + 52,342,165 + 153,806 = \mathbf{87,668,330 \text{ tonnes}}$ ($100.0\%$).
3. $\text{UNRESOLVED\_IDENTITY} = \text{EXPLICITLY\_UNDISCLOSED} + \text{INVALID\_OR\_PLACEHOLDER} = 23,393 + 7 = \mathbf{23,400 \text{ records}}$ ($52,495,971\text{ t}$).

#### D. Batch 10635 Empirical Reference Calculation & Identifier Provenance
In Verra batch `'10635'` (Project ID `'959'`, Guanaré Forest Plantations), the database contains 1 issuance record (200,000 t) and 9 retirement records totaling **161,607 tonnes**:
- 1 record with `beneficiary = NULL` (rowid 2461): **15,000 tonnes** (9.28%).
- 2 records with `beneficiary = '_'` (rowid 2440 [142,500 t] + rowid 2389 [677 t]): **143,177 tonnes** (88.60%).
- 6 records with non-placeholder corporate beneficiaries (`Avisera`, `Mitsui/Lundin`, `Beiersdorf`): **3,430 tonnes** (2.12%).
- Under Policy 1 (naive non-empty string), coverage was $146,607 / 161,607 = \mathbf{90.72\%}$.
- Under Policy 2 (stricter non-placeholder screening), coverage is $3,430 / 161,607 = \mathbf{2.12\%}$.
- The transition from naive field-presence to non-placeholder screening causes a verified coverage drop of **88.60 percentage points** (from 90.72% to 2.12%), accurately isolating genuine corporate retirements.

> [!NOTE]
> **Identifier Provenance Warning:** SQLite `rowid` integers cited in analytical examples (e.g. 2440, 2389, 2461) are SQLite's internal row identifiers for the inspected database snapshot (`var/registry_demo.sqlite`). They are **not permanent identifiers** across regenerated, rebuilt, or re-ingested datasets. Natural composite identification across the global database requires `(kind, registry, batch_id, unit_start, unit_end)`, as `(registry, batch_id, unit_start, unit_end)` alone contains 130 duplicate pairs between full-batch retirements and their parent issuances.

#### E. Methodological and Linguistic Distinctions
OnceOnly enforces strict precision in analytical reporting:
1. **Raw Field Presence vs Non-Placeholder Disclosure:** Syntactic presence of a non-null string does not establish that a beneficiary value is valid or non-placeholder.
2. **Non-Placeholder Disclosed vs Verified Legal Entity:** A populated, non-placeholder organization name (e.g. `"Shell"`, `"Dexus"`) indicates an identifiable claimant string, but does **not** imply external legal entity verification (such as GLEIF LEI lookup or corporate registry validation). Entity resolution (Phase 2A) and legal verification are distinct downstream processes.
3. **Explicit Undisclosed Marker vs Legal Privacy Waiver:** An explicit marker (`"Not Disclosed"`, `"Undisclosed"`, `"Unknown"`, `NULL`) records missing or undisclosed beneficiary information under the documented source-data classification policy, but does not independently establish the reason for non-disclosure or a legal or contractual privacy entitlement.
4. **Invalid Placeholders vs Explicitly Undisclosed:** Placeholders (`"_"`, `"Test"`) indicate form bypass or testing artifacts and must never be conflated with intentional non-disclosure waivers.
5. **No Artificial Pooling:** Unresolved and placeholder quantities are tracked as an aggregate coverage deficit and must **never** be pooled into an artificial claimant when computing conditional Shannon entropy or HHI.
6. **Separation of Concerns:** Legal-entity verification, entity deduplication, and syntactic beneficiary-field validation are separate, non-interchangeable processes.

Concentration indices (Shannon entropy and HHI) are **conditional metrics**, computed strictly over the disclosed population $\mathcal{D}$ using normalized conditional probabilities:

$$p'_k = \frac{u_k}{Q_{\text{disclosed}}} \quad \text{for } k \in \mathcal{D}, \quad \text{such that} \quad \sum_{k \in \mathcal{D}} p'_k = 1.0$$

### 3.2 Shannon Entropy
Base-2 Shannon entropy quantifies the information dispersion of holdings among disclosed claimants:

$$H(X) = - \sum_{k=1}^{K} p'_k \log_2(p'_k)$$

#### Invariants and Edge Cases:
- **Zero-Probability Convention:** $\lim_{p \to 0^+} p \log_2(p) = 0$. Implemented as `if p > 0.0`.
- **Monopoly Holding ($K = 1$):** $p_1 = 1.0 \implies H(X) = - (1.0 \log_2 1.0) = 0.0$ bits.
- **Uniform Distribution ($p_k = 1/K$):** $H(X) = - \sum_{k=1}^K \frac{1}{K} \log_2(1/K) = \log_2(K) = H_{\max}$.
- **Normalized Shannon Entropy:**
  $$H_{\text{norm}}(X) = \begin{cases}
  \frac{H(X)}{\log_2(K)} & \text{if } K > 1 \\
  0.0 & \text{if } K \le 1
  \end{cases}$$
  Bounded strictly in $[0.0, 1.0]$. $H_{\text{norm}} = 0.0$ indicates single-buyer monopoly; $H_{\text{norm}} = 1.0$ indicates perfect uniform dispersion.

### 3.3 Herfindahl-Hirschman Index (HHI)
Measures market concentration using the classical economic scale:

$$\text{HHI} = \sum_{k=1}^{K} (100 \cdot p'_k)^2 = 10,000 \sum_{k=1}^{K} (p'_k)^2$$

- **Theoretical Range:** $\left[\frac{10,000}{K}, 10,000\right]$.
- **Normalized HHI ($\text{HHI}^*$):**
  $$\text{HHI}^* = \begin{cases}
  \frac{\text{HHI} - \frac{10,000}{K}}{10,000 - \frac{10,000}{K}} & \text{if } K > 1 \\
  1.0 & \text{if } K = 1 \\
  0.0 & \text{if } K = 0
  \end{cases}$$
  Bounded strictly in $[0.0, 1.0]$.

### 3.4 Concentration Tiers
Concentration tiers follow established US Department of Justice / Federal Trade Commission antitrust thresholds adapted for corporate carbon accounting:

| Tier Label | Mathematical Condition | Market Interpretation |
|:---|:---|:---|
| `MONOPOLY` | $K = 1 \lor \text{HHI} \ge 9,999$ | Single corporate buyer holds 100% of batch retirements |
| `HIGHLY_CONCENTRATED` | $\text{HHI} > 2,500$ | Dominated by one or two major corporate claimants |
| `MODERATELY_CONCENTRATED`| $1,500 \le \text{HHI} \le 2,500$ | Moderate distribution among several mid-sized buyers |
| `DISPERSED` | $500 \le \text{HHI} < 1,500$ | Unconcentrated, diversified corporate buyer pool |
| `EXTREME_DISPERSION` | $\text{HHI} < 500$ | Highly fragmented retail pool or fractional offset program |

---

## 4. Capability C: Temporal Retirement Intelligence

### 4.1 Liquidation Velocity: Calendar-Day vs Elapsed-Time
Registry public records provide discrete calendar dates ($t_i \in \text{Date}$), not high-resolution microsecond timestamps. To avoid numerical singularities (division by zero) when all retirements within a batch occur on the exact same date ($t_{(M)} = t_{(1)}$), OnceOnly employs the **inclusive calendar-day span** rather than an infinitesimal elapsed-time duration:

- **Inclusive Calendar-Day Span ($\Delta t_{\text{span}}$):**
  $$\Delta t_{\text{span}} = \max\left(1, \quad (t_{(M)} - t_{(1)}).\text{days} + 1\right)$$
  - *Single calendar day:* $\Delta t_{\text{span}} = (0) + 1 = 1$ calendar day.
  - *Consecutive days:* $\Delta t_{\text{span}} = (1) + 1 = 2$ calendar days.

- **Liquidation Velocity ($V$):**
  $$V = \frac{\sum_{i=1}^{M} q_i}{\Delta t_{\text{span}}} \quad \left(\frac{\text{tonnes}}{\text{calendar day}}\right)$$

This guarantees non-negative, finite velocity across all non-empty batches without fabricating fictitious intraday timestamps.

### 4.2 Vintage Lag (Dormancy)
Measures the duration between credit vintage/issuance and first retirement:

$$\Delta t_{\text{vintage}} = \max\left(0, \quad (t_{(1)} - t_{\text{vintage}}).\text{days}\right)$$

where $t_{\text{vintage}}$ is defined as `YYYY-01-01` of the project vintage year, or the confirmed registry issuance date.

### 4.3 Rapid Liquidation Burst Detection
A batch triggers the `RAPID_BURST` indicator if and only if all three deterministic conditions hold:

$$\text{RapidBurst} \iff \begin{cases}
\frac{Q_{\text{dated}}}{Q_{\text{total}}} \ge 0.80 & \text{(High cumulative volume)} \\
\Delta t_{\text{span}} \le 7 \text{ days} & \text{(Acute liquidation window)} \\
\Delta t_{\text{vintage}} \ge 1,095 \text{ days (3 years)} & \text{(Prolonged vintage latency)}
\end{cases}$$

### 4.4 Fiscal Year-End Clustering
Detects year-end compliance or corporate reporting rushes:

$$S_{\text{fiscal}} = \frac{\sum_{i \in \text{LateDec}} q_i}{Q_{\text{dated}}} \times 100.0 \quad \text{where} \quad \text{LateDec} = \{i : \text{Month}(t_i) = 12 \land \text{Day}(t_i) \ge 17\}$$

$$\text{FiscalClusterDetected} \iff \left( S_{\text{fiscal}} \ge 50.0\% \right) \land \left( Q_{\text{dated}} \ge 100 \text{ tonnes} \right)$$

---

## 5. Capability D: Cross-Registry Analytics

### 5.1 Serial Isolation Invariant
Under no circumstances are numerical serial integers compared directly across different registries:

$$\forall \mathcal{I}_A \in \text{VCS}, \mathcal{I}_B \in \text{GS}: \quad \mathcal{I}_A \cap \mathcal{I}_B = \emptyset \quad (\text{Strict Domain Boundary})$$

### 5.2 Multi-Signal Project Correlation Formulation
Cross-registry project correlation evaluates similarity between project profiles $\mathcal{P}_A \in \text{Registry}_A$ and $\mathcal{P}_B \in \text{Registry}_B$:

$$\text{Confidence}(\mathcal{P}_A, \mathcal{P}_B) = 0.45 \cdot S_{\text{name}} + 0.40 \cdot S_{\text{developer}} + 15.0 \cdot \mathbb{I}(\text{Country}_A = \text{Country}_B)$$

where:
- $S_{\text{name}} = 0.6 \cdot \text{TokenSetRatio}(\text{Name}_A, \text{Name}_B) + 0.4 \cdot \text{TokenSortRatio}(\text{Name}_A, \text{Name}_B) \in [0, 100]$
- $S_{\text{developer}} = \text{EntityResolutionEngine.resolve\_pair}(\text{Dev}_A, \text{Dev}_B).\text{overall\_score} \in [0, 100]$
- $\text{Confidence} \in [0.0, 100.0]$

### 5.3 Project Correlation vs Duplicate-Credit Conclusions
Cross-registry project correlation assesses the likelihood that two registered project entities represent the same underlying real-world emission reduction project. 

Crucially, **a high correlation score does NOT constitute a definitive finding of double-claiming or duplicate credit issuance**. Because registries operate mutually exclusive serial number spaces, verifying double-claiming across registries requires bilateral registry attestation or evidence of simultaneous retirement certificates for the same vintage tonne. Project correlation operates strictly as an investigatory triage signal.

---

## 6. Hand-Worked Reference Calculations

### Case 1: Perfectly Dispersed Batch ($N = 4$ identical claimants)
- Input: $Q = \{250, 250, 250, 250\}$, Claimants: $\{A, B, C, D\}$. $Q_{\text{total}} = 1000$.
- $p'_A = p'_B = p'_C = p'_D = 0.25$.
- Shannon Entropy:
  $$H(X) = - 4 \times (0.25 \log_2 0.25) = - 4 \times (0.25 \times -2.0) = \mathbf{2.0000 \text{ bits}}$$
  $H_{\max} = \log_2(4) = 2.0000$.
  $H_{\text{norm}} = 2.0 / 2.0 = \mathbf{1.0000}$.
- HHI:
  $$\text{HHI} = 4 \times 25.0^2 = 4 \times 625 = \mathbf{2,500.00}$$
  $\text{HHI}^* = (2500 - 2500) / (10000 - 2500) = \mathbf{0.0000}$.
- Gini:
  $q = [250, 250, 250, 250]$. Weighted sum $= 1(250) + 2(250) + 3(250) + 4(250) = 2500$.
  $G = \frac{2 \times 2500}{4 \times 1000} - \frac{5}{4} = \frac{5000}{4000} - 1.25 = 1.25 - 1.25 = \mathbf{0.0000}$.
- Mean $= 250.0$, Median $= 250.0$, $s = 0.0$.

### Case 2: Highly Skewed Batch ($N = 4$ allocations, 1 dominant)
- Input: $q = [10, 10, 10, 970]$, $Q_{\text{total}} = 1000$.
- $p_1 = p_2 = p_3 = 0.01$, $p_4 = 0.97$.
- Shannon Entropy:
  $0.97 \log_2(0.97) = 0.97 \times (-0.043943) = -0.042625$
  $0.01 \log_2(0.01) = 0.01 \times (-6.643856) = -0.066439$
  $$H(X) = - (-0.042625 + 3 \times -0.066439) = \mathbf{0.2419 \text{ bits}}$$
  $H_{\text{norm}} = 0.2419 / 2.0 = \mathbf{0.1210}$.
- HHI:
  $$\text{HHI} = 97.0^2 + 3 \times 1.0^2 = 9409 + 3 = \mathbf{9,412.00}$$
  $\text{HHI}^* = (9412 - 2500) / (10000 - 2500) = 6912 / 7500 = \mathbf{0.9216}$.
- Gini:
  Sorted $y = [10, 10, 10, 970]$.
  Weighted sum $= 1(10) + 2(10) + 3(10) + 4(970) = 10 + 20 + 30 + 3880 = 3940$.
  $$G = \frac{2 \times 3940}{4 \times 1000} - \frac{5}{4} = \frac{7880}{4000} - 1.25 = 1.97 - 1.25 = \mathbf{0.7200}$$
- Mean $= 250.0$, Median $= 10.0$, $s = 480.0$.

### Case 3: Dual-Track Accounting with Redacted Beneficiary
- Input: Entity A: 400, Entity B: 200, Entity C: 200, "Not Disclosed": 200. $Q_{\text{total}} = 1000$.
- Disclosed: $Q_{\text{disclosed}} = 800$, Unresolved: $Q_{\text{unresolved}} = 200$.
- $\text{Coverage Ratio} = 800 / 1000 = \mathbf{0.8000}$ (80% disclosed, 20% unresolved).
- Disclosed Probabilities: $p'_A = 400/800 = 0.50$, $p'_B = 200/800 = 0.25$, $p'_C = 200/800 = 0.25$.
- Disclosed Entropy:
  $$H(X) = - (0.50 \log_2 0.50 + 2 \times 0.25 \log_2 0.25) = - (-0.50 - 0.50) = \mathbf{1.5000 \text{ bits}}$$
  $H_{\max} = \log_2(3) = 1.5850$ bits.
  $H_{\text{norm}} = 1.5000 / 1.5850 = \mathbf{0.9464}$.
- Disclosed HHI:
  $$\text{HHI}_{\text{disclosed}} = 50.0^2 + 25.0^2 + 25.0^2 = 2500 + 625 + 625 = \mathbf{3,750.00}$$
  Classification: `HIGHLY_CONCENTRATED` among disclosed buyers.

---

## 7. Numerical Stability and Validation Contracts

1. **Floating-Point Guardrails:** All internal probability summations are verified to satisfy $|1.0 - \sum p_i| \le 10^{-6}$.
2. **Logarithm Domain Contract:** `log2` is never invoked on non-positive floats ($x \le 0$).
3. **Empty Input Contract:** An empty allocation set `[]` returns zero for all continuous metrics and assigns tier `DISPERSED` with `claimant_count: 0`.
4. **Finite Bound Contract:** All normalized metrics ($H_{\text{norm}}, \text{HHI}^*, G$) are clamped strictly to $[0.0, 1.0]$ via `max(0.0, min(1.0, val))` to protect against floating-point rounding epsilon.


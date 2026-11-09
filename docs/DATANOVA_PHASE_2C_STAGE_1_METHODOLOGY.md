# ONCEONLY — DATANOVA 2026
# PHASE 2C: STAGE 1 METHODOLOGY — BENEFICIARY CONCENTRATION & BATCH FRAGMENTATION
## Hardened Mathematical, Statistical & Architectural Specification

**Project:** OnceOnly — Carbon Market Integrity Platform ("Every retired tonne, claimed once")  
**Competition:** DATANOVA 2026 Global Data-thon  
**Document Type:** Analytical Methodology & Mathematical Foundations  
**Status:** Approved, Implemented & Hardened (Phase 2C Stage 1)  
**Date:** 2026-11-09  
**Branch:** `datanova/phase-0-baseline`  
**Commit:** `6a6165502121c116b12df0caff02671b23946966`

---

## 1. Executive Summary & Epistemic Scope

Phase 2C Stage 1 implements investigative intelligence for carbon credit retirement portfolios across voluntary registries (Verra VCS and Gold Standard). The methodology addresses two fundamental analytical dimensions:
1. **Beneficiary Concentration Intelligence:** Quantifying how retirement credit volumes are distributed among disclosed corporate claimant strings, establishing dual-track accounting between disclosed and unresolved identity populations.
2. **Batch Fragmentation Intelligence:** Quantifying the internal allocation structure of credit batches, analyzing tranche sizing inequality (within-batch and macro pooled Gini coefficients), absolute micro-claims vs relative small allocations, and interval geometry.

> [!IMPORTANT]
> **Investigative Intelligence Principle:**  
> These capabilities generate **investigative intelligence, NOT legal or regulatory fraud determinations**. High concentration, micro-claim fragmentation, or non-disclosure reflect structural market characteristics, retail aggregation programs, or commercial privacy choices. The system never labels a batch, project, registry, or claimant fraudulent based on statistical metrics alone.
>
> **Antitrust Market Definition Guardrail:**  
> Herfindahl-Hirschman Index (HHI) measures in this system describe the empirical distribution of disclosed retirement quantities among normalized beneficiary strings in the observed dataset. They do **not** constitute market shares in an economically defined relevant antitrust market and do not establish competition-law or regulatory conclusions.

---

## 2. Capability A: Beneficiary Concentration Methodology

### 2.1 Population Isolation & Denominator Integrity
All beneficiary concentration metrics operate strictly upon the **retirement population** ($\text{kind} = \text{'retirement'}$). 

- **Population Invariant:** Issuance records ($\text{kind} = \text{'issuance'}$) are strictly excluded from all concentration denominators. In voluntary carbon registries, issuance records represent creation events held by developers or registries prior to retirement and universally lack corporate beneficiary attribution ($N_{\text{issuance}} = 669$, all `beneficiary = NULL`). Mixing issuance into retirement calculations incorrectly inflates the undisclosed denominator.
- **Dynamic Calculation:** Denominators are calculated dynamically from the selected input records, never hardcoded.

### 2.2 Beneficiary Classification Policy & Four-Category Taxonomy
Raw registry strings exhibit differing levels of quality, redaction, and syntactic noise. OnceOnly establishes a deterministic four-category taxonomy:

| Category | Mathematical Definition & Criteria | Database Instances | Purpose & Guardrails |
| :--- | :--- | :--- | :--- |
| **`NON_PLACEHOLDER_DISCLOSED`** | Populated string passing syntactic placeholder checks. | `"Shell"`, `"Dexus"`, `"Qantas"`, `"3M"`, `"Telstra"` | Identifiable corporate claimant string. **Epistemic boundary:** Standardizes string labels only; does **NOT** establish verified legal corporate identity, GLEIF LEI verification, parent/subsidiary consolidation, or beneficial ownership. |
| **`EXPLICITLY_UNDISCLOSED`** | Missing (`NULL`), empty string (`""`), whitespace, or explicit non-disclosure markers (`"not disclosed"`, `"undisclosed"`, `"unknown"`, `"n/a"`, `"na"`, `"none"`, `"null"`, `"unspecified"`). | `NULL`, `"Not Disclosed"`, `"Undisclosed"` | **Approved Definition:** *"Records with missing, unknown, or explicitly undisclosed beneficiary information under the documented source-data classification policy. This classification does not independently establish the reason for non-disclosure or a legal or contractual privacy entitlement."* |
| **`INVALID_OR_PLACEHOLDER`** | Syntactic punctuation bypass tokens (`"_"`) or documented testing placeholders (`"Test"`, `"Test _ Num. Ord Cliente"`). | `"_"` (5 records, 153,804 t), `"Test"` (1 record, 1 t), `"Test _ Num. Ord Cliente"` (1 record, 1 t) | Form-bypass or staging artifacts. Never conflated with intentional non-disclosure waivers. Legitimate corporate entities containing the substring "test" (e.g. *"Testing Laboratories Inc."*) are preserved as `NON_PLACEHOLDER_DISCLOSED`. |
| **`UNRESOLVED_IDENTITY`** | $\text{EXPLICITLY\_UNDISCLOSED} \cup \text{INVALID\_OR\_PLACEHOLDER}$ | Union of missing, undisclosed, and placeholder records | Total deficit in corporate claimant transparency. |

### 2.3 Dual-Track Coverage Accounting
To eliminate distortion caused by redacted records without artificially inflating market concentration, OnceOnly computes dual-track coverage across the entire input population:

- **Record-Count Coverage:**
  $$\text{Coverage}_{\text{records}} = \frac{N_{\text{disclosed}}}{N_{\text{total}}} \times 100\%$$
- **Quantity-Weighted Coverage:**
  $$\text{Coverage}_{\text{tonnes}} = \frac{Q_{\text{disclosed}}}{Q_{\text{total}}} \times 100\%$$
- **Unresolved Deficit Rate:**
  $$\text{Deficit}_{\text{tonnes}} = \frac{Q_{\text{unresolved}}}{Q_{\text{total}}} \times 100\% = 100\% - \text{Coverage}_{\text{tonnes}}$$

> [!WARNING]
> **No Artificial Monopoly Pooling:**  
> Unresolved quantities ($Q_{\text{unresolved}}$) must **never** be pooled into a single fictitious "Undisclosed" monopoly claimant. Concentration indices (Shannon entropy and HHI) are **conditional metrics** computed exclusively over the disclosed population $\mathcal{D}$.

### 2.4 Conditional Concentration Indices
For the set of $K$ distinct disclosed beneficiaries with quantities $u_1, u_2, \dots, u_K$, normalized conditional shares are:
$$p'_k = \frac{u_k}{Q_{\text{disclosed}}} \quad \text{such that} \quad \sum_{k=1}^K p'_k = 1.0$$

#### A. Base-2 Shannon Entropy
Measures information diversity among disclosed buyers:
$$H(X) = - \sum_{k=1}^K p'_k \log_2(p'_k)$$
- **Boundary convention:** $\lim_{p \to 0} p \log_2 p = 0$.
- **Normalized Shannon Equitability ($H_{\text{norm}}$):**
  $$H_{\text{norm}}(X) = \begin{cases} \frac{H(X)}{\log_2(K)} & \text{if } K > 1 \\ 0.0 & \text{if } K \le 1 \end{cases}$$
  Bounded strictly in $[0.0, 1.0]$. $0.0$ signifies monopoly; $1.0$ signifies uniform dispersion.

#### B. Herfindahl-Hirschman Index (HHI)
Measures portfolio concentration on the classical economic scale $[0, 10,000]$:
$$\text{HHI} = \sum_{k=1}^K (100 \cdot p'_k)^2 = 10,000 \sum_{k=1}^K (p'_k)^2$$
- **Normalized HHI ($\text{HHI}^*$):**
  $$\text{HHI}^* = \begin{cases} \frac{\text{HHI} - \frac{10,000}{K}}{10,000 - \frac{10,000}{K}} & \text{if } K > 1 \\ 1.0 & \text{if } K = 1 \\ 0.0 & \text{if } K = 0 \end{cases}$$
  Bounded strictly in $[0.0, 1.0]$.

#### C. Descriptive Concentration Tiers (Hardened from Antitrust Overreach)
To avoid unsubstantiated antitrust liability claims while providing clear categorization, OnceOnly utilizes **descriptive portfolio concentration bands**:
- `SINGLE_LABEL_DOMINANCE`: $K = 1 \lor \text{HHI} \ge 9,999$ (One disclosed label holds 100% of disclosed volume)
- `HIGH_CONCENTRATION`: $\text{HHI} > 2,500$ (Disclosed volume concentrated among few entities)
- `MODERATE_CONCENTRATION`: $1,500 \le \text{HHI} \le 2,500$ (Moderate distribution across claimants)
- `BROAD_DISTRIBUTION`: $500 \le \text{HHI} < 1,500$ (Broad distribution across multiple claimants)
- `HIGH_DISPERSION`: $\text{HHI} < 500$ (High dispersion across numerous small claimants)
- `NOT_CLASSIFIED`: $K = 0$ (Zero disclosed volume available to classify)

---

## 3. Capability B: Batch Fragmentation Methodology

### 3.1 Namespace Isolation & Batch Identity
Batches are identified strictly by the composite namespace:
$$\text{Batch Key} = (\text{registry}, \text{batch\_id})$$
- Serial ranges and batch identifiers from distinct registries (e.g. VCS vs Gold Standard) are **never merged or equated**.
- Within each batch, analysis operates exclusively on retirement records.

### 3.2 Allocation Sizing Dispersion
For batch allocation quantities $Q = \{q_1, q_2, \dots, q_N\}$:
- **Mean Allocation Size:** $\mu = \frac{Q_{\text{total}}}{N}$
- **Median Allocation Size:** Middle value of sorted sequence $q_{(1)} \le \dots \le q_{(N)}$.
- **Sample Standard Deviation ($s$):**
  $$s = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (q_i - \mu)^2} \quad (\text{for } N \ge 2, \text{ else } 0.0)$$
- **Interquartile Range (IQR):** $\text{IQR} = P_{75} - P_{25}$, computed using linear interpolation.

### 3.3 Gini Coefficient of Allocation Sizing
The sample Gini coefficient measures allocation size inequality:
$$G = \frac{2 \sum_{i=1}^N i \cdot q_{(i)}}{N \cdot Q_{\text{total}}} - \frac{N + 1}{N}$$
- **Finite-Sample Corrected Gini ($G^*$):**
  $$G^* = \begin{cases} \frac{N}{N-1} G & \text{if } N > 1 \\ 0.0 & \text{if } N \le 1 \end{cases}$$
- **Bounds:** $G \in [0.0, 1.0]$. $G = 0.0$ indicates perfect tranche equality; $G \to 1.0$ indicates extreme tranche asymmetry.

### 3.4 Micro-Claims vs. Relative Small Allocations (De-Coupled)
In earlier revisions, the heuristic $\tau = \max(10, Q_{\text{batch}} \times 0.01)$ scaled linearly with batch size, resulting in institutional retirement tranches (such as 1,079 t in Batch 10635) being mislabeled as "micro-claims". The methodology strictly separates these concepts:

1. **Absolute Micro-Claims (De Minimis Screening):**
   $$\tau_{\text{micro}} = 10.0 \text{ tonnes}$$
   - Identifies true retail, automated consumer, or sub-tonne credit retirement events.
   - Criterion: $0.0 < q_i \le \tau_{\text{micro}}$. (Non-positive values are excluded).
   - In Batch 10635 ($161,607\text{ t}$), absolute micro-claims = **0**.
2. **Relative Small Allocations (Portfolio Fragmentation):**
   $$\tau_{\text{rel}} = Q_{\text{batch}} \times 0.01 \quad (1\% \text{ of batch volume})$$
   - Identifies allocations that are fractional relative to the batch project size.
   - Criterion: $0.0 < q_i \le \tau_{\text{rel}}$.
   - In Batch 10635, relative small allocations = **7** ($4,107\text{ t}$, including tranches of 320 t, 423 t, 483 t, 550 t, 575 t, 677 t, and 1,079 t).

### 3.5 Interval Structure & Boundary Geometry
Using an efficient $O(N \log N)$ sweep-line algorithm over sorted $(unit\_start, unit\_end)$ intervals, the engine computes:
1. **Interval Validity:** Checks $unit\_start \le unit\_end$ and non-negative bounds.
2. **Interval Span:** $\text{span} = \max(unit\_end) - \min(unit\_start) + 1$.
3. **Interval Density:** $Q_{\text{total}} / \text{span} \in [0.0, 1.0]$.
4. **Exact Duplicates:** Identical start and end boundaries within the batch.
5. **Overlapping Intervals (Collision Events):** Count of allocation intervals colliding with preceding active intervals in sweep-line order.
6. **Pairwise Overlap Count:** Exact count of distinct overlapping interval pairs $(i, j)$ where $i < j$ and $\max(s_i, s_j) \le \min(e_i, e_j)$, computed via active window pruning.
7. **Contiguous Segments:** Adjacent boundaries where $start_{i+1} = current\_max\_end + 1$.
8. **Disjoint Gaps:** Unclaimed voids where $start_{i+1} > current\_max\_end + 1$.

### 3.6 Micro-Batch Inequality vs. Macro Pooled Allocation Gini
The methodology explicitly distinguishes between two different Gini metrics:
1. **Across-Batch Distribution of Within-Batch Ginis:**
   - Evaluates allocation uniformity *within individual credit projects* ($N=725$ batches).
   - Mean within-batch Gini = **0.4924** (median = 0.5361).
   - Measures whether project developers issue credits in uniform tranche blocks.
2. **Macro Pooled Allocation Gini:**
   - Evaluates credit sizing inequality *across the entire 37,335-allocation registry portfolio*.
   - Pooled Gini = **0.9605** ($Q_{\text{pooled}} = 87,668,330\text{ t}$, mean tranche size = $2,348.15\text{ t}$).
   - Reflects the macro reality of carbon markets: high skew between multi-hundred-thousand-tonne bulk institutional retirements and retail micro-claims.

---

## 4. Analytical Invariants & Guardrails

1. **Serial Isolation Invariant:** Serial numbers are never compared across different registries.
2. **Zero-Entropy Convention:** A single beneficiary ($K=1$) has $H(X) = 0.0$ and $H_{\text{norm}} = 0.0$.
3. **No Artificial Inflation:** Adding undisclosed records does not alter conditional disclosed-only HHI or entropy.
4. **Denominator Zero Safety:** Empty inputs or zero-quantity records produce clean zero metrics without NaN or Infinity.
5. **No Fraud Labels:** High Gini or low disclosure rates are presented neutrally as factual statistical distributions.
6. **No Antitrust Overreach:** Tiers avoid competition-law market definition terms (`MONOPOLY`, `HIGHLY_CONCENTRATED`).

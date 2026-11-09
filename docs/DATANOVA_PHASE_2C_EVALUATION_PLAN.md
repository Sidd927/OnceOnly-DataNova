# ONCEONLY — DATANOVA 2026
# PHASE 2C: EVALUATION PLAN — STATISTICAL & TEMPORAL INTELLIGENCE

**Project:** OnceOnly — Carbon Market Integrity Platform  
**Target Competition:** DATANOVA 2026 Global Data-thon  
**Document Type:** Empirical Evaluation Plan & Benchmark Specification  
**Status:** Audit & Pre-Implementation Planning (Phase 2C Stage 1)  
**Author:** Principal Data Scientist & QA Director  
**Date:** 2026-11-09  
**Active Branch:** `datanova/phase-0-baseline`

---

## 1. Overview & Evaluation Philosophy

Phase 2C introduces quantitative, probabilistic, and temporal metrics into OnceOnly. Unlike deterministic serial interval checks (Phase 2B) where an outcome is binary (Overlap vs Disjoint), statistical metrics require **numerical precision, boundary verification, and distribution invariance testing**.

The evaluation methodology is structured around three core pillars:
1. **Mathematical Invariant Verification:** Every metric must strictly respect its theoretical bounds (e.g., $0 \le G \le 1$, $0 \le H \le \log_2 m$, $\text{HHI} \in [10000/m, 10000]$) under all combinations of inputs, including singletons, degenerate distributions, and extreme outliers.
2. **Deterministic Ground-Truth Benchmarks:** Synthetic and curated empirical batches with analytically derived exact values to measure floating-point accuracy and numerical stability.
3. **Domain-Specific Risk Detection Validation:** Realistic market scenarios modeling cartel concentration, smurfing evasion, liquidation dumping, and cross-registry duplication risks with explicit true-positive and false-positive controls.

---

## 2. Benchmark Architecture (`data/benchmarks/statistical_analytics_benchmark.json`)

The evaluation suite will utilize a structured JSON benchmark containing **eight distinct scenario categories**:

```
data/benchmarks/
└── statistical_analytics_benchmark.json   # Ground-truth test scenarios & expected outputs
```

### 2.1 Benchmark Partitioning Strategy
To prevent overfitting during development:
- **Partition A: Unit Test Suite (60%):** Integrated into `backend/tests/test_analytics.py` for continuous regression testing.
- **Partition B: Independent Evaluation Suite (40%):** Evaluated exclusively by `eval/eval_analytics.py` producing versioned audit artifacts in `eval/results/analytics_results.md` and `analytics_results.json`.

---

## 3. Test Scenario Categories & Ground-Truth Specifications

### Scenario 1: Perfect Uniform Dispersion (Baseline Min-Concentration)
- **Input:** 10 claimants, each retiring exactly 1,000 tonnes ($Q_{\text{total}} = 10,000$).
- **Expected Analytical Ground Truth:**
  - $p_i = 0.10$ for all $i \in \{1, \dots, 10\}$.
  - $\text{HHI}_{\text{disclosed}} = 10 \times (100 \times 0.10)^2 = 1,000.0$.
  - $\text{HHI}_{\text{norm}} = \frac{1000 - 1000}{10000 - 1000} = 0.0$.
  - $H(P) = - \sum_{i=1}^{10} 0.10 \log_2(0.10) = \log_2(10) \approx 3.32192809$ bits.
  - $H_{\text{norm}} = 1.0$.
  - $G = 0.0$ (perfect equality).
  - Micro-claims: 0 events, share = 0.0.
  - Risk Flags: None.

### Scenario 2: Monopoly Cornering (Extreme Cartel Concentration)
- **Input:** 1 dominant claimant retiring 95,000 tonnes; 5 minor claimants retiring 1,000 tonnes each ($Q_{\text{total}} = 100,000$).
- **Expected Analytical Ground Truth:**
  - $p_{\text{dom}} = 0.95$, $p_{\text{minor}} = 0.01$.
  - $\text{HHI}_{\text{disclosed}} = (95)^2 + 5 \times (1)^2 = 9025 + 5 = 9,030.0$.
  - $\text{HHI}_{\text{norm}} = \frac{9030 - 1666.67}{10000 - 1666.67} \approx 0.8836$.
  - $H(P) = - [0.95 \log_2(0.95) + 5 \times 0.01 \log_2(0.01)] \approx 0.0703 + 0.3322 \approx 0.4025$ bits.
  - $H_{\text{norm}} = \frac{0.4025}{\log_2(6)} \approx 0.1557$.
  - Gini $G > 0.75$.
  - Risk Flags: `HIGH_BENEFICIARY_CONCENTRATION`.

### Scenario 3: Micro-Claim Smurfing / Evasion (Extreme Sizing Fragmentation)
- **Input:** 1 anchor event of 5,000 tonnes; 500 micro-claim events of 10 tonnes each ($Q_{\text{total}} = 10,000$, $N = 501$).
- **Expected Analytical Ground Truth:**
  - Micro-claim count: 500 events (threshold $\le 10$ t).
  - Micro-claim units: 5,000 tonnes ($50.0\%$ of total volume).
  - Mean event size: $10000 / 501 \approx 19.96$ tonnes.
  - Median event size: $10.0$ tonnes.
  - Gini coefficient $G \approx 0.499$ ($G^* \approx 0.500$).
  - Risk Flags: `ANOMALOUS_MICRO_CLAIM_FRAGMENTATION`.

### Scenario 4: Undisclosed Data Sparsity (Berkeley VROD Dual-Track Emulation)
- **Input:** 10 events totaling 10,000 tonnes.
  - 6 events have `beneficiary = None`, `"Not Disclosed"`, or `"Undisclosed"` totaling 7,000 tonnes ($70\%$).
  - 2 events to "Acme Corp" totaling 2,000 tonnes ($20\%$).
  - 2 events to "Beta LLC" totaling 1,000 tonnes ($10\%$).
- **Expected Analytical Ground Truth:**
  - Total units: 10,000; Disclosed units: 3,000; Unresolved units: 7,000.
  - Coverage ratio $C = 0.30$; Unresolved share $U = 0.70$.
  - Sum invariant: $C + U = 1.0$.
  - Disclosed shares: Acme = $2000/3000 = 66.67\%$, Beta = $1000/3000 = 33.33\%$.
  - $\text{HHI}_{\text{disclosed}} = (66.67)^2 + (33.33)^2 \approx 4444.89 + 1110.89 = 5,555.78$.
  - Invariant: Unresolved volume is NOT factored into $\text{HHI}_{\text{disclosed}}$ as a single entity (which would have yielded an invalid HHI $> 70^2 = 4900$).

### Scenario 5: Rapid Liquidation Burst (Dumping Anomaly)
- **Input:** 50,000 tonnes retired across 8 transactions between 2023-04-10 and 2023-04-12 (timespan = 3 days).
- **Expected Analytical Ground Truth:**
  - Timespan $\Delta T = 3$ days.
  - Burn rate $\mathcal{V} = 50000 / 3 \approx 16,666.67$ tonnes/day.
  - Peak daily volume: $\ge 20,000$ tonnes on single date.
  - `liquidation_burst_flag` = `True`.
  - Risk Flags: `RAPID_LIQUIDATION_BURST`.

### Scenario 6: Dormant Vintage Liquidation
- **Input:** Batch with `vintage = 2014`. All retirements occur on 2024-06-30.
- **Expected Analytical Ground Truth:**
  - Base vintage date: 2014-01-01.
  - Vintage lag: $(2024\text{-}06\text{-}30 - 2014\text{-}01\text{-}01) = 3,833$ calendar days ($\approx 10.5$ years).
  - Minimum, mean, and maximum lag all equal 3,833 days.

### Scenario 7: Cross-Registry Dual-Listing Match (True Positive)
- **Input A (Verra VCS):** Project ID "1477", Name "Rimba Raya Biodiversity Reserve Project", Country "ID", Vintage 2018. Proponent: "InfiniteEARTH".
- **Input B (Gold Standard GS):** Project ID "GS-4089", Name "Rimba Raya Biodiversity Project", Country "ID", Vintage 2018. Proponent: "Infinite Earth Ltd".
- **Expected Analytical Ground Truth:**
  - Project name similarity: $> 0.90$.
  - Country match: `True` ("ID" == "ID").
  - Developer similarity: $> 0.85$.
  - Vintage overlap: `True` (2018 == 2018).
  - Composite confidence $S_{\text{composite}} \ge 0.85$.
  - `potential_duplicate_risk` = `True`.
  - Invariant Check: Serials between VCS and GS are NOT checked or matched.

### Scenario 8: Cross-Registry False Positive Control (True Negative)
- **Input A (Verra VCS):** Project ID "820", Name "Clean Solar Energy Project", Country "IN", Vintage 2020.
- **Input B (Gold Standard GS):** Project ID "GS-1102", Name "Clean Solar Project", Country "CL", Vintage 2016.
- **Expected Analytical Ground Truth:**
  - Project name similarity: $> 0.70$ (shares generic words).
  - Country match: `False` ("IN" != "CL").
  - Vintage overlap: `False` ($|2020 - 2016| = 4 > 1$).
  - Composite confidence $S_{\text{composite}} < 0.60$.
  - `potential_duplicate_risk` = `False`.
  - No false alarm triggered.

---

## 4. Invariant Test Matrix & Acceptance Boundaries

Every test case executed during evaluation must validate the following invariants:

| Category | Invariant Expression | Permissible Range | Failure Condition |
| :--- | :--- | :--- | :--- |
| **Entropy** | $H(P) = -\sum p_i \log_2 p_i$ | $[0, \log_2 m]$ | $H < 0$ or $H > \log_2(m) + 10^{-7}$ |
| **Equitability** | $H_{\text{norm}} = H / \log_2 m$ | $[0.0, 1.0]$ | $H_{\text{norm}} < 0.0$ or $> 1.0$ |
| **HHI** | $\sum (100 \cdot p_i)^2$ | $[10000/m, 10000.0]$ | $\text{HHI} < \frac{10000}{m} - 10^{-4}$ or $> 10000$ |
| **Normalized HHI** | $\text{HHI}_{\text{norm}}$ | $[0.0, 1.0]$ | $\text{HHI}_{\text{norm}} < 0.0$ or $> 1.0$ |
| **Sample Gini** | $G = \frac{2\sum i y_i}{n \sum y} - \frac{n+1}{n}$ | $[0.0, \frac{n-1}{n}]$ | $G < 0.0$ or $G > 1.0$ |
| **Corrected Gini**| $G^* = \frac{n}{n-1} G$ | $[0.0, 1.0]$ | $G^* < 0.0$ or $G^* > 1.0$ |
| **Dual-Track Sum**| $C + U = \frac{Q_{\text{disclosed}} + Q_{\text{unresolved}}}{Q_{\text{total}}}$ | $1.0 \pm 10^{-7}$ | $|C + U - 1.0| > 10^{-7}$ |
| **Velocity** | $\mathcal{V} = Q_{\text{total}} / \Delta T$ | $[0.0, \infty)$ | $\mathcal{V} < 0.0$ or $\Delta T < 1$ |
| **Serial Isolation**| $\text{Serials}(A) \cap \text{Serials}(B)$ | $\emptyset$ (Never evaluated) | Any cross-registry serial collision raised |

---

## 5. Evaluation Harness Design (`eval/eval_analytics.py`)

The evaluation script `eval/eval_analytics.py` will execute the evaluation protocol:

```python
"""Phase 2C Statistical and Temporal Analytics Evaluation Harness."""
import json
import time
from pathlib import Path
from typing import Dict, Any, List

def run_evaluation(benchmark_path: Path) -> Dict[str, Any]:
    """Execute analytical scenarios and verify invariants against ground truth."""
    ...
```

### Reporting Outputs:
1. **JSON Output (`eval/results/analytics_results.json`):** Machine-readable evaluation report containing:
   - Total scenarios evaluated.
   - Pass/fail status per scenario.
   - Mean Absolute Error (MAE) and Max Absolute Error across all continuous metrics.
   - Invariant violation count (must be exactly 0).
   - Execution benchmark latency (total and per-batch).
2. **Markdown Summary (`eval/results/analytics_results.md`):** Executive report formatted for inclusion in submission documentation, including accuracy tables, confusion matrices for risk detection, and execution time charts.

---

## 6. Success Criteria & Hardening Targets

The Phase 2C evaluation will be deemed successful only if:
1. **Invariant Integrity:** 100% of mathematical invariants hold across all synthetic and empirical batches. Zero violations permitted.
2. **Numerical Precision:** $\text{MAE} \le 10^{-5}$ across all benchmark metrics when compared to analytical closed-form solutions.
3. **True Positive Rate (Risk Flags):** $100\%$ detection of monopoly concentration, micro-claim smurfing, and rapid liquidation bursts in benchmark scenarios.
4. **False Positive Rate (Controls):** $0\%$ false positive alerts on uniform dispersion, balanced batches, and cross-registry negative controls.
5. **Execution Latency:** Sub-millisecond calculation ($< 1.0\text{ ms}$) per batch of up to 1,000 events on standard developer hardware.
6. **Zero External Dependencies:** Verified that all calculations execute via standard Python libraries (`math`, `statistics`, `datetime`, `collections`).


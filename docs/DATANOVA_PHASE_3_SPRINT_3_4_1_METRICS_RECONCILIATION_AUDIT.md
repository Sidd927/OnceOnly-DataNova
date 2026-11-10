# Sprint 3.4.1: Population Metrics Reconciliation Audit

| | |
|---|---|
| Date | 2026-11-10 |
| Code base | `datanova/phase-0-baseline` at `bf08180` (before this audit's fixes) |
| Reference DB | `var/registry_demo.sqlite`, materialized from `data/reference/demo_subset.csv.gz` |
| Reference DB SHA-256 | `35f5bdd9c5f1ee391656b47d80af2b52dda2efc65962a5676baef5d12005ebbd` |

The DB SHA-256 is for the materialized SQLite file on this machine. The file's bytes can change if it is rebuilt; the row content is pinned by the tests below.

## 1. Verdict

**The frozen Stage 1 figures are correct.** They are reproduced exactly by:

- the current engine;
- the live API, at its serialized precision;
- an independent SQL recomputation that imports no application code.

**The Sprint 3.4 report's figures for HHI, entropy, equitability and the Telstra volume cannot be produced by any code path in the repository.** No backend calculation, API response, TypeScript transformation or rendered value yields 215.17, 9.37 bits, 0.706 or 3,767,118 t. They are report errors.

The report's `bf08180` commit changed no backend file, and the UI renders these values directly from the API.

The trace did uncover **four genuine defects**, which are now fixed (§4):

1. The API serialization zeroed most beneficiary shares.
2. The Lorenz charts displayed a Gini computed over a different population.
3. A hard-coded metric fallback.
4. Wrong hard-coded batch-preset statistics.

There was also a minor off-by-one in the Lorenz deciles.

## 2. Reproduced values

| Metric | Frozen Stage 1 | Engine (full precision) | Independent SQL | API (serialized) | Sprint 3.4 report |
|---|---:|---:|---:|---:|---:|
| Retirement records | 37,335 | 37,335 | 37,335 | 37,335 | 37,335 |
| Disclosed volume (t) | 35,172,359 | 35,172,359 | 35,172,359 | 35,172,359 | (not stated) |
| Unique disclosed labels K | 9,933 | 9,933 | 9,933 | 9,933 | 9,933 |
| HHI (0–10,000) | 245.6410 | 245.6410035 | 245.6410 | 245.64 | **215.17** |
| Normalized HHI | 0.024466 | 0.0244659 | n/a | 0.0245 | n/a |
| Shannon entropy (bits) | 7.5166 | 7.5165817 | 7.5166 | 7.5166 | **9.37** |
| Equitability H / log₂K | 0.5661 | 0.5660923 | 0.5661 | 0.5661 | **0.706** |
| Dominant label | Telstra Corporation Limited | same | same | same | same |
| Telstra volume (t) | 3,766,034 | 3,766,034 | 3,766,034 | 3,766,045 † | **3,767,118** |
| Top-3 share | 23.13 % | 23.129 % | 23.129 % | 0.2313 | 23.13 % |
| Pooled allocation Gini | 0.960471 | 0.9604714 | 0.960471 | 0.9605 | ≈ 0.9605 |
| Mean within-batch Gini | 0.492445 | 0.4924454 | 0.492445 | 0.4924 | ≈ 0.4924 |
| Top 1 % of labels' volume share | n/a | 74.56 % | n/a | n/a | **48.2 %** |
| Bottom 80 % of labels' volume share | n/a | 0.418 % | n/a | n/a | 0.41 % |

† Before the fix, the UI derived Telstra's volume as `share × disclosed_units` from a share rounded to 6 decimals, which gives 3,766,045. After the fix, shares are unrounded and the UI shows 3,766,034.

## 3. Definitions verified

These definitions were verified in `backend/app/analytics/concentration.py`, `fragmentation.py` and `engine.py`, and match the Stage 1 methodology.

| Item | Definition |
|---|---|
| Population | `records.kind = 'retirement'` (37,335 rows). The 669 issuance rows are excluded. Both registries are included; there is no registry filter |
| Beneficiary classes | `EXPLICITLY_UNDISCLOSED`: null, empty, or none / null / not disclosed / undisclosed / unknown / n/a / na / unspecified (case-insensitive). `INVALID_OR_PLACEHOLDER`: `_`, `test`, `test _ num. ord cliente`. Everything else is `NON_PLACEHOLDER_DISCLOSED` |
| Label key | The disclosed label with surrounding whitespace trimmed only. No case folding and no entity resolution, so label counts are *labels*, not legal entities. Records with quantity ≤ 0 are skipped |
| Shares | pₖ = qₖ / Σ disclosed q. Undisclosed volume is excluded from the denominator |
| HHI | 10,000 · Σ pₖ² |
| Normalized HHI | (HHI − 10,000/K) / (10,000 − 10,000/K) |
| Entropy | H = −Σ pₖ log₂ pₖ, in bits |
| Equitability | H / log₂ K |
| Pooled allocation Gini | Gini over all 37,335 retirement quantities, including undisclosed ones |
| Mean within-batch Gini | Unweighted mean, over 725 `(registry, batch_id)` batches, of each batch's allocation-size Gini |
| Lorenz curve (UI) | Ascending sort of the disclosed label shares, cumulative share against cumulative label fraction, endpoints (0,0) and (1,1) |

**Sensitivity check.** I tested whether the Sprint 3.4 numbers could come from a different label policy:

| Label policy | K | HHI | H |
|---|---:|---:|---:|
| Case-folding | 9,865 | 250.82 | 7.4659 |
| NFKC + whitespace + case-folding | 9,864 | 250.82 | 7.4658 |

Telstra appears under exactly **one** label in the population, so aggregation variants cannot produce 3,767,118. None of the variants comes near 215.17 or 9.37 bits.

## 4. Defects found and corrected

| # | Defect | Evidence | Fix | Test |
|---|---|---|---|---|
| D1 | `ConcentrationMetrics.to_dict` rounded `disclosed_shares` to 6 decimals. 6,307 of 9,933 labels serialized as exactly `0.0` | The Lorenz chart (which filters `> 0`) plotted 3,626 labels. Its computed Gini was 0.933 against the true 0.975 | Serialize shares unrounded (`backend/app/analytics/models.py`). Headline metrics keep their existing rounding. No methodology change | `test_api_serializes_every_disclosed_share_without_zeroing` |
| D2 | The Lorenz charts used `giniOverride`, labelling a curve of **beneficiary-label shares** (disclosed volume only) with the **pooled allocation Gini** (all 37,335 allocations). The batch-level chart did the same with the batch allocation Gini | `Observatory.tsx` | Override removed. The chart shows the Gini of the plotted distribution, and the subtitles state the population and that it differs from the pooled Gini. The hard-coded "9,933" and the incorrect "against total retired volume" were replaced with live values and "disclosed volume" | Build and lint; Playwright |
| D3 | Hard-coded fallback `?? "0.4924"` for the mean within-batch Gini | `Observatory.tsx:498` | The UI renders "Unavailable" when the value is absent | Frontend sweep (§5) |
| D4 | Batch preset descriptions contained hard-coded statistics. Three of the four Gini values were wrong: Istanbul 0.8872 (actual 0.9260), Kinnaur 0.9654 (actual 0.8383), DDWL 0.7410 (actual 0.9036) | `AnalyticsEngine.analyze_batch(...)` | Presets now carry identifiers and project descriptions only. All figures come from the batch API after selection | Build and lint |
| D5 | Lorenz decile shares summed `floor(p·n) + 1` observations | `LorenzCurveChart.tsx` | Sum the first `floor(p·n)` observations | Build and lint |

Other literals removed in the same sweep:

- Observatory: "37,335 verified retirement records" now comes from the API; "669 issuance records" is now a generic statement.
- `ComparativePacingChart.tsx`: the hard-coded "669 issuances" is now generic.
- `CrossRegistry.tsx`: per-registry tiles that displayed `0 t` when statistics were missing now show "Unavailable".

## 5. Traceability summary

| Layer | Finding |
|---|---|
| SQLite | Counts by kind and registry: retirement VCS 30,111 (79,964,179 t), GS 7,224 (7,704,151 t); issuance VCS 669 |
| Engine | `AnalyticsEngine.analyze_population_summary()` reproduces the Stage 1 figures (above) |
| API | `GET /api/analytics/population/summary` rounds headline metrics to 2 or 4 decimals. Before the fix it rounded shares to 6 decimals (D1) |
| TypeScript types | `frontend/src/api/analytics.ts` mirrors the fields. No transformation |
| UI | HHI is rounded to an integer, entropy to 2 decimals, equitability to 3 decimals; percentages come from shares. Defects D2–D5 were in this layer |
| Sprint 3.4 report | Four figures do not trace to any layer. A dated erratum has been appended to the report; the original text is preserved |

## 6. Reproduction

```bash
# Engine
cd backend && ../.venv/bin/python -c "from app.analytics import AnalyticsEngine as E; s=E.analyze_population_summary(); c=s.overall_concentration; print(c.hhi_disclosed, c.entropy_shannon_disclosed, c.entropy_normalized, c.unique_disclosed_beneficiaries, s.pooled_allocation_gini, s.batch_gini_distribution['mean'])"

# Regression tests (pin the accepted values and the serialization)
cd backend && ../.venv/bin/python -m pytest -q tests/test_population_metrics_reconciliation.py
```

The independent recomputation used a standalone script with no application imports. It applies the definitions in §3 directly to `SELECT registry, batch_id, quantity, beneficiary FROM records WHERE kind='retirement'`; its outputs are the "Independent SQL" column.

## 7. Methodology status

No threshold, formula, population definition or classification was changed. The fixes affect only:

- serialization precision of a display input (D1);
- the frontend's labelling and presentation (D2–D5).

The frozen Stage 1 values remain authoritative and are now pinned by `backend/tests/test_population_metrics_reconciliation.py`.

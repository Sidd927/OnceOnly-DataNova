"""Allocation size dispersion, Gini coefficient, interval structure, and batch fragmentation analytics."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .concentration import classify_beneficiary
from .models import (
    BatchIntervalStructure,
    BeneficiaryCategory,
    FragmentationMetrics,
)


def calculate_gini_coefficient(quantities: Sequence[Union[int, float]]) -> float:
    """Calculate the sample Gini coefficient of inequality for allocation sizes.

    G = (2 * sum(i * y_i) / (n * sum(y))) - ((n + 1) / n)
    where y is sorted in ascending order (1-indexed).
    Ranges from 0.0 (perfect equality) to (n-1)/n (maximal inequality).
    """
    if not quantities:
        return 0.0

    vals = sorted([float(x) for x in quantities if x > 0])
    n = len(vals)
    if n <= 1:
        return 0.0

    total = sum(vals)
    if total <= 0.0:
        return 0.0

    weighted_sum = sum((i + 1) * y for i, y in enumerate(vals))
    gini = (2.0 * weighted_sum) / (n * total) - (n + 1.0) / n
    return max(0.0, min(1.0, gini))


def calculate_gini_sample_corrected(gini: float, n: int) -> float:
    """Calculate finite-sample corrected Gini coefficient: G* = (n / (n - 1)) * G."""
    if n <= 1:
        return 0.0
    corrected = (float(n) / float(n - 1)) * gini
    return max(0.0, min(1.0, corrected))


def calculate_median(values: Sequence[float]) -> float:
    """Compute exact median of a list of floats."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def calculate_percentile(sorted_vals: Sequence[float], p: float) -> float:
    """Compute p-th percentile (0 <= p <= 1) with linear interpolation."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    idx = p * (n - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    weight = idx - lo
    return (1.0 - weight) * sorted_vals[lo] + weight * sorted_vals[hi]


def analyze_interval_structure(
    records: Sequence[Dict[str, Any]],
    total_units: float = 0.0,
) -> BatchIntervalStructure:
    """Analyze interval structure, overlaps, exact duplicates, and contiguous segments for a batch.

    Uses an efficient O(N log N) sweep-line algorithm over sorted intervals.
    Never compares numerical serial ranges across registries.
    """
    extracted_intervals: List[Tuple[int, int]] = []
    has_invalid = False

    for r in records:
        if "unit_start" in r and "unit_end" in r and r["unit_start"] is not None and r["unit_end"] is not None:
            try:
                s = int(r["unit_start"])
                e = int(r["unit_end"])
                if s > e or s < 0 or e < 0:
                    has_invalid = True
                else:
                    extracted_intervals.append((s, e))
            except (ValueError, TypeError):
                has_invalid = True

    n = len(extracted_intervals)
    if n == 0:
        return BatchIntervalStructure(
            total_intervals=0,
            min_unit_start=None,
            max_unit_end=None,
            interval_span=None,
            interval_density=0.0,
            exact_duplicate_intervals_count=0,
            overlapping_intervals_count=0,
            contiguous_intervals_count=0,
            disjoint_gaps_count=0,
            has_invalid_intervals=has_invalid,
        )

    # Sort intervals by (unit_start, unit_end)
    sorted_ints = sorted(extracted_intervals, key=lambda x: (x[0], x[1]))
    min_s = sorted_ints[0][0]
    max_e = max(e for _, e in sorted_ints)
    span = max_e - min_s + 1

    density = (total_units / span) if span > 0 else 0.0

    exact_duplicates = 0
    overlaps = 0
    pairwise_overlaps = 0
    contiguous = 0
    gaps = 0

    current_max_end = sorted_ints[0][1]

    # Collision events sweep
    for i in range(1, n):
        prev_s, prev_e = sorted_ints[i - 1]
        curr_s, curr_e = sorted_ints[i]

        if prev_s == curr_s and prev_e == curr_e:
            exact_duplicates += 1

        if curr_s <= current_max_end:
            overlaps += 1
        elif curr_s == current_max_end + 1:
            contiguous += 1
        elif curr_s > current_max_end + 1:
            gaps += 1

        if curr_e > current_max_end:
            current_max_end = curr_e

    # Exact pairwise overlaps: count pairs (i, j) with i < j where s_j <= e_i
    for i in range(n):
        curr_s, curr_e = sorted_ints[i]
        for j in range(i + 1, n):
            next_s, next_e = sorted_ints[j]
            if next_s <= curr_e:
                pairwise_overlaps += 1
            else:
                # Since sorted by start, all subsequent intervals have next_s_k >= next_s > curr_e
                break

    return BatchIntervalStructure(
        total_intervals=n,
        min_unit_start=min_s,
        max_unit_end=max_e,
        interval_span=span,
        interval_density=max(0.0, min(1.0, density)),
        exact_duplicate_intervals_count=exact_duplicates,
        overlapping_intervals_count=overlaps,
        pairwise_overlap_count=pairwise_overlaps,
        contiguous_intervals_count=contiguous,
        disjoint_gaps_count=gaps,
        has_invalid_intervals=has_invalid,
    )


def evaluate_batch_fragmentation(
    records: Sequence[Dict[str, Any]],
    registry: Optional[str] = None,
    batch_id: Optional[str] = None,
    project_id: Optional[str] = None,
    micro_threshold: float = 10.0,
) -> FragmentationMetrics:
    """Compute comprehensive batch fragmentation metrics, sizing dispersion, and interval structure.

    Parameters
    ----------
    records : Sequence[Dict[str, Any]]
        List of retirement records within the batch.
    registry : Optional[str]
        Registry namespace (e.g. 'VCS', 'GS').
    batch_id : Optional[str]
        Batch identifier within the registry.
    project_id : Optional[str]
        Project identifier if available.
    micro_threshold : float
        Absolute threshold in tonnes for identifying micro-claims (default 10.0).

    Returns
    -------
    FragmentationMetrics
        Immutable container with Gini, quantiles, dispersion, and micro-claim indicators.
    """
    quantities: List[float] = []
    class_counts: Dict[str, int] = defaultdict(int)
    class_quantities: Dict[str, float] = defaultdict(float)
    disclosed_beneficiaries = set()

    for item in records:
        if "quantity" in item and item["quantity"] is not None:
            q = float(item["quantity"])
        elif "unit_start" in item and "unit_end" in item and item["unit_start"] is not None and item["unit_end"] is not None:
            q = float(int(item["unit_end"]) - int(item["unit_start"]) + 1)
        else:
            q = 0.0

        if q < 0.0:
            q = 0.0

        quantities.append(q)

        # Beneficiary classification
        ben = item.get("beneficiary") if "beneficiary" in item else item.get("claimant")
        cat = classify_beneficiary(ben)
        class_counts[cat.value] += 1
        class_quantities[cat.value] += q

        if cat == BeneficiaryCategory.NON_PLACEHOLDER_DISCLOSED and ben:
            disclosed_beneficiaries.add(str(ben).strip())

    n = len(quantities)
    total_units = sum(quantities)

    # Calculate record and quantity shares by classification
    class_rec_shares = {k: (v / n if n > 0 else 0.0) for k, v in class_counts.items()}
    class_qty_shares = {k: (v / total_units if total_units > 0 else 0.0) for k, v in class_quantities.items()}

    # Interval structure analysis
    interval_struct = analyze_interval_structure(records, total_units=total_units)

    if n == 0 or total_units <= 0.0:
        return FragmentationMetrics(
            total_events=n,
            total_units=total_units,
            gini_coefficient=0.0,
            gini_sample_corrected=0.0,
            mean_event_size=0.0,
            median_event_size=0.0,
            min_event_size=0.0,
            max_event_size=0.0,
            p25_event_size=0.0,
            p75_event_size=0.0,
            std_dev_event_size=0.0,
            iqr_event_size=0.0,
            micro_claim_count=0,
            micro_claim_units=0.0,
            micro_claim_record_share=0.0,
            micro_claim_quantity_share=0.0,
            micro_claim_threshold_used=micro_threshold,
            small_tranche_count=0,
            small_tranche_units=0.0,
            small_tranche_record_share=0.0,
            small_tranche_quantity_share=0.0,
            small_tranche_threshold_used=0.0,
            classification_counts=dict(class_counts),
            classification_quantities=dict(class_quantities),
            classification_record_shares=class_rec_shares,
            classification_quantity_shares=class_qty_shares,
            distinct_disclosed_beneficiaries=len(disclosed_beneficiaries),
            intervals=interval_struct,
        )

    mean_val = total_units / n
    sorted_q = sorted(quantities)
    median_val = calculate_median(sorted_q)
    min_val = sorted_q[0]
    max_val = sorted_q[-1]

    # Sample standard deviation (N >= 2 else 0.0)
    if n >= 2:
        variance = sum((x - mean_val) ** 2 for x in sorted_q) / (n - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0

    # Quartiles and IQR
    q25 = calculate_percentile(sorted_q, 0.25)
    q75 = calculate_percentile(sorted_q, 0.75)
    iqr = q75 - q25

    # Gini coefficients
    raw_gini = calculate_gini_coefficient(quantities)
    corrected_gini = calculate_gini_sample_corrected(raw_gini, n)

    # Absolute de minimis micro-claims: 0 < q <= micro_threshold (default 10.0 tonnes)
    micro_items = [q for q in quantities if 0.0 < q <= micro_threshold]
    micro_count = len(micro_items)
    micro_units = sum(micro_items)
    micro_rec_share = (micro_count / n) if n > 0 else 0.0
    micro_qty_share = (micro_units / total_units) if total_units > 0 else 0.0

    # Relative small allocations: 0 < q <= 1% of total batch volume
    small_tranche_threshold = total_units * 0.01
    small_tranche_items = [q for q in quantities if 0.0 < q <= small_tranche_threshold]
    small_tranche_count = len(small_tranche_items)
    small_tranche_units = sum(small_tranche_items)
    small_tranche_rec_share = (small_tranche_count / n) if n > 0 else 0.0
    small_tranche_qty_share = (small_tranche_units / total_units) if total_units > 0 else 0.0

    return FragmentationMetrics(
        total_events=n,
        total_units=total_units,
        gini_coefficient=raw_gini,
        gini_sample_corrected=corrected_gini,
        mean_event_size=mean_val,
        median_event_size=median_val,
        min_event_size=min_val,
        max_event_size=max_val,
        p25_event_size=q25,
        p75_event_size=q75,
        std_dev_event_size=std_dev,
        iqr_event_size=iqr,
        micro_claim_count=micro_count,
        micro_claim_units=micro_units,
        micro_claim_record_share=micro_rec_share,
        micro_claim_quantity_share=micro_qty_share,
        micro_claim_threshold_used=micro_threshold,
        small_tranche_count=small_tranche_count,
        small_tranche_units=small_tranche_units,
        small_tranche_record_share=small_tranche_rec_share,
        small_tranche_quantity_share=small_tranche_qty_share,
        small_tranche_threshold_used=small_tranche_threshold,
        classification_counts=dict(class_counts),
        classification_quantities=dict(class_quantities),
        classification_record_shares=class_rec_shares,
        classification_quantity_shares=class_qty_shares,
        distinct_disclosed_beneficiaries=len(disclosed_beneficiaries),
        intervals=interval_struct,
    )

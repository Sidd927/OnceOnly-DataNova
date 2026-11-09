"""Deterministic interval mathematics and geometric overlap calculations."""
from __future__ import annotations

from .models import IntervalOverlap, OverlapType


def compute_interval_overlap(
    s_c: int,
    e_c: int,
    s_e: int,
    e_e: int,
    same_namespace: bool = True,
) -> IntervalOverlap:
    """Compute exact quantitative overlap metrics between candidate [s_c, e_c] and existing [s_e, e_e]."""
    if s_c > e_c:
        raise ValueError(f"Invalid candidate interval: start ({s_c}) > end ({e_c})")
    if s_e > e_e:
        raise ValueError(f"Invalid existing interval: start ({s_e}) > end ({e_e})")

    q_c = e_c - s_c + 1
    q_e = e_e - s_e + 1

    # Different namespace -> no overlap possible
    if not same_namespace:
        return IntervalOverlap(
            overlap_type=OverlapType.NO_OVERLAP.value,
            overlap_start=None,
            overlap_end=None,
            overlap_units=0,
            candidate_units=q_c,
            existing_units=q_e,
            pct_of_candidate=0.0,
            pct_of_existing=0.0,
            is_conflict=False,
        )

    lo = max(s_c, s_e)
    hi = min(e_c, e_e)

    if lo <= hi:
        # Genuine overlap detected
        overlap_units = hi - lo + 1
        pct_c = (overlap_units / q_c) * 100.0
        pct_e = (overlap_units / q_e) * 100.0

        if s_c == s_e and e_c == e_e:
            otype = OverlapType.EXACT_OVERLAP.value
        elif s_e <= s_c and e_c <= e_e:
            otype = OverlapType.CONTAINMENT.value
        elif s_c <= s_e and e_e <= e_c:
            otype = OverlapType.SUPERSET.value
        else:
            otype = OverlapType.PARTIAL_OVERLAP.value

        return IntervalOverlap(
            overlap_type=otype,
            overlap_start=lo,
            overlap_end=hi,
            overlap_units=overlap_units,
            candidate_units=q_c,
            existing_units=q_e,
            pct_of_candidate=pct_c,
            pct_of_existing=pct_e,
            is_conflict=True,
        )
    else:
        # Non-overlapping: check if adjacent (abutting)
        if e_c + 1 == s_e or e_e + 1 == s_c:
            otype = OverlapType.ADJACENT.value
        else:
            otype = OverlapType.DISJOINT.value

        return IntervalOverlap(
            overlap_type=otype,
            overlap_start=None,
            overlap_end=None,
            overlap_units=0,
            candidate_units=q_c,
            existing_units=q_e,
            pct_of_candidate=0.0,
            pct_of_existing=0.0,
            is_conflict=False,
        )


def validate_disjoint_ranges(ranges: list[tuple[int, int]]) -> tuple[bool, str | None]:
    """Verify that a set of ranges in the same namespace contains no internal self-overlaps."""
    if len(ranges) <= 1:
        return True, None

    sorted_ranges = sorted(ranges, key=lambda r: (r[0], r[1]))
    for i in range(len(sorted_ranges) - 1):
        curr = sorted_ranges[i]
        nxt = sorted_ranges[i + 1]
        if curr[1] >= nxt[0]:
            return False, f"Self-overlapping range detected: [{curr[0]}-{curr[1]}] overlaps [{nxt[0]}-{nxt[1]}]"

    return True, None

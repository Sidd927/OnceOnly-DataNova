"""Allocation-aware reconciliation and split interval subsystem for OnceOnly."""
from __future__ import annotations

from .engine import AllocationReconciler
from .intervals import compute_interval_overlap, validate_disjoint_ranges
from .models import (
    AllocationType,
    ClaimReconciliationReport,
    IntervalOverlap,
    OverlapType,
    ReconciliationItem,
)

__all__ = [
    "AllocationReconciler",
    "AllocationType",
    "ClaimReconciliationReport",
    "IntervalOverlap",
    "OverlapType",
    "ReconciliationItem",
    "compute_interval_overlap",
    "validate_disjoint_ranges",
]


"""Data models for interval reconciliation, overlap classification, and allocation analysis."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class OverlapType(str, Enum):
    """Geometric relationship between two serial unit intervals."""
    NO_OVERLAP = "NO_OVERLAP"
    EXACT_OVERLAP = "EXACT_OVERLAP"
    EXACT_DUPLICATE = "EXACT_OVERLAP"  # Backward-compatible alias
    CONTAINMENT = "CONTAINMENT"
    SUPERSET = "SUPERSET"
    PARTIAL_OVERLAP = "PARTIAL_OVERLAP"
    ADJACENT = "ADJACENT"
    DISJOINT = "DISJOINT"


class AllocationType(str, Enum):
    """Categorization of allocation scenarios combining interval overlap and entity identity."""
    # Section 5 primary classifications
    LEGITIMATE_SPLIT = "LEGITIMATE_SPLIT"
    ALLOCATION_CONFLICT = "ALLOCATION_CONFLICT"
    INTERMEDIARY_ATTRIBUTION = "INTERMEDIARY_ATTRIBUTION"
    UNRESOLVED_BENEFICIARY = "UNRESOLVED_BENEFICIARY"
    CROSS_NAMESPACE = "CROSS_NAMESPACE"

    # Granular behavioral sub-classifications
    SAME_UNITS_SAME_CLAIMANT = "SAME_UNITS_SAME_CLAIMANT"
    SAME_UNITS_RELATED_CLAIMANTS = "SAME_UNITS_RELATED_CLAIMANTS"
    SAME_UNITS_UNRELATED_CLAIMANTS = "SAME_UNITS_UNRELATED_CLAIMANTS"
    DIFFERENT_UNITS_SAME_CLAIMANT = "DIFFERENT_UNITS_SAME_CLAIMANT"
    DIFFERENT_UNITS_DIFFERENT_CLAIMANTS = "DIFFERENT_UNITS_DIFFERENT_CLAIMANTS"


@dataclass(frozen=True)
class IntervalOverlap:
    """Exact quantitative overlap metrics between two serial unit ranges."""
    overlap_type: str
    overlap_start: int | None
    overlap_end: int | None
    overlap_units: int
    candidate_units: int
    existing_units: int
    pct_of_candidate: float
    pct_of_existing: float
    is_conflict: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "overlap_type": self.overlap_type,
            "overlap_start": self.overlap_start,
            "overlap_end": self.overlap_end,
            "overlap_units": self.overlap_units,
            "candidate_units": self.candidate_units,
            "existing_units": self.existing_units,
            "pct_of_candidate": round(self.pct_of_candidate, 2),
            "pct_of_existing": round(self.pct_of_existing, 2),
            "is_conflict": self.is_conflict,
        }


@dataclass
class ReconciliationItem:
    """Detailed reconciliation result for a candidate block against an active range."""
    candidate_block_idx: int
    candidate_range: tuple[int, int]
    candidate_claimant: str
    prior_claim_id: int | None
    prior_claim_ref: str | None
    prior_claimant: str | None
    prior_range: tuple[int, int]
    prior_status: str | None
    registry: str
    batch_id: str
    overlap: IntervalOverlap
    allocation_type: str
    entity_match_tier: str
    entity_relationship: str
    explanation: str
    audit_recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_block_idx": self.candidate_block_idx,
            "candidate_range": list(self.candidate_range),
            "candidate_claimant": self.candidate_claimant,
            "prior_claim_id": self.prior_claim_id,
            "prior_claim_ref": self.prior_claim_ref,
            "prior_claimant": self.prior_claimant,
            "prior_range": list(self.prior_range),
            "prior_status": self.prior_status,
            "namespace": f"{self.registry}:{self.batch_id}",
            "overlap": self.overlap.to_dict(),
            "allocation_type": self.allocation_type,
            "entity_match_tier": self.entity_match_tier,
            "entity_relationship": self.entity_relationship,
            "explanation": self.explanation,
            "audit_recommendation": self.audit_recommendation,
        }


@dataclass
class ClaimReconciliationReport:
    """Comprehensive multi-block reconciliation report for an entire claim."""
    claim_id: int
    claimant: str
    total_blocks: int
    total_units: int
    has_conflicts: bool
    conflict_count: int
    items: list[ReconciliationItem] = field(default_factory=list)
    split_allocations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claimant": self.claimant,
            "total_blocks": self.total_blocks,
            "total_units": self.total_units,
            "has_conflicts": self.has_conflicts,
            "conflict_count": self.conflict_count,
            "items": [item.to_dict() for item in self.items],
            "split_allocations": self.split_allocations,
        }

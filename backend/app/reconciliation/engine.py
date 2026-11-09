"""Allocation-aware reconciliation engine integrating interval mathematics and entity resolution."""
from __future__ import annotations

from typing import Any

from app.entity_resolution import EntityResolutionEngine, MatchResult

from .intervals import compute_interval_overlap, validate_disjoint_ranges
from .models import (
    AllocationType,
    ClaimReconciliationReport,
    IntervalOverlap,
    OverlapType,
    ReconciliationItem,
)


class AllocationReconciler:
    """Reconciles carbon unit ranges against existing claims with allocation and entity awareness."""

    @classmethod
    def reconcile_allocation_pair(
        cls,
        alloc_a: dict[str, Any],
        alloc_b: dict[str, Any],
        block_idx: int = 0,
    ) -> ReconciliationItem:
        """Compare candidate allocation (A) against existing allocation (B)."""
        reg_a = (alloc_a.get("registry") or "").strip().upper()
        reg_b = (alloc_b.get("registry") or "").strip().upper()
        batch_a = str(alloc_a.get("batch_id") or "").strip()
        batch_b = str(alloc_b.get("batch_id") or "").strip()

        s_a = int(alloc_a["unit_start"])
        e_a = int(alloc_a["unit_end"])
        s_b = int(alloc_b["unit_start"])
        e_b = int(alloc_b["unit_end"])

        claimant_a = str(alloc_a.get("claimant") or "").strip()
        claimant_b = str(alloc_b.get("claimant") or "").strip()

        # 1. Namespace validation
        same_namespace = (reg_a == reg_b and batch_a == batch_b and bool(reg_a) and bool(batch_a))
        if not same_namespace:
            overlap = compute_interval_overlap(s_a, e_a, s_b, e_b, same_namespace=False)
            return ReconciliationItem(
                candidate_block_idx=block_idx,
                candidate_range=(s_a, e_a),
                candidate_claimant=claimant_a,
                prior_claim_id=alloc_b.get("claim_id"),
                prior_claim_ref=alloc_b.get("claim_ref"),
                prior_claimant=claimant_b,
                prior_range=(s_b, e_b),
                prior_status=alloc_b.get("status"),
                registry=reg_a,
                batch_id=batch_a,
                overlap=overlap,
                allocation_type=AllocationType.CROSS_NAMESPACE.value,
                entity_match_tier="N/A",
                entity_relationship="CROSS_NAMESPACE",
                explanation=f"Allocations belong to different namespaces ({reg_a}:{batch_a} vs {reg_b}:{batch_b}). Serial units are distinct and non-conflicting.",
                audit_recommendation="No action required: distinct unit inventories.",
            )

        # 2. Geometric Interval Overlap Computation
        overlap = compute_interval_overlap(s_a, e_a, s_b, e_b, same_namespace=True)

        # 3. Entity Resolution Analysis
        entity_res: MatchResult = EntityResolutionEngine.resolve_pair(claimant_a, claimant_b)
        is_pool = bool(entity_res.intermediary_context and entity_res.intermediary_context.role == "CUSTOMER_POOL")
        is_placeholder = (
            entity_res.entity_a.is_placeholder
            or entity_res.entity_b.is_placeholder
            or entity_res.relationship_type == "UNRESOLVED"
            or is_pool
        )
        is_same = (entity_res.is_match and entity_res.relationship_type in ("EXACT_MATCH", "CANONICAL_VARIANT"))
        is_related = (entity_res.is_match and entity_res.relationship_type == "CORPORATE_HIERARCHY_OR_SUBSIDIARY")
        is_intermediary = (entity_res.relationship_type == "INTERMEDIARY_DELEGATION")

        q_a = e_a - s_a + 1
        q_b = e_b - s_b + 1
        claim_ref_b = alloc_b.get("claim_ref") or "prior record"
        ns_str = f"{reg_a}:{batch_a}"

        # 4. Multi-Dimensional Allocation Classification
        if not overlap.is_conflict:
            # NON-OVERLAPPING CASES (Units are distinct)
            if is_placeholder:
                alloc_type = AllocationType.UNRESOLVED_BENEFICIARY.value
                explanation = (
                    f"Non-overlapping allocation [{s_a:,}-{e_a:,}] in batch {batch_a}, but beneficial ownership is undisclosed or ambiguous."
                )
                rec = "Verify downstream allocation assignment from retiring account holder."
            elif is_same:
                alloc_type = AllocationType.DIFFERENT_UNITS_SAME_CLAIMANT.value
                explanation = (
                    f"Same claimant '{claimant_a}' holds multiple distinct allocations in batch {batch_a} "
                    f"([{s_a:,}-{e_a:,}] and [{s_b:,}-{e_b:,}], {overlap.overlap_type.lower()}). Legitimate multi-tranche claim."
                )
                rec = "Verify combined quantity matches claimant's total offset disclosure."
            else:
                # Legitimate split allocation across distinct entities
                alloc_type = AllocationType.LEGITIMATE_SPLIT.value
                explanation = (
                    f"Legitimate split allocation in batch {batch_a}: claimant '{claimant_a}' [{s_a:,}-{e_a:,}] ({q_a:,} units) "
                    f"and claimant '{claimant_b}' [{s_b:,}-{e_b:,}] ({q_b:,} units) hold distinct, non-overlapping unit ranges ({overlap.overlap_type.lower()})."
                )
                rec = "Confirm individual allocation certificates verify each claimant's portion."
        else:
            # OVERLAPPING CASES (Shared units detected)
            if is_placeholder:
                alloc_type = AllocationType.UNRESOLVED_BENEFICIARY.value
                explanation = (
                    f"Unit overlap of {overlap.overlap_units:,} units in batch {batch_a} involves an undisclosed or anonymous beneficiary. "
                    f"Double use cannot be ruled out without broker allocation records."
                )
                rec = "Request retiring account holder's allocation ledger to identify the true beneficial owner."
            elif is_intermediary:
                alloc_type = AllocationType.INTERMEDIARY_ATTRIBUTION.value
                explanation = (
                    f"Unit overlap of {overlap.overlap_units:,} units ({overlap.overlap_type.lower()}) between '{claimant_a}' "
                    f"and intermediary/principal '{claimant_b}'. {entity_res.explanation}"
                )
                rec = "Verify broker-to-client pass-through allocation contract."
            elif is_same:
                alloc_type = AllocationType.SAME_UNITS_SAME_CLAIMANT.value
                explanation = (
                    f"Duplicate claim or revision by the same claimant '{claimant_a}': {overlap.overlap_units:,} units ({overlap.overlap_type.lower()}) "
                    f"match existing claim {claim_ref_b}. Affects {overlap.pct_of_candidate:.1f}% of candidate range and {overlap.pct_of_existing:.1f}% of existing claim."
                )
                rec = "If this is a revision of an unanchored claim, withdraw the prior claim; otherwise avoid double-counting on the ledger."
            elif is_related:
                alloc_type = AllocationType.SAME_UNITS_RELATED_CLAIMANTS.value
                explanation = (
                    f"Conflicting claim across related corporate entities: {overlap.overlap_units:,} units ({overlap.overlap_type.lower()}) "
                    f"claimed by '{claimant_a}' and related entity '{claimant_b}'. {entity_res.explanation}"
                )
                rec = "Determine which entity (parent or subsidiary) holds primary carbon reporting rights."
            else:
                alloc_type = AllocationType.ALLOCATION_CONFLICT.value
                explanation = (
                    f"Potential double use: {overlap.overlap_units:,} units of {ns_str} [{overlap.overlap_start:,}-{overlap.overlap_end:,}] "
                    f"are claimed by two unrelated entities ('{claimant_a}' vs '{claimant_b}'). Affects {overlap.pct_of_candidate:.1f}% of candidate range."
                )
                rec = f"Request retiring account holder allocation records. If {claim_ref_b} is invalid, challenge on-chain."

        return ReconciliationItem(
            candidate_block_idx=block_idx,
            candidate_range=(s_a, e_a),
            candidate_claimant=claimant_a,
            prior_claim_id=alloc_b.get("claim_id"),
            prior_claim_ref=alloc_b.get("claim_ref"),
            prior_claimant=claimant_b,
            prior_range=(s_b, e_b),
            prior_status=alloc_b.get("status"),
            registry=reg_a,
            batch_id=batch_a,
            overlap=overlap,
            allocation_type=alloc_type,
            entity_match_tier=entity_res.match_tier,
            entity_relationship=entity_res.relationship_type,
            explanation=explanation,
            audit_recommendation=rec,
        )

    @classmethod
    def reconcile_claim_blocks(
        cls,
        claim_id: int,
        claimant: str,
        blocks: list[dict[str, Any]],
        active_ranges: list[Any],
    ) -> ClaimReconciliationReport:
        """Reconcile all blocks of a claim against active ledger ranges."""
        total_units = sum(int(b["unit_end"]) - int(b["unit_start"]) + 1 for b in blocks)
        items: list[ReconciliationItem] = []
        splits: list[dict[str, Any]] = []

        for idx, b in enumerate(blocks):
            alloc_a = {
                "registry": b["registry"],
                "batch_id": b["batch_id"],
                "unit_start": b["unit_start"],
                "unit_end": b["unit_end"],
                "claimant": claimant,
            }

            # Find matching active ranges in same namespace
            for ar in active_ranges:
                alloc_b = {
                    "registry": ar.registry,
                    "batch_id": ar.batch_id,
                    "unit_start": ar.unit_start,
                    "unit_end": ar.unit_end,
                    "claimant": ar.claimant,
                    "claim_id": getattr(ar, "claim_id", None),
                    "claim_ref": getattr(ar, "claim_ref", None),
                    "status": getattr(ar, "status", None),
                }

                item = cls.reconcile_allocation_pair(alloc_a, alloc_b, block_idx=idx)
                if item.overlap.is_conflict:
                    items.append(item)
                elif item.allocation_type == AllocationType.LEGITIMATE_SPLIT.value:
                    splits.append(item.to_dict())

        conflicts = [item for item in items if item.overlap.is_conflict]

        return ClaimReconciliationReport(
            claim_id=claim_id,
            claimant=claimant,
            total_blocks=len(blocks),
            total_units=total_units,
            has_conflicts=bool(conflicts),
            conflict_count=len(conflicts),
            items=items,
            split_allocations=splits,
        )

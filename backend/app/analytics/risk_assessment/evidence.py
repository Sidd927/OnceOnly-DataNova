"""Evidence collection, extraction, and normalization across analytical subsystems."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
from ..models import (
    ConcentrationMetrics,
    CrossRegistryEntityComparison,
    CrossRegistryProjectComparison,
    FragmentationMetrics,
    MetadataProvenance,
    ProjectCorrelationCategory,
    TemporalBurstsResponse,
    TemporalGapsResponse,
)
from .models import (
    EvidenceCategory,
    EvidenceItem,
    EvidenceSeverity,
    EvidenceStrength,
    SourceStage,
)
from .rules import (
    DOMINANT_SHARE_THRESHOLD,
    GINI_HIGH_INEQUALITY_THRESHOLD,
    HHI_DOMINANCE_THRESHOLD,
    HHI_HIGH_CONCENTRATION_THRESHOLD,
    MICRO_CLAIM_EVENT_COUNT_THRESHOLD,
    MICRO_CLAIM_TONNE_LIMIT,
    MICRO_CLAIM_VOLUME_SHARE_THRESHOLD,
    RULE_DEFINITIONS,
    TEMPORAL_BURST_MIN_TONNES,
    TEMPORAL_BURST_Z_THRESHOLD,
    UNRESOLVED_SHARE_MATERIAL_THRESHOLD,
)


class EvidenceCollector:
    """Collects, standardizes, and converts analytical metrics into structured EvidenceItem objects."""

    # -------------------------------------------------------------------------
    # PHASE 2A: Entity Resolution Evidence
    # -------------------------------------------------------------------------

    @staticmethod
    def from_entity_resolution(
        match_result: Any,
        entity_a: str,
        entity_b: str,
        provenance: MetadataProvenance = MetadataProvenance.AD_HOC_API_INPUT,
    ) -> List[EvidenceItem]:
        """Convert Phase 2A EntityMatcher/EntityResolutionEngine result into EvidenceItems."""
        items: List[EvidenceItem] = []
        rel_type = getattr(match_result, "relationship_type", None)
        rel_val = rel_type.value if hasattr(rel_type, "value") else str(rel_type or "")
        score = float(getattr(match_result, "overall_score", 0.0) or 0.0)
        match_tier = getattr(match_result, "match_tier", None)
        tier_val = match_tier.value if hasattr(match_tier, "value") else str(match_tier or "")

        if rel_val == "CORPORATE_HIERARCHY_OR_SUBSIDIARY":
            r_def = RULE_DEFINITIONS["RULE-ENT-002"]
            items.append(
                EvidenceItem(
                    id=f"EVD-ENT-HIERARCHY-{abs(hash((entity_a, entity_b))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Corporate Hierarchy Variation: '{entity_a}' vs '{entity_b}'",
                    explanation=(
                        f"Entities share core root brand tokens but differ in legal, divisional, or subsidiary qualifiers "
                        f"(match score {score:.1f}/100, tier '{tier_val}')."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=EvidenceStrength.MODERATE,
                    supporting_records=[entity_a, entity_b],
                    metrics={"score": score, "relationship": rel_val, "tier": tier_val},
                    thresholds={"tier": tier_val},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        f"Shared brand tokens do not establish identical legal entities or common ownership.",
                    ],
                    missing_information=[
                        "Corporate registry ownership filings or beneficial ownership register.",
                    ],
                    recommended_action="Verify parent/subsidiary corporate hierarchy and confirm which entity is authorized to retire credits.",
                )
            )

        return items

    @staticmethod
    def from_intermediary_analysis(
        raw_text: str,
        intermediary_rel: Any,
        provenance: MetadataProvenance = MetadataProvenance.AD_HOC_API_INPUT,
    ) -> List[EvidenceItem]:
        """Convert Phase 2A IntermediaryExtractor result into EvidenceItems."""
        items: List[EvidenceItem] = []
        is_inter = getattr(intermediary_rel, "is_intermediary", False)
        if not is_inter:
            return items

        broker = getattr(intermediary_rel, "intermediary_name", None) or "Unknown Intermediary"
        client = getattr(intermediary_rel, "principal_name", None) or "Undisclosed Principal"
        r_def = RULE_DEFINITIONS["RULE-ENT-001"]

        counter = []
        if client and client != "Undisclosed Principal":
            counter.append(f"Principal client '{client}' was successfully parsed from text.")

        missing = []
        if not client or client == "Undisclosed Principal":
            missing.append("Beneficial end-user identity is not specified in retirement text.")

        items.append(
            EvidenceItem(
                id=f"EVD-ENT-INTERMEDIARY-{abs(hash(raw_text)) % 100000:05d}",
                category=r_def.category,
                source_stage=r_def.source_stage,
                rule_id=r_def.rule_id,
                title=f"Intermediary Attribution Phrasing: '{broker}'",
                explanation=(
                    f"Retirement record indicates intermediary broker/retailer phrasing: '{raw_text}'. "
                    f"Identified intermediary '{broker}' acting on behalf of '{client}'."
                ),
                severity=r_def.default_severity,
                evidence_strength=EvidenceStrength.MODERATE,
                supporting_records=[raw_text],
                metrics={"is_intermediary": True, "broker": broker, "principal": client},
                thresholds={},
                provenance=provenance,
                limitations=r_def.limitations,
                counterevidence=counter,
                missing_information=missing,
                recommended_action="Request broker settlement certificate confirming the ultimate beneficial owner of the climate claim.",
            )
        )
        return items

    # -------------------------------------------------------------------------
    # PHASE 2B: Reconciliation & Allocation Evidence
    # -------------------------------------------------------------------------

    @staticmethod
    def from_reconciliation_item(
        rec_item: Any,
        provenance: MetadataProvenance = MetadataProvenance.DATABASE_CENSUS,
    ) -> List[EvidenceItem]:
        """Convert Phase 2B ReconciliationItem into EvidenceItems."""
        items: List[EvidenceItem] = []
        overlap = getattr(rec_item, "overlap", None)
        if not overlap:
            return items

        overlap_type = str(getattr(overlap, "overlap_type", "DISJOINT")).strip().upper()
        alloc_type = str(getattr(rec_item, "allocation_type", "")).strip().upper()
        c_range = list(getattr(rec_item, "candidate_range", (0, 0)))
        p_range = list(getattr(rec_item, "prior_range", (0, 0)))
        cand_claimant = str(getattr(rec_item, "candidate_claimant", ""))
        prior_claimant = str(getattr(rec_item, "prior_claimant", ""))
        prior_ref = str(getattr(rec_item, "prior_claim_ref", ""))
        namespace = str(getattr(rec_item, "namespace", f"{getattr(rec_item, 'registry', '')}:{getattr(rec_item, 'batch_id', '')}"))
        overlap_units = int(getattr(overlap, "overlap_units", 0))

        # Check for EXACT overlap
        if overlap_type in ("EXACT", "EXACT_OVERLAP", "EXACT_DUPLICATE"):
            r_def = RULE_DEFINITIONS["RULE-REC-001"]
            items.append(
                EvidenceItem(
                    id=f"EVD-REC-EXACT-{abs(hash((namespace, tuple(c_range), prior_ref))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Exact Serial Unit Overlap: {c_range[0]}-{c_range[1]} ({namespace})",
                    explanation=(
                        f"Candidate claim range {c_range[0]}-{c_range[1]} ({overlap_units} units) in namespace '{namespace}' "
                        f"exactly matches an already-anchored active range registered to prior claim '{prior_ref}' ({prior_claimant})."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[
                        f"Candidate: {c_range[0]}-{c_range[1]} ({cand_claimant})",
                        f"Active Ledger: {prior_ref} ({prior_claimant})",
                    ],
                    metrics={"overlap_units": overlap_units, "overlap_type": overlap_type, "allocation_type": alloc_type},
                    thresholds={"overlap_type": "EXACT"},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        f"Prior claim status is '{getattr(rec_item, 'prior_status', 'active')}'; units remain locked on ledger.",
                    ] if getattr(rec_item, "prior_status", None) else [],
                    missing_information=[],
                    recommended_action="Block claim registration immediately. Direct conflicting parties to initiate on-chain challenge.",
                    dependency_group_id=f"GRP-SERIAL-{namespace}-{c_range[0]}-{c_range[1]}",
                )
            )

        # Check for PARTIAL overlap
        elif overlap_type in ("PARTIAL_OVERLAP", "OVERLAP_LEFT", "OVERLAP_RIGHT"):
            r_def = RULE_DEFINITIONS["RULE-REC-002"]
            items.append(
                EvidenceItem(
                    id=f"EVD-REC-PARTIAL-{abs(hash((namespace, tuple(c_range), prior_ref))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Partial Serial Unit Overlap: {overlap_units} units ({namespace})",
                    explanation=(
                        f"Candidate claim range {c_range[0]}-{c_range[1]} partially intersects active prior claim '{prior_ref}' "
                        f"({prior_claimant}) by {overlap_units} units."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Intersection: {overlap_units} units in {namespace}"],
                    metrics={"overlap_units": overlap_units, "overlap_type": overlap_type, "allocation_type": alloc_type},
                    thresholds={"overlap_type": overlap_type},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[],
                    missing_information=[],
                    recommended_action="Reject overlapping range. Allow candidate to re-submit sanitized range excluding the conflicting units.",
                    dependency_group_id=f"GRP-SERIAL-{namespace}-{c_range[0]}-{c_range[1]}",
                )
            )

        # Check for CONTAINED overlap
        elif overlap_type in ("CONTAINMENT", "CONTAINED", "CONTAINS", "SUPERSET"):
            r_def = RULE_DEFINITIONS["RULE-REC-003"]
            items.append(
                EvidenceItem(
                    id=f"EVD-REC-CONTAINED-{abs(hash((namespace, tuple(c_range), prior_ref))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Contained Serial Unit Overlap: {c_range[0]}-{c_range[1]} ({namespace})",
                    explanation=(
                        f"Candidate claim range {c_range[0]}-{c_range[1]} is entirely enveloped by prior active claim '{prior_ref}' "
                        f"({prior_claimant})."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Candidate: {c_range}", f"Enveloping Prior: {p_range}"],
                    metrics={"overlap_units": overlap_units, "overlap_type": overlap_type, "allocation_type": alloc_type},
                    thresholds={"overlap_type": overlap_type},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        f"Verify if claimant '{cand_claimant}' has contractual delegation from prior claimant '{prior_claimant}'."
                    ],
                    missing_information=[],
                    recommended_action="Block registration until sub-allocation authorization is cryptographically attested.",
                    dependency_group_id=f"GRP-SERIAL-{namespace}-{c_range[0]}-{c_range[1]}",
                )
            )

        # Check for LEGITIMATE SPLIT
        elif alloc_type == "LEGITIMATE_SPLIT" or (overlap_type == "DISJOINT" and cand_claimant != prior_claimant):
            r_def = RULE_DEFINITIONS["RULE-REC-004"]
            items.append(
                EvidenceItem(
                    id=f"EVD-REC-SPLIT-{abs(hash((namespace, tuple(c_range), tuple(p_range)))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Legitimate Split Allocation: Disjoint Units ({namespace})",
                    explanation=(
                        f"Candidate range {c_range[0]}-{c_range[1]} and prior range {p_range[0]}-{p_range[1]} share batch "
                        f"'{namespace}' but occupy strictly disjoint intervals (0 unit overlap)."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Candidate: {c_range}", f"Adjacent: {p_range}"],
                    metrics={"overlap_units": 0, "overlap_type": "DISJOINT", "allocation_type": "LEGITIMATE_SPLIT"},
                    thresholds={"overlap_units": 0},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        "[OBSERVED] Mathematical verification confirms zero shared units between claims.",
                    ],
                    contextual_caveats=[
                        "Normal commercial retirement partitioning across separate buyers or departments.",
                    ],
                    missing_information=[],
                    recommended_action="No adverse action required. Proceed with normal ledger anchoring.",
                )
            )

        return items

    # -------------------------------------------------------------------------
    # PHASE 2C STAGE 1: Concentration & Fragmentation Evidence
    # -------------------------------------------------------------------------

    @staticmethod
    def from_concentration_metrics(
        conc: ConcentrationMetrics,
        registry: str,
        batch_id: str,
        provenance: MetadataProvenance = MetadataProvenance.DATABASE_CENSUS,
    ) -> List[EvidenceItem]:
        """Convert Phase 2C Stage 1 ConcentrationMetrics into EvidenceItems."""
        items: List[EvidenceItem] = []
        ns = f"{registry}:{batch_id}"

        # 1. Single-beneficiary dominance
        if conc.dominant_disclosed_share >= DOMINANT_SHARE_THRESHOLD and conc.hhi_disclosed >= HHI_DOMINANCE_THRESHOLD:
            r_def = RULE_DEFINITIONS["RULE-CON-001"]
            items.append(
                EvidenceItem(
                    id=f"EVD-CON-DOMINANCE-{abs(hash((ns, conc.dominant_disclosed_beneficiary))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Single-Beneficiary Portfolio Dominance: '{conc.dominant_disclosed_beneficiary}' ({ns})",
                    explanation=(
                        f"Dominant beneficiary '{conc.dominant_disclosed_beneficiary}' accounts for "
                        f"{conc.dominant_disclosed_share:.1%} of disclosed batch volume with HHI {conc.hhi_disclosed:.0f}."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Batch {ns}", f"Entity: {conc.dominant_disclosed_beneficiary}"],
                    metrics={
                        "dominant_share": conc.dominant_disclosed_share,
                        "hhi_disclosed": conc.hhi_disclosed,
                        "unique_disclosed": conc.unique_disclosed_beneficiaries,
                    },
                    thresholds={"dominant_share_min": DOMINANT_SHARE_THRESHOLD, "hhi_min": HHI_DOMINANCE_THRESHOLD},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        f"[OBSERVED] Total batch disclosed volume is {conc.disclosed_units:,.1f} tonnes across {conc.unique_disclosed_beneficiaries} claimants.",
                        "Anchor buyer agreements are standard practice for large-scale corporate sustainability commitments.",
                    ],
                    contextual_caveats=[
                        "Anchor buyer agreements are standard practice for large-scale corporate sustainability commitments (private bilateral contracts not verified).",
                    ],
                    missing_information=[],
                    recommended_action="Inspect bilateral purchase contract to verify legitimate whole-batch allocation.",
                    dependency_group_id=f"GRP-BENEFICIARY-{ns}",
                )
            )

        # 2. High concentration among several claimants
        elif conc.hhi_disclosed >= HHI_HIGH_CONCENTRATION_THRESHOLD and conc.unique_disclosed_beneficiaries >= 3:
            r_def = RULE_DEFINITIONS["RULE-CON-002"]
            items.append(
                EvidenceItem(
                    id=f"EVD-CON-HIGH-{abs(hash((ns, conc.hhi_disclosed))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"High Beneficiary Concentration: HHI {conc.hhi_disclosed:.0f} ({ns})",
                    explanation=(
                        f"Batch volume exhibits high portfolio concentration (HHI {conc.hhi_disclosed:.0f}) across "
                        f"{conc.unique_disclosed_beneficiaries} distinct claimants."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Batch {ns}"],
                    metrics={"hhi_disclosed": conc.hhi_disclosed, "unique_disclosed": conc.unique_disclosed_beneficiaries},
                    thresholds={"hhi_min": HHI_HIGH_CONCENTRATION_THRESHOLD},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[],
                    missing_information=[],
                    recommended_action="Perform standard beneficiary portfolio verification.",
                    dependency_group_id=f"GRP-BENEFICIARY-{ns}",
                )
            )

        # 3. Material undisclosed share
        if conc.unresolved_share >= UNRESOLVED_SHARE_MATERIAL_THRESHOLD:
            r_def = RULE_DEFINITIONS["RULE-CON-003"]
            items.append(
                EvidenceItem(
                    id=f"EVD-CON-UNDISCLOSED-{abs(hash((ns, conc.unresolved_share))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Material Undisclosed Beneficiary Share: {conc.unresolved_share:.1%} ({ns})",
                    explanation=(
                        f"{conc.unresolved_share:.1%} of retirement volume ({conc.unresolved_units:,.1f} tonnes) in batch '{ns}' "
                        f"has undisclosed, placeholder, or missing beneficiary identifiers."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Batch {ns}"],
                    metrics={"unresolved_share": conc.unresolved_share, "unresolved_units": conc.unresolved_units},
                    thresholds={"unresolved_share_min": UNRESOLVED_SHARE_MATERIAL_THRESHOLD},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        "Registry-level confidentiality provisions frequently permit redacted beneficiary entries.",
                    ],
                    missing_information=[
                        f"Beneficiary identity absent for {conc.unresolved_units:,.1f} tonnes.",
                    ],
                    recommended_action="Request identity disclosure from retirement account holder before granting verified status.",
                    dependency_group_id=f"GRP-BENEFICIARY-{ns}",
                )
            )

        return items

    @staticmethod
    def from_fragmentation_metrics(
        frag: FragmentationMetrics,
        registry: str,
        batch_id: str,
        provenance: MetadataProvenance = MetadataProvenance.DATABASE_CENSUS,
    ) -> List[EvidenceItem]:
        """Convert Phase 2C Stage 1 FragmentationMetrics into EvidenceItems."""
        items: List[EvidenceItem] = []
        ns = f"{registry}:{batch_id}"

        # 1. Micro-claims smurfing
        micro_cnt = getattr(frag, "micro_claims_count", 0)
        micro_share = getattr(frag, "micro_claims_volume_share", 0.0)
        if micro_cnt >= MICRO_CLAIM_EVENT_COUNT_THRESHOLD and micro_share >= MICRO_CLAIM_VOLUME_SHARE_THRESHOLD:
            r_def = RULE_DEFINITIONS["RULE-FRG-001"]
            items.append(
                EvidenceItem(
                    id=f"EVD-FRG-SMURFING-{abs(hash((ns, micro_cnt, micro_share))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Anomalous Micro-Claim Fragmentation: {micro_cnt} events ({ns})",
                    explanation=(
                        f"Batch '{ns}' contains {micro_cnt} micro-claim events (<= {MICRO_CLAIM_TONNE_LIMIT} tonnes each) "
                        f"representing {micro_share:.1%} of total batch volume ({getattr(frag, 'micro_claims_units', 0.0):,.1f} tonnes)."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Batch {ns}: {micro_cnt} micro events"],
                    metrics={"micro_count": micro_cnt, "micro_share": micro_share, "micro_threshold": MICRO_CLAIM_TONNE_LIMIT},
                    thresholds={"micro_count_min": MICRO_CLAIM_EVENT_COUNT_THRESHOLD, "micro_share_min": MICRO_CLAIM_VOLUME_SHARE_THRESHOLD},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        "Retail carbon offset programs (e.g. flight or ride-share offsets) naturally produce high micro-claim volumes.",
                    ],
                    contextual_caveats=[
                        "Retail carbon offset programs (e.g. flight or ride-share offsets) naturally produce high micro-claim volumes (aggregator API distribution not verified off-chain).",
                    ],
                    missing_information=[],
                    recommended_action="Verify aggregator distribution channels to confirm genuine retail micro-claim transactions.",
                    dependency_group_id=f"GRP-FRAGMENTATION-{ns}",
                )
            )

        # 2. Extreme sizing inequality
        gini_sc = getattr(frag, "gini_sample_corrected", 0.0)
        tot_events = getattr(frag, "total_events", 0)
        if gini_sc >= GINI_HIGH_INEQUALITY_THRESHOLD and tot_events >= 10:
            r_def = RULE_DEFINITIONS["RULE-FRG-002"]
            items.append(
                EvidenceItem(
                    id=f"EVD-FRG-GINI-{abs(hash((ns, gini_sc))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"High Sizing Inequality: Gini {gini_sc:.2f} ({ns})",
                    explanation=(
                        f"Retirement sizes in batch '{ns}' exhibit high statistical inequality (Gini {gini_sc:.2f}) "
                        f"across {tot_events} transactions (mean {getattr(frag, 'mean_event_size', 0.0):.1f}t vs median {getattr(frag, 'median_event_size', 0.0):.1f}t)."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Batch {ns}: {tot_events} events"],
                    metrics={"gini_sample_corrected": gini_sc, "mean_size": getattr(frag, "mean_event_size", 0.0), "median_size": getattr(frag, "median_event_size", 0.0)},
                    thresholds={"gini_min": GINI_HIGH_INEQUALITY_THRESHOLD},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[],
                    missing_information=[],
                    recommended_action="Inspect volume distribution to identify wholesale anchor chunks vs retail fragments.",
                    dependency_group_id=f"GRP-FRAGMENTATION-{ns}",
                )
            )

        return items

    # -------------------------------------------------------------------------
    # PHASE 2C STAGE 2: Temporal Intelligence Evidence
    # -------------------------------------------------------------------------

    @staticmethod
    def from_temporal_bursts(
        burst_resp: TemporalBurstsResponse,
        provenance: MetadataProvenance = MetadataProvenance.DATABASE_CENSUS,
    ) -> List[EvidenceItem]:
        """Convert Phase 2C Stage 2 TemporalBurstsResponse into EvidenceItems."""
        items: List[EvidenceItem] = []
        bursts = getattr(burst_resp, "bursts", [])
        if not bursts:
            return items

        r_def = RULE_DEFINITIONS["RULE-TMP-001"]
        for b in bursts:
            period_label = getattr(b, "period_label", "Unknown Period")
            tot_tonnes = float(getattr(b, "total_tonnes", 0.0))
            z_score = float(getattr(b, "z_score", 0.0))
            med = float(getattr(b, "baseline_median", 0.0))
            mad = float(getattr(b, "baseline_mad", 0.0))

            items.append(
                EvidenceItem(
                    id=f"EVD-TMP-BURST-{abs(hash((period_label, tot_tonnes))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Anomalous Volume Burst: {period_label} ({tot_tonnes:,.1f} tonnes, Z={z_score:.1f})",
                    explanation=(
                        f"Retirement pacing spiked to {tot_tonnes:,.1f} tonnes in {period_label}, exceeding historical "
                        f"baseline median ({med:.1f}t) by {z_score:.1f} MAD multiples (threshold {TEMPORAL_BURST_Z_THRESHOLD})."
                    ),
                    severity=r_def.default_severity,
                    evidence_strength=r_def.default_strength,
                    supporting_records=[f"Period: {period_label}", f"Volume: {tot_tonnes:,.1f}t"],
                    metrics={"total_tonnes": tot_tonnes, "z_score": z_score, "baseline_median": med, "baseline_mad": mad},
                    thresholds={"z_score_threshold": TEMPORAL_BURST_Z_THRESHOLD, "min_tonnes": TEMPORAL_BURST_MIN_TONNES},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        f"[OBSERVED] Baseline lookback window establishes normal non-peak median of {med:,.1f} tonnes.",
                        "Corporate compliance deadlines (e.g. Q4 or fiscal year end) routinely trigger bulk retirement clusters.",
                    ],
                    contextual_caveats=[
                        "Corporate compliance deadlines (e.g. Q4 CDP disclosures or EU ETS compliance cycles) create natural seasonal bursts (scheduling not attested).",
                    ],
                    missing_information=[],
                    recommended_action="Cross-reference burst period with buyer disclosure deadlines to confirm operational scheduling.",
                    dependency_group_id=f"GRP-TEMPORAL-{period_label}",
                )
            )

        return items

    @staticmethod
    def from_temporal_gaps(
        gap_resp: TemporalGapsResponse,
        provenance: MetadataProvenance = MetadataProvenance.DATABASE_CENSUS,
    ) -> List[EvidenceItem]:
        """Convert Phase 2C Stage 2 TemporalGapsResponse into EvidenceItems."""
        items: List[EvidenceItem] = []
        gaps = getattr(gap_resp, "gaps", [])
        if not gaps:
            return items

        r_def = RULE_DEFINITIONS["RULE-TMP-002"]
        for g in gaps:
            duration_months = int(getattr(g, "duration_months", 0) or 0)
            p_start = getattr(g, "start_period", "")
            p_end = getattr(g, "end_period", "")
            if duration_months >= 3:
                items.append(
                    EvidenceItem(
                        id=f"EVD-TMP-GAP-{abs(hash((p_start, p_end))) % 100000:05d}",
                        category=r_def.category,
                        source_stage=r_def.source_stage,
                        rule_id=r_def.rule_id,
                        title=f"Prolonged Inactivity Gap: {duration_months} periods ({p_start} to {p_end})",
                        explanation=(
                            f"Project exhibited {duration_months} consecutive periods of complete inactivity "
                            f"between {p_start} and {p_end} before resuming retirements."
                        ),
                        severity=r_def.default_severity,
                        evidence_strength=r_def.default_strength,
                        supporting_records=[f"Inactivity interval: {p_start} to {p_end}"],
                        metrics={"duration_periods": duration_months, "start_period": p_start, "end_period": p_end},
                        thresholds={"min_periods": 3},
                        provenance=provenance,
                        limitations=r_def.limitations,
                        counterevidence=[
                            "Intermittent credit issuances and market liquidity gaps create normal periods of retirement dormancy.",
                        ],
                        missing_information=[],
                        recommended_action="Verify project operational continuity during dormant period.",
                        dependency_group_id=f"GRP-TEMPORAL-GAP-{p_start}",
                    )
                )

        return items

    # -------------------------------------------------------------------------
    # PHASE 2C STAGE 3: Cross-Registry Evidence
    # -------------------------------------------------------------------------

    @staticmethod
    def from_cross_registry_comparison(
        cmp: CrossRegistryProjectComparison,
        provenance: MetadataProvenance = MetadataProvenance.DATABASE_CENSUS,
    ) -> List[EvidenceItem]:
        """Convert Phase 2C Stage 3 CrossRegistryProjectComparison into EvidenceItems."""
        items: List[EvidenceItem] = []
        cat = str(cmp.correlation_category).strip().upper()
        p_a = cmp.project_a
        p_b = cmp.project_b

        # 1. Collision
        if cat == ProjectCorrelationCategory.CROSS_REGISTRY_IDENTIFIER_COLLISION.value:
            r_def = RULE_DEFINITIONS["RULE-XREG-002"]
            items.append(
                EvidenceItem(
                    id=f"EVD-XREG-COLLISION-{abs(hash((p_a.project_id, p_b.project_id))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Cross-Registry Identifier Collision: ID '{p_a.project_id}' ({p_a.registry} vs {p_b.registry})",
                    explanation=cmp.explanation,
                    severity=r_def.default_severity,
                    evidence_strength=EvidenceStrength.WEAK,
                    supporting_records=[f"{p_a.registry} ID: {p_a.project_id}", f"{p_b.registry} ID: {p_b.project_id}"],
                    metrics={"name_similarity": cmp.name_similarity_score, "is_cross_registry": True},
                    thresholds={},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        f"Registry '{p_a.registry}' and '{p_b.registry}' maintain completely independent, uncoordinated ID namespaces.",
                        f"Numeric equivalence ('{p_a.project_id}') is an artifact of independent integer counters, NOT project identity.",
                    ],
                    missing_information=[],
                    recommended_action="Treat as coincidental integer collision. Do not flag as dual-listing without corroborating project titles.",
                    dependency_group_id=f"GRP-CROSSREG-ID-{p_a.project_id}",
                )
            )

        # 2. Strong Correlation
        elif cat == ProjectCorrelationCategory.STRONG_ATTRIBUTE_CORRELATION.value:
            r_def = RULE_DEFINITIONS["RULE-XREG-001"]
            items.append(
                EvidenceItem(
                    id=f"EVD-XREG-STRONG-{abs(hash((p_a.project_name, p_b.project_name))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Strong Cross-Registry Correlation: '{p_a.project_name}' vs '{p_b.project_name}'",
                    explanation=cmp.explanation,
                    severity=r_def.default_severity,
                    evidence_strength=EvidenceStrength.MODERATE,
                    supporting_records=[f"{p_a.registry}: {p_a.project_name}", f"{p_b.registry}: {p_b.project_name}"],
                    metrics={"name_similarity": cmp.name_similarity_score, "country_relation": cmp.country_relation},
                    thresholds={"similarity_threshold": 0.85},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        "Investigative triage signal only. Dual-registration may be formally approved or represent distinct project phases.",
                    ],
                    missing_information=[
                        "Independent registry attestation confirming whether credits were transferred or co-issued.",
                    ],
                    recommended_action="Inspect project design documents on both registries to determine if projects represent identical physical assets.",
                    dependency_group_id=f"GRP-CROSSREG-PROJ-{abs(hash(p_a.project_name)) % 10000:04d}",
                )
            )

        # 3. Contradictory Attributes
        elif cat == ProjectCorrelationCategory.CONFLICTING_ATTRIBUTES.value:
            r_def = RULE_DEFINITIONS["RULE-XREG-003"]
            items.append(
                EvidenceItem(
                    id=f"EVD-XREG-CONFLICT-{abs(hash((p_a.project_name, p_b.project_name))) % 100000:05d}",
                    category=r_def.category,
                    source_stage=r_def.source_stage,
                    rule_id=r_def.rule_id,
                    title=f"Contradictory Attributes: '{p_a.project_name}' vs '{p_b.project_name}'",
                    explanation=cmp.explanation,
                    severity=r_def.default_severity,
                    evidence_strength=EvidenceStrength.CONTRADICTORY,
                    supporting_records=[
                        f"{p_a.registry}: {p_a.project_name} ({p_a.country})",
                        f"{p_b.registry}: {p_b.project_name} ({p_b.country})",
                    ],
                    metrics={"name_similarity": cmp.name_similarity_score, "country_relation": cmp.country_relation},
                    thresholds={"similarity_min": 0.50},
                    provenance=provenance,
                    limitations=r_def.limitations,
                    counterevidence=[
                        f"National jurisdiction contradiction ('{p_a.country}' vs '{p_b.country}') proves projects are geographically distinct physical assets.",
                    ],
                    missing_information=[],
                    recommended_action="Dismiss potential dual-registration concern; geographic contradiction establishes separate physical assets.",
                    dependency_group_id=f"GRP-CROSSREG-PROJ-{abs(hash(p_a.project_name)) % 10000:04d}",
                )
            )

        return items

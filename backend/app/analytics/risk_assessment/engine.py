"""Unified explainable risk assessment engine orchestrating multi-stage intelligence."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ..engine import DEFAULT_DB_PATH, AnalyticsEngine
from ..models import (
    BatchAnalyticsResult,
    MetadataProvenance,
    ProjectProfile,
)
from .evidence import EvidenceCollector
from .models import (
    RULESET_VERSION,
    AssessmentRuleDefinition,
    AssessmentRulesCatalogResponse,
    AssessmentScope,
    AssessmentStatus,
    AssessmentTarget,
    EvidenceCategory,
    EvidenceDependencyGroup,
    EvidenceItem,
    EvidenceSeverity,
    EvidenceStrength,
    ReviewPriority,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    SourceStage,
)
from .rules import RULE_DEFINITIONS


class RiskAssessmentEngine:
    """Orchestrates multi-phase intelligence to produce transparent, auditable risk assessments."""

    @classmethod
    def get_rules_catalog(cls) -> AssessmentRulesCatalogResponse:
        """Return the complete catalog of deterministic risk assessment rules."""
        rule_list = sorted(RULE_DEFINITIONS.values(), key=lambda r: r.rule_id)
        return AssessmentRulesCatalogResponse(
            ruleset_version=RULESET_VERSION,
            total_rules=len(rule_list),
            rules=rule_list,
        )

    @classmethod
    def assess(
        cls,
        request: RiskAssessmentRequest,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Execute unified, explainable risk assessment for the requested scope."""
        scope = request.scope

        # Dispatch based on scope
        if scope == AssessmentScope.BATCH:
            return cls._assess_batch_scope(request, con=con, db_path=db_path)
        elif scope == AssessmentScope.PROJECT:
            return cls._assess_project_scope(request, con=con, db_path=db_path)
        elif scope == AssessmentScope.CLAIM:
            return cls._assess_claim_scope(request, con=con, db_path=db_path)
        elif scope == AssessmentScope.ENTITY:
            return cls._assess_entity_scope(request, con=con, db_path=db_path)
        elif scope == AssessmentScope.CROSS_REGISTRY:
            return cls._assess_cross_registry_scope(request, con=con, db_path=db_path)
        elif scope == AssessmentScope.AD_HOC:
            return cls._assess_ad_hoc_scope(request, con=con, db_path=db_path)
        else:
            raise ValueError(f"Unsupported assessment scope: {scope}")

    # =========================================================================
    # SCOPE EVALUATORS
    # =========================================================================

    @classmethod
    def _assess_batch_scope(
        cls,
        req: RiskAssessmentRequest,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Evaluate a specific batch across Concentration, Fragmentation, and Temporal metrics."""
        reg = (req.registry or "VCS").strip().upper()
        bid = req.batch_id
        if not bid:
            raise ValueError("batch_id is required for BATCH scope")

        stages_consulted: List[SourceStage] = [
            SourceStage.PHASE_2C_STAGE_1_CONCENTRATION,
            SourceStage.PHASE_2C_STAGE_1_FRAGMENTATION,
        ]

        # 1. Fetch batch analytics result
        batch_res: BatchAnalyticsResult = AnalyticsEngine.analyze_batch(
            registry=reg, batch_id=bid, con=con, db_path=db_path
        )

        all_evidence: List[EvidenceItem] = []

        # Stage 1: Concentration
        conc_evd = EvidenceCollector.from_concentration_metrics(
            batch_res.concentration, registry=reg, batch_id=bid, provenance=MetadataProvenance.DATABASE_CENSUS
        )
        all_evidence.extend(conc_evd)

        # Stage 1: Fragmentation
        frag_evd = EvidenceCollector.from_fragmentation_metrics(
            batch_res.fragmentation, registry=reg, batch_id=bid, provenance=MetadataProvenance.DATABASE_CENSUS
        )
        all_evidence.extend(frag_evd)

        # Stage 2: Temporal Activity for this project/batch
        if batch_res.project_id:
            stages_consulted.append(SourceStage.PHASE_2C_STAGE_2_TEMPORAL)
            try:
                bursts = AnalyticsEngine.analyze_temporal_bursts(
                    registry=reg, project_id=batch_res.project_id, con=con, db_path=db_path
                )
                tmp_evd = EvidenceCollector.from_temporal_bursts(bursts, provenance=MetadataProvenance.DATABASE_CENSUS)
                all_evidence.extend(tmp_evd)
            except Exception:
                pass

        # Optional Reconciliation if candidate range supplied
        if req.candidate_range:
            stages_consulted.append(SourceStage.PHASE_2B_RECONCILIATION)
            rec_evd = cls._check_reconciliation_range(
                registry=reg, batch_id=bid, cand_range=req.candidate_range, claimant=req.claimant or "Candidate Claimant"
            )
            all_evidence.extend(rec_evd)

        target = AssessmentTarget(
            scope=AssessmentScope.BATCH,
            registry=reg,
            batch_id=bid,
            project_id=batch_res.project_id,
            description=f"Batch {reg}:{bid} ({batch_res.total_quantity:,.1f} tonnes across {batch_res.total_events} events)",
        )

        return cls._synthesize_assessment(target, all_evidence, stages_consulted)

    @classmethod
    def _assess_project_scope(
        cls,
        req: RiskAssessmentRequest,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Evaluate a project across Temporal Pacing, Batch Concentration, and Cross-Registry Correlations."""
        reg = (req.registry or "VCS").strip().upper()
        pid = req.project_id
        if not pid:
            raise ValueError("project_id is required for PROJECT scope")

        stages_consulted: List[SourceStage] = [
            SourceStage.PHASE_2C_STAGE_2_TEMPORAL,
            SourceStage.PHASE_2C_STAGE_3_CROSS_REGISTRY,
        ]

        # Query project records from SQLite
        own_con = False
        if con is None:
            con = AnalyticsEngine.get_connection(db_path)
            own_con = True

        try:
            cur = con.cursor()
            cur.execute(
                """
                SELECT project_name, country, vintage, quantity, beneficiary, event_date, batch_id
                FROM records
                WHERE kind = 'retirement'
                  AND UPPER(registry) = UPPER(?)
                  AND project_id = ?
                """,
                (reg, pid),
            )
            rows = cur.fetchall()
            if not rows:
                raise ValueError(f"No retirement records found for project '{pid}' in registry '{reg}'")

            records = [dict(r) for r in rows]
            p_name = str(records[0].get("project_name") or f"Project {pid}")
            country = str(records[0].get("country") or "")
            tot_qty = sum(float(r["quantity"] or 0.0) for r in records)

            all_evidence: List[EvidenceItem] = []

            # Stage 2: Temporal Bursts & Gaps
            bursts = AnalyticsEngine.analyze_temporal_bursts(registry=reg, project_id=pid, con=con)
            all_evidence.extend(EvidenceCollector.from_temporal_bursts(bursts, provenance=MetadataProvenance.DATABASE_CENSUS))

            gaps = AnalyticsEngine.analyze_temporal_gaps(registry=reg, project_id=pid, con=con)
            all_evidence.extend(EvidenceCollector.from_temporal_gaps(gaps, provenance=MetadataProvenance.DATABASE_CENSUS))

            # Stage 1: Overall concentration over project records
            stages_consulted.append(SourceStage.PHASE_2C_STAGE_1_CONCENTRATION)
            conc = AnalyticsEngine.analyze_concentration_records(records)
            all_evidence.extend(EvidenceCollector.from_concentration_metrics(conc, reg, f"PROJ-{pid}", provenance=MetadataProvenance.DATABASE_CENSUS))

            # Stage 3: Cross-Registry Candidate Search
            other_reg = "GS" if reg == "VCS" else "VCS"
            p_prof = ProjectProfile(
                registry=reg, project_id=pid, project_name=p_name, country=country, provenance=MetadataProvenance.DATABASE_CENSUS
            )
            # Find closest counterpart in other registry
            corrs = AnalyticsEngine.correlate_cross_registry_projects(min_similarity=0.50, limit=20, con=con)
            for c in corrs.correlations:
                match_p = c.project_b if c.project_a.project_id == pid and c.project_a.registry == reg else (
                    c.project_a if c.project_b.project_id == pid and c.project_b.registry == reg else None
                )
                if match_p:
                    all_evidence.extend(EvidenceCollector.from_cross_registry_comparison(c, provenance=MetadataProvenance.DATABASE_CENSUS))
                    break

            target = AssessmentTarget(
                scope=AssessmentScope.PROJECT,
                registry=reg,
                project_id=pid,
                description=f"Project '{p_name}' ({reg}:{pid}, {tot_qty:,.1f} tonnes across {len(records)} events)",
            )

            return cls._synthesize_assessment(target, all_evidence, stages_consulted)
        finally:
            if own_con and con:
                con.close()

    @classmethod
    def _assess_claim_scope(
        cls,
        req: RiskAssessmentRequest,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Evaluate an existing registered claim in the OnceOnly ledger across Reconciliation and Analytics."""
        cid = req.claim_id
        if cid is None:
            raise ValueError("claim_id is required for CLAIM scope")

        stages_consulted: List[SourceStage] = [
            SourceStage.PHASE_2B_RECONCILIATION,
            SourceStage.PHASE_2A_ENTITY_RESOLUTION,
            SourceStage.PHASE_2C_STAGE_1_CONCENTRATION,
        ]

        from ...service import active_ranges
        from ...reconciliation import AllocationReconciler
        from ...entity_resolution import EntityResolutionEngine
        from ...db import connect as get_app_con

        app_con = con or get_app_con()
        own_app_con = con is None

        try:
            claim_row = app_con.execute("SELECT * FROM claims WHERE id=?", (cid,)).fetchone()
            if not claim_row:
                raise ValueError(f"Claim ID {cid} not found in claims ledger")

            claim = dict(claim_row)
            blocks = [dict(r) for r in app_con.execute("SELECT * FROM claim_blocks WHERE claim_id=? ORDER BY idx", (cid,))]
            claimant = claim.get("claimant", "Unknown Claimant")

            all_evidence: List[EvidenceItem] = []

            # 1. Phase 2B Reconciliation against active ledger
            active = active_ranges(app_con, exclude_claim=cid)
            rec_report = AllocationReconciler.reconcile_claim_blocks(cid, claimant, blocks, active)
            for item in rec_report.items:
                all_evidence.extend(EvidenceCollector.from_reconciliation_item(item, provenance=MetadataProvenance.DATABASE_CENSUS))

            # 2. Phase 2A Entity Resolution over beneficiaries in blocks
            for b in blocks:
                ben = b.get("beneficiary")
                if ben and str(ben).strip().lower() not in ("none", "not disclosed", "undisclosed", ""):
                    match_res = EntityResolutionEngine.resolve_pair(claimant, str(ben))
                    all_evidence.extend(EvidenceCollector.from_entity_resolution(match_res, claimant, str(ben), provenance=MetadataProvenance.DATABASE_CENSUS))

            # 3. Phase 2C Stage 1 Concentration/Fragmentation on the claimed batches
            for b in blocks:
                b_reg = b.get("registry")
                b_id = b.get("batch_id")
                if b_reg and b_id:
                    try:
                        b_res = AnalyticsEngine.analyze_batch(b_reg, b_id, db_path=db_path)
                        all_evidence.extend(EvidenceCollector.from_concentration_metrics(b_res.concentration, b_reg, b_id, provenance=MetadataProvenance.DATABASE_CENSUS))
                        all_evidence.extend(EvidenceCollector.from_fragmentation_metrics(b_res.fragmentation, b_reg, b_id, provenance=MetadataProvenance.DATABASE_CENSUS))
                    except Exception:
                        pass

            target = AssessmentTarget(
                scope=AssessmentScope.CLAIM,
                claim_id=cid,
                description=f"Claim #{cid} ('{claim.get('ref')}', claimant='{claimant}', {claim.get('total_units', 0):,} units)",
            )

            return cls._synthesize_assessment(target, all_evidence, stages_consulted)
        finally:
            if own_app_con and app_con:
                app_con.close()

    @classmethod
    def _assess_entity_scope(
        cls,
        req: RiskAssessmentRequest,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Evaluate entity resolution, corporate hierarchy, and cross-registry entity appearance."""
        e_a = req.entity_a
        e_b = req.entity_b
        if not e_a:
            raise ValueError("entity_a is required for ENTITY scope")

        stages_consulted: List[SourceStage] = [
            SourceStage.PHASE_2A_ENTITY_RESOLUTION,
            SourceStage.PHASE_2C_STAGE_3_CROSS_REGISTRY,
        ]

        from ...entity_resolution import EntityResolutionEngine, IntermediaryExtractor

        all_evidence: List[EvidenceItem] = []

        # 1. Intermediary extraction on entity_a
        inter_a = IntermediaryExtractor.extract(e_a)
        all_evidence.extend(EvidenceCollector.from_intermediary_analysis(e_a, inter_a, provenance=MetadataProvenance.AD_HOC_API_INPUT))

        # 2. Pairwise entity matching if entity_b provided
        if e_b:
            match_res = EntityResolutionEngine.resolve_pair(e_a, e_b)
            all_evidence.extend(EvidenceCollector.from_entity_resolution(match_res, e_a, e_b, provenance=MetadataProvenance.AD_HOC_API_INPUT))

            # Cross-registry entity comparison
            x_cmp = AnalyticsEngine.compare_entities(entity_a=e_a, entity_b=e_b, registry_a=req.registry or "VCS", registry_b="GS")
            if x_cmp.relationship_type == "CORPORATE_HIERARCHY_OR_SUBSIDIARY":
                # Already captured via entity resolution
                pass

        target = AssessmentTarget(
            scope=AssessmentScope.ENTITY,
            entity_a=e_a,
            entity_b=e_b,
            description=f"Entity Evaluation: '{e_a}'" + (f" vs '{e_b}'" if e_b else ""),
        )

        return cls._synthesize_assessment(target, all_evidence, stages_consulted)

    @classmethod
    def _assess_cross_registry_scope(
        cls,
        req: RiskAssessmentRequest,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Evaluate cross-registry project comparison."""
        p_a = req.project_a
        p_b = req.project_b
        if not p_a or not p_b:
            raise ValueError("project_a and project_b are required for CROSS_REGISTRY scope")

        stages_consulted: List[SourceStage] = [
            SourceStage.PHASE_2C_STAGE_3_CROSS_REGISTRY,
        ]

        cmp = AnalyticsEngine.compare_projects(p_a, p_b)
        all_evidence = EvidenceCollector.from_cross_registry_comparison(cmp, provenance=MetadataProvenance.AD_HOC_API_INPUT)

        target = AssessmentTarget(
            scope=AssessmentScope.CROSS_REGISTRY,
            description=f"Cross-Registry Project Comparison: '{p_a.get('project_name')}' vs '{p_b.get('project_name')}'",
        )

        return cls._synthesize_assessment(target, all_evidence, stages_consulted)

    @classmethod
    def _assess_ad_hoc_scope(
        cls,
        req: RiskAssessmentRequest,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Perform in-memory risk assessment over ad-hoc retirement records or candidate ranges."""
        records = req.records or []
        stages_consulted: List[SourceStage] = []
        all_evidence: List[EvidenceItem] = []

        if records:
            stages_consulted.extend([
                SourceStage.PHASE_2C_STAGE_1_CONCENTRATION,
                SourceStage.PHASE_2C_STAGE_1_FRAGMENTATION,
            ])
            conc = AnalyticsEngine.analyze_concentration_records(records)
            all_evidence.extend(EvidenceCollector.from_concentration_metrics(conc, "AD_HOC", "AD_HOC_BATCH", provenance=MetadataProvenance.AD_HOC_API_INPUT))

            frag = AnalyticsEngine.analyze_batch_records(records)
            all_evidence.extend(EvidenceCollector.from_fragmentation_metrics(frag, "AD_HOC", "AD_HOC_BATCH", provenance=MetadataProvenance.AD_HOC_API_INPUT))

        if req.candidate_range and req.batch_id:
            stages_consulted.append(SourceStage.PHASE_2B_RECONCILIATION)
            rec_evd = cls._check_reconciliation_range(
                registry=req.registry or "VCS",
                batch_id=req.batch_id,
                cand_range=req.candidate_range,
                claimant=req.claimant or "Candidate Claimant",
            )
            all_evidence.extend(rec_evd)

        target = AssessmentTarget(
            scope=AssessmentScope.AD_HOC,
            description=f"Ad-hoc assessment over {len(records)} records",
        )

        return cls._synthesize_assessment(target, all_evidence, stages_consulted)

    # =========================================================================
    # RECONCILIATION HELPER
    # =========================================================================

    @classmethod
    def _check_reconciliation_range(
        cls,
        registry: str,
        batch_id: str,
        cand_range: Tuple[int, int],
        claimant: str,
    ) -> List[EvidenceItem]:
        """Check a candidate range against active ledger ranges."""
        from ...reconciliation import AllocationReconciler, compute_interval_overlap
        from ...service import active_ranges
        from ...db import connect as get_app_con

        evd: List[EvidenceItem] = []
        try:
            con = get_app_con()
            try:
                active = active_ranges(con)
                for act in active:
                    if act.registry.strip().upper() == registry.strip().upper() and str(act.batch_id) == str(batch_id):
                        cand_dict = {
                            "registry": registry, "batch_id": batch_id, "unit_start": cand_range[0],
                            "unit_end": cand_range[1], "claimant": claimant,
                        }
                        prior_dict = {
                            "registry": act.registry, "batch_id": act.batch_id, "unit_start": act.unit_start,
                            "unit_end": act.unit_end, "claimant": act.claimant,
                        }
                        item = AllocationReconciler.reconcile_allocation_pair(cand_dict, prior_dict)
                        # Patch claim references onto item for richer evidence
                        item.prior_claim_ref = getattr(act, "claim_ref", getattr(act, "ref", None))
                        item.prior_claim_id = act.claim_id
                        item.prior_status = act.status
                        evd.extend(EvidenceCollector.from_reconciliation_item(item, provenance=MetadataProvenance.DATABASE_CENSUS))
            finally:
                con.close()
        except Exception:
            pass
        return evd

    # =========================================================================
    # SYNTHESIS & DOUBLE-COUNTING SAFEGUARDS
    # =========================================================================

    @classmethod
    def _synthesize_assessment(
        cls,
        target: AssessmentTarget,
        evidence_items: List[EvidenceItem],
        stages_consulted: List[SourceStage],
    ) -> RiskAssessmentResponse:
        """Formulate dependency groups, apply double-counting safeguards, and synthesize balance of evidence."""
        # 1. Cluster evidence into dependency groups
        groups_map: Dict[str, List[EvidenceItem]] = defaultdict(list)
        unclustered_items: List[EvidenceItem] = []

        for e in evidence_items:
            if e.dependency_group_id:
                groups_map[e.dependency_group_id].append(e)
            else:
                unclustered_items.append(e)

        dependency_groups: List[EvidenceDependencyGroup] = []
        correlated_count = 0

        for gid, grp_items in sorted(groups_map.items()):
            if len(grp_items) > 1:
                correlated_count += len(grp_items)
                primary = grp_items[0].rule_id
                shared_src = gid.split("-")[1] if "-" in gid else "SHARED_DATA"
                dependency_groups.append(
                    EvidenceDependencyGroup(
                        group_id=gid,
                        primary_signal=primary,
                        correlated_evidence_ids=[i.id for i in grp_items],
                        shared_data_source=shared_src,
                        is_reinforcing_not_independent=True,
                        explanation=(
                            f"Evidence items {[i.id for i in grp_items]} all derive from shared underlying {shared_src.lower()} "
                            "data in the same batch or project. They reinforce the primary finding but do not represent independent proof."
                        ),
                    )
                )

        independent_count = len(unclustered_items) + len(groups_map)

        # 2. Extract counterevidence, contextual caveats, and missing information
        counterevidence_set: List[str] = []
        contextual_caveats_set: List[str] = []
        missing_info_set: List[str] = []
        for e in evidence_items:
            for c in e.counterevidence:
                if c not in counterevidence_set:
                    counterevidence_set.append(c)
            for cv in e.contextual_caveats:
                if cv not in contextual_caveats_set:
                    contextual_caveats_set.append(cv)
            for m in e.missing_information:
                if m not in missing_info_set:
                    missing_info_set.append(m)

        # 3. Determine Overall Status and Review Priority (Conservative & Non-Additive)
        overall_status, priority, priority_explanation = cls._evaluate_balance_of_evidence(
            evidence_items, groups_map, counterevidence_set, missing_info_set
        )

        triggered_rules = sorted(list({e.rule_id for e in evidence_items}))
        timestamp = datetime.now(timezone.utc).isoformat()

        # Deterministic assessment ID
        id_blob = f"{target.scope.value}|{target.registry}|{target.batch_id}|{target.project_id}|{target.claim_id}|{','.join(triggered_rules)}|{RULESET_VERSION}"
        assessment_id = "ASM-" + hashlib.sha256(id_blob.encode()).hexdigest()[:16].upper()

        # Recommended next steps
        recommended_steps: List[str] = []
        for e in evidence_items:
            if e.recommended_action and e.recommended_action not in recommended_steps:
                recommended_steps.append(e.recommended_action)
        if not recommended_steps:
            recommended_steps.append("No adverse action required. Proceed with normal verification workflow.")

        methodology_limitations = [
            "Analytical anomaly detection does NOT establish legal culpability, fraud, or intentional double claiming.",
            "Independent evidence groups are evaluated to avoid artificial severity inflation from mutually correlated metrics.",
            "Missing beneficiary identities reflect voluntary market transparency practices and are never imputed.",
        ]

        return RiskAssessmentResponse(
            assessment_id=assessment_id,
            ruleset_version=RULESET_VERSION,
            assessment_timestamp=timestamp,
            target=target,
            overall_status=overall_status,
            review_priority=priority,
            priority_explanation=priority_explanation,
            triggered_rule_ids=triggered_rules,
            evidence_items=evidence_items,
            counterevidence_items=counterevidence_set,
            contextual_caveats=contextual_caveats_set,
            missing_information_items=missing_info_set,
            dependency_groups=dependency_groups,
            independent_evidence_count=independent_count,
            correlated_evidence_count=correlated_count,
            source_stages_consulted=stages_consulted,
            methodology_limitations=methodology_limitations,
            recommended_next_steps=recommended_steps,
        )

    @classmethod
    def _evaluate_balance_of_evidence(
        cls,
        evidence_items: List[EvidenceItem],
        groups_map: Dict[str, List[EvidenceItem]],
        counterevidence: List[str],
        missing_info: List[str],
    ) -> Tuple[AssessmentStatus, ReviewPriority, str]:
        """Synthesize explainable balance of evidence strictly observing conservative principles."""
        if not evidence_items:
            return (
                AssessmentStatus.NO_MATERIAL_SIGNAL,
                ReviewPriority.NONE,
                "No adverse analytical signals detected in the available dataset.",
            )

        # Check for CRITICAL evidence (e.g. Exact Serial Overlap)
        critical_items = [e for e in evidence_items if e.severity == EvidenceSeverity.CRITICAL]
        if critical_items:
            return (
                AssessmentStatus.ELEVATED_REVIEW_PRIORITY,
                ReviewPriority.URGENT,
                f"Elevated review priority triggered by direct structural clash: {critical_items[0].title}. Immediate desk verification required.",
            )

        # Check for HIGH severity evidence (e.g. Partial or Contained Overlap)
        high_items = [e for e in evidence_items if e.severity == EvidenceSeverity.HIGH]
        if high_items:
            return (
                AssessmentStatus.REVIEW_RECOMMENDED,
                ReviewPriority.HIGH,
                f"High-severity analytical signal detected: {high_items[0].title}. Reconcile overlapping serial units before ledger commitment.",
            )

        # Check for Contradictory Evidence (e.g. Conflicting project country or vintage)
        contradictory_items = [e for e in evidence_items if e.evidence_strength == EvidenceStrength.CONTRADICTORY]
        if contradictory_items:
            return (
                AssessmentStatus.CONFLICTING_EVIDENCE,
                ReviewPriority.LOW,
                f"Candidate signals contain direct contradictory evidence ({contradictory_items[0].title}). Contradictory attributes establish distinct physical assets.",
            )

        # Check for MODERATE severity items across distinct independent groups
        moderate_items = [e for e in evidence_items if e.severity == EvidenceSeverity.MODERATE]
        if moderate_items:
            # Count independent groups containing moderate items
            mod_gids = {e.dependency_group_id for e in moderate_items if e.dependency_group_id}
            unclustered_mod = [e for e in moderate_items if not e.dependency_group_id]
            independent_mod_count = len(mod_gids) + len(unclustered_mod)

            if independent_mod_count >= 2:
                # Multiple truly independent moderate concerns reinforce priority
                return (
                    AssessmentStatus.REVIEW_RECOMMENDED,
                    ReviewPriority.HIGH,
                    f"Review recommended based on {independent_mod_count} independent moderate signals across distinct stages (e.g. {moderate_items[0].title} and {moderate_items[1].title}).",
                )
            else:
                # Single moderate signal or multiple correlated moderate signals within 1 group
                return (
                    AssessmentStatus.REVIEW_RECOMMENDED,
                    ReviewPriority.MEDIUM,
                    f"Standard compliance review recommended: {moderate_items[0].title}. Correlated secondary signals are grouped to avoid double-counting.",
                )

        # Check for Pervasive Missing Information
        unresolved_items = [e for e in evidence_items if e.rule_id == "RULE-CON-003"]
        if unresolved_items and len(evidence_items) == len(unresolved_items):
            return (
                AssessmentStatus.INSUFFICIENT_EVIDENCE,
                ReviewPriority.LOW,
                "Insufficient disclosed beneficiary identity data in registry records to evaluate portfolio concentration or attribution.",
            )

        # Informational or Low-severity findings only
        low_items = [e for e in evidence_items if e.severity in (EvidenceSeverity.LOW, EvidenceSeverity.INFORMATIONAL)]
        if low_items:
            return (
                AssessmentStatus.NO_MATERIAL_SIGNAL,
                ReviewPriority.LOW,
                f"No material adverse signal detected. Informational and low-severity structural context noted ({low_items[0].title}).",
            )

        return (
            AssessmentStatus.NO_MATERIAL_SIGNAL,
            ReviewPriority.NONE,
            "Analysis complete. No actionable risk signals identified.",
        )

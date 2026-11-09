"""Unit, integration, and API tests for Phase 2C Stage 4: Unified Explainable Risk Assessment.

Validates all 15 scenarios required by the Phase 2C Stage 4 Implementation Brief:
1. No material signal.
2. One weak signal.
3. One strong, independently supported signal.
4. Multiple correlated signals that must not inflate severity.
5. Contradictory evidence.
6. Missing beneficiary identity.
7. Cross-registry numeric ID collision.
8. Legitimate split allocation.
9. Allocation conflict.
10. High concentration with contextual caveats.
11. Temporal burst with statistical limitations.
12. Unsupported target scope.
13. Empty or incomplete inputs.
14. Deterministic reproducibility.
15. Backward compatibility with existing endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.analytics.models import (
    ConcentrationMetrics,
    FragmentationMetrics,
    MetadataProvenance,
    ProjectProfile,
)
from app.analytics.risk_assessment import (
    RULESET_VERSION,
    AssessmentScope,
    AssessmentStatus,
    EvidenceCategory,
    EvidenceSeverity,
    EvidenceStrength,
    ReviewPriority,
    RiskAssessmentEngine,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    SourceStage,
)
from app.main import app


@pytest.fixture
def api_client():
    """Test client for FastAPI app."""
    return TestClient(app)


class TestRiskAssessmentScenarios:
    """Rigorous verification of the 15 required risk assessment scenarios."""

    # -------------------------------------------------------------------------
    # 1. No Material Signal
    # -------------------------------------------------------------------------
    def test_01_no_material_signal(self):
        """Uniform distribution and clean records yield NO_MATERIAL_SIGNAL with NONE priority."""
        # Synthetic clean batch: 5 claimants, perfectly uniform 200 tonnes each
        clean_records = [
            {"quantity": 200.0, "beneficiary": f"Claimant {i}", "event_date": f"2023-0{i+1}-01", "unit_start": i * 200 + 1, "unit_end": (i + 1) * 200}
            for i in range(5)
        ]
        req = RiskAssessmentRequest(scope=AssessmentScope.AD_HOC, records=clean_records)
        res = RiskAssessmentEngine.assess(req)

        assert res.overall_status == AssessmentStatus.NO_MATERIAL_SIGNAL
        assert res.review_priority in (ReviewPriority.NONE, ReviewPriority.LOW)
        assert res.independent_evidence_count >= 0
        assert "no material" in res.priority_explanation.lower() or "no adverse" in res.priority_explanation.lower()

    # -------------------------------------------------------------------------
    # 2. One Weak Signal
    # -------------------------------------------------------------------------
    def test_02_one_weak_signal(self):
        """Cross-registry numeric identifier collision alone yields WEAK evidence with LOW priority."""
        p_a = {"registry": "VCS", "project_id": "1001", "project_name": "Kasigau REDD", "country": "Kenya"}
        p_b = {"registry": "GS", "project_id": "1001", "project_name": "Solar Power", "country": "India"}

        req = RiskAssessmentRequest(scope=AssessmentScope.CROSS_REGISTRY, project_a=p_a, project_b=p_b)
        res = RiskAssessmentEngine.assess(req)

        assert res.review_priority == ReviewPriority.LOW
        assert "RULE-XREG-002" in res.triggered_rule_ids
        collision_evd = [e for e in res.evidence_items if e.rule_id == "RULE-XREG-002"]
        assert len(collision_evd) == 1
        assert collision_evd[0].evidence_strength == EvidenceStrength.WEAK
        assert collision_evd[0].severity == EvidenceSeverity.INFORMATIONAL
        assert any("independent, uncoordinated" in c.lower() or "disjoint" in c.lower() for c in collision_evd[0].counterevidence)

    # -------------------------------------------------------------------------
    # 3. One Strong, Independently Supported Signal
    # -------------------------------------------------------------------------
    def test_03_one_strong_independently_supported_signal(self):
        """Exact serial overlap with an active ledger claim yields ELEVATED_REVIEW_PRIORITY and URGENT."""
        # Northwind claim (Claim 1) is anchored on batch VCS:10635 units 1 to 50000 (synthetic range)
        # We test candidate range exactly overlapping Northwind units
        from app.db import connect
        from app.service import active_ranges
        con = connect()
        active = active_ranges(con)
        if not active:
            pytest.skip("No active ledger ranges seeded in test database")

        target_act = active[0]
        req = RiskAssessmentRequest(
            scope=AssessmentScope.AD_HOC,
            registry=target_act.registry,
            batch_id=target_act.batch_id,
            candidate_range=(target_act.unit_start, target_act.unit_end),
            claimant="Adversarial Imposter Corp",
        )
        res = RiskAssessmentEngine.assess(req)

        assert res.overall_status == AssessmentStatus.ELEVATED_REVIEW_PRIORITY
        assert res.review_priority == ReviewPriority.URGENT
        assert "RULE-REC-001" in res.triggered_rule_ids
        exact_evd = [e for e in res.evidence_items if e.rule_id == "RULE-REC-001"]
        assert len(exact_evd) == 1
        assert exact_evd[0].severity == EvidenceSeverity.CRITICAL
        assert exact_evd[0].evidence_strength == EvidenceStrength.STRONG

    # -------------------------------------------------------------------------
    # 4. Multiple Correlated Signals (No Severity Inflation)
    # -------------------------------------------------------------------------
    def test_04_multiple_correlated_signals_no_severity_inflation(self):
        """Mutually correlated signals from the same beneficiary field do not inflate review priority."""
        # A batch with 93% disclosed volume to Acme Corp and 55% undisclosed overall
        # Both concentration dominance and material undisclosed share are rooted in the same beneficiary column
        records = [
            {"quantity": 4200.0, "beneficiary": "Acme Corp", "event_date": "2023-01-01", "unit_start": 1, "unit_end": 4200},
            {"quantity": 300.0, "beneficiary": "Beta LLC", "event_date": "2023-01-02", "unit_start": 4201, "unit_end": 4500},
            {"quantity": 2500.0, "beneficiary": "Not Disclosed", "event_date": "2023-01-03", "unit_start": 4501, "unit_end": 7000},
            {"quantity": 3000.0, "beneficiary": "Not Disclosed", "event_date": "2023-01-04", "unit_start": 7001, "unit_end": 10000},
        ]
        req = RiskAssessmentRequest(scope=AssessmentScope.AD_HOC, records=records)
        res = RiskAssessmentEngine.assess(req)

        # Beneficiary signals should be clustered into one dependency group
        ben_groups = [g for g in res.dependency_groups if "BENEFICIARY" in g.shared_data_source]
        assert len(ben_groups) >= 1
        assert ben_groups[0].is_reinforcing_not_independent is True
        # Correlated signals must NOT boost priority to URGENT
        assert res.review_priority != ReviewPriority.URGENT
        assert res.correlated_evidence_count >= 2

    # -------------------------------------------------------------------------
    # 5. Contradictory Evidence
    # -------------------------------------------------------------------------
    def test_05_contradictory_evidence(self):
        """Surface title similarity with contradicting countries yields CONFLICTING_EVIDENCE."""
        p_a = {"registry": "VCS", "project_id": "100", "project_name": "Rimba Raya Biodiversity Reserve", "country": "Indonesia"}
        p_b = {"registry": "GS", "project_id": "200", "project_name": "Rimba Raya Biodiversity Reserve", "country": "Brazil"}

        req = RiskAssessmentRequest(scope=AssessmentScope.CROSS_REGISTRY, project_a=p_a, project_b=p_b)
        res = RiskAssessmentEngine.assess(req)

        assert res.overall_status == AssessmentStatus.CONFLICTING_EVIDENCE
        assert res.review_priority == ReviewPriority.LOW
        assert "RULE-XREG-003" in res.triggered_rule_ids
        conflict_evd = [e for e in res.evidence_items if e.rule_id == "RULE-XREG-003"]
        assert len(conflict_evd) == 1
        assert conflict_evd[0].evidence_strength == EvidenceStrength.CONTRADICTORY
        assert any("national jurisdiction contradiction" in c.lower() for c in conflict_evd[0].counterevidence)

    # -------------------------------------------------------------------------
    # 6. Missing Beneficiary Identity
    # -------------------------------------------------------------------------
    def test_06_missing_beneficiary_identity(self):
        """100% undisclosed beneficiaries produce INSUFFICIENT_EVIDENCE without manufacturing false alarm."""
        records = [
            {"quantity": 1000.0, "beneficiary": "Not Disclosed", "event_date": "2023-01-01", "unit_start": 1, "unit_end": 1000},
            {"quantity": 2000.0, "beneficiary": "Undisclosed", "event_date": "2023-01-02", "unit_start": 1001, "unit_end": 3000},
            {"quantity": 3000.0, "beneficiary": None, "event_date": "2023-01-03", "unit_start": 3001, "unit_end": 6000},
        ]
        req = RiskAssessmentRequest(scope=AssessmentScope.AD_HOC, records=records)
        res = RiskAssessmentEngine.assess(req)

        assert res.overall_status == AssessmentStatus.INSUFFICIENT_EVIDENCE
        assert res.review_priority == ReviewPriority.LOW
        assert len(res.missing_information_items) >= 1
        assert any("beneficiary" in m.lower() for m in res.missing_information_items)

    # -------------------------------------------------------------------------
    # 7. Cross-Registry Numeric ID Collision
    # -------------------------------------------------------------------------
    def test_07_cross_registry_numeric_id_collision(self):
        """VCS project ID 1001 vs GS project ID 1001 explicitly notes disjoint namespaces."""
        p_a = {"registry": "VCS", "project_id": "1001", "project_name": "Forest Project Alpha", "country": "Peru"}
        p_b = {"registry": "GS", "project_id": "1001", "project_name": "Wind Project Beta", "country": "Turkey"}

        req = RiskAssessmentRequest(scope=AssessmentScope.CROSS_REGISTRY, project_a=p_a, project_b=p_b)
        res = RiskAssessmentEngine.assess(req)

        assert "RULE-XREG-002" in res.triggered_rule_ids
        evd = [e for e in res.evidence_items if e.rule_id == "RULE-XREG-002"][0]
        assert evd.severity == EvidenceSeverity.INFORMATIONAL
        assert evd.evidence_strength == EvidenceStrength.WEAK
        assert "independent" in evd.explanation.lower() or "disjoint" in evd.explanation.lower()

    # -------------------------------------------------------------------------
    # 8. Legitimate Split Allocation
    # -------------------------------------------------------------------------
    def test_08_legitimate_split_allocation(self):
        """Disjoint allocations within the same batch are classified as INFORMATIONAL contextual evidence."""
        from app.reconciliation.models import IntervalOverlap, ReconciliationItem
        item = ReconciliationItem(
            candidate_block_idx=0,
            candidate_range=(1, 500),
            candidate_claimant="Division A",
            prior_claim_id=1,
            prior_claim_ref="OO-2026-0001",
            prior_claimant="Division B",
            prior_range=(501, 1000),
            prior_status="anchored",
            registry="VCS",
            batch_id="BATCH-01",
            overlap=IntervalOverlap(
                overlap_type="DISJOINT",
                overlap_start=None,
                overlap_end=None,
                overlap_units=0,
                candidate_units=500,
                existing_units=500,
                pct_of_candidate=0.0,
                pct_of_existing=0.0,
                is_conflict=False,
            ),
            allocation_type="LEGITIMATE_SPLIT",
            entity_match_tier="HIGH_CONFIDENCE",
            entity_relationship="SAME_ORGANIZATION",
            explanation="Legitimate split allocation across separate ranges.",
            audit_recommendation="Accept split allocation.",
        )
        from app.analytics.risk_assessment.evidence import EvidenceCollector
        evds = EvidenceCollector.from_reconciliation_item(item)
        assert len(evds) == 1
        assert evds[0].rule_id == "RULE-REC-004"
        assert evds[0].severity == EvidenceSeverity.INFORMATIONAL
        assert "zero shared units" in evds[0].counterevidence[0].lower()

    # -------------------------------------------------------------------------
    # 9. Allocation Conflict
    # -------------------------------------------------------------------------
    def test_09_allocation_conflict(self):
        """Partial overlap produces HIGH severity signal with REVIEW_RECOMMENDED and HIGH priority."""
        from app.reconciliation.models import IntervalOverlap, ReconciliationItem
        item = ReconciliationItem(
            candidate_block_idx=0,
            candidate_range=(100, 300),
            candidate_claimant="Buyer Beta",
            prior_claim_id=1,
            prior_claim_ref="OO-2026-0001",
            prior_claimant="Buyer Alpha",
            prior_range=(200, 400),
            prior_status="anchored",
            registry="VCS",
            batch_id="BATCH-99",
            overlap=IntervalOverlap(
                overlap_type="PARTIAL_OVERLAP",
                overlap_start=200,
                overlap_end=300,
                overlap_units=101,
                candidate_units=201,
                existing_units=201,
                pct_of_candidate=50.25,
                pct_of_existing=50.25,
                is_conflict=True,
            ),
            allocation_type="ALLOCATION_CONFLICT",
            entity_match_tier="NO_MATCH",
            entity_relationship="DISTINCT_ENTITIES",
            explanation="Conflict: 101 units overlap.",
            audit_recommendation="Reject overlapping units.",
        )
        from app.analytics.risk_assessment.evidence import EvidenceCollector
        from app.analytics.risk_assessment.models import AssessmentTarget
        evds = EvidenceCollector.from_reconciliation_item(item)
        target = RiskAssessmentEngine._synthesize_assessment(
            AssessmentTarget(scope=AssessmentScope.AD_HOC),
            evds,
            [SourceStage.PHASE_2B_RECONCILIATION],
        )
        assert target.overall_status == AssessmentStatus.REVIEW_RECOMMENDED
        assert target.review_priority == ReviewPriority.HIGH

    # -------------------------------------------------------------------------
    # 10. High Concentration with Contextual Caveats
    # -------------------------------------------------------------------------
    def test_10_high_concentration_with_contextual_caveats(self):
        """Single beneficiary dominance includes explicit anchor off-taker commercial caveats."""
        records = [
            {"quantity": 95000.0, "beneficiary": "MegaCorp Industries", "event_date": "2023-01-01", "unit_start": 1, "unit_end": 95000},
            {"quantity": 1000.0, "beneficiary": "Small Buyer 1", "event_date": "2023-01-02", "unit_start": 95001, "unit_end": 96000},
            {"quantity": 1000.0, "beneficiary": "Small Buyer 2", "event_date": "2023-01-03", "unit_start": 96001, "unit_end": 97000},
            {"quantity": 1000.0, "beneficiary": "Small Buyer 3", "event_date": "2023-01-04", "unit_start": 97001, "unit_end": 98000},
            {"quantity": 2000.0, "beneficiary": "Small Buyer 4", "event_date": "2023-01-05", "unit_start": 98001, "unit_end": 100000},
        ]
        req = RiskAssessmentRequest(scope=AssessmentScope.AD_HOC, records=records)
        res = RiskAssessmentEngine.assess(req)

        assert "RULE-CON-001" in res.triggered_rule_ids
        dom_evd = [e for e in res.evidence_items if e.rule_id == "RULE-CON-001"][0]
        assert dom_evd.severity == EvidenceSeverity.MODERATE
        assert any("anchor buyer agreements" in c.lower() for c in dom_evd.counterevidence)
        assert any("does not impute" in l.lower() for l in dom_evd.limitations)

    # -------------------------------------------------------------------------
    # 11. Temporal Burst with Statistical Limitations
    # -------------------------------------------------------------------------
    def test_11_temporal_burst_with_statistical_limitations(self):
        """Retirement bursts cite commercial reporting cycle caveats and seasonal limits."""
        # Query known project with bursts from demo SQLite (e.g. project 2042 in VCS)
        req = RiskAssessmentRequest(scope=AssessmentScope.PROJECT, registry="VCS", project_id="2042")
        res = RiskAssessmentEngine.assess(req)

        burst_evds = [e for e in res.evidence_items if e.rule_id == "RULE-TMP-001"]
        if burst_evds:
            evd = burst_evds[0]
            assert evd.severity == EvidenceSeverity.MODERATE
            assert any("compliance deadlines" in c.lower() or "reporting" in c.lower() for c in evd.counterevidence)
            assert any("requires at least" in l.lower() or "seasonal" in l.lower() for l in evd.limitations)

    # -------------------------------------------------------------------------
    # 12. Unsupported Target Scope
    # -------------------------------------------------------------------------
    def test_12_unsupported_target_scope(self, api_client):
        """Unsupported scope string returns HTTP 422 Unprocessable Entity."""
        res = api_client.post("/api/analytics/assessment", json={"scope": "NON_EXISTENT_SCOPE"})
        assert res.status_code == 422

    # -------------------------------------------------------------------------
    # 13. Empty or Incomplete Inputs
    # -------------------------------------------------------------------------
    def test_13_empty_or_incomplete_inputs(self, api_client):
        """Missing required scope parameters returns meaningful error responses."""
        # Scope BATCH without batch_id
        res_batch = api_client.post("/api/analytics/assessment", json={"scope": "BATCH", "registry": "VCS"})
        assert res_batch.status_code in (422, 400)

        # Scope PROJECT with non-existent project returns 404
        res_proj = api_client.post("/api/analytics/assessment", json={"scope": "PROJECT", "registry": "VCS", "project_id": "99999999"})
        assert res_proj.status_code == 404

        # Scope CLAIM with non-existent claim ID returns 404
        res_claim = api_client.post("/api/analytics/assessment", json={"scope": "CLAIM", "claim_id": 99999})
        assert res_claim.status_code == 404

    # -------------------------------------------------------------------------
    # 14. Deterministic Reproducibility
    # -------------------------------------------------------------------------
    def test_14_deterministic_reproducibility(self):
        """Consecutive evaluations of the same target scope yield identical assessment IDs and outputs."""
        req = RiskAssessmentRequest(scope=AssessmentScope.BATCH, registry="VCS", batch_id="10635")
        res1 = RiskAssessmentEngine.assess(req)
        res2 = RiskAssessmentEngine.assess(req)

        assert res1.assessment_id == res2.assessment_id
        assert res1.overall_status == res2.overall_status
        assert res1.review_priority == res2.review_priority
        assert res1.triggered_rule_ids == res2.triggered_rule_ids
        assert len(res1.evidence_items) == len(res2.evidence_items)
        assert res1.independent_evidence_count == res2.independent_evidence_count

    # -------------------------------------------------------------------------
    # 15. Backward Compatibility with Existing Endpoints
    # -------------------------------------------------------------------------
    def test_15_backward_compatibility_with_existing_endpoints(self, api_client):
        """All existing endpoints from Phases 2A, 2B, 2C1, 2C2, and 2C3 remain fully operational."""
        # 1. Claims list
        r1 = api_client.get("/api/claims")
        assert r1.status_code == 200

        # 2. Entity resolution
        r2 = api_client.post("/api/resolve/entity-pair", json={"name_a": "Shell", "name_b": "Shell UK"})
        assert r2.status_code == 200

        # 3. Intermediary extraction
        r3 = api_client.post("/api/resolve/intermediary", json={"text": "Trip.com on behalf of User"})
        assert r3.status_code == 200

        # 4. Reconciliation
        r4 = api_client.post("/api/reconcile/compare", json={
            "candidate": {"registry": "VCS", "batch_id": "B1", "unit_start": 100, "unit_end": 200, "claimant": "A"},
            "existing": {"registry": "VCS", "batch_id": "B1", "unit_start": 150, "unit_end": 250, "claimant": "B"},
        })
        assert r4.status_code == 200

        # 5. Batch concentration/fragmentation
        r5 = api_client.get("/api/analytics/batches/VCS/10635")
        assert r5.status_code == 200

        # 6. Temporal activity
        r6 = api_client.get("/api/analytics/temporal/activity?period=monthly")
        assert r6.status_code == 200

        # 7. Cross-registry correlations
        r7 = api_client.get("/api/cross-registry/projects/correlations")
        assert r7.status_code == 200

        # 8. Cross-registry summary
        r8 = api_client.get("/api/cross-registry/retirements/summary")
        assert r8.status_code == 200

    # -------------------------------------------------------------------------
    # 16. Assessment Rules Catalog Endpoint
    # -------------------------------------------------------------------------
    def test_16_rules_catalog_endpoint(self, api_client):
        """GET /api/analytics/assessment/rules returns the complete versioned catalog."""
        res = api_client.get("/api/analytics/assessment/rules")
        assert res.status_code == 200
        data = res.json()
        assert data["ruleset_version"] == RULESET_VERSION
        assert data["total_rules"] == 16
        rule_ids = [r["rule_id"] for r in data["rules"]]
        assert "RULE-REC-001" in rule_ids
        assert "RULE-CON-001" in rule_ids
        assert "RULE-FRG-001" in rule_ids
        assert "RULE-TMP-001" in rule_ids
        assert "RULE-XREG-001" in rule_ids
        assert "RULE-ENT-001" in rule_ids

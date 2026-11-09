"""Comprehensive test suite for OnceOnly Entity Resolution & Intermediary Subsystem."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.entity_resolution import (
    EntityCandidateGenerator,
    EntityMatcher,
    EntityName,
    EntityNormalizer,
    EntityResolutionEngine,
    IntermediaryExtractor,
    IntermediaryRole,
    MatchTier,
    RelationshipType,
)
from app.main import app

client = TestClient(app)


# ==============================================================================
# 1. Normalization & Provenance Tests
# ==============================================================================

def test_canonical_legal_suffix_extraction():
    cases = [
        ("Acme Industries Ltd.", "ltd", "acme industries"),
        ("ACME INDUSTRIES LIMITED", "ltd", "acme industries"),
        ("Acme Corp.", "corp", "acme"),
        ("Acme Corporation", "corp", "acme"),
        ("Acme Inc.", "inc", "acme"),
        ("Acme Incorporated", "inc", "acme"),
        ("Acme LLC", "llc", "acme"),
        ("Siemens AG", "ag", "siemens"),
        ("natureOffice GmbH", "gmbh", "natureoffice"),
        ("Minerva S.A.", "sa", "minerva"),
        ("Enel S.p.A.", "spa", "enel"),
        ("UNLSH Mobility B.V.", "bv", "unlsh mobility"),
        ("RISEL COMBUSTIVEIS LTDA", "ltda", "risel combustiveis"),
        ("Webjet Marketing Pty Ltd", "pvt ltd", "webjet marketing"),
        ("Tata Consultancy Services Pvt Ltd", "pvt ltd", "tata consultancy services"),
    ]
    for raw, expected_suffix, expected_canon in cases:
        ent = EntityNormalizer.normalize(raw)
        assert ent.legal_suffix == expected_suffix, f"Failed suffix for '{raw}': got '{ent.legal_suffix}'"
        assert ent.canonical_name == expected_canon, f"Failed canon for '{raw}': got '{ent.canonical_name}'"
        assert ent.raw_value == raw
        assert not ent.is_placeholder
        assert any("legal_suffix_extracted" in op for op in ent.operations)


def test_abbreviation_expansion():
    ent = EntityNormalizer.normalize("Global Tech & Intl Mfg Solns Ltd")
    assert ent.canonical_name == "global technology international manufacturing solutions"
    assert "technology" in ent.tokens
    assert "international" in ent.tokens
    assert "manufacturing" in ent.tokens
    assert "solutions" in ent.tokens


def test_mojibake_and_unicode_normalization():
    # Mojibake curly apostrophe
    ent1 = EntityNormalizer.normalize("Patch‚Äôs Green Desk")
    assert "Patch’s" in (ent1.normalized_value or "") or "patch" in ent1.canonical_name

    # Diacritics
    ent2 = EntityNormalizer.normalize("Société Générale S.A.")
    assert ent2.canonical_name == "societe generale"
    assert "société" in (ent2.normalized_value or "").lower()
    assert ent2.legal_suffix == "sa"


def test_placeholder_classification():
    placeholders = ["Not Disclosed", "undisclosed", "N/A", "Confidential", "None", "", "   "]
    for p in placeholders:
        ent = EntityNormalizer.normalize(p)
        assert ent.is_placeholder is True
        assert ent.canonical_name == ""


# ==============================================================================
# 2. Intermediary & Allocation Extraction Tests
# ==============================================================================

def test_bilateral_intermediary_delegation():
    # Real VROD string
    raw = "TBK Group on behalf of Lenovo"
    rel = IntermediaryExtractor.extract(raw)
    assert rel.is_delegated is True
    assert rel.intermediary_raw == "TBK Group"
    assert rel.principal_raw == "Lenovo"
    assert rel.role == IntermediaryRole.BROKER_OR_TRADER.value
    assert rel.principal_entity is not None and rel.principal_entity.canonical_name == "lenovo"
    assert rel.intermediary_entity is not None and rel.intermediary_entity.canonical_name == "tbk group"


def test_direct_action_not_flagged_as_intermediary():
    # "Retired on behalf of: Acme Corp" -> "Retired" is not an intermediary broker
    raw = "Retired on behalf of: Acme Corp"
    rel = IntermediaryExtractor.extract(raw)
    assert rel.is_delegated is False
    assert rel.principal_raw == "Acme Corp"
    assert rel.intermediary_raw is None
    assert rel.role == IntermediaryRole.DIRECT.value


def test_customer_pool_allocation():
    cases = [
        ("On behalf of Patch's customers and their end users", "Patch"),
        ("ClimeCo Green Customers", "ClimeCo"),
        ("Trip.com customers", "Trip.com"),
    ]
    for raw, expected_int in cases:
        rel = IntermediaryExtractor.extract(raw)
        assert rel.is_delegated is True
        assert rel.role == IntermediaryRole.CUSTOMER_POOL.value
        assert rel.intermediary_raw == expected_int


def test_trailing_purpose_clause_stripping():
    raw = "Retired on behalf of easyJet for aviation Scope 1 CO2e and easyJet holidays Scope 3 emissions"
    rel = IntermediaryExtractor.extract(raw)
    assert rel.principal_raw == "easyJet"
    assert rel.principal_entity is not None and rel.principal_entity.canonical_name == "easyjet"


# ==============================================================================
# 3. Explainable Similarity & Relationship Matching Tests
# ==============================================================================

def test_exact_match_and_canonical_variants():
    # Same name, different suffix spelling
    res = EntityResolutionEngine.resolve_pair("Acme Industries Limited", "ACME INDUSTRIES LTD.")
    assert res.overall_score == 100.0
    assert res.match_tier == MatchTier.HIGH_CONFIDENCE.value
    assert res.relationship_type == RelationshipType.CANONICAL_VARIANT.value
    assert res.is_match is True
    assert len(res.positive_signals) >= 1
    assert not res.contradictory_signals


def test_hard_negative_sector_conflict():
    # Shared root "Acme", but conflicting domain tokens "Solar" vs "Wind"
    res = EntityResolutionEngine.resolve_pair("Acme Solar LLC", "Acme Wind LLC")
    assert res.overall_score < 50.0
    assert res.match_tier == MatchTier.INSUFFICIENT_EVIDENCE.value
    assert res.relationship_type == RelationshipType.DIFFERENT_ENTITIES.value
    assert res.is_match is False
    assert any("Conflicting industry/sector tokens" in c for c in res.contradictory_signals)


def test_hard_negative_number_conflict():
    # Similar string with different client IDs
    res = EntityResolutionEngine.resolve_pair("Customer 10184", "Customer 10185")
    assert res.overall_score < 50.0
    assert res.relationship_type == RelationshipType.DIFFERENT_ENTITIES.value
    assert res.is_match is False
    assert any("Mismatched numeric identifiers" in c for c in res.contradictory_signals)


def test_hard_negative_distinct_companies():
    # Brand overlap with completely different businesses
    res1 = EntityResolutionEngine.resolve_pair("Delta Air Lines Inc.", "Delta Electronics Inc.")
    assert res1.is_match is False
    assert res1.relationship_type == RelationshipType.DIFFERENT_ENTITIES.value

    res2 = EntityResolutionEngine.resolve_pair("Apple Inc.", "Applied Materials Inc.")
    assert res2.is_match is False


def test_corporate_hierarchy_subsidiary():
    # Parent vs regional subsidiary
    res = EntityResolutionEngine.resolve_pair("Microsoft Corporation", "Microsoft Ireland Operations Ltd")
    assert res.relationship_type == RelationshipType.CORPORATE_HIERARCHY_OR_SUBSIDIARY.value
    assert res.match_tier == MatchTier.MEDIUM_CONFIDENCE.value
    assert res.is_match is True
    assert "ireland" in res.explanation


def test_placeholder_resolution_insufficient_evidence():
    res = EntityResolutionEngine.resolve_pair("Shell PLC", "Not Disclosed")
    assert res.overall_score == 0.0
    assert res.match_tier == MatchTier.INSUFFICIENT_EVIDENCE.value
    assert res.relationship_type == RelationshipType.UNRESOLVED.value
    assert res.is_match is False


def test_intermediary_delegation_resolution():
    # Claimant matches beneficial principal in intermediary retirement
    res = EntityResolutionEngine.resolve_pair("Lenovo", "TBK Group on behalf of Lenovo")
    assert res.overall_score >= 90.0
    assert res.relationship_type == RelationshipType.INTERMEDIARY_DELEGATION.value
    assert res.match_tier == MatchTier.HIGH_CONFIDENCE.value
    assert res.is_match is True
    assert res.intermediary_context is not None
    assert res.intermediary_context.intermediary_raw == "TBK Group"


# ==============================================================================
# 4. Candidate Generation & Blocking Tests
# ==============================================================================

def test_blocking_efficiency_and_candidate_reduction():
    claimants = ["Acme Industries", "Delta Air Lines", "Siemens"]
    registry = [
        "ACME INDUSTRIES LTD", "Delta Electronics", "Siemens AG",
        "Shell PLC", "Unrelated Solar", "Another Entity Ltd",
    ]
    c_ents = [EntityNormalizer.normalize(c) for c in claimants]
    r_ents = [EntityNormalizer.normalize(r) for r in registry]

    candidates = EntityCandidateGenerator.generate_candidate_pairs(c_ents, r_ents)
    # Total pairs = 3 * 6 = 18. Candidates generated should be strictly fewer (e.g. 3-4 pairs)
    assert len(candidates) < 18
    metrics = EntityCandidateGenerator.blocking_metrics(len(claimants), len(registry), len(candidates))
    assert metrics["reduction_percent"] >= 75.0

    # Ensure true match candidates were captured
    pairs_captured = {(c.canonical_name, r.canonical_name) for c, r, _ in candidates}
    assert ("acme industries", "acme industries") in pairs_captured
    assert ("siemens", "siemens") in pairs_captured


# ==============================================================================
# 5. Registry Ranking & API Tests
# ==============================================================================

def test_resolve_claimant_against_registry_ranking():
    bens = ["Unrelated Co", "ACME INDUSTRIES LTD", "Acme Solar LLC"]
    matches = EntityResolutionEngine.resolve_claimant_against_registry("Acme Industries", bens)
    assert len(matches) == 3
    # Top match should be ACME INDUSTRIES LTD with high score
    assert matches[0].entity_b.raw_value == "ACME INDUSTRIES LTD"
    assert matches[0].overall_score >= 95.0
    # Acme Solar should have lower score due to sector conflict
    assert matches[1].entity_b.raw_value == "Acme Solar LLC" or matches[2].entity_b.raw_value == "Acme Solar LLC"


def test_api_entity_pair_endpoint():
    resp = client.post("/api/resolve/entity-pair", json={
        "name_a": "Minerva S.A.",
        "name_b": "MINERVA SA",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] == 100.0
    assert data["relationship_type"] == "CANONICAL_VARIANT"
    assert data["is_match"] is True
    assert "token_set_ratio" in data["feature_scores"]


def test_api_intermediary_endpoint():
    resp = client.post("/api/resolve/intermediary", json={
        "text": "GP-31 - On behalf of Telefonica Brazil - 2021 emissions",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_delegated"] is True
    assert data["principal_raw"] == "Telefonica Brazil"
    assert data["intermediary_raw"] == "GP-31"
    assert data["role"] == "BROKER_OR_TRADER"

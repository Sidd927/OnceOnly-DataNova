"""Comprehensive test suite for Phase 2C Stage 3: Cross-Registry Intelligence.

Covers:
1. Project comparison logic & correlation category taxonomy:
   - EXACT_IDENTIFIER_MATCH (noting disjoint namespaces for cross-registry)
   - STRONG_ATTRIBUTE_CORRELATION
   - PARTIAL_ATTRIBUTE_CORRELATION
   - NAME_SIMILARITY_ONLY
   - CONFLICTING_ATTRIBUTES (contradictory countries / disjoint vintages)
   - INSUFFICIENT_EVIDENCE
2. Candidate generation and ranking across Verra VCS and Gold Standard.
3. Cross-registry entity comparison with Phase 2A integration and legal entity disclaimers.
4. Cross-registry retirement summary statistics and strict issuance exclusion (669 excluded).
5. Cross-registry retirement pacing and trend time series (yearly and monthly).
6. Adversarial and boundary safety invariants:
   - Serial Isolation Invariant (disjoint namespaces, never equating serial numbers across registries)
   - Missing fields handling (developer/project_type/methodology absent without hallucinating confidence)
   - Geographic jurisdiction conflicts
7. REST API endpoint responses and validation error handling (HTTP 200, HTTP 422).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.analytics import (
    CROSS_REGISTRY_DISCLAIMER,
    AnalyticsEngine,
    CrossRegistryCorrelationsResponse,
    CrossRegistryEntityComparison,
    CrossRegistryProjectComparison,
    CrossRegistryRetirementSummary,
    CrossRegistryTrendsResponse,
    EvidenceStrength,
    MetadataProvenance,
    ProjectCorrelationCategory,
    ProjectProfile,
    compare_countries,
    compare_cross_registry_entities,
    compare_projects,
    compare_vintages,
    correlate_registry_projects,
    get_cross_registry_retirement_summary,
    get_cross_registry_retirement_trends,
    normalize_project_name,
)
from app.main import app

client = TestClient(app)


# ==============================================================================
# SECTION 1: PROJECT COMPARISON & CORRELATION TAXONOMY TESTS
# ==============================================================================

class TestProjectComparison:
    """Tests for pairwise project attribute comparison and categorization."""

    def test_exact_identifier_cross_registry(self):
        """Cross-registry identical IDs must be categorized as CROSS_REGISTRY_IDENTIFIER_COLLISION."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="1001",
            project_name="Rimba Raya Biodiversity Reserve",
            country="Indonesia",
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="1001",
            project_name="Kasigau Corridor REDD Project",
            country="Kenya",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.CROSS_REGISTRY_IDENTIFIER_COLLISION
        assert res.is_cross_registry is True
        assert res.identifier_match is True
        # Must note namespace disjointness in conflicting attributes or explanation
        assert any("disjoint" in note.lower() for note in res.conflicting_attributes)

    def test_cross_registry_collision_matching_name_country_not_exact_match(self):
        """Matching name and country must NOT silently turn cross-registry collision into EXACT_IDENTIFIER_MATCH."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="1001",
            project_name="Rimba Raya Biodiversity Reserve",
            country="Indonesia",
            vintage="2020",
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="1001",
            project_name="Rimba Raya Biodiversity Reserve",
            country="Indonesia",
            vintage="2020",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.CROSS_REGISTRY_IDENTIFIER_COLLISION
        assert res.correlation_category != ProjectCorrelationCategory.EXACT_IDENTIFIER_MATCH
        assert res.is_cross_registry is True

    def test_cross_registry_different_identifiers(self):
        """Different project IDs across registries report identifier_match=False."""
        p_a = ProjectProfile(registry="VCS", project_id="VCS-101", project_name="Wind A", country="India")
        p_b = ProjectProfile(registry="GS", project_id="GS-202", project_name="Wind B", country="India")
        res = compare_projects(p_a, p_b)
        assert res.identifier_match is False
        assert any("Different Project IDs" in note for note in res.conflicting_attributes)

    def test_exact_similarity_formula_40_30_30(self):
        """Verify the exact 40/30/30 composite similarity weighting."""
        from app.analytics.cross_registry import calculate_project_name_similarity
        name1 = "Adani Renewable Wind Power Project"
        name2 = "DDWL Renewable Energy Power Project"
        comp, s_set, s_sort, jw, t1, t2 = calculate_project_name_similarity(name1, name2)
        expected = 0.40 * s_set + 0.30 * s_sort + 0.30 * jw
        assert abs(comp - expected) < 1e-6

    def test_exact_identifier_same_registry(self):
        """Same-registry identical IDs reflect the same registry record."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="1001",
            project_name="Rimba Raya Biodiversity Reserve",
            country="Indonesia",
        )
        p_b = ProjectProfile(
            registry="VCS",
            project_id="1001",
            project_name="Rimba Raya Biodiversity Reserve Phase 2",
            country="Indonesia",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.EXACT_IDENTIFIER_MATCH
        assert res.is_cross_registry is False
        assert res.identifier_match is True
        assert any("identical" in note.lower() for note in res.matching_attributes)

    def test_strong_attribute_correlation(self):
        """High title similarity, matching country, and overlapping vintage yields STRONG."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="VCS-888",
            project_name="Rimba Raya Biodiversity Reserve Project",
            country="Indonesia",
            vintage="2016-2020",
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="GS-999",
            project_name="Rimba Raya Biodiversity Reserve",
            country="Indonesia",
            vintage="2018-2021",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.STRONG_ATTRIBUTE_CORRELATION
        assert res.evidence_strength == EvidenceStrength.STRONG
        assert res.name_similarity_score >= 0.85
        assert res.country_relation == "MATCH"
        assert res.vintage_relation == "OVERLAP"
        assert len(res.matching_attributes) >= 3

    def test_partial_attribute_correlation(self):
        """Moderate title similarity with matching country yields PARTIAL correlation."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="2042",
            project_name="Renewable Wind Power Project by Adani",
            country="India",
            vintage="2019 - 2023",
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="5673",
            project_name="Renewable Energy Power project by DDWL",
            country="India",
            vintage="2020 - 2021",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.PARTIAL_ATTRIBUTE_CORRELATION
        assert res.evidence_strength == EvidenceStrength.MODERATE
        assert res.country_relation == "MATCH"

    def test_name_similarity_only(self):
        """High title similarity without confirming country or vintage yields NAME_SIMILARITY_ONLY."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="VCS-101",
            project_name="Amazon Reforestation Community Carbon Initiative",
            country=None,
            vintage=None,
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="GS-202",
            project_name="Amazon Reforestation Community Carbon Project",
            country=None,
            vintage=None,
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.NAME_SIMILARITY_ONLY
        assert res.evidence_strength == EvidenceStrength.WEAK
        assert "Developer/proponent information missing" in " ".join(res.missing_attributes)

    def test_conflicting_country_attributes(self):
        """Surface title similarity with contradicting national jurisdictions yields CONFLICTING."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="VCS-301",
            project_name="Renewable Solar Energy Power Generation Project",
            country="India",
            vintage="2020",
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="GS-402",
            project_name="Renewable Solar Energy Power Generation Plant",
            country="Brazil",
            vintage="2020",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.CONFLICTING_ATTRIBUTES
        assert res.evidence_strength == EvidenceStrength.CONTRADICTORY
        assert res.country_relation == "CONFLICT"
        assert any("Conflicting country jurisdiction" in c for c in res.conflicting_attributes)

    def test_conflicting_vintages(self):
        """Same country but widely disjoint vintages (>5 year gap) yields CONFLICTING."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="VCS-501",
            project_name="Karnataka Clean Energy Wind Farm",
            country="India",
            vintage="2005",
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="GS-602",
            project_name="Karnataka Clean Energy Wind Project",
            country="India",
            vintage="2024",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.CONFLICTING_ATTRIBUTES
        assert res.evidence_strength == EvidenceStrength.CONTRADICTORY
        assert res.vintage_relation == "DISJOINT"

    def test_insufficient_evidence(self):
        """Dissimilar project names (<65% similarity) yield INSUFFICIENT_EVIDENCE."""
        p_a = ProjectProfile(
            registry="VCS",
            project_id="VCS-111",
            project_name="Southern Cardamom REDD+ Project",
            country="Cambodia",
        )
        p_b = ProjectProfile(
            registry="GS",
            project_id="GS-222",
            project_name="Safe Water Supply in Rwanda",
            country="Rwanda",
        )
        res = compare_projects(p_a, p_b)
        assert res.correlation_category == ProjectCorrelationCategory.INSUFFICIENT_EVIDENCE
        assert res.evidence_strength == EvidenceStrength.INSUFFICIENT
        assert res.name_similarity_score < 0.65


# ==============================================================================
# SECTION 2: CROSS-REGISTRY CORRELATIONS CENSUS & FILTERING TESTS
# ==============================================================================

class TestCrossRegistryCensus:
    """Tests for multi-project pairwise evaluation across Verra and Gold Standard."""

    def test_census_evaluation_count(self):
        """Census evaluates all 16 VCS projects against all 6 GS projects (96 pairs)."""
        resp = correlate_registry_projects(min_similarity=0.50, limit=100)
        assert isinstance(resp, CrossRegistryCorrelationsResponse)
        assert resp.total_candidates_evaluated == 96
        assert resp.matched_candidates_count >= 1
        assert len(resp.correlations) == resp.matched_candidates_count
        assert resp.disclaimer == CROSS_REGISTRY_DISCLAIMER

    def test_category_filter(self):
        """Filtering by category returns only the requested category."""
        resp = correlate_registry_projects(
            min_similarity=0.50,
            category_filter="PARTIAL_ATTRIBUTE_CORRELATION",
            limit=50,
        )
        for c in resp.correlations:
            assert c.correlation_category == ProjectCorrelationCategory.PARTIAL_ATTRIBUTE_CORRELATION

    def test_category_filter_identifier_collision(self):
        """Category filter supports CROSS_REGISTRY_IDENTIFIER_COLLISION without error."""
        resp = correlate_registry_projects(
            min_similarity=0.0,
            category_filter="CROSS_REGISTRY_IDENTIFIER_COLLISION",
            limit=10,
        )
        assert resp.category_filter == "CROSS_REGISTRY_IDENTIFIER_COLLISION"
        for c in resp.correlations:
            assert c.correlation_category == ProjectCorrelationCategory.CROSS_REGISTRY_IDENTIFIER_COLLISION

    def test_country_filter(self):
        """Filtering by country returns only correlations where at least one project matches."""
        resp = correlate_registry_projects(
            min_similarity=0.50,
            country_filter="India",
            limit=50,
        )
        for c in resp.correlations:
            assert c.project_a.country == "India" or c.project_b.country == "India"

    def test_ranking_order(self):
        """Candidate correlations are ranked by name similarity score descending."""
        resp = correlate_registry_projects(min_similarity=0.50, limit=50)
        scores = [c.name_similarity_score for c in resp.correlations]
        assert scores == sorted(scores, reverse=True)


# ==============================================================================
# SECTION 3: ENTITY RESOLUTION ACROSS REGISTRIES
# ==============================================================================

class TestCrossRegistryEntityResolution:
    """Tests for entity matching across registries leveraging Phase 2A engine."""

    def test_exact_entity_match(self):
        """Identical legal entity string across registries."""
        res = compare_cross_registry_entities(
            entity_a="Shell",
            entity_b="Shell",
            registry_a="VCS",
            registry_b="GS",
        )
        assert isinstance(res, CrossRegistryEntityComparison)
        assert res.is_match is True
        assert res.entity_normalized_a == "shell"
        assert res.entity_normalized_b == "shell"
        assert "disclaimer" in res.to_dict()

    def test_corporate_hierarchy_variation(self):
        """Parent vs subsidiary entity strings."""
        res = compare_cross_registry_entities(
            entity_a="Shell",
            entity_b="Shell International Petroleum Co Ltd",
            registry_a="VCS",
            registry_b="GS",
        )
        assert res.is_match is True
        assert res.relationship_type == "CORPORATE_HIERARCHY_OR_SUBSIDIARY"
        assert res.overall_score >= 60.0

    def test_intermediary_attribution(self):
        """Delegated beneficiary format with broker or intermediary prefix."""
        res = compare_cross_registry_entities(
            entity_a="Trip.com customers",
            entity_b="Trip.com",
            registry_a="VCS",
            registry_b="GS",
        )
        assert res.is_match is True
        assert res.relationship_type == "INTERMEDIARY_DELEGATION"

    def test_distinct_entities(self):
        """Unrelated corporate entities across registries."""
        res = compare_cross_registry_entities(
            entity_a="Shell",
            entity_b="Microsoft Corporation",
            registry_a="VCS",
            registry_b="GS",
        )
        assert res.is_match is False
        assert res.relationship_type == "DIFFERENT_ENTITIES"


# ==============================================================================
# SECTION 4: CROSS-REGISTRY RETIREMENT SUMMARY TESTS
# ==============================================================================

class TestCrossRegistryRetirementSummary:
    """Tests for aggregated retirement metrics across Verra VCS and Gold Standard."""

    def test_summary_census_values(self):
        """Verify exact retirement record counts and tonnage excluding issuances."""
        summary = get_cross_registry_retirement_summary()
        assert isinstance(summary, CrossRegistryRetirementSummary)

        # VCS metrics
        vcs = summary.registries["VCS"]
        assert vcs.total_retirement_records == 30111
        assert vcs.total_retired_tonnes == 79964179.0
        assert vcs.active_projects_count == 16
        assert vcs.issuance_records_excluded == 669

        # GS metrics
        gs = summary.registries["GS"]
        assert gs.total_retirement_records == 7224
        assert gs.total_retired_tonnes == 7704151.0
        assert gs.active_projects_count == 6
        assert gs.issuance_records_excluded == 0

        # Combined metrics
        assert summary.combined_retirement_records == 37335
        assert summary.combined_retired_tonnes == 87668330.0
        assert summary.total_issuance_records_excluded == 669

    def test_disclosure_rates(self):
        """Verify transparency / disclosure rates computed on non-placeholder volume."""
        summary = get_cross_registry_retirement_summary()
        vcs = summary.registries["VCS"]
        gs = summary.registries["GS"]

        # VCS disclosed quantity rate ~43.44%
        assert round(vcs.beneficiary_quantity_disclosure_rate_pct, 1) == 43.4
        assert round(vcs.quantity_disclosure_rate_pct, 1) == 43.4  # Deprecated alias
        assert round(vcs.beneficiary_record_disclosure_rate_pct, 1) == 44.5
        assert round(vcs.record_disclosure_rate_pct, 1) == 44.5  # Deprecated alias

        # GS disclosed quantity rate ~7.69%
        assert round(gs.beneficiary_quantity_disclosure_rate_pct, 1) == 7.7
        assert round(gs.quantity_disclosure_rate_pct, 1) == 7.7  # Deprecated alias
        assert round(gs.beneficiary_record_disclosure_rate_pct, 1) == 7.3
        assert round(gs.record_disclosure_rate_pct, 1) == 7.3  # Deprecated alias

        # Comparability notes generated
        assert len(summary.comparability_notes) >= 2


# ==============================================================================
# SECTION 5: CROSS-REGISTRY RETIREMENT TRENDS TESTS
# ==============================================================================

class TestCrossRegistryRetirementTrends:
    """Tests for comparative pacing time series."""

    def test_yearly_trends(self):
        """Verify yearly trend series spanning 2010 through 2026."""
        resp = get_cross_registry_retirement_trends(period_type="yearly")
        assert isinstance(resp, CrossRegistryTrendsResponse)
        assert resp.period_type == "yearly"
        assert resp.total_periods == 17

        # Total combined tonnes across all periods must equal 87,668,330
        sum_tonnes = sum(p.combined_total_tonnes for p in resp.trends)
        assert round(sum_tonnes, 2) == 87668330.0

        # Total combined records across all periods must equal 37,335
        sum_records = sum(p.combined_record_count for p in resp.trends)
        assert sum_records == 37335

    def test_monthly_trends(self):
        """Verify monthly trend series."""
        resp = get_cross_registry_retirement_trends(period_type="monthly")
        assert resp.period_type == "monthly"
        assert resp.total_periods > 100
        # Check first period
        first = resp.trends[0]
        assert first.period_label.startswith("2010-")


# ==============================================================================
# SECTION 6: ADVERSARIAL CASES & SAFETY INVARIANTS
# ==============================================================================

class TestSafetyInvariants:
    """Tests ensuring data integrity, serial isolation, and missing field handling."""

    def test_serial_isolation_invariant(self):
        """Serial numbers and IDs from different registries belong to disjoint namespaces."""
        # Both registries could have serial "1-100", but they are NOT equivalent units
        vcs_p = ProjectProfile(registry="VCS", project_id="100", project_name="VCS Wind")
        gs_p = ProjectProfile(registry="GS", project_id="100", project_name="GS Wind")
        res = compare_projects(vcs_p, gs_p)

        # The project IDs match, but because registries differ, must document disjoint namespaces
        assert res.is_cross_registry is True
        assert res.correlation_category == ProjectCorrelationCategory.CROSS_REGISTRY_IDENTIFIER_COLLISION
        assert any("disjoint" in note.lower() for note in res.conflicting_attributes)

    def test_project_profile_provenance_database_census(self):
        """Database-queried profiles must carry MetadataProvenance.DATABASE_CENSUS."""
        resp = correlate_registry_projects(min_similarity=0.5, limit=5)
        assert len(resp.correlations) > 0
        for c in resp.correlations:
            assert c.project_a.provenance == MetadataProvenance.DATABASE_CENSUS
            assert c.project_b.provenance == MetadataProvenance.DATABASE_CENSUS

    def test_project_profile_provenance_ad_hoc_input(self):
        """Ad-hoc API inputs default to MetadataProvenance.AD_HOC_API_INPUT."""
        p = ProjectProfile(registry="VCS", project_id="VCS-1", project_name="Test Project")
        assert p.provenance == MetadataProvenance.AD_HOC_API_INPUT
        d = p.model_dump()
        assert d["provenance"] == "AD_HOC_API_INPUT"

    def test_project_profile_mixed_metadata_preservation(self):
        """Caller-supplied metadata fields are preserved without claiming DB origin."""
        p = ProjectProfile(
            registry="VCS",
            project_id="VCS-99",
            project_name="Solar Project",
            developer="Solar Corp Inc",
            project_type="Renewable Energy",
            methodology="ACM0002",
        )
        assert p.provenance == MetadataProvenance.AD_HOC_API_INPUT
        assert p.developer == "Solar Corp Inc"
        assert p.project_type == "Renewable Energy"
        assert p.methodology == "ACM0002"

    def test_unpopulated_fields_no_hallucination(self):
        """When developer/methodology are missing, they must be marked in missing_attributes."""
        p_a = ProjectProfile(registry="VCS", project_id="1", project_name="Solar Alpha")
        p_b = ProjectProfile(registry="GS", project_id="2", project_name="Solar Beta")
        res = compare_projects(p_a, p_b)

        assert res.developer_similarity is None
        assert "Developer/proponent information missing from one or both projects" in res.missing_attributes

    def test_country_comparison_variants(self):
        """ISO codes and variant country representations normalize correctly."""
        assert compare_countries("Indonesia", "ID")[0] == "MATCH"
        assert compare_countries("United States", "USA")[0] == "MATCH"
        assert compare_countries("India", "Brazil")[0] == "CONFLICT"
        assert compare_countries("India", None)[0] == "MISSING"

    def test_vintage_comparison_variants(self):
        """Vintage single years and ranges compare correctly."""
        assert compare_vintages(2020, "2019-2021")[0] == "OVERLAP"
        assert compare_vintages("2015-2018", "2019-2022")[0] == "ADJACENT"
        assert compare_vintages(2010, 2025)[0] == "DISJOINT"
        assert compare_vintages(None, 2020)[0] == "MISSING"


# ==============================================================================
# SECTION 7: REST API ENDPOINT TESTS
# ==============================================================================

class TestCrossRegistryAPI:
    """Tests for the 5 mounted REST API endpoints."""

    def test_api_projects_compare_success(self):
        resp = client.post("/api/cross-registry/projects/compare", json={
            "project_a": {
                "registry": "VCS",
                "project_id": "VCS-101",
                "project_name": "Rimba Raya Biodiversity Reserve",
                "country": "Indonesia",
            },
            "project_b": {
                "registry": "GS",
                "project_id": "GS-202",
                "project_name": "Rimba Raya Peatland Project",
                "country": "Indonesia",
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "correlation_category" in data
        assert "evidence_strength" in data
        assert "disclaimer" in data

    def test_api_projects_correlations_success(self):
        resp = client.get("/api/cross-registry/projects/correlations?min_similarity=0.50&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_candidates_evaluated"] == 96
        assert len(data["correlations"]) <= 10
        assert "disclaimer" in data

    def test_api_projects_correlations_invalid_category(self):
        resp = client.get("/api/cross-registry/projects/correlations?category=INVALID_CAT")
        assert resp.status_code == 422
        assert "Invalid category" in resp.json()["detail"]

    def test_api_projects_correlations_collision_category_filter(self):
        resp = client.get("/api/cross-registry/projects/correlations?category=CROSS_REGISTRY_IDENTIFIER_COLLISION")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category_filter"] == "CROSS_REGISTRY_IDENTIFIER_COLLISION"

    def test_api_entities_compare_success(self):
        resp = client.post("/api/cross-registry/entities/compare", json={
            "entity_a": "Shell",
            "entity_b": "Shell International Petroleum Co Ltd",
            "registry_a": "VCS",
            "registry_b": "GS",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_match"] is True
        assert data["relationship_type"] == "CORPORATE_HIERARCHY_OR_SUBSIDIARY"
        assert "disclaimer" in data

    def test_api_entities_compare_missing_body(self):
        resp = client.post("/api/cross-registry/entities/compare", json={})
        assert resp.status_code == 422

    def test_api_retirements_summary_success(self):
        resp = client.get("/api/cross-registry/retirements/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["combined_retirement_records"] == 37335
        assert data["combined_retired_tonnes"] == 87668330.0
        assert data["total_issuance_records_excluded"] == 669
        assert "VCS" in data["registries"]
        assert "GS" in data["registries"]

    def test_api_retirements_trends_yearly(self):
        resp = client.get("/api/cross-registry/retirements/trends?period=yearly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_type"] == "yearly"
        assert len(data["trends"]) == 17

    def test_api_retirements_trends_monthly(self):
        resp = client.get("/api/cross-registry/retirements/trends?period=monthly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_type"] == "monthly"

    def test_api_retirements_trends_invalid_period(self):
        resp = client.get("/api/cross-registry/retirements/trends?period=hourly")
        assert resp.status_code == 422
        assert "Invalid period" in resp.json()["detail"]

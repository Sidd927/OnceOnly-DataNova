"""Sprint 3.4.1: pin the accepted Stage 1 population metrics and their API serialization.

Reference values are the frozen Stage 1 figures (docs/DATANOVA_PHASE_2C_STAGE_1_FINAL_ACCEPTANCE_AUDIT.md §4),
independently reproduced in docs/DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md.
"""
import math

from fastapi.testclient import TestClient

from app.analytics import AnalyticsEngine


def _summary():
    return AnalyticsEngine.analyze_population_summary()


def test_population_concentration_pinned_to_stage1_reference():
    s = _summary()
    c = s.overall_concentration
    assert s.total_retirement_records == 37335
    assert c.disclosed_units == 35172359.0
    assert c.unique_disclosed_beneficiaries == 9933
    assert math.isclose(c.hhi_disclosed, 245.6410, abs_tol=5e-4)
    assert math.isclose(c.hhi_normalized, 0.024466, abs_tol=5e-6)
    assert math.isclose(c.entropy_shannon_disclosed, 7.5166, abs_tol=5e-5)
    assert math.isclose(c.entropy_normalized, 0.5661, abs_tol=5e-5)
    assert c.dominant_disclosed_beneficiary == "Telstra Corporation Limited"
    assert math.isclose(c.dominant_disclosed_share * c.disclosed_units, 3766034.0, abs_tol=0.5)
    assert math.isclose(c.top3_disclosed_share, 0.2313, abs_tol=5e-5)
    assert math.isclose(s.pooled_allocation_gini, 0.960471, abs_tol=5e-7)
    assert math.isclose(s.batch_gini_distribution["mean"], 0.492445, abs_tol=5e-7)


def test_equitability_uses_log2_of_label_count():
    c = _summary().overall_concentration
    assert math.isclose(c.entropy_normalized, c.entropy_shannon_disclosed / math.log2(c.unique_disclosed_beneficiaries), rel_tol=1e-12)


def test_api_serializes_every_disclosed_share_without_zeroing():
    """Regression: 6-decimal rounding serialized 6,307 of 9,933 shares as 0.0, truncating the Lorenz curve."""
    from app.main import app

    body = TestClient(app).get("/api/analytics/population/summary").json()
    oc = body["overall_concentration"]
    shares = oc["disclosed_shares"]
    assert len(shares) == oc["unique_disclosed_beneficiaries"] == 9933
    assert all(v > 0 for v in shares.values())
    assert math.isclose(sum(shares.values()), 1.0, abs_tol=1e-9)
    # Volume derived in the UI (share x disclosed units) matches the source sum.
    assert round(shares["Telstra Corporation Limited"] * oc["disclosed_units"]) == 3766034
    # Headline values agree with the engine at the serialized precision.
    assert oc["hhi_disclosed"] == 245.64
    assert oc["entropy_shannon_disclosed"] == 7.5166
    assert oc["entropy_normalized"] == 0.5661
    assert body["pooled_allocation_gini"] == 0.9605
    assert body["batch_gini_distribution"]["mean"] == 0.4924

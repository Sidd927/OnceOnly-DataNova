"""Sprint 3.4.1: pin the accepted Stage 1 population metrics and their API serialization.

The canonical population is the demo DB that the committed code materializes from the committed CSV, which is
what a fresh clone and the Docker image use. Each test runs on a fresh materialization (tmp_env), never on a
developer's var/ copy. The frozen Stage 1 audit used a pre-normalization materialization (9,933 labels, entropy
7.5166); the canonical build has 9,931 labels and entropy 7.5165, with HHI, equitability, the Telstra volume,
top-3 share and both Ginis unchanged at their reported precision.
See docs/DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md §8.
"""
import math

from fastapi.testclient import TestClient


def _summary():
    from app.analytics import AnalyticsEngine  # imported after tmp_env so it reads the isolated settings

    return AnalyticsEngine.analyze_population_summary()


def test_population_concentration_pinned_to_canonical_population(tmp_env):
    s = _summary()
    c = s.overall_concentration
    assert s.total_retirement_records == 37335
    assert c.disclosed_units == 35172359.0
    assert c.unique_disclosed_beneficiaries == 9931
    assert math.isclose(c.hhi_disclosed, 245.6410, abs_tol=5e-4)
    assert math.isclose(c.hhi_normalized, 0.024466, abs_tol=5e-6)
    assert math.isclose(c.entropy_shannon_disclosed, 7.516503, abs_tol=5e-6)
    assert math.isclose(c.entropy_normalized, 0.5661, abs_tol=5e-5)
    assert c.dominant_disclosed_beneficiary == "Telstra Corporation Limited"
    assert math.isclose(c.dominant_disclosed_share * c.disclosed_units, 3766034.0, abs_tol=0.5)
    assert math.isclose(c.top3_disclosed_share, 0.2313, abs_tol=5e-5)
    assert math.isclose(s.pooled_allocation_gini, 0.960471, abs_tol=5e-7)
    assert math.isclose(s.batch_gini_distribution["mean"], 0.492445, abs_tol=5e-7)


def test_equitability_uses_log2_of_label_count(tmp_env):
    c = _summary().overall_concentration
    assert math.isclose(c.entropy_normalized, c.entropy_shannon_disclosed / math.log2(c.unique_disclosed_beneficiaries), rel_tol=1e-12)


def test_api_serializes_every_disclosed_share_without_zeroing(tmp_env):
    """Regression: 6-decimal rounding serialized 6,307 of 9,931 shares as 0.0, truncating the Lorenz curve."""
    from app.main import app

    body = TestClient(app).get("/api/analytics/population/summary").json()
    oc = body["overall_concentration"]
    shares = oc["disclosed_shares"]
    assert len(shares) == oc["unique_disclosed_beneficiaries"] == 9931
    assert all(v > 0 for v in shares.values())
    assert math.isclose(sum(shares.values()), 1.0, abs_tol=1e-9)
    # Volume derived in the UI (share x disclosed units) matches the source sum.
    assert round(shares["Telstra Corporation Limited"] * oc["disclosed_units"]) == 3766034
    # Headline values agree with the engine at the serialized precision.
    assert oc["hhi_disclosed"] == 245.64
    assert oc["entropy_shannon_disclosed"] == 7.5165
    assert oc["entropy_normalized"] == 0.5661
    assert body["pooled_allocation_gini"] == 0.9605
    assert body["batch_gini_distribution"]["mean"] == 0.4924


def test_stale_demo_db_is_rebuilt_not_used(tmp_env):
    """A materialization without the current build stamp (e.g. built before Phase 1 normalization) is rebuilt."""
    import sqlite3

    from app.config import settings
    from app.reference import demo_db_is_current, ensure_demo_db

    ensure_demo_db(settings.reference_demo, settings.reference_subset_csv)
    assert demo_db_is_current(settings.reference_demo, settings.reference_subset_csv)
    con = sqlite3.connect(settings.reference_demo)
    con.execute("DELETE FROM meta WHERE key='build'")
    con.execute("UPDATE records SET beneficiary='1. FC K\u221a\u2202ln GmbH & Co. KGaA' WHERE beneficiary='1. FC Köln GmbH & Co. KGaA'")
    con.commit()
    con.close()
    assert not demo_db_is_current(settings.reference_demo, settings.reference_subset_csv)
    assert _summary().overall_concentration.unique_disclosed_beneficiaries == 9931  # analytics rebuilt it first
    assert demo_db_is_current(settings.reference_demo, settings.reference_subset_csv)


def test_canonical_population_uses_repaired_labels(tmp_env):
    """The canonical build carries Phase 1's mojibake repairs, which is why it has 9,931 labels rather than 9,933."""
    import sqlite3

    from app.analytics.engine import resolve_analytics_db_path

    con = sqlite3.connect(f"file:{resolve_analytics_db_path()}?mode=ro", uri=True)
    count = lambda b: con.execute("SELECT COUNT(*) FROM records WHERE beneficiary=?", (b,)).fetchone()[0]
    assert count("1. FC Köln GmbH & Co. KGaA") > 0
    assert count("1. FC K\u221a\u2202ln GmbH & Co. KGaA") == 0

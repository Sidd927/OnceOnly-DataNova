"""The analytics population DB follows ONCEONLY_REFERENCE_DEMO_DB (as Docker sets it) and fails clearly."""
import dataclasses

import pytest
from fastapi.testclient import TestClient


def test_analytics_uses_configured_demo_db_and_materializes_it(tmp_env):
    from app.analytics.engine import AnalyticsEngine, resolve_analytics_db_path

    target = tmp_env / "ref_demo.sqlite"  # tmp_env sets ONCEONLY_REFERENCE_DEMO_DB here; it does not exist yet
    assert not target.exists()
    assert resolve_analytics_db_path() == str(target)
    assert target.exists()
    assert AnalyticsEngine.analyze_population_summary().total_retirement_records == 37335


def test_population_endpoint_and_health_use_configured_path(tmp_env):
    from app.main import app

    c = TestClient(app)
    assert c.get("/api/analytics/population/summary").json()["total_retirement_records"] == 37335
    h = c.get("/api/health").json()["analytics"]
    assert h["available"] is True and h["db"] == "ref_demo.sqlite"


def test_missing_population_db_is_a_clear_503(tmp_env, monkeypatch):
    from app.analytics import engine
    from app.main import app

    monkeypatch.setattr(engine, "settings", dataclasses.replace(engine.settings, reference_subset_csv=tmp_env / "absent.csv.gz"))
    with pytest.raises(engine.AnalyticsDatabaseUnavailable):
        engine.resolve_analytics_db_path()
    r = TestClient(app).get("/api/analytics/population/summary")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "ANALYTICS_DB_UNAVAILABLE"


def test_read_only_analytics_responses_are_memoized_and_identical(tmp_env):
    from app.main import app

    c = TestClient(app)
    url = "/api/analytics/temporal/activity?period=weekly"
    first, second = c.get(url), c.get(url)
    assert first.status_code == second.status_code == 200
    assert first.headers["x-onceonly-cache"] == "miss" and second.headers["x-onceonly-cache"] == "hit"
    assert first.content == second.content
    # Writes and non-analytics routes are never cached; errors are not cached either.
    assert "x-onceonly-cache" not in c.get("/api/claims").headers
    bad = c.get("/api/analytics/temporal/activity?period=hourly")
    assert bad.status_code == 422 and "x-onceonly-cache" not in bad.headers

"""Demo presets in the UI must point at real seeded claims, real projects and real rules."""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = json.loads((ROOT / "frontend/src/lib/demoTargets.json").read_text())


def _seed_order() -> list[str]:
    src = (ROOT / "backend/scripts/seed_demo.py").read_text()
    return re.findall(r'submit\("([^"]+)"\)', src)


def test_claim_presets_follow_seed_submission_order():
    order = _seed_order()
    manifest = {m["file"]: m for m in json.loads((ROOT / "data/demo/manifest.json").read_text())}
    for t in TARGETS["claims"]:
        assert order[t["claim_id"] - 1] == t["seed_file"], t
        assert t["ref"] == f"OO-2026-{t['claim_id']:04d}"
        claimant_first_word = manifest[t["seed_file"]]["claimant"].split()[0]
        assert t["label"].startswith(claimant_first_word), (t["label"], claimant_first_word)


def test_project_preset_exists_in_reference_subset(tmp_env):
    from app.reference import Reference

    ref = Reference.open()
    con = sqlite3.connect(f"file:{ref.path}?mode=ro", uri=True)
    p = TARGETS["project"]
    n = con.execute("SELECT COUNT(*) FROM records WHERE registry=? AND project_id=?", (p["registry"], p["project_id"])).fetchone()[0]
    assert n > 0


def test_rule_search_example_is_in_assessment_catalog():
    from app.analytics import AnalyticsEngine

    ids = {r.rule_id for r in AnalyticsEngine.get_assessment_rules_catalog().rules}
    assert TARGETS["rule_search_example"] in ids


def test_frontend_has_no_phantom_demo_names_or_rules():
    src = "\n".join(p.read_text() for p in (ROOT / "frontend/src").rglob("*.ts*"))
    assert "Equinox" not in src
    assert "RULE-INT-001" not in src

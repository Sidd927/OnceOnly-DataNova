"""Read-only access to the registry reference index (real Berkeley VROD registry records).

Supports dual-mode execution:
  - 'full': full local index built from VROD raw files (~470k retirement rows).
  - 'demo-subset': committed reference subset (38,004 rows across 22 projects).
  - 'auto': prefers 'full' if valid; falls back seamlessly to 'demo-subset'.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import settings
from .normalization import normalize_date_iso, normalize_text_field

log = logging.getLogger("onceonly.reference")

COLS = [
    "kind", "registry", "batch_id", "unit_start", "unit_end", "quantity", "serial", "project_id",
    "project_name", "vintage", "country", "event_date", "beneficiary", "reason", "source_sheet", "source_row",
]


@dataclass
class Coverage:
    retired_units: int
    issued_units: int
    records: list[dict]  # retirement records intersecting the range
    issuance_records: list[dict]


def validate_reference_db(path: Path) -> tuple[bool, str | None]:
    """Verify that a SQLite reference database exists, is non-empty, and conforms to the expected schema."""
    if not path.exists():
        return False, f"File does not exist: {path}"
    if path.stat().st_size == 0:
        return False, f"Database file is empty (0 bytes): {path}"

    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        # Check SQLite header / readability
        con.execute("PRAGMA schema_version")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "records" not in tables or "meta" not in tables:
            con.close()
            return False, f"Missing required tables (found: {sorted(tables)})"

        cols = [r[1] for r in con.execute("PRAGMA table_info(records)").fetchall()]
        if cols != COLS:
            con.close()
            return False, f"Schema mismatch: expected {COLS}, got {cols}"

        row_count = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if row_count == 0:
            con.close()
            return False, "Database contains zero records in 'records' table"

        indices = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        if "ix_ns" not in indices:
            log.warning("Index 'ix_ns' missing in %s; queries may be slower", path)

        con.close()
        return True, None
    except sqlite3.DatabaseError as e:
        return False, f"Database corruption or SQLite error: {e}"


def build_demo_db(csv_path: Path, out: Path) -> None:
    """Materialize the committed demo subset CSV into a SQLite index with idempotent normalization."""
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    tmp = out.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    con.execute(f"CREATE TABLE records ({', '.join(COLS)})")

    # Clean text fields non-destructively during materialization
    rows = []
    for r in df[COLS].itertuples(index=False):
        row_dict = dict(zip(COLS, r))
        # Non-destructive text cleaning
        p_name = normalize_text_field(row_dict["project_name"] or None).normalized_value
        ben = normalize_text_field(row_dict["beneficiary"] or None).normalized_value
        reason = normalize_text_field(row_dict["reason"] or None).normalized_value
        date_val = normalize_date_iso(row_dict["event_date"] or None).normalized_value

        row = (
            row_dict["kind"] or None,
            row_dict["registry"] or None,
            row_dict["batch_id"] or None,
            int(row_dict["unit_start"]) if row_dict["unit_start"] else None,
            int(row_dict["unit_end"]) if row_dict["unit_end"] else None,
            int(row_dict["quantity"]) if row_dict["quantity"] else None,
            row_dict["serial"] or None,
            row_dict["project_id"] or None,
            p_name,
            row_dict["vintage"] or None,
            row_dict["country"] or None,
            date_val or row_dict["event_date"] or None,
            ben,
            reason,
            row_dict["source_sheet"] or None,
            int(row_dict["source_row"]) if row_dict["source_row"] else None,
        )
        rows.append(row)

    con.executemany(f"INSERT INTO records VALUES ({','.join('?' * len(COLS))})", rows)
    con.execute("CREATE INDEX ix_ns ON records(registry, batch_id, unit_start)")
    con.execute("CREATE INDEX ix_proj ON records(registry, project_id, vintage)")
    con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    src = {
        "dataset": "Berkeley Carbon Trading Project — VROD registry files (curated demo subset)",
        "version": "2026-08 (data through 2026-08-31)",
        "license": "CC BY 4.0",
        "url": "https://gspp.berkeley.edu/berkeley-carbon-trading-project/offsets-database",
        "normalized": True,
    }
    con.execute("INSERT INTO meta VALUES ('source', ?)", (json.dumps(src),))
    con.execute("INSERT INTO meta VALUES ('scope', ?)", (json.dumps("demo-subset"),))
    con.commit()
    con.close()
    tmp.replace(out)


class Reference:
    def __init__(self, path: Path, scope: str):
        self.path = path
        self.scope = scope
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        self.con.row_factory = sqlite3.Row

    @classmethod
    def open(cls) -> "Reference | None":
        mode = os.environ.get("ONCEONLY_REFERENCE_MODE", settings.reference_mode)
        # 1. Mode full or auto: check full index
        if mode in ("auto", "full") and settings.reference_full.exists():
            valid, err = validate_reference_db(settings.reference_full)
            if valid:
                return cls(settings.reference_full, "full")
            log.warning("Full reference DB at %s invalid: %s", settings.reference_full, err)

        if mode == "full":
            return None

        # 2. Mode demo or auto fallback: ensure demo db is materialized
        if not settings.reference_demo.exists() and settings.reference_subset_csv.exists():
            build_demo_db(settings.reference_subset_csv, settings.reference_demo)

        if settings.reference_demo.exists():
            valid, err = validate_reference_db(settings.reference_demo)
            if valid:
                return cls(settings.reference_demo, "demo-subset")
            log.warning("Demo reference DB at %s invalid: %s", settings.reference_demo, err)

        return None

    @classmethod
    def open_or_raise(cls) -> "Reference":
        ref = cls.open()
        if ref is None:
            raise RuntimeError(
                f"No valid reference registry index found in mode '{settings.reference_mode}'. "
                f"Run 'make data-download && make data' to build the full 493k-record index, "
                f"or ensure '{settings.reference_subset_csv}' exists to materialize the reproducible demo subset."
            )
        return ref

    def verify_integrity(self) -> dict:
        """Run self-integrity checks and return detailed counts."""
        check = self.con.execute("PRAGMA quick_check").fetchone()[0]
        counts = self.con.execute("SELECT registry, kind, COUNT(*) FROM records GROUP BY registry, kind").fetchall()
        ns_count = self.con.execute("SELECT COUNT(DISTINCT registry || ':' || batch_id) FROM records").fetchone()[0]
        total_rows = self.con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        return {
            "status": "ok" if check == "ok" else "corrupt",
            "sqlite_check": check,
            "path": str(self.path),
            "scope": self.scope,
            "total_records": total_rows,
            "namespaces": ns_count,
            "row_counts": {f"{r[0]}_{r[1]}": r[2] for r in counts},
        }

    def meta(self) -> dict:
        out = {k: json.loads(v) for k, v in self.con.execute("SELECT key, value FROM meta")}
        counts = self.con.execute("SELECT registry, kind, COUNT(*) FROM records GROUP BY registry, kind").fetchall()
        out["row_counts"] = {f"{r[0]}_{r[1]}": r[2] for r in counts}
        out["scope"] = self.scope
        return out

    def _intersecting(self, kind: str, registry: str, batch_id: str, start: int, end: int) -> list[dict]:
        rows = self.con.execute(
            "SELECT * FROM records WHERE kind=? AND registry=? AND batch_id=? AND unit_start<=? AND unit_end>=? ORDER BY unit_start",
            (kind, registry, batch_id, end, start),
        ).fetchall()
        return [dict(r) for r in rows]

    def coverage(self, registry: str, batch_id: str, start: int, end: int) -> Coverage:
        ret = self._intersecting("retirement", registry, batch_id, start, end)
        iss = self._intersecting("issuance", registry, batch_id, start, end)
        return Coverage(_union_len(ret, start, end), _union_len(iss, start, end), ret, iss)

    def batch_known(self, registry: str, batch_id: str) -> bool:
        return self.con.execute("SELECT 1 FROM records WHERE registry=? AND batch_id=? LIMIT 1", (registry, batch_id)).fetchone() is not None

    def retired_total(self, registry: str, project_id: str, vintage: str) -> int | None:
        r = self.con.execute(
            "SELECT SUM(quantity), COUNT(*) FROM records WHERE kind='retirement' AND registry=? AND project_id=? AND vintage=?",
            (registry, project_id, vintage),
        ).fetchone()
        return int(r[0]) if r and r[1] else None

    def project_name(self, registry: str, project_id: str) -> str | None:
        r = self.con.execute("SELECT project_name FROM records WHERE registry=? AND project_id=? AND project_name IS NOT NULL LIMIT 1", (registry, project_id)).fetchone()
        return r[0] if r else None

    def sample_retirements(self, limit: int = 20) -> list[dict]:
        rows = self.con.execute(
            "SELECT * FROM records WHERE kind='retirement' ORDER BY event_date DESC, quantity DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def _union_len(records: list[dict], start: int, end: int) -> int:
    spans = sorted((max(r["unit_start"], start), min(r["unit_end"], end)) for r in records)
    total, cur_s, cur_e = 0, None, None
    for s, e in spans:
        if cur_e is None or s > cur_e + 1:
            if cur_e is not None:
                total += cur_e - cur_s + 1
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s + 1
    return total

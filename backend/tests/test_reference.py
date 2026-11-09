"""Unit tests for reference database loading, validation, and integrity checks."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.config import settings
from app.reference import Reference, validate_reference_db


def test_validate_reference_db_valid_demo():
    ref = Reference.open()
    assert ref is not None
    valid, err = validate_reference_db(ref.path)
    assert valid is True
    assert err is None


def test_validate_reference_db_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.sqlite"
    valid, err = validate_reference_db(missing)
    assert valid is False
    assert "File does not exist" in err


def test_validate_reference_db_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.sqlite"
    empty.touch()
    valid, err = validate_reference_db(empty)
    assert valid is False
    assert "empty" in err


def test_validate_reference_db_corrupt_file(tmp_path: Path):
    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"NOT A SQLITE DATABASE GARBAGE DATA")
    valid, err = validate_reference_db(corrupt)
    assert valid is False
    assert "corruption" in err.lower() or "error" in err.lower()


def test_validate_reference_db_missing_table(tmp_path: Path):
    bad = tmp_path / "bad_schema.sqlite"
    con = sqlite3.connect(bad)
    con.execute("CREATE TABLE wrong_table (id INT)")
    con.commit()
    con.close()
    valid, err = validate_reference_db(bad)
    assert valid is False
    assert "Missing required tables" in err


def test_reference_open_modes(monkeypatch, tmp_path: Path):
    # Mode demo
    monkeypatch.setenv("ONCEONLY_REFERENCE_MODE", "demo")
    ref = Reference.open()
    assert ref is not None
    assert ref.scope == "demo-subset"

    # Mode full when full db missing returns None
    old_full = settings.reference_full
    try:
        object.__setattr__(settings, "reference_full", tmp_path / "nonexistent.sqlite")
        monkeypatch.setenv("ONCEONLY_REFERENCE_MODE", "full")
        assert Reference.open() is None

        # Reference.open_or_raise raises RuntimeError
        with pytest.raises(RuntimeError) as exc:
            Reference.open_or_raise()
        assert "No valid reference registry index found" in str(exc.value)
    finally:
        object.__setattr__(settings, "reference_full", old_full)


def test_reference_verify_integrity():
    ref = Reference.open_or_raise()
    integrity = ref.verify_integrity()
    assert integrity["status"] == "ok"
    assert integrity["sqlite_check"] == "ok"
    assert integrity["total_records"] > 0
    assert integrity["namespaces"] > 0
    assert "VCS_retirement" in integrity["row_counts"]

"""Comprehensive unit tests for the OnceOnly normalization and provenance layer."""
from __future__ import annotations

import unicodedata

import pytest

from app.normalization import (
    NormalizationRecord,
    normalize_beneficiary_name,
    normalize_dashes,
    normalize_date_iso,
    normalize_registry_id,
    normalize_text_field,
    normalize_whitespace,
    repair_mojibake,
)


def test_mojibake_repair_real_registry_examples():
    # Real examples found in Berkeley VROD 2026-08
    raw_proj = "‚ÄòGuanar√©‚Äô Forest Plantations"
    repaired, modified = repair_mojibake(raw_proj)
    assert modified is True
    assert repaired == "‘Guanaré’ Forest Plantations"

    raw_ben = "Etelec Italia S.p.A. Societ√† Benefit"
    repaired, modified = repair_mojibake(raw_ben)
    assert modified is True
    assert repaired == "Etelec Italia S.p.A. Società Benefit"

    raw_apostrophe = "Patch‚Äôs customers"
    repaired, modified = repair_mojibake(raw_apostrophe)
    assert modified is True
    assert repaired == "Patch’s customers"

    raw_dash = "Scope 1 ‚Äì FY 2023"
    repaired, modified = repair_mojibake(raw_dash)
    assert modified is True
    assert repaired == "Scope 1 – FY 2023"


def test_mojibake_repair_idempotency_and_clean_strings():
    clean_text = "Clean project title with standard ASCII characters"
    repaired, modified = repair_mojibake(clean_text)
    assert modified is False
    assert repaired == clean_text

    # Idempotency: f(f(x)) == f(x)
    raw = "‚ÄòGuanar√©‚Äô"
    rep1, mod1 = repair_mojibake(raw)
    rep2, mod2 = repair_mojibake(rep1)
    assert mod1 is True
    assert mod2 is False
    assert rep1 == rep2 == "‘Guanaré’"


def test_mojibake_nbsp_and_decomposed_unicode_idempotency():
    # 1. Non-breaking space mojibake: ¬† decodes to \u00a0, then collapses to space
    raw_nbsp = "Webjet Marketing Pty¬†Ltd (NZ)"
    rec1 = normalize_text_field(raw_nbsp)
    rec2 = normalize_text_field(rec1.normalized_value)
    assert rec1.normalized_value == "Webjet Marketing Pty Ltd (NZ)"
    assert rec2.normalized_value == "Webjet Marketing Pty Ltd (NZ)"
    assert rec1.normalized_value == rec2.normalized_value

    # 2. Decomposed Unicode: SchuÃàtte decodes to Schütte, then precomposes to Schütte via NFC
    raw_umlaut = "Franz Joseph SchuÃàtte GmbH"
    rec1_u = normalize_text_field(raw_umlaut)
    rec2_u = normalize_text_field(rec1_u.normalized_value)
    assert rec1_u.normalized_value == "Franz Joseph Schütte GmbH"
    assert rec2_u.normalized_value == "Franz Joseph Schütte GmbH"
    assert rec1_u.normalized_value == rec2_u.normalized_value


def test_whitespace_normalization():
    # Non-breaking spaces (\u00a0 and \u202f) and multiple consecutive spaces
    text = "Company\u00a0\u00a0Name    LLC\u202f"
    cleaned = normalize_whitespace(text)
    assert cleaned == "Company Name LLC"
    assert normalize_whitespace("") == ""
    assert normalize_whitespace("   \t  ") == ""


def test_dash_normalization():
    # Various Unicode dash variants normalized to ASCII hyphen-minus
    dashes = "18453‐896309560‑896329558‒VCS–VCU—1507−VER"
    normalized = normalize_dashes(dashes)
    assert normalized == "18453-896309560-896329558-VCS-VCU-1507-VER"


def test_normalize_text_field_provenance_and_raw_preservation():
    raw = "  ‚ÄòGuanar√©‚Äô   Forest\u00a0Plantations  "
    rec = normalize_text_field(raw)

    assert rec.raw_value == raw
    assert rec.normalized_value == "‘Guanaré’ Forest Plantations"
    assert rec.is_modified is True
    assert "mojibake_repair" in rec.operations
    assert "whitespace_normalization" in rec.operations

    # Conversion to dict
    d = rec.to_dict()
    assert d["raw_value"] == raw
    assert d["normalized_value"] == "‘Guanaré’ Forest Plantations"
    assert d["is_modified"] is True
    assert isinstance(d["operations"], list)

    # None handling
    none_rec = normalize_text_field(None)
    assert none_rec.raw_value is None
    assert none_rec.normalized_value is None
    assert none_rec.is_modified is False
    assert none_rec.operations == ()


def test_normalize_date_iso():
    # Clean ISO date
    assert normalize_date_iso("2024-08-31").normalized_value == "2024-08-31"

    # ISO timestamp with time
    assert normalize_date_iso("2024-08-31T15:30:00Z").normalized_value == "2024-08-31"

    # DD/MM/YYYY format (unambiguous day > 12)
    rec_dmy = normalize_date_iso("15/08/2024")
    assert rec_dmy.normalized_value == "2024-08-15"
    assert "date_format_dmy" in rec_dmy.operations

    # MM/DD/YYYY format (unambiguous month > 12 swapped)
    rec_mdy = normalize_date_iso("08/25/2024")
    assert rec_mdy.normalized_value == "2024-08-25"
    assert "date_format_mdy" in rec_mdy.operations

    # Ambiguous date where both day and month <= 12
    rec_amb = normalize_date_iso("05/06/2024")
    assert rec_amb.normalized_value == "2024-06-05"  # registry-standard DD/MM/YYYY convention
    assert "date_ambiguous_day_month" in rec_amb.operations
    assert "date_format_dmy_assumed" in rec_amb.operations

    # Text formats
    assert normalize_date_iso("15 Aug 2024").normalized_value == "2024-08-15"
    assert normalize_date_iso("August 15, 2024").normalized_value == "2024-08-15"

    # None and empty
    assert normalize_date_iso(None).normalized_value is None
    assert normalize_date_iso("   ").normalized_value is None


def test_normalize_registry_id():
    assert normalize_registry_id("vcs").normalized_value == "VCS"
    assert normalize_registry_id("VERRA").normalized_value == "VCS"
    assert normalize_registry_id("Gold Standard").normalized_value == "GS"
    assert normalize_registry_id("gs").normalized_value == "GS"
    assert normalize_registry_id("OTHER").normalized_value == "OTHER"
    assert normalize_registry_id(None).normalized_value is None


def test_beneficiary_normalization_and_placeholder_classification():
    # Named beneficiaries
    rec, status = normalize_beneficiary_name("Northwind Foods LLC")
    assert status == "named"
    assert rec.normalized_value == "Northwind Foods LLC"

    rec, status = normalize_beneficiary_name("Etelec Italia S.p.A. Societ√† Benefit")
    assert status == "named"
    assert rec.normalized_value == "Etelec Italia S.p.A. Società Benefit"

    # Placeholders / Redactions
    for ph in ["Not Disclosed", "undisclosed", "N/A", "none", "unknown", "confidential", "Anonymous", "No Beneficiary"]:
        rec, status = normalize_beneficiary_name(ph)
        assert status == "placeholder", f"Failed for {ph}"
        assert rec.normalized_value is None
        assert rec.raw_value == ph
        assert "placeholder_suppressed" in rec.operations

    # Empty
    rec, status = normalize_beneficiary_name("")
    assert status == "empty"
    assert rec.normalized_value is None

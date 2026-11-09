"""Data normalization and provenance tracking layer for OnceOnly.

Provides deterministic, non-destructive normalization for registry records and claim
evidence. Preserves the raw source value alongside the normalized value and records
all applied operations.

Adheres strictly to the Critical Data-Integrity Rule:
- Never silently overwrite or discard source values.
- Apply only defensible, mathematically/empirically verified transformations.
- Guarantee idempotency: f(f(x)) == f(x).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

# Unicode dash variants that occur in certificates, reports and scanned PDFs
_DASH_VARIANTS = "‐‑‒–—−"
_DASH_MAP = {ord(c): "-" for c in _DASH_VARIANTS}

# Common mojibake markers originating from MacRoman / Windows-1252 double-encoded UTF-8
_MOJIBAKE_MARKERS = ("‚Ä", "√", "¬", "Ã", "â")

# Beneficiary placeholders that indicate privacy redaction or undisclosed ownership
_PLACEHOLDER_BENEFICIARIES = {
    "not disclosed",
    "undisclosed",
    "n/a",
    "na",
    "n a",
    "none",
    "unknown",
    "confidential",
    "private",
    "anonym",
    "anonymous",
    "no beneficiary",
    "not applicable",
}


@dataclass(frozen=True)
class NormalizationRecord:
    """Provenance container tracking raw value, normalized result, and applied operations."""
    raw_value: str | None
    normalized_value: str | None
    operations: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_modified(self) -> bool:
        return self.raw_value != self.normalized_value

    def to_dict(self) -> dict:
        return {
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "operations": list(self.operations),
            "is_modified": self.is_modified,
        }


def repair_mojibake(text: str) -> tuple[str, bool]:
    """Repair MacRoman/Windows-1252 double-encoded UTF-8 sequences safely.
    
    Returns (repaired_text, was_modified). Only applies transformation if text
    contains recognized mojibake markers and decodes cleanly into valid UTF-8.
    """
    if not text or not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text, False
    try:
        # Pre-clean non-breaking space characters that conflict with mac_roman UTF-8 continuation
        sanitized = text.replace("\u00a0", " ").replace("\u202f", " ")
        repaired = sanitized.encode("mac_roman").decode("utf-8")
        if repaired != text:
            return repaired, True
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return text, False


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace: replace NBSP variants with standard space, collapse multi-spaces, strip."""
    if not text:
        return ""
    # Replace non-breaking spaces (\u00a0) and narrow NBSP (\u202f)
    s = text.replace("\u00a0", " ").replace("\u202f", " ")
    # Collapse multiple consecutive whitespace characters (excluding newlines if structured)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def normalize_dashes(text: str) -> str:
    """Normalize all Unicode dash variants to standard ASCII hyphen-minus."""
    if not text:
        return ""
    return text.translate(_DASH_MAP)


def normalize_text_field(raw: str | None) -> NormalizationRecord:
    """Clean free-text fields (project names, reasons, titles) non-destructively with 100% idempotency."""
    if raw is None:
        return NormalizationRecord(None, None, ())
    
    ops = []
    current = raw
    
    # 1. Mojibake repair first (safely decode double-encoded sequences e.g. ¬† -> \u00a0, SchuÃàtte -> Schütte)
    repaired, modified = repair_mojibake(current)
    if modified:
        ops.append("mojibake_repair")
        current = repaired

    # 2. Unicode NFC normalization (precompose combining characters e.g. Schütte -> Schütte)
    nfc = unicodedata.normalize("NFC", current)
    if nfc != current:
        ops.append("unicode_nfc")
        current = nfc

    # 3. Whitespace normalization (replace NBSP variants, collapse spaces, strip)
    cleaned_ws = normalize_whitespace(current)
    if cleaned_ws != current:
        ops.append("whitespace_normalization")
        current = cleaned_ws

    return NormalizationRecord(
        raw_value=raw,
        normalized_value=current or None,
        operations=tuple(ops),
    )


def normalize_date_iso(date_str: str | None) -> NormalizationRecord:
    """Normalize various date formats (YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, Excel dates) to ISO YYYY-MM-DD.
    
    Explicitly tracks ambiguity when day and month are both <= 12 and ambiguous.
    """
    if not date_str or not date_str.strip():
        return NormalizationRecord(date_str, None, ())
    
    s = date_str.strip()
    ops = []
    
    # Already clean ISO YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return NormalizationRecord(date_str, s, ())
    
    # ISO timestamp with time: 2024-08-31T00:00:00 -> 2024-08-31
    if len(s) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", s[:10]):
        return NormalizationRecord(date_str, s[:10], ("iso_timestamp_truncate",))
        
    # Formats: DD/MM/YYYY or DD.MM.YYYY
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", s)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Disambiguate day vs month
        if mth > 12 >= d:  # MM/DD/YYYY unambiguous (e.g. 08/25/2024)
            d, mth = mth, d
            ops.append("date_format_mdy")
        elif d > 12 >= mth:  # DD/MM/YYYY unambiguous (e.g. 25/08/2024)
            ops.append("date_format_dmy")
        elif d <= 12 and mth <= 12:
            if d != mth:
                # Ambiguous: e.g. 05/06/2024 could be May 6 or June 5
                ops.append("date_ambiguous_day_month")
            ops.append("date_format_dmy_assumed")
            
        try:
            dt = datetime(y, mth, d)
            iso = dt.strftime("%Y-%m-%d")
            return NormalizationRecord(date_str, iso, tuple(ops))
        except ValueError:
            pass
            
    # Formats: DD Month YYYY (e.g. 15 Aug 2024)
    for fmt in ("%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return NormalizationRecord(date_str, dt.strftime("%Y-%m-%d"), ("date_parse_text",))
        except ValueError:
            continue
            
    # Return raw if unparseable
    return NormalizationRecord(date_str, s, ("unparsed_verbatim",))


def normalize_registry_id(registry_str: str | None) -> NormalizationRecord:
    """Canonicalize registry codes to 'VCS' or 'GS'."""
    if not registry_str:
        return NormalizationRecord(registry_str, None, ())
        
    s = registry_str.strip().upper()
    if s in ("VCS", "VERRA", "VERRA VCS"):
        return NormalizationRecord(registry_str, "VCS", ("registry_canonicalize",) if s != "VCS" else ())
    if s in ("GS", "GOLD STANDARD", "GOLD"):
        return NormalizationRecord(registry_str, "GS", ("registry_canonicalize",) if s != "GS" else ())
        
    return NormalizationRecord(registry_str, s, ())


def normalize_beneficiary_name(name_str: str | None) -> tuple[NormalizationRecord, str]:
    """Clean beneficiary name and classify status: ('named', 'placeholder', or 'empty')."""
    if not name_str or not name_str.strip():
        return NormalizationRecord(name_str, None, ()), "empty"
        
    rec = normalize_text_field(name_str)
    val = rec.normalized_value or ""
    
    # Check if placeholder
    clean_alpha = re.sub(r"[^a-z0-9]+", "", val.lower()).strip()
    clean_spaced = re.sub(r"[^a-z0-9]+", " ", val.lower()).strip()
    if (
        clean_alpha in _PLACEHOLDER_BENEFICIARIES
        or clean_spaced in _PLACEHOLDER_BENEFICIARIES
        or not clean_alpha
    ):
        return NormalizationRecord(rec.raw_value, None, rec.operations + ("placeholder_suppressed",)), "placeholder"
        
    return rec, "named"

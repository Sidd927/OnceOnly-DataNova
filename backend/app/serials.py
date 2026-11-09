"""Deterministic parsing of registry serial numbers into unit ranges.

A serial block identifies a contiguous range of units inside one issuance batch.
Unit numbers are only unique *within* a batch (measured on Berkeley VROD 2026-08:
Verra unit numbers restart across batches), so every block is keyed by
``(registry, batch_id)`` — the namespace used on chain.

Supported formats (verified against VROD registry files, see backend/scripts/build_reference.py):

* Verra VCS:  ``18453-896309560-896329558-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0``
* Verra legacy (no "VCS-" segment): ``7056-367376734-367376744-VCU-263-VER-ID-14-674-01012016-31122016-1``
* Gold Standard: ``GS1-1-XZ-GS12303-17-2022-30775-1077-1127``
* Gold Standard legacy: ``GS1-1-VN-1083-4-2011-364-7073-10000``

Resilient extraction capabilities (Phase 1):
* Table columns (Batch, From, To, Rest separated by tabs, pipes, or structured spaces)
* OCR character healing ('O'/'o' -> '0', 'l'/'I' -> '1' in strictly numeric fields)
* Prose retirement declarations ("units X to Y of Verra batch Z")
* Full provenance tracking per block (method, raw text, transformations, confidence)
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_DASHES = "‐‑‒–—−"

VERRA_RE = re.compile(
    r"(?<![A-Za-z0-9\-_])"
    r"(?P<batch>\d{1,7})-(?P<start>\d{1,12})-(?P<end>\d{1,12})-(?:VCS-)?VCU-(?P<seq>\d+)-(?P<org>[A-Z0-9]{2,5})"
    r"-(?P<country>[A-Z]{2})(?:-(?P<scope>\d{1,2}))?-(?P<project>\d{1,6})-(?P<vstart>\d{8})[-_](?P<vend>\d{8})-(?P<flag>\d)"
    r"(?![A-Za-z0-9\-_])"
)
GOLD_RE = re.compile(
    r"(?<![A-Za-z0-9\-_])"
    r"(?P<prefix>GS\d+-\d+-(?P<country>[A-Z]{2})-(?:GS)?(?P<project>\d{1,6})-(?P<scope>\d{1,2})-(?P<vintage>\d{4})-(?P<batch>\d{1,7}))"
    r"-(?P<start>\d{1,12})-(?P<end>\d{1,12})"
    r"(?![A-Za-z0-9\-_])"
)

# Targeted OCR-tolerant patterns for scanned documents
VERRA_OCR_RE = re.compile(
    r"(?<![A-Za-z0-9\-_])"
    r"(?P<batch>[0-9OolI]{1,7})-(?P<start>[0-9OolI]{1,12})-(?P<end>[0-9OolI]{1,12})-(?:VCS-)?VCU-(?P<seq>[0-9OolI]+)-(?P<org>[A-Z0-9]{2,5})"
    r"-(?P<country>[A-Z]{2})(?:-(?P<scope>[0-9OolI]{1,2}))?-(?P<project>[0-9OolI]{1,6})-(?P<vstart>[0-9OolI]{8})[-_](?P<vend>[0-9OolI]{8})-(?P<flag>[0-9OolI])"
    r"(?![A-Za-z0-9\-_])",
    re.IGNORECASE,
)
GOLD_OCR_RE = re.compile(
    r"(?<![A-Za-z0-9\-_])"
    r"(?P<prefix>GS[0-9OolI]+-[0-9OolI]+-(?P<country>[A-Z]{2})-(?:GS)?(?P<project>[0-9OolI]{1,6})-(?P<scope>[0-9OolI]{1,2})-(?P<vintage>[0-9OolI]{4})-(?P<batch>[0-9OolI]{1,7}))"
    r"-(?P<start>[0-9OolI]{1,12})-(?P<end>[0-9OolI]{1,12})"
    r"(?![A-Za-z0-9\-_])",
    re.IGNORECASE,
)

# Prose range patterns
PROSE_RE = re.compile(
    r"(?:retired\s+)?units?\s+(?P<start>[\d,.]+)\s+(?:to|through|-|–)\s+(?P<end>[\d,.]+)\s+"
    r"(?:of|from|in)\s+(?:(?P<reg>Verra|VCS|Gold Standard|GS)\s+)?(?:issuance\s+)?batch\s+#?\s*(?P<batch>[A-Za-z0-9\-_]+)"
    r"(?:\s*\((?:project\s*(?P<project>\d+))?(?:,\s*)?(?:vintage\s*(?P<vintage>\d{4}(?:-\d{4})?))?\))?",
    re.IGNORECASE,
)
PROSE_RE_ALT = re.compile(
    r"(?:(?P<reg>Verra|VCS|Gold Standard|GS)\s+)?(?:issuance\s+)?batch\s+#?\s*(?P<batch>[A-Za-z0-9\-_]+)"
    r"(?:\s*\((?:project\s*(?P<project>\d+))?(?:,\s*)?(?:vintage\s*(?P<vintage>\d{4}(?:-\d{4})?))?\))?"
    r"[,;\s]+(?:retired\s+)?units?\s+(?P<start>[\d,.]+)\s+(?:to|through|-|–)\s+(?P<end>[\d,.]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SerialBlock:
    registry: str  # "VCS" | "GS"
    batch_id: str
    unit_start: int
    unit_end: int
    serial: str
    project_id: str | None = None
    vintage: str | None = None
    country: str | None = None
    source_method: str = "regex"  # "regex" | "table" | "ocr_healed" | "prose" | "llm"
    raw_text: str | None = None
    transformations: tuple[str, ...] = ()
    confidence: str = "high"  # "high" | "medium" | "low"
    is_ambiguous: bool = False

    @property
    def quantity(self) -> int:
        return self.unit_end - self.unit_start + 1

    @property
    def namespace(self) -> str:
        return f"{self.registry}:{self.batch_id}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quantity"] = self.quantity
        d["namespace"] = self.namespace
        return d


class SerialError(ValueError):
    pass


def normalize(text: str) -> str:
    """Undo common layout damage: unicode dashes, spaces/newlines around hyphens."""
    for d in _DASHES:
        text = text.replace(d, "-")
    text = re.sub(r"\s*-\s*\n\s*", "-", text)  # serial wrapped after a hyphen
    text = re.sub(r"\s*\n\s*-\s*", "-", text)  # wrapped before a hyphen
    text = re.sub(r"(?<=[0-9A-Z])\s+-\s+(?=[0-9A-Z])", "-", text)  # "123 - 456"
    return text


def heal_ocr_digits(s: str | None) -> str | None:
    """Safely heal OCR-damaged digits in strictly numeric positions."""
    if not s:
        return s
    return s.translate(str.maketrans("OoIl", "0011"))


def _vintage_from_verra(vstart: str, vend: str) -> str:
    y1, y2 = vstart[4:], vend[4:]
    return y2 if y1 == y2 else f"{y1}-{y2}"


def _from_match(
    m: re.Match,
    registry: str,
    source_method: str = "regex",
    raw_text: str | None = None,
    transformations: tuple[str, ...] = (),
    confidence: str = "high",
) -> SerialBlock:
    start, end = int(m.group("start")), int(m.group("end"))
    if start < 1 or end < start:
        raise SerialError(f"invalid unit range {start}-{end} in {m.group(0)}")
    if registry == "VCS":
        return SerialBlock(
            registry="VCS",
            batch_id=m.group("batch"),
            unit_start=start,
            unit_end=end,
            serial=m.group(0),
            project_id=m.group("project"),
            vintage=_vintage_from_verra(m.group("vstart"), m.group("vend")),
            country=m.group("country"),
            source_method=source_method,
            raw_text=raw_text or m.group(0),
            transformations=transformations,
            confidence=confidence,
        )
    return SerialBlock(
        registry="GS",
        batch_id=m.group("prefix"),
        unit_start=start,
        unit_end=end,
        serial=m.group(0),
        project_id=m.group("project"),
        vintage=m.group("vintage"),
        country=m.group("country"),
        source_method=source_method,
        raw_text=raw_text or m.group(0),
        transformations=transformations,
        confidence=confidence,
    )


def parse_serial(serial: str, heal_ocr: bool = False) -> SerialBlock:
    """Parse exactly one serial string (whole string must match)."""
    s = normalize(serial.strip()).upper()
    s = re.sub(r"\s+", "", s)
    m = VERRA_RE.fullmatch(s)
    if m:
        return _from_match(m, "VCS")
    m = GOLD_RE.fullmatch(s)
    if m:
        return _from_match(m, "GS")

    if heal_ocr:
        # Check if OCR repair yields a valid Verra serial
        m_ocr = VERRA_OCR_RE.fullmatch(s)
        if m_ocr:
            d = m_ocr.groupdict()
            parts = [
                heal_ocr_digits(d["batch"]),
                heal_ocr_digits(d["start"]),
                heal_ocr_digits(d["end"]),
                "VCS-VCU" if "VCS-" in s else "VCU",
                heal_ocr_digits(d["seq"]),
                d["org"].upper(),
                d["country"].upper(),
            ]
            if d.get("scope"):
                parts.append(heal_ocr_digits(d["scope"]))
            parts.extend([
                heal_ocr_digits(d["project"]),
                f"{heal_ocr_digits(d['vstart'])}-{heal_ocr_digits(d['vend'])}",
                heal_ocr_digits(d["flag"]),
            ])
            repaired = "-".join(parts)
            m_rep = VERRA_RE.fullmatch(repaired)
            if m_rep:
                return _from_match(
                    m_rep,
                    "VCS",
                    source_method="ocr_healed",
                    raw_text=serial,
                    transformations=("ocr_char_healed",),
                    confidence="medium",
                )

        # Check if OCR repair yields a valid Gold Standard serial
        m_gs_ocr = GOLD_OCR_RE.fullmatch(s)
        if m_gs_ocr:
            d = m_gs_ocr.groupdict()
            prefix_parts = d["prefix"].split("-")
            healed_prefix = [
                prefix_parts[0],
                heal_ocr_digits(prefix_parts[1]),
                prefix_parts[2].upper(),
                f"GS{heal_ocr_digits(d['project'])}" if prefix_parts[3].startswith("GS") else heal_ocr_digits(prefix_parts[3]),
                heal_ocr_digits(prefix_parts[4]),
                heal_ocr_digits(prefix_parts[5]),
                heal_ocr_digits(prefix_parts[6]),
            ]
            repaired = f"{'-'.join(healed_prefix)}-{heal_ocr_digits(d['start'])}-{heal_ocr_digits(d['end'])}"
            m_rep = GOLD_RE.fullmatch(repaired)
            if m_rep:
                return _from_match(
                    m_rep,
                    "GS",
                    source_method="ocr_healed",
                    raw_text=serial,
                    transformations=("ocr_char_healed",),
                    confidence="medium",
                )

    raise SerialError(f"unrecognized serial format: {serial[:120]!r}")


def _spans_overlap(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(a <= start < b or a < end <= b or (start <= a and end >= b) for a, b in spans)


def find_serials(text: str) -> list[SerialBlock]:
    """Find every serial block in free text, tables, prose ranges, and OCR scans. Deduplicates exact repeats."""
    norm = normalize(text)
    out: list[SerialBlock] = []
    seen: set[tuple] = set()
    spans: list[tuple[int, int]] = []

    # Pass 1: Strict standard regex (highest confidence, 100% precision)
    for registry, rx in (("VCS", VERRA_RE), ("GS", GOLD_RE)):
        for m in rx.finditer(norm):
            if _spans_overlap(spans, m.start(), m.end()):
                continue
            try:
                b = _from_match(m, registry, source_method="regex", raw_text=m.group(0))
            except SerialError:
                continue
            key = (b.registry, b.batch_id, b.unit_start, b.unit_end)
            if key not in seen:
                seen.add(key)
                out.append(b)
            spans.append((m.start(), m.end()))

    # Pass 2: Structured Table Extraction (tab, pipe, or multi-space delimited columns)
    for line in norm.splitlines():
        cells = [c.strip() for c in re.split(r"[\t|]+|\s{2,}", line) if c.strip()]
        if len(cells) >= 3:
            cand = "-".join(cells)
            try:
                b = parse_serial(cand, heal_ocr=True)
                key = (b.registry, b.batch_id, b.unit_start, b.unit_end)
                if key not in seen:
                    seen.add(key)
                    out.append(
                        SerialBlock(
                            registry=b.registry,
                            batch_id=b.batch_id,
                            unit_start=b.unit_start,
                            unit_end=b.unit_end,
                            serial=b.serial,
                            project_id=b.project_id,
                            vintage=b.vintage,
                            country=b.country,
                            source_method="table",
                            raw_text=line.strip(),
                            transformations=("table_columns_joined",),
                            confidence="high",
                        )
                    )
            except SerialError:
                pass

    # Pass 3: OCR character healing on degraded scans
    for m in VERRA_OCR_RE.finditer(norm):
        if _spans_overlap(spans, m.start(), m.end()):
            continue
        d = m.groupdict()
        parts = [
            heal_ocr_digits(d["batch"]),
            heal_ocr_digits(d["start"]),
            heal_ocr_digits(d["end"]),
            "VCS-VCU" if "VCS-" in m.group(0).upper() else "VCU",
            heal_ocr_digits(d["seq"]),
            d["org"].upper(),
            d["country"].upper(),
        ]
        if d.get("scope"):
            parts.append(heal_ocr_digits(d["scope"]))
        parts.extend([
            heal_ocr_digits(d["project"]),
            f"{heal_ocr_digits(d['vstart'])}-{heal_ocr_digits(d['vend'])}",
            heal_ocr_digits(d["flag"]),
        ])
        healed_str = "-".join(parts)
        try:
            b = parse_serial(healed_str)
            key = (b.registry, b.batch_id, b.unit_start, b.unit_end)
            if key not in seen:
                seen.add(key)
                out.append(
                    SerialBlock(
                        registry=b.registry,
                        batch_id=b.batch_id,
                        unit_start=b.unit_start,
                        unit_end=b.unit_end,
                        serial=b.serial,
                        project_id=b.project_id,
                        vintage=b.vintage,
                        country=b.country,
                        source_method="ocr_healed",
                        raw_text=m.group(0),
                        transformations=("ocr_char_healed",),
                        confidence="medium",
                    )
                )
                spans.append((m.start(), m.end()))
        except SerialError:
            pass

    for m in GOLD_OCR_RE.finditer(norm):
        if _spans_overlap(spans, m.start(), m.end()):
            continue
        d = m.groupdict()
        prefix_parts = d["prefix"].split("-")
        healed_prefix = [
            prefix_parts[0],
            heal_ocr_digits(prefix_parts[1]),
            prefix_parts[2].upper(),
            f"GS{heal_ocr_digits(d['project'])}" if prefix_parts[3].startswith("GS") else heal_ocr_digits(prefix_parts[3]),
            heal_ocr_digits(prefix_parts[4]),
            heal_ocr_digits(prefix_parts[5]),
            heal_ocr_digits(prefix_parts[6]),
        ]
        healed_str = f"{'-'.join(healed_prefix)}-{heal_ocr_digits(d['start'])}-{heal_ocr_digits(d['end'])}"
        try:
            b = parse_serial(healed_str)
            key = (b.registry, b.batch_id, b.unit_start, b.unit_end)
            if key not in seen:
                seen.add(key)
                out.append(
                    SerialBlock(
                        registry=b.registry,
                        batch_id=b.batch_id,
                        unit_start=b.unit_start,
                        unit_end=b.unit_end,
                        serial=b.serial,
                        project_id=b.project_id,
                        vintage=b.vintage,
                        country=b.country,
                        source_method="ocr_healed",
                        raw_text=m.group(0),
                        transformations=("ocr_char_healed",),
                        confidence="medium",
                    )
                )
                spans.append((m.start(), m.end()))
        except SerialError:
            pass

    # Pass 4: Prose range extraction ("units 1000 to 2000 of Verra batch 12345")
    for rx in (PROSE_RE, PROSE_RE_ALT):
        for m in rx.finditer(norm):
            if _spans_overlap(spans, m.start(), m.end()):
                continue
            try:
                s_val = int(re.sub(r"[^\d]", "", m.group("start")))
                e_val = int(re.sub(r"[^\d]", "", m.group("end")))
                batch = m.group("batch").strip()
                reg_str = (m.group("reg") or "").strip()
                reg = "GS" if ("g" in reg_str.lower() or batch.startswith("GS")) else "VCS"
                if s_val <= e_val and s_val >= 1:
                    key = (reg, batch, s_val, e_val)
                    if key not in seen:
                        seen.add(key)
                        out.append(
                            SerialBlock(
                                registry=reg,
                                batch_id=batch,
                                unit_start=s_val,
                                unit_end=e_val,
                                serial=f"{batch}-{s_val}-{e_val}-{reg}",
                                project_id=m.group("project"),
                                vintage=m.group("vintage"),
                                country=None,
                                source_method="prose",
                                raw_text=m.group(0).strip(),
                                transformations=("prose_range_parsed",),
                                confidence="medium",
                            )
                        )
                        spans.append((m.start(), m.end()))
            except (ValueError, TypeError):
                pass

    return out


def find_ambiguous_mentions(text: str) -> list[dict]:
    """Identify rejected, inverted, or ambiguous serial specifications in document text."""
    norm = normalize(text)
    ambiguous = []

    # Inverted ranges in prose: e.g. units 500 to 400
    for rx in (PROSE_RE, PROSE_RE_ALT):
        for m in rx.finditer(norm):
            try:
                s_val = int(re.sub(r"[^\d]", "", m.group("start")))
                e_val = int(re.sub(r"[^\d]", "", m.group("end")))
                if s_val > e_val:
                    ambiguous.append({
                        "type": "inverted_unit_range",
                        "raw_text": m.group(0),
                        "detail": f"Start unit {s_val} exceeds end unit {e_val}",
                    })
            except (ValueError, TypeError):
                pass

    return ambiguous


def overlap(a: SerialBlock, b: SerialBlock) -> tuple[int, int] | None:
    """Inclusive overlap of two blocks in the same namespace, else None."""
    if a.namespace != b.namespace:
        return None
    lo, hi = max(a.unit_start, b.unit_start), min(a.unit_end, b.unit_end)
    return (lo, hi) if lo <= hi else None

"""Evidence text extraction and structured fact extraction.

Two independent extractors run on every document:
  * deterministic: layout-aware & OCR-resilient serial parser (always on, auditable, used for anchoring)
  * llm (optional): Claude returns schema-validated JSON; every serial it reports is
    re-parsed by the deterministic parser before it can influence a claim.
  * mock llm: deterministic simulation mode for offline zero-cost benchmark evaluation.
"""
from __future__ import annotations

import io
import logging
import os
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from .config import settings
from .normalization import normalize_beneficiary_name, normalize_date_iso
from .serials import (
    SerialBlock,
    SerialError,
    find_ambiguous_mentions,
    find_serials,
    parse_serial,
)

log = logging.getLogger("onceonly.extraction")


def pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def document_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf") or data[:5] == b"%PDF-":
        return pdf_text(data)
    return data.decode("utf-8", errors="replace")


# ----------------------------------------------------------------- deterministic

_QTY_RE = re.compile(r"(?:quantity|qty|amount|total)[^\d\n]{0,30}([\d][\d,\. ]{0,15}\d|\d)", re.I)
_BEN_RE = re.compile(
    r"(?:beneficiary|beneficial owner|retired on behalf of|on behalf of|using entity)\s*[:\-]?\s*(.+?)"
    r"(?=\s*[.;]?(?:\s+(?:date|retirement date|vintage|quantity|project)\s*[:\-])|[;\n\r]|$)",
    re.I,
)
_DATE_RE = re.compile(r"(?:retirement date|date of retirement|retired on)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}[/.]\d{4}|\d{1,2} \w+ \d{4})", re.I)
_U_REG = re.compile(r"\b(VCS|Verra|Gold Standard|GS)\b", re.I)
_U_PID = re.compile(r"\b(?:project|GS ?ID|ID)\s*(?:ID)?\s*#?\s*(?:GS)?(\d{2,6})\b", re.I)
_U_VIN = re.compile(r"\bvintage\s*(\d{4})\b", re.I)
_U_QTY = re.compile(r"(\d[\d,\.]*)\s*(?:tCO2e|tonnes|t\b|VCUs|VERs|credits)", re.I)


def _key(b: SerialBlock) -> tuple:
    return (b.registry, b.batch_id, b.unit_start, b.unit_end)


def _num(s: str | None) -> int | None:
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


@dataclass
class UnserializedAssertion:
    registry: str
    project_id: str
    vintage: str
    quantity: int
    text: str


@dataclass
class Extraction:
    blocks: list[SerialBlock]
    stated_quantity: int | None = None
    beneficiary: str | None = None
    retirement_date: str | None = None
    unserialized: list[UnserializedAssertion] = field(default_factory=list)
    ambiguous_mentions: list[dict] = field(default_factory=list)
    llm_used: bool = False
    llm_status: str = "not-configured"  # not-configured | ok | error | disabled | mock
    llm_blocks: list[SerialBlock] = field(default_factory=list)
    llm_rejected: list[str] = field(default_factory=list)
    llm_fields: dict = field(default_factory=dict)
    parser_keys: set = field(default_factory=set)


def deterministic_extract(text: str) -> Extraction:
    blocks = find_serials(text)
    ambiguous = find_ambiguous_mentions(text)
    qty = _num(m.group(1)) if (m := _QTY_RE.search(text)) else None

    # Beneficiary normalization
    raw_ben = m.group(1).strip()[:200] if (m := _BEN_RE.search(text)) else None
    ben_rec, ben_kind = normalize_beneficiary_name(raw_ben)
    ben = ben_rec.normalized_value if ben_kind == "named" else raw_ben

    # Date normalization
    raw_date = m.group(1) if (m := _DATE_RE.search(text)) else None
    date_rec = normalize_date_iso(raw_date)
    date = date_rec.normalized_value or raw_date

    uns = []
    if not blocks:
        # heuristic: registry, project, vintage and quantity mentioned in the same sentence, any order
        for sent in re.split(r"(?<=[.;])\s+|\n+", text):
            r, p, v, q = _U_REG.search(sent), _U_PID.search(sent), _U_VIN.search(sent), _U_QTY.search(sent)
            if r and p and v and q and _num(q.group(1)):
                reg = "GS" if r.group(1).upper() in ("GS", "GOLD STANDARD") else "VCS"
                uns.append(UnserializedAssertion(reg, p.group(1), v.group(1), _num(q.group(1)), sent.strip()[:200]))

    return Extraction(
        blocks=blocks,
        stated_quantity=qty,
        beneficiary=ben,
        retirement_date=date,
        unserialized=uns,
        ambiguous_mentions=ambiguous,
        parser_keys={_key(b) for b in blocks},
    )


# --------------------------------------------------------------------------- llm

class LlmBlock(BaseModel):
    serial: str = Field(description="Full registry serial number exactly as printed, joined if wrapped across lines; empty if only a range is described")
    quantity: int | None = Field(default=None, description="Number of credits/units in this block")
    project_id: str | None = None
    vintage: str | None = None


class LlmExtraction(BaseModel):
    beneficiary: str | None = Field(default=None, description="Entity the credits were retired for/on behalf of")
    retirement_date: str | None = Field(default=None, description="ISO date YYYY-MM-DD if present")
    total_quantity: int | None = None
    blocks: list[LlmBlock] = Field(default_factory=list)


SYSTEM_PROMPT = (
    "You extract facts from carbon credit retirement certificates and corporate offset-claim documents. "
    "Return only what the document states. Copy serial numbers exactly, character for character; if a serial "
    "is broken across lines or columns, join the pieces. Do not infer serials that are not printed. "
    "Do not judge whether credits are legitimate, high quality, or double counted."
)


def is_mock_llm() -> bool:
    return os.environ.get("ONCEONLY_MOCK_LLM") == "1" or settings.llm_model == "mock"


def llm_available() -> bool:
    return is_mock_llm() or (settings.llm_enabled and bool(settings.anthropic_api_key))


def mock_llm_extract(text: str) -> LlmExtraction:
    """Deterministic offline mock extraction fixture for testing and CI without live API credentials."""
    blocks = find_serials(text)
    qty = _num(m.group(1)) if (m := _QTY_RE.search(text)) else None
    raw_ben = m.group(1).strip()[:200] if (m := _BEN_RE.search(text)) else None
    ben_rec, _ = normalize_beneficiary_name(raw_ben)
    raw_date = m.group(1) if (m := _DATE_RE.search(text)) else None
    date_rec = normalize_date_iso(raw_date)

    llm_blks = [
        LlmBlock(
            serial=b.serial,
            quantity=b.quantity,
            project_id=b.project_id,
            vintage=b.vintage,
        )
        for b in blocks
    ]
    return LlmExtraction(
        beneficiary=ben_rec.normalized_value or raw_ben,
        retirement_date=date_rec.normalized_value or raw_date,
        total_quantity=qty,
        blocks=llm_blks,
    )


def llm_extract(text: str) -> LlmExtraction:
    if is_mock_llm():
        return mock_llm_extract(text)

    import anthropic

    # Explicit key and base URL: never inherit unrelated credentials from the environment.
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, base_url="https://api.anthropic.com", timeout=60.0, max_retries=1)
    response = client.messages.parse(
        model=settings.llm_model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"<document>\n{text[:60000]}\n</document>\nExtract the retirement facts."}],
        output_format=LlmExtraction,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"no structured output (stop_reason={response.stop_reason})")
    return response.parsed_output


def extract(text: str, use_llm: bool | None = None) -> Extraction:
    ex = deterministic_extract(text)
    want = llm_available() if use_llm is None else (use_llm and llm_available())
    if not want:
        ex.llm_status = "disabled" if not settings.llm_enabled else "not-configured"
        return ex
    try:
        out = llm_extract(text)
    except Exception as e:  # network, auth, rate limit, refusal, validation: fall back to parser
        log.warning("LLM extraction failed: %s", e)
        ex.llm_status = "error"
        ex.llm_fields = {"error": type(e).__name__}
        return ex
    ex.llm_used, ex.llm_status = True, ("mock" if is_mock_llm() else "ok")
    ex.llm_fields = out.model_dump()
    for b in out.blocks:
        if not b.serial:
            ex.llm_rejected.append("(range described without a serial)")
            continue
        try:
            ex.llm_blocks.append(parse_serial(b.serial, heal_ocr=True))
        except SerialError:
            ex.llm_rejected.append(b.serial[:120])
    # Merge: blocks only the LLM found are kept but tagged for review downstream.
    for b in ex.llm_blocks:
        if _key(b) not in ex.parser_keys:
            ex.blocks.append(b)
    ex.beneficiary = ex.beneficiary or out.beneficiary
    ex.retirement_date = ex.retirement_date or out.retirement_date
    ex.stated_quantity = ex.stated_quantity or out.total_quantity
    return ex


def block_source(ex: Extraction, b: SerialBlock) -> str:
    """'both' = parser and LLM agree; 'parser' = parser only; 'llm' = LLM only (needs review)."""
    in_det = _key(b) in ex.parser_keys
    in_llm = any(_key(x) == _key(b) for x in ex.llm_blocks)
    if in_det and in_llm:
        return "both"
    return "llm" if in_llm else "parser"

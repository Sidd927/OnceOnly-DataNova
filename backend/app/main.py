"""OnceOnly API."""
from __future__ import annotations

import html
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, model_validator

from . import db, service
from .chain import try_ledger
from .config import ROOT, settings
from .extraction import llm_available
from .reference import Reference
from .rules import RULES
from .analytics import (
    AnalyticsEngine,
    BatchAnalyticsRequest,
    BatchAnalyticsResult,
    BatchFragmentationRequest,
    ConcentrationRequest,
    CrossRegistryEntityCompareRequest,
    CrossRegistryProjectCompareRequest,
    RiskAssessmentRequest,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="OnceOnly API", version="0.1.0", description="Every retired tonne, claimed once.")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])

_state: dict = {}


def con():
    if "con" not in _state:
        _state["con"] = db.connect()
    return _state["con"]


def ref() -> Reference | None:
    if "ref" not in _state:
        _state["ref"] = Reference.open()
    return _state["ref"]


@app.exception_handler(service.ServiceError)
async def _svc_err(_: Request, e: service.ServiceError):
    return JSONResponse(status_code=e.status, content={"error": e.message, "detail": e.detail})


# ------------------------------------------------------------------- read models

def claim_detail(claim_id: int) -> dict:
    c = con().execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if c is None:
        raise HTTPException(404, "Claim not found")
    out = dict(c)
    out.pop("claimant_salt", None)
    out["synthetic"] = bool(out["synthetic"])
    out["extraction"] = json.loads(out.pop("extraction_json") or "{}")
    out["evidence"] = [dict(r) | {"text_excerpt": (r["text_excerpt"] or "")[:1500]} for r in con().execute("SELECT id, filename, sha256, size, mime, text_excerpt FROM evidence WHERE claim_id=?", (claim_id,))]
    out["blocks"] = [dict(r) | {"quantity": r["unit_end"] - r["unit_start"] + 1, "namespace": f"{r['registry']}:{r['batch_id']}"} for r in con().execute("SELECT * FROM claim_blocks WHERE claim_id=? ORDER BY idx", (claim_id,))]
    out["findings"] = [dict(r) | {"evidence": json.loads(r["evidence_json"] or "{}")} for r in con().execute("SELECT * FROM findings WHERE claim_id=? ORDER BY CASE severity WHEN 'blocking' THEN 0 WHEN 'review' THEN 1 WHEN 'info' THEN 2 ELSE 3 END, id", (claim_id,))]
    for f in out["findings"]:
        f.pop("evidence_json", None)
    out["events"] = [dict(r) | {"detail": json.loads(r["detail_json"] or "{}")} for r in con().execute("SELECT * FROM events WHERE claim_id=? ORDER BY id", (claim_id,))]
    for e in out["events"]:
        e.pop("detail_json", None)
    out["total_units"] = sum(b["quantity"] for b in out["blocks"])
    out["unit_strips"] = unit_strips(claim_id, out["blocks"])
    return out


def unit_strips(claim_id: int, blocks: list[dict]) -> list[dict]:
    """For each block: the registry records and other claims in the same namespace, for visualization."""
    strips = []
    r = ref()
    for b in blocks:
        lo, hi = b["unit_start"], b["unit_end"]
        records = []
        if r is not None:
            cov = r.coverage(b["registry"], b["batch_id"], lo, hi)
            records = [{"unit_start": x["unit_start"], "unit_end": x["unit_end"], "kind": "retirement", "event_date": x["event_date"], "beneficiary": x["beneficiary"], "serial": x["serial"]} for x in cov.records[:50]]
            if not records:
                records = [{"unit_start": x["unit_start"], "unit_end": x["unit_end"], "kind": "issuance", "event_date": x["event_date"], "serial": x["serial"]} for x in cov.issuance_records[:5]]
        others = [dict(x) for x in con().execute(
            """SELECT c.id AS claim_id, c.ref, c.claimant, c.status, b.unit_start, b.unit_end FROM claim_blocks b JOIN claims c ON c.id=b.claim_id
               WHERE b.registry=? AND b.batch_id=? AND c.id != ? AND b.unit_start <= ? AND b.unit_end >= ?""",
            (b["registry"], b["batch_id"], claim_id, hi + (hi - lo + 1), lo - (hi - lo + 1)),
        )]
        spans = [lo, hi] + [x["unit_start"] for x in records + others] + [x["unit_end"] for x in records + others]
        strips.append({"block_index": b["idx"], "namespace": b["namespace"], "claim": {"unit_start": lo, "unit_end": hi},
                       "records": records, "others": others, "domain": [min(spans), max(spans)]})
    return strips


def summarize(c) -> dict:
    d = dict(c)
    for k in ("claimant_salt", "extraction_json"):
        d.pop(k, None)
    d["synthetic"] = bool(d["synthetic"])
    d["total_units"] = con().execute("SELECT COALESCE(SUM(unit_end-unit_start+1),0) FROM claim_blocks WHERE claim_id=?", (c["id"],)).fetchone()[0]
    d["block_count"] = con().execute("SELECT COUNT(*) FROM claim_blocks WHERE claim_id=?", (c["id"],)).fetchone()[0]
    counts = {r[0]: r[1] for r in con().execute("SELECT severity, COUNT(*) FROM findings WHERE claim_id=? GROUP BY severity", (c["id"],))}
    d["finding_counts"] = counts
    return d


# ------------------------------------------------------------------------ routes

@app.get("/api/health")
def health():
    ledger, err = try_ledger()
    r = ref()
    return {
        "status": "ok",
        "reference": {"loaded": r is not None, "scope": r.scope if r else None},
        "chain": {"available": ledger is not None, "error": err, **({"chain_id": ledger.chain_id, "address": ledger.address, "block_number": ledger.w3.eth.block_number, "public_network": ledger.chain_id != 31337} if ledger else {})},
        "llm": {"configured": llm_available(), "model": settings.llm_model if llm_available() else None},
        "public_demo": settings.public_demo,
    }


# ------------------------------------------------------------- public demo guards

PUBLIC_WRITE_MESSAGE = (
    "Ledger writes are disabled on this public demo instance so every visitor sees the same story. "
    "The seeded anchoring and the contract's rejection are real transactions on the instance's local chain. "
    "Run OnceOnly locally (see the README) to anchor, challenge or withdraw claims."
)
_submissions: dict[str, list[float]] = {}


def guard_ledger_write():
    if settings.public_demo:
        raise service.ServiceError(403, PUBLIC_WRITE_MESSAGE, {"public_demo": True})


def guard_claim_submission(request: Request):
    if not settings.public_demo:
        return
    import time

    total = con().execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    if total >= settings.public_max_claims:
        raise service.ServiceError(429, "This public demo instance has reached its claim limit. It resets when restarted; the local version has no limit.", {"public_demo": True})
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown"))
    now = time.time()
    recent = [t for t in _submissions.get(ip, []) if now - t < 600]
    if len(recent) >= settings.public_rate_per_10min:
        raise service.ServiceError(429, f"Too many claim checks from this address. The public demo allows {settings.public_rate_per_10min} per 10 minutes.", {"public_demo": True})
    _submissions[ip] = [*recent, now]


@app.get("/api/overview")
def overview():
    c = con()
    by_status = {r[0]: r[1] for r in c.execute("SELECT status, COUNT(*) FROM claims GROUP BY status")}
    units_anchored = c.execute("SELECT COALESCE(SUM(b.unit_end-b.unit_start+1),0) FROM claim_blocks b JOIN claims c ON c.id=b.claim_id WHERE c.status IN ('anchored','challenged')").fetchone()[0]
    rejected = c.execute("SELECT COUNT(*) FROM events WHERE kind='chain_rejected'").fetchone()[0]
    dup_findings = c.execute("SELECT COUNT(DISTINCT claim_id) FROM findings WHERE rule_id='DUP-001'").fetchone()[0]
    ledger, err = try_ledger()
    r = ref()
    audit_path = ROOT / "eval/results/registry_audit.json"
    eval_path = ROOT / "eval/results/latest.json"
    recent = [dict(x) | {"detail": json.loads(x["detail_json"] or "{}")} for x in c.execute(
        "SELECT e.id, e.kind, e.tx_hash, e.block_number, e.created_at, e.detail_json, e.claim_id, cl.ref, cl.claimant FROM events e LEFT JOIN claims cl ON cl.id=e.claim_id ORDER BY e.id DESC LIMIT 12")]
    for x in recent:
        x.pop("detail_json", None)
    chain_events = [dict(x) for x in c.execute(
        "SELECT e.id, e.kind, e.tx_hash, e.block_number, e.created_at, e.claim_id, cl.ref, cl.claimant FROM events e LEFT JOIN claims cl ON cl.id=e.claim_id "
        "WHERE e.tx_hash IS NOT NULL ORDER BY e.id DESC LIMIT 10")]
    return {
        "recent_chain_events": chain_events,
        "claims": {"total": sum(by_status.values()), "by_status": by_status, "units_anchored": units_anchored, "with_double_use_findings": dup_findings, "chain_rejections": rejected},
        "chain": ledger.info() if ledger else {"available": False, "error": err},
        "reference": r.meta() if r else None,
        "registry_audit": json.loads(audit_path.read_text()) if audit_path.exists() else None,
        "evaluation": json.loads(eval_path.read_text()) if eval_path.exists() else None,
        "llm": {"configured": llm_available(), "model": settings.llm_model if llm_available() else None},
        "recent_events": recent,
    }


@app.get("/api/claims")
def list_claims():
    return [summarize(c) for c in con().execute("SELECT * FROM claims ORDER BY id DESC")]


class EntityPairRequest(BaseModel):
    name_a: str
    name_b: str


class IntermediaryRequest(BaseModel):
    text: str


@app.post("/api/resolve/entity-pair")
def resolve_entity_pair(body: EntityPairRequest):
    from .entity_resolution import EntityResolutionEngine
    res = EntityResolutionEngine.resolve_pair(body.name_a, body.name_b)
    return res.to_dict()


@app.post("/api/resolve/intermediary")
def resolve_intermediary(body: IntermediaryRequest):
    from .entity_resolution import EntityResolutionEngine
    res = EntityResolutionEngine.extract_intermediary(body.text)
    return res.to_dict()


# ------------------------------------------------------------------- allocation & reconciliation (Phase 2B)

class AllocationModel(BaseModel):
    registry: str
    batch_id: str
    unit_start: int
    unit_end: int
    claimant: str
    claim_id: int | None = None
    claim_ref: str | None = None
    status: str | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> AllocationModel:
        if self.unit_start < 0:
            raise ValueError(f"unit_start must be non-negative, got {self.unit_start}")
        if self.unit_end < 0:
            raise ValueError(f"unit_end must be non-negative, got {self.unit_end}")
        if self.unit_start > self.unit_end:
            raise ValueError(f"unit_start ({self.unit_start}) cannot exceed unit_end ({self.unit_end})")
        return self


class CompareAllocationsRequest(BaseModel):
    candidate: AllocationModel
    existing: AllocationModel


class BatchReconcileRequest(BaseModel):
    registry: str
    batch_id: str
    allocations: list[AllocationModel]


@app.post("/api/reconcile/compare")
def reconcile_compare(body: CompareAllocationsRequest):
    from .reconciliation import AllocationReconciler
    item = AllocationReconciler.reconcile_allocation_pair(body.candidate.model_dump(), body.existing.model_dump())
    return item.to_dict()


@app.post("/api/reconcile/batch")
def reconcile_batch(body: BatchReconcileRequest):
    from .reconciliation import AllocationReconciler, validate_disjoint_ranges
    allocs = [a.model_dump() for a in body.allocations]
    ranges = [(int(a["unit_start"]), int(a["unit_end"])) for a in allocs]
    is_disjoint, err = validate_disjoint_ranges(ranges)

    pairwise = []
    splits = []
    conflicts = []
    for i in range(len(allocs)):
        for j in range(i + 1, len(allocs)):
            res = AllocationReconciler.reconcile_allocation_pair(allocs[i], allocs[j])
            p_dict = res.to_dict()
            pairwise.append(p_dict)
            if res.overlap.is_conflict:
                conflicts.append(p_dict)
            else:
                splits.append(p_dict)

    return {
        "registry": body.registry,
        "batch_id": body.batch_id,
        "total_allocations": len(allocs),
        "total_units": sum(int(a["unit_end"]) - int(a["unit_start"]) + 1 for a in allocs),
        "is_disjoint": is_disjoint,
        "disjoint_error": err,
        "conflicts": conflicts,
        "splits": splits,
        "pairwise_count": len(pairwise),
    }


@app.get("/api/claims/{claim_id}/reconciliation")
def get_claim_reconciliation(claim_id: int):
    from .reconciliation import AllocationReconciler
    claim = con().execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if claim is None:
        raise HTTPException(404, "Claim not found")
    blocks = [dict(r) for r in con().execute("SELECT * FROM claim_blocks WHERE claim_id=? ORDER BY idx", (claim_id,))]
    active = service.active_ranges(con(), exclude_claim=claim_id)
    report = AllocationReconciler.reconcile_claim_blocks(claim_id, claim["claimant"], blocks, active)
    return report.to_dict()


@app.post("/api/claims", status_code=201)
async def create_claim(
    request: Request,
    claimant: str = Form(...),
    claim_date: str | None = Form(None),
    period: str | None = Form(None),
    statement: str | None = Form(None),
    text: str | None = Form(None),
    synthetic: bool = Form(True),
    use_llm: bool | None = Form(None),
    files: list[UploadFile] | None = File(None),
):
    guard_claim_submission(request)
    uploads = []
    for f in files or []:
        data = await f.read(settings.max_upload_bytes + 1)
        uploads.append(service.Upload(Path(f.filename or "upload").name, data, f.content_type))
    cid = service.create_claim(con(), ref(), claimant=claimant, claim_date=claim_date, period=period, statement=statement,
                               pasted_text=text, uploads=uploads, synthetic=synthetic, use_llm=use_llm)
    return claim_detail(cid)


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: int):
    return claim_detail(claim_id)


@app.post("/api/claims/{claim_id}/recheck")
def recheck(claim_id: int):
    service.run_checks(con(), ref(), claim_id)
    return claim_detail(claim_id)


class AnchorBody(BaseModel):
    acknowledge_review: bool = False
    force: bool = False


@app.post("/api/claims/{claim_id}/anchor")
def anchor(claim_id: int, body: AnchorBody):
    guard_ledger_write()
    res = service.anchor(con(), ref(), claim_id, body.acknowledge_review, body.force)
    return {"result": res, "claim": claim_detail(claim_id)}


class ChallengeBody(BaseModel):
    reason: str


@app.post("/api/claims/{claim_id}/challenge")
def challenge(claim_id: int, body: ChallengeBody):
    guard_ledger_write()
    res = service.challenge(con(), claim_id, body.reason)
    return {"result": res, "claim": claim_detail(claim_id)}


class ResolveBody(BaseModel):
    upheld: bool
    note: str = ""


@app.post("/api/claims/{claim_id}/resolve")
def resolve(claim_id: int, body: ResolveBody):
    guard_ledger_write()
    res = service.resolve(con(), claim_id, body.upheld, body.note)
    return {"result": res, "claim": claim_detail(claim_id)}


@app.post("/api/claims/{claim_id}/withdraw")
def withdraw(claim_id: int):
    guard_ledger_write()
    res = service.withdraw(con(), claim_id)
    return {"result": res, "claim": claim_detail(claim_id)}


@app.post("/api/verify")
async def verify(
    ref_: str | None = Form(None, alias="ref"),
    chain_claim_id: int | None = Form(None),
    claimant: str | None = Form(None),
    salt: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    up = None
    if file is not None:
        up = service.Upload(Path(file.filename or "upload").name, await file.read(settings.max_upload_bytes + 1), file.content_type)
    return service.verify(con(), ref_, chain_claim_id, up, salt, claimant)


@app.get("/api/claims/{claim_id}/report.json")
def report_json(claim_id: int):
    d = claim_detail(claim_id)
    d.pop("unit_strips", None)
    return JSONResponse(d, headers={"Content-Disposition": f'attachment; filename="{d["ref"]}-integrity-report.json"'})


@app.get("/api/claims/{claim_id}/report.html", response_class=HTMLResponse)
def report_html(claim_id: int):
    d = claim_detail(claim_id)
    e = html.escape
    rows = "".join(
        f"<tr><td class=mono>{e(b['namespace'])}</td><td class=mono>{b['unit_start']:,}–{b['unit_end']:,}</td><td>{b['quantity']:,}</td><td>{e(b['project_id'] or '')}</td><td>{e(b['vintage'] or '')}</td></tr>"
        for b in d["blocks"])
    finds = "".join(
        f"<div class='f {e(f['severity'])}'><b>{e(f['rule_id'])} · {e(f['severity'].upper())}</b> — {e(f['title'])}<p>{e(f['explanation'])}</p>"
        + (f"<p><i>Uncertain:</i> {e(f['uncertainty'])}</p>" if f["uncertainty"] else "") + (f"<p><i>Next action:</i> {e(f['next_action'])}</p>" if f["next_action"] else "") + "</div>"
        for f in d["findings"])
    events = "".join(f"<li>{e(ev['created_at'])} — {e(ev['kind'])}{' · tx ' + e(ev['tx_hash']) if ev['tx_hash'] else ''}</li>" for ev in d["events"])
    chain = (f"Anchored as on-chain claim #{d['chain_claim_id']} in block {d['block_number']} (chain id {d['chain_id']}, contract {e(d['contract_address'] or '')}), tx {e(d['tx_hash'] or '')}."
             if d["chain_claim_id"] else "Not anchored on the ledger.")
    local_note = " Chain id 31337 is a local development network, not a public blockchain." if d.get("chain_id") == 31337 else ""
    page = f"""<!doctype html><html><head><meta charset=utf-8><title>{e(d['ref'])} — OnceOnly integrity report</title>
<style>body{{font:14px/1.5 system-ui,sans-serif;max-width:860px;margin:32px auto;color:#14211b}}.mono{{font-family:ui-monospace,monospace}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:6px;text-align:left}}
.f{{border-left:4px solid #999;padding:6px 12px;margin:10px 0;background:#fafaf7}}.blocking{{border-color:#b42318}}.review{{border-color:#b54708}}.pass{{border-color:#067647}}.banner{{background:#fff4d6;padding:8px 12px;border-radius:6px}}</style></head><body>
<h1>Claim integrity report — {e(d['ref'])}</h1>
{"<p class=banner><b>SYNTHETIC DEMO CLAIM.</b> Claimant and certificate are fictional; registry records are real public data (Berkeley VROD 2026-08, CC BY 4.0).</p>" if d['synthetic'] else ""}
<p><b>Claimant:</b> {e(d['claimant'])} · <b>Period:</b> {e(d['period'] or '—')} · <b>Status:</b> {e(d['status'])} · <b>Verdict:</b> {e(d['verdict'] or '')}</p>
<p><b>Ledger:</b> {chain}{local_note}</p>
<p class=mono>Evidence commitment: {e(d['evidence_hash'] or '')}<br>Report hash: {e(d['report_hash'] or '')}<br>Claimant commitment: {e(d['claimant_commitment'])}</p>
<h2>Claimed unit ranges ({d['total_units']:,} units)</h2><table><tr><th>Namespace</th><th>Units</th><th>Qty</th><th>Project</th><th>Vintage</th></tr>{rows}</table>
<h2>Findings</h2>{finds}<h2>Audit trail</h2><ul>{events}</ul>
<p style="color:#666;font-size:12px">OnceOnly checks whether the same registry units are claimed more than once and reconciles serials with a public registry snapshot. It does not assess credit quality, additionality or permanence, and a finding is not a determination of fraud.</p></body></html>"""
    return HTMLResponse(page)


@app.get("/api/evidence/{sha256}")
def evidence_lookup(sha256: str):
    """Which claims already cite a document with this SHA-256 (read-only; used for intake feedback)."""
    if len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256.lower()):
        raise HTTPException(422, "Expected a 64-character hex SHA-256 digest")
    rows = con().execute(
        "SELECT c.id AS claim_id, c.ref, c.claimant, c.status, e.filename FROM evidence e JOIN claims c ON c.id=e.claim_id WHERE e.sha256=? ORDER BY c.id",
        (sha256.lower(),),
    ).fetchall()
    return {"sha256": sha256.lower(), "claims": [dict(r) for r in rows]}


@app.get("/api/reference/lookup")
def reference_lookup(serial: str):
    from .serials import SerialError, parse_serial

    try:
        b = parse_serial(serial)
    except SerialError as e:
        raise HTTPException(422, str(e))
    r = ref()
    if r is None:
        raise HTTPException(503, "Reference index not loaded")
    cov = r.coverage(b.registry, b.batch_id, b.unit_start, b.unit_end)
    return {"block": b.to_dict(), "retired_units": cov.retired_units, "issued_units": cov.issued_units, "records": cov.records[:20], "scope": r.scope}


@app.get("/api/reference/samples")
def reference_samples(limit: int = 12):
    r = ref()
    if r is None:
        raise HTTPException(503, "Reference index not loaded")
    return {"scope": r.scope, "records": r.sample_retirements(min(limit, 50))}


@app.get("/api/rules")
def rules():
    return RULES


@app.get("/api/eval")
def evaluation():
    d = ROOT / "eval/results"
    out = {}
    for name in ("latest.json", "registry_audit.json", "gas.json"):
        p = d / name
        if p.exists():
            out[name.removesuffix(".json")] = json.loads(p.read_text())
    return out


# ------------------------------------------------------------- demo documents

DEMO_DIR = ROOT / "data/demo"


def _demo_manifest() -> list[dict]:
    p = DEMO_DIR / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else []


@app.get("/api/samples")
def samples():
    return _demo_manifest()


@app.get("/api/samples/{name}")
def sample_file(name: str):
    from fastapi.responses import FileResponse

    allowed = {m["file"] for m in _demo_manifest()}
    if name not in allowed:  # only files listed in the manifest; no path traversal
        raise HTTPException(404, "Unknown sample")
    media = "application/pdf" if name.endswith(".pdf") else "text/plain"
    return FileResponse(DEMO_DIR / name, media_type=media, filename=name)


# ------------------------------------------------------- analytics (Phase 2C Stage 1)


@app.get("/api/analytics/population/summary")
def analytics_population_summary():
    """Retrieve population-level dual-track concentration and batch fragmentation summaries."""
    from .analytics import AnalyticsEngine
    summary = AnalyticsEngine.analyze_population_summary()
    return summary.to_dict()


@app.get("/api/analytics/batches/{registry}/{batch_id}")
def analytics_batch(registry: str, batch_id: str):
    """Retrieve concentration and fragmentation analytics for a specific batch in a registry namespace."""
    from .analytics import AnalyticsEngine
    try:
        res = AnalyticsEngine.analyze_batch(registry=registry, batch_id=batch_id)
        return res.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/analytics/concentration")
def analytics_concentration(body: ConcentrationRequest):
    """Perform ad-hoc beneficiary concentration analysis over supplied retirement records."""
    from .analytics import AnalyticsEngine
    metrics = AnalyticsEngine.analyze_concentration_records(
        body.records, total_units_override=body.total_units_override
    )
    return metrics.to_dict()


@app.post("/api/analytics/fragmentation")
def analytics_fragmentation(body: BatchFragmentationRequest):
    """Perform ad-hoc batch fragmentation and interval structure analysis over supplied records."""
    from .analytics import AnalyticsEngine
    metrics = AnalyticsEngine.analyze_batch_records(
        body.records,
        registry=body.registry,
        batch_id=body.batch_id,
        project_id=body.project_id,
        micro_threshold=body.micro_threshold,
    )
    return metrics.to_dict()


@app.post("/api/analytics/batch")
def analytics_batch_adhoc(body: BatchAnalyticsRequest):
    """Perform combined concentration and batch fragmentation analysis over ad-hoc retirement records."""
    from datetime import datetime, timezone
    from .analytics import AnalyticsEngine, BatchAnalyticsResult
    concentration = AnalyticsEngine.analyze_concentration_records(body.records)
    fragmentation = AnalyticsEngine.analyze_batch_records(
        body.records,
        registry=body.registry,
        batch_id=body.batch_id,
        project_id=body.project_id,
    )
    res = BatchAnalyticsResult(
        registry=body.registry,
        batch_id=body.batch_id,
        project_id=body.project_id,
        project_name=body.project_name,
        country=body.country,
        vintage=body.vintage,
        total_quantity=fragmentation.total_units,
        total_events=fragmentation.total_events,
        concentration=concentration,
        fragmentation=fragmentation,
        computed_at=datetime.now(timezone.utc),
    )
    return res.to_dict()


# ------------------------------------------------------- temporal analytics (Phase 2C Stage 2)


@app.get("/api/analytics/temporal/activity")
def analytics_temporal_activity(
    registry: Optional[str] = Query(None, description="Optional registry code ('VCS', 'GS')"),
    project_id: Optional[str] = Query(None, description="Optional project identifier"),
    start_date: Optional[str] = Query(None, description="Optional ISO start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional ISO end date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="Aggregation granularity: daily, weekly, monthly"),
):
    """Retrieve temporal retirement activity aggregated across continuous calendar periods."""
    from .analytics import AnalyticsEngine, parse_date
    p_type = period.strip().lower()
    if p_type not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Must be 'daily', 'weekly', or 'monthly'.",
        )
    p_start = parse_date(start_date) if start_date else None
    if start_date and p_start is None:
        raise HTTPException(status_code=422, detail=f"Invalid start_date format: '{start_date}'. Must be YYYY-MM-DD.")
    p_end = parse_date(end_date) if end_date else None
    if end_date and p_end is None:
        raise HTTPException(status_code=422, detail=f"Invalid end_date format: '{end_date}'. Must be YYYY-MM-DD.")
    if p_start and p_end and p_start > p_end:
        raise HTTPException(status_code=422, detail=f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    resp = AnalyticsEngine.analyze_temporal_activity(
        registry=registry,
        project_id=project_id,
        start_date=p_start,
        end_date=p_end,
        period_type=p_type,
    )
    return resp.to_dict()


@app.get("/api/analytics/temporal/trends")
def analytics_temporal_trends(
    registry: Optional[str] = Query(None, description="Optional registry code ('VCS', 'GS')"),
    project_id: Optional[str] = Query(None, description="Optional project identifier"),
    start_date: Optional[str] = Query(None, description="Optional ISO start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional ISO end date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="Aggregation granularity: daily, weekly, monthly"),
    window: int = Query(4, ge=1, description="Rolling window size in prior periods"),
    threshold_pct: float = Query(5.0, ge=0.0, description="Percentage threshold for direction classification"),
):
    """Retrieve rolling average trends and directional velocity classifications."""
    from .analytics import AnalyticsEngine, parse_date
    p_type = period.strip().lower()
    if p_type not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Must be 'daily', 'weekly', or 'monthly'.",
        )
    p_start = parse_date(start_date) if start_date else None
    if start_date and p_start is None:
        raise HTTPException(status_code=422, detail=f"Invalid start_date format: '{start_date}'. Must be YYYY-MM-DD.")
    p_end = parse_date(end_date) if end_date else None
    if end_date and p_end is None:
        raise HTTPException(status_code=422, detail=f"Invalid end_date format: '{end_date}'. Must be YYYY-MM-DD.")
    if p_start and p_end and p_start > p_end:
        raise HTTPException(status_code=422, detail=f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    resp = AnalyticsEngine.analyze_temporal_trends(
        registry=registry,
        project_id=project_id,
        start_date=p_start,
        end_date=p_end,
        period_type=p_type,
        window=window,
        threshold_pct=threshold_pct,
    )
    return resp.to_dict()


@app.get("/api/analytics/temporal/bursts")
def analytics_temporal_bursts(
    registry: Optional[str] = Query(None, description="Optional registry code ('VCS', 'GS')"),
    project_id: Optional[str] = Query(None, description="Optional project identifier"),
    start_date: Optional[str] = Query(None, description="Optional ISO start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional ISO end date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="Aggregation granularity: daily, weekly, monthly"),
    baseline_window: int = Query(12, ge=1, description="Historical baseline window size in periods"),
    sensitivity: float = Query(3.0, ge=0.5, description="MAD multiplier threshold k"),
    min_history: int = Query(5, ge=1, description="Minimum historical baseline periods"),
    min_tonne_threshold: float = Query(100.0, ge=0.0, description="Minimum volume threshold for burst flag"),
    min_record_threshold: int = Query(2, ge=1, description="Minimum record threshold for burst flag"),
):
    """Detect anomalous transaction volume and frequency bursts using robust leave-one-out baseline."""
    from .analytics import AnalyticsEngine, parse_date
    p_type = period.strip().lower()
    if p_type not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Must be 'daily', 'weekly', or 'monthly'.",
        )
    p_start = parse_date(start_date) if start_date else None
    if start_date and p_start is None:
        raise HTTPException(status_code=422, detail=f"Invalid start_date format: '{start_date}'. Must be YYYY-MM-DD.")
    p_end = parse_date(end_date) if end_date else None
    if end_date and p_end is None:
        raise HTTPException(status_code=422, detail=f"Invalid end_date format: '{end_date}'. Must be YYYY-MM-DD.")
    if p_start and p_end and p_start > p_end:
        raise HTTPException(status_code=422, detail=f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    resp = AnalyticsEngine.analyze_temporal_bursts(
        registry=registry,
        project_id=project_id,
        start_date=p_start,
        end_date=p_end,
        period_type=p_type,
        baseline_window=baseline_window,
        sensitivity=sensitivity,
        min_history=min_history,
        min_tonne_threshold=min_tonne_threshold,
        min_record_threshold=min_record_threshold,
    )
    return resp.to_dict()


@app.get("/api/analytics/temporal/gaps")
def analytics_temporal_gaps(
    registry: Optional[str] = Query(None, description="Optional registry code ('VCS', 'GS')"),
    project_id: Optional[str] = Query(None, description="Optional project identifier"),
    start_date: Optional[str] = Query(None, description="Optional ISO start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional ISO end date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="Aggregation granularity: daily, weekly, monthly"),
):
    """Analyze temporal inactivity intervals and coverage gaps across calendar periods."""
    from .analytics import AnalyticsEngine, parse_date
    p_type = period.strip().lower()
    if p_type not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Must be 'daily', 'weekly', or 'monthly'.",
        )
    p_start = parse_date(start_date) if start_date else None
    if start_date and p_start is None:
        raise HTTPException(status_code=422, detail=f"Invalid start_date format: '{start_date}'. Must be YYYY-MM-DD.")
    p_end = parse_date(end_date) if end_date else None
    if end_date and p_end is None:
        raise HTTPException(status_code=422, detail=f"Invalid end_date format: '{end_date}'. Must be YYYY-MM-DD.")
    if p_start and p_end and p_start > p_end:
        raise HTTPException(status_code=422, detail=f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    resp = AnalyticsEngine.analyze_temporal_gaps(
        registry=registry,
        project_id=project_id,
        start_date=p_start,
        end_date=p_end,
        period_type=p_type,
    )
    return resp.to_dict()


# ------------------------------------------------------- cross-registry analytics (Phase 2C Stage 3)

@app.post("/api/cross-registry/projects/compare")
def cross_registry_projects_compare(body: CrossRegistryProjectCompareRequest):
    """Compare two projects across or within registries and produce explainable correlation evidence."""
    from .analytics import AnalyticsEngine
    cmp = AnalyticsEngine.compare_projects(body.project_a, body.project_b)
    return cmp.to_dict()


@app.get("/api/cross-registry/projects/correlations")
def cross_registry_projects_correlations(
    min_similarity: float = Query(0.50, ge=0.0, le=1.0, description="Minimum name similarity threshold"),
    category: Optional[str] = Query(None, description="Optional category filter (e.g. 'STRONG_ATTRIBUTE_CORRELATION')"),
    country: Optional[str] = Query(None, description="Optional country name or ISO alpha-2 code filter"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of candidate correlations to return"),
):
    """Generate and rank candidate project correlations across Verra VCS and Gold Standard."""
    from .analytics import AnalyticsEngine, ProjectCorrelationCategory
    cat_val = category.strip().upper() if category else None
    if cat_val and cat_val not in [c.value for c in ProjectCorrelationCategory]:
        valid_cats = ", ".join(c.value for c in ProjectCorrelationCategory)
        raise HTTPException(status_code=422, detail=f"Invalid category '{category}'. Valid options: {valid_cats}")
    resp = AnalyticsEngine.correlate_cross_registry_projects(
        min_similarity=min_similarity,
        category_filter=cat_val,
        country_filter=country,
        limit=limit,
    )
    return resp.to_dict()


@app.post("/api/cross-registry/entities/compare")
def cross_registry_entities_compare(body: CrossRegistryEntityCompareRequest):
    """Compare two entity names across registries using the Phase 2A resolution engine."""
    from .analytics import AnalyticsEngine
    res = AnalyticsEngine.compare_entities(
        entity_a=body.entity_a,
        entity_b=body.entity_b,
        registry_a=body.registry_a,
        registry_b=body.registry_b,
    )
    return res.to_dict()


@app.get("/api/cross-registry/retirements/summary")
def cross_registry_retirements_summary():
    """Retrieve comparative retirement summary statistics across voluntary registries."""
    from .analytics import AnalyticsEngine
    resp = AnalyticsEngine.get_cross_registry_retirement_summary()
    return resp.to_dict()


@app.get("/api/cross-registry/retirements/trends")
def cross_registry_retirements_trends(
    period: str = Query("yearly", description="Trend period granularity: 'yearly' or 'monthly'"),
):
    """Retrieve comparative retirement pacing time series across registries."""
    from .analytics import AnalyticsEngine
    p_clean = period.strip().lower()
    if p_clean not in ("yearly", "monthly"):
        raise HTTPException(status_code=422, detail=f"Invalid period '{period}'. Must be 'yearly' or 'monthly'.")
    resp = AnalyticsEngine.get_cross_registry_retirement_trends(period_type=p_clean)
    return resp.to_dict()


# ------------------------------------------------------- unified risk assessment (Phase 2C Stage 4)


@app.post("/api/analytics/assessment")
def analytics_risk_assessment(body: RiskAssessmentRequest):
    """Execute unified, explainable risk assessment aggregating multi-stage intelligence."""
    from .analytics import AnalyticsEngine
    try:
        res = AnalyticsEngine.assess_risk(body)
        return res.to_dict()
    except ValueError as e:
        msg = str(e).lower()
        if "not found" in msg or "no retirement records" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/analytics/assessment/rules")
def analytics_risk_assessment_rules():
    """Retrieve catalog of versioned deterministic risk assessment rules."""
    from .analytics import AnalyticsEngine
    catalog = AnalyticsEngine.get_assessment_rules_catalog()
    return catalog.model_dump()





# ------------------------------------------------------- built frontend (optional)

if settings.static_dir and (settings.static_dir / "index.html").exists():
    from fastapi.staticfiles import StaticFiles

    _static = settings.static_dir
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        from fastapi.responses import FileResponse

        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        candidate = (_static / full_path).resolve()
        if full_path and candidate.is_file() and _static.resolve() in candidate.parents:
            return FileResponse(candidate)  # e.g. favicon.svg
        return FileResponse(_static / "index.html")  # client-side routes

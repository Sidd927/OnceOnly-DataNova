"""Claim lifecycle orchestration: ingest → extract → check → anchor → verify → challenge."""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass

from eth_utils import keccak

from . import db
from .chain import try_ledger
from .config import settings
from .extraction import Extraction, block_source, document_text, extract
from .reference import Reference
from .rules import BLOCKING, REVIEW, ActiveRange, Finding, evaluate, norm_name, verdict


class ServiceError(Exception):
    def __init__(self, status: int, message: str, detail: dict | None = None):
        super().__init__(message)
        self.status, self.message, self.detail = status, message, detail or {}


@dataclass
class Upload:
    filename: str
    data: bytes
    mime: str | None = None


ALLOWED_EXT = (".pdf", ".txt", ".md")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def claimant_commitment(name: str, salt: str) -> str:
    return "0x" + keccak(text=f"{salt}|{norm_name(name)}").hex()


def store_evidence(u: Upload) -> str:
    digest = sha256_hex(u.data)
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)
    p = settings.evidence_dir / digest  # content-addressed; never served directly
    if not p.exists():
        p.write_bytes(u.data)
    return digest


def evidence_root(digests: list[str]) -> str:
    """Single commitment over all evidence documents (sorted sha256 digests)."""
    if len(digests) == 1:
        return "0x" + digests[0]
    return "0x" + hashlib.sha256("".join(sorted(digests)).encode()).hexdigest()


def active_ranges(con, exclude_claim: int | None = None) -> list[ActiveRange]:
    rows = con.execute(
        f"""SELECT c.id, c.ref, c.claimant, c.status, c.chain_claim_id, c.tx_hash, b.registry, b.batch_id, b.unit_start, b.unit_end
            FROM claim_blocks b JOIN claims c ON c.id=b.claim_id
            WHERE c.status IN ({','.join('?' * len(db.LOCKING))}) AND c.id != ?""",
        (*db.LOCKING, exclude_claim or -1),
    ).fetchall()
    return [ActiveRange(r["id"], r["ref"], r["claimant"], r["status"], r["registry"], r["batch_id"], r["unit_start"], r["unit_end"], r["chain_claim_id"], r["tx_hash"]) for r in rows]


def claimed_totals(con) -> dict[tuple, int]:
    rows = con.execute(
        f"""SELECT b.registry, b.project_id, b.vintage, SUM(b.unit_end-b.unit_start+1) FROM claim_blocks b JOIN claims c ON c.id=b.claim_id
            WHERE c.status IN ({','.join('?' * len(db.LOCKING))}) GROUP BY 1,2,3""",
        db.LOCKING,
    ).fetchall()
    return {(r[0], r[1], r[2]): r[3] for r in rows}


def reused_evidence(con, digests: list[str], claim_id: int | None) -> list[dict]:
    if not digests:
        return []
    rows = con.execute(
        f"""SELECT e.filename, e.sha256, c.ref AS claim_ref, c.claimant, c.id AS claim_id FROM evidence e JOIN claims c ON c.id=e.claim_id
            WHERE e.sha256 IN ({','.join('?' * len(digests))}) AND c.id != ? AND c.status NOT IN ('withdrawn','revoked')""",
        (*digests, claim_id or -1),
    ).fetchall()
    return [dict(r) for r in rows]


def report_hash(ref: str, blocks: list[dict], findings: list[Finding]) -> str:
    canonical = json.dumps(
        {"ref": ref, "blocks": [{k: b[k] for k in ("registry", "batch_id", "unit_start", "unit_end")} for b in blocks],
         "findings": sorted([f.rule_id, f.severity, f.block_index if f.block_index is not None else -1] for f in findings)},
        sort_keys=True, separators=(",", ":"),
    )
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


# ------------------------------------------------------------------- create/check

def create_claim(con, ref_index: Reference | None, *, claimant: str, claim_date: str | None, period: str | None, statement: str | None,
                 pasted_text: str | None, uploads: list[Upload], synthetic: bool = True, use_llm: bool | None = None) -> int:
    claimant = (claimant or "").strip()
    if not claimant:
        raise ServiceError(422, "Claimant is required")
    if not uploads and not (pasted_text or "").strip():
        raise ServiceError(422, "Provide at least one evidence document or pasted certificate text")
    for u in uploads:
        if not u.filename.lower().endswith(ALLOWED_EXT):
            raise ServiceError(415, f"Unsupported file type: {u.filename}. Allowed: {', '.join(ALLOWED_EXT)}")
        if len(u.data) > settings.max_upload_bytes:
            raise ServiceError(413, f"{u.filename} exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit")
    if pasted_text and pasted_text.strip():
        uploads = [*uploads, Upload("pasted-text.txt", pasted_text.encode(), "text/plain")]

    texts, ev_rows = [], []
    for u in uploads:
        try:
            t = document_text(u.filename, u.data)
        except Exception as e:
            raise ServiceError(422, f"Could not read {u.filename}: {type(e).__name__}") from e
        digest = store_evidence(u)
        texts.append(t)
        ev_rows.append((u.filename, digest, len(u.data), u.mime, t[:4000]))

    full_text = "\n\n".join(texts)
    ex = extract(full_text, use_llm=use_llm)
    salt = secrets.token_hex(16)
    with db.tx(con):
        ref = db.next_ref(con)
        ts = db.now()
        cur = con.execute(
            """INSERT INTO claims (ref, claimant, claimant_salt, claimant_commitment, claim_date, period, statement, synthetic, status,
               evidence_hash, llm_status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref, claimant, salt, claimant_commitment(claimant, salt), claim_date, period, statement, int(synthetic), "checked",
             evidence_root([r[1] for r in ev_rows]), ex.llm_status, ts, ts),
        )
        claim_id = cur.lastrowid
        con.executemany("INSERT INTO evidence (claim_id, filename, sha256, size, mime, text_excerpt) VALUES (?,?,?,?,?,?)", [(claim_id, *r) for r in ev_rows])
        for i, b in enumerate(ex.blocks):
            con.execute(
                "INSERT INTO claim_blocks (claim_id, idx, registry, batch_id, unit_start, unit_end, serial, project_id, vintage, country, source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (claim_id, i, b.registry, b.batch_id, b.unit_start, b.unit_end, b.serial, b.project_id, b.vintage, b.country, block_source(ex, b)),
            )
        con.execute("UPDATE claims SET extraction_json=? WHERE id=?", (json.dumps(_extraction_summary(ex)), claim_id))
        db.add_event(con, claim_id, "submitted", {"documents": [{"filename": r[0], "sha256": r[1], "size": r[2]} for r in ev_rows], "synthetic": synthetic})
        db.add_event(con, claim_id, "extracted", {"blocks": len(ex.blocks), "llm_status": ex.llm_status, "unserialized": len(ex.unserialized)})
    run_checks(con, ref_index, claim_id, ex=ex)
    return claim_id


def _extraction_summary(ex: Extraction) -> dict:
    return {
        "stated_quantity": ex.stated_quantity,
        "beneficiary": ex.beneficiary,
        "retirement_date": ex.retirement_date,
        "unserialized": [u.__dict__ for u in ex.unserialized],
        "llm_status": ex.llm_status,
        "llm_used": ex.llm_used,
        "llm_rejected": ex.llm_rejected,
        "llm_fields": ex.llm_fields,
    }


def _rebuild_extraction(con, claim_id: int) -> Extraction:
    """Reconstruct the extraction from stored blocks (re-checks never re-call the LLM)."""
    from .extraction import UnserializedAssertion
    from .serials import SerialBlock

    c = con.execute("SELECT extraction_json FROM claims WHERE id=?", (claim_id,)).fetchone()
    summ = json.loads(c["extraction_json"] or "{}")
    rows = con.execute("SELECT * FROM claim_blocks WHERE claim_id=? ORDER BY idx", (claim_id,)).fetchall()
    blocks = [SerialBlock(r["registry"], r["batch_id"], r["unit_start"], r["unit_end"], r["serial"], r["project_id"], r["vintage"], r["country"]) for r in rows]
    ex = Extraction(blocks=blocks, stated_quantity=summ.get("stated_quantity"), beneficiary=summ.get("beneficiary"), retirement_date=summ.get("retirement_date"),
                    unserialized=[UnserializedAssertion(**u) for u in summ.get("unserialized", [])], llm_status=summ.get("llm_status", "not-configured"),
                    llm_used=summ.get("llm_used", False), llm_rejected=summ.get("llm_rejected", []))
    ex.parser_keys = {(r["registry"], r["batch_id"], r["unit_start"], r["unit_end"]) for r in rows if r["source"] in ("parser", "both")}
    ex.llm_blocks = [b for b, r in zip(blocks, rows) if r["source"] in ("llm", "both")]
    return ex


def run_checks(con, ref_index: Reference | None, claim_id: int, ex: Extraction | None = None) -> list[Finding]:
    claim = con.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if claim is None:
        raise ServiceError(404, "Claim not found")
    ex = ex or _rebuild_extraction(con, claim_id)
    digests = [r["sha256"] for r in con.execute("SELECT sha256 FROM evidence WHERE claim_id=?", (claim_id,))]
    findings = evaluate(
        claimant=claim["claimant"], claim_date=claim["claim_date"], ex=ex, ref=ref_index,
        active=active_ranges(con, exclude_claim=claim_id), reused_evidence=reused_evidence(con, digests, claim_id),
        claimed_totals=claimed_totals(con),
    )
    v = verdict(findings)
    blocks = [dict(r) for r in con.execute("SELECT * FROM claim_blocks WHERE claim_id=? ORDER BY idx", (claim_id,))]
    rh = report_hash(claim["ref"], blocks, findings)
    with db.tx(con):
        con.execute("DELETE FROM findings WHERE claim_id=?", (claim_id,))
        con.executemany(
            "INSERT INTO findings (claim_id, rule_id, severity, title, explanation, uncertainty, next_action, evidence_json, block_index) VALUES (?,?,?,?,?,?,?,?,?)",
            [(claim_id, f.rule_id, f.severity, f.title, f.explanation, f.uncertainty, f.next_action, json.dumps(f.evidence), f.block_index) for f in findings],
        )
        new_status = claim["status"]
        if claim["status"] in ("checked", "blocked"):
            new_status = "blocked" if v == "blocked" else "checked"
        con.execute("UPDATE claims SET verdict=?, report_hash=?, status=?, updated_at=? WHERE id=?", (v, rh, new_status, db.now(), claim_id))
        if rh != claim["report_hash"]:  # log only when the outcome changed
            db.add_event(con, claim_id, "checked", {"verdict": v, "counts": _counts(findings), "report_hash": rh})
    return findings


def _counts(findings) -> dict:
    out: dict[str, int] = {}
    for f in findings:
        sev = f.severity if isinstance(f, Finding) else f["severity"]
        out[sev] = out.get(sev, 0) + 1
    return out


# ------------------------------------------------------------------------- anchor

def anchor(con, ref_index: Reference | None, claim_id: int, acknowledge_review: bool = False, force: bool = False) -> dict:
    claim = con.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if claim is None:
        raise ServiceError(404, "Claim not found")
    if claim["status"] in ("anchored", "challenged"):
        raise ServiceError(409, f"Claim is already {claim['status']} on the ledger")
    if claim["status"] in ("revoked", "withdrawn"):
        raise ServiceError(409, f"Claim was {claim['status']}; submit a new claim")
    findings = run_checks(con, ref_index, claim_id)  # always re-check against the latest ledger state
    blocks = [dict(r) for r in con.execute("SELECT * FROM claim_blocks WHERE claim_id=? ORDER BY idx", (claim_id,))]
    if not blocks:
        raise ServiceError(422, "Nothing to anchor: no serial blocks were identified (EVD-001)")
    blocking = [f for f in findings if f.severity == BLOCKING]
    review = [f for f in findings if f.severity == REVIEW]
    if blocking and not force:
        raise ServiceError(409, "Blocking findings prevent anchoring", {"blocking": [f.to_dict() for f in blocking]})
    if review and not acknowledge_review and not force:
        raise ServiceError(409, "Review findings must be acknowledged before anchoring", {"review": [f.rule_id for f in review]})

    ledger, err = try_ledger()
    if ledger is None:
        raise ServiceError(503, f"Ledger unavailable: {err}")
    claim = con.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    result = ledger.register(claim["ref"], blocks, claim["claimant_commitment"], claim["evidence_hash"], claim["report_hash"], submit_on_revert=force)
    with db.tx(con):
        if result["ok"]:
            con.execute(
                "UPDATE claims SET status='anchored', chain_claim_id=?, tx_hash=?, block_number=?, chain_id=?, contract_address=?, updated_at=? WHERE id=?",
                (result["claim_id"], result["tx_hash"], result["block_number"], ledger.chain_id, ledger.address, db.now(), claim_id),
            )
            db.add_event(con, claim_id, "anchored", {"chain_claim_id": result["claim_id"], "gas_used": result["gas_used"], "acknowledged_review": [f.rule_id for f in review]},
                         result["tx_hash"], result["block_number"])
        else:
            db.add_event(con, claim_id, "chain_rejected", {"revert": result["revert"], "submitted": result.get("submitted"), "tx_status": result.get("tx_status")},
                         result.get("tx_hash"), result.get("block_number"))
    if not result["ok"]:
        raise ServiceError(409, f"The ClaimLedger contract rejected the claim: {result['revert']['error']}", {"chain": result})
    return result


# --------------------------------------------------------------- lifecycle on chain

def _anchored(con, claim_id: int):
    c = con.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if c is None:
        raise ServiceError(404, "Claim not found")
    if c["chain_claim_id"] is None:
        raise ServiceError(409, "Claim is not anchored on the ledger")
    ledger, err = try_ledger()
    if ledger is None:
        raise ServiceError(503, f"Ledger unavailable: {err}")
    return c, ledger


def challenge(con, claim_id: int, reason: str) -> dict:
    if not reason.strip():
        raise ServiceError(422, "A challenge needs a reason")
    c, ledger = _anchored(con, claim_id)
    res = ledger.challenge(c["chain_claim_id"], reason)
    if not res["ok"]:
        raise ServiceError(409, f"Contract rejected the challenge: {res['revert']['error']}", {"chain": res})
    with db.tx(con):
        con.execute("UPDATE claims SET status='challenged', updated_at=? WHERE id=?", (db.now(), claim_id))
        db.add_event(con, claim_id, "challenged", {"reason": reason, "reason_hash": "0x" + keccak(text=reason).hex(), "challenger": res["challenger"]}, res["tx_hash"], res["block_number"])
    return res


def resolve(con, claim_id: int, upheld: bool, note: str) -> dict:
    c, ledger = _anchored(con, claim_id)
    res = ledger.resolve(c["chain_claim_id"], upheld, note or ("upheld" if upheld else "dismissed"))
    if not res["ok"]:
        raise ServiceError(409, f"Contract rejected the resolution: {res['revert']['error']}", {"chain": res})
    new = "revoked" if upheld else "anchored"
    with db.tx(con):
        con.execute("UPDATE claims SET status=?, updated_at=? WHERE id=?", (new, db.now(), claim_id))
        db.add_event(con, claim_id, "challenge_upheld" if upheld else "challenge_dismissed", {"note": note}, res["tx_hash"], res["block_number"])
    return res


def withdraw(con, claim_id: int) -> dict:
    c, ledger = _anchored(con, claim_id)
    res = ledger.withdraw(c["chain_claim_id"])
    if not res["ok"]:
        raise ServiceError(409, f"Contract rejected the withdrawal: {res['revert']['error']}", {"chain": res})
    with db.tx(con):
        con.execute("UPDATE claims SET status='withdrawn', updated_at=? WHERE id=?", (db.now(), claim_id))
        db.add_event(con, claim_id, "withdrawn", {}, res["tx_hash"], res["block_number"])
    return res


# ------------------------------------------------------------------------- verify

COMMITMENT_SCHEME = (
    "One document: evidence_hash = 0x || SHA-256(document). Several documents: evidence_hash = "
    "0x || SHA-256(concatenation of the documents' lowercase hex SHA-256 digests, sorted)."
)
CHECK_PASS, CHECK_FAIL, CHECK_WARN, CHECK_SKIP = "PASS", "FAIL", "WARN", "NOT_PERFORMED"


def assess_document(digest: str, onchain_root: str, committed_digests: list[str] | None) -> dict:
    """Classify an uploaded document against the on-chain evidence commitment.

    The on-chain record holds one 32-byte evidence commitment. A document is proven to be covered by it
    only when (a) its digest *is* the commitment (single-document claims) or (b) it belongs to a digest
    list that recomputes, under COMMITMENT_SCHEME, to exactly the on-chain commitment. A digest that is
    merely listed in the application database is an off-chain record match, never an on-chain proof.
    """
    leaves = sorted(committed_digests or [])
    recomputed = evidence_root(leaves) if leaves else None
    listed = digest in leaves
    if ("0x" + digest) == onchain_root:
        status = "ONCHAIN_ROOT_MATCH"
        explanation = "The document's SHA-256 equals the evidence commitment stored on chain."
    elif listed and len(leaves) > 1 and recomputed == onchain_root:
        status = "ONCHAIN_MEMBERSHIP_PROVEN"
        explanation = (f"The document's SHA-256 is one of {len(leaves)} digests whose sorted concatenation hashes to the "
                       "on-chain evidence commitment. Anyone can recompute this from the digests listed below.")
    elif listed:
        status = "OFFCHAIN_RECORD_ONLY"
        explanation = ("The application database lists this document for the claim, but the database's digest list does not "
                       "recompute to the on-chain commitment. This is not an on-chain proof; treat the record as inconsistent.")
    else:
        status = "NO_MATCH"
        explanation = "The document differs from every committed evidence document (a one-byte change alters the SHA-256)."
    return {
        "sha256": digest,
        "status": status,
        "matches_onchain_commitment": status in ("ONCHAIN_ROOT_MATCH", "ONCHAIN_MEMBERSHIP_PROVEN"),
        "offchain_record_match": listed,
        "explanation": explanation,
        "proof": {
            "scheme": COMMITMENT_SCHEME,
            "leaves": leaves,
            "recomputed_root": recomputed,
            "onchain_root": onchain_root,
            "recomputed_matches_onchain": recomputed == onchain_root if recomputed else None,
        },
        "does_not_prove": "A matching fingerprint shows the bytes are unchanged since registration. It does not show the document's statements are true.",
    }


def _check(cid: str, label: str, status: str, detail: str) -> dict:
    return {"id": cid, "label": label, "status": status, "detail": detail}


def verify(con, ref: str | None, chain_claim_id: int | None, upload: Upload | None, salt: str | None = None, claimant: str | None = None) -> dict:
    from .chain import namespace, network_kind, try_ledger_detailed

    ledger, code, err = try_ledger_detailed()
    if ledger is None:
        raise ServiceError(503, f"Ledger unavailable: {err}", {"code": code})
    if chain_claim_id is None:
        if not ref:
            raise ServiceError(422, "Provide a claim reference (e.g. OO-2026-0001) or an on-chain claim id")
        chain_claim_id = ledger.claim_id_by_ref(ref.strip())
        if chain_claim_id == 0:
            return {"found": False, "message": f"No claim with reference {ref} exists on the ledger at {ledger.address}.", "chain": ledger.info()}
    try:
        onchain = ledger.get_claim(int(chain_claim_id))
    except Exception:
        return {"found": False, "message": f"Claim id {chain_claim_id} does not exist on the ledger.", "chain": ledger.info()}

    info = ledger.info()
    code_check = ledger.code_verification()
    checks = [
        _check("NETWORK", "Network identity", CHECK_PASS if info["chain_id"] == info["deployment_chain_id"] else CHECK_FAIL,
               f"Chain ID {info['chain_id']} ({'local Hardhat development chain, not a public network' if network_kind(info['chain_id']) == 'LOCAL_DEVELOPMENT_CHAIN' else 'non-local chain'}); "
               f"matches the deployment record's chain ID {info['deployment_chain_id']}."),
        _check("DEPLOYMENT_CODE", "Contract code", {"CODE_MATCHES_ARTIFACT": CHECK_PASS, "CODE_DIFFERS_FROM_ARTIFACT": CHECK_FAIL}.get(code_check["status"], CHECK_SKIP),
               {"CODE_MATCHES_ARTIFACT": f"Runtime bytecode at {info['address']} is identical to the compiled ClaimLedger artifact.",
                "CODE_DIFFERS_FROM_ARTIFACT": f"Runtime bytecode at {info['address']} differs from the compiled ClaimLedger artifact.",
                }.get(code_check["status"], "The compiled contract artifact is not available on this server, so the deployed code was not compared.")),
        _check("ONCHAIN_RECORD", "On-chain claim record", CHECK_PASS,
               f"Claim #{onchain['claim_id']} read from the contract: status '{onchain['status']}', {len(onchain['ranges'])} unit range(s)."),
    ]
    out = {"found": True, "chain": info, "code_verification": code_check, "onchain": onchain, "checks": checks,
           "commitment_scheme": COMMITMENT_SCHEME}

    local = con.execute("SELECT id, ref, claimant, claimant_salt, synthetic, tx_hash, block_number, evidence_hash FROM claims WHERE chain_claim_id=? AND contract_address=?",
                        (int(chain_claim_id), ledger.address)).fetchone()
    digests: list[str] | None = None
    if local:
        out["local"] = {"id": local["id"], "ref": local["ref"], "tx_hash": local["tx_hash"], "block_number": local["block_number"], "synthetic": bool(local["synthetic"])}
        digests = [r["sha256"] for r in con.execute("SELECT sha256 FROM evidence WHERE claim_id=?", (local["id"],))]
        out["evidence_documents"] = len(digests)
        blocks = con.execute("SELECT registry, batch_id, unit_start, unit_end FROM claim_blocks WHERE claim_id=?", (local["id"],)).fetchall()
        local_ranges = sorted(("0x" + namespace(b["registry"], b["batch_id"]).hex(), b["unit_start"], b["unit_end"]) for b in blocks)
        chain_ranges = sorted((r["namespace"], r["unit_start"], r["unit_end"]) for r in onchain["ranges"])
        checks.append(_check("RANGES_RECONCILE", "Unit ranges: database vs chain", CHECK_PASS if local_ranges == chain_ranges else CHECK_FAIL,
                             "The application's unit ranges for this claim equal the ranges stored on chain." if local_ranges == chain_ranges
                             else "The application's unit ranges differ from the ranges stored on chain; the chain is authoritative."))
        recomputed = evidence_root(digests) if digests else None
        checks.append(_check("EVIDENCE_COMMITMENT", "Evidence digests reproduce the on-chain commitment",
                             CHECK_PASS if recomputed == onchain["evidence_hash"] else CHECK_FAIL,
                             f"{len(digests)} document digest(s) recompute to the on-chain evidence commitment." if recomputed == onchain["evidence_hash"]
                             else "The stored document digests do not recompute to the on-chain evidence commitment."))
    else:
        checks.append(_check("RANGES_RECONCILE", "Unit ranges: database vs chain", CHECK_SKIP, "This server has no application record for the on-chain claim."))
        checks.append(_check("EVIDENCE_COMMITMENT", "Evidence digests reproduce the on-chain commitment", CHECK_SKIP,
                             "No document digest list is available on this server; only a single-document upload can be compared with the commitment."))

    if upload is not None:
        doc = assess_document(sha256_hex(upload.data), onchain["evidence_hash"], digests)
        doc["filename"] = upload.filename
        out["document"] = doc
        checks.append(_check("DOCUMENT", "Uploaded document", CHECK_PASS if doc["matches_onchain_commitment"] else CHECK_WARN if doc["status"] == "OFFCHAIN_RECORD_ONLY" else CHECK_FAIL,
                             f"{doc['status']}: {doc['explanation']}"))
    else:
        checks.append(_check("DOCUMENT", "Uploaded document", CHECK_SKIP, "No document was uploaded."))

    if claimant and salt:
        ok = claimant_commitment(claimant, salt) == onchain["claimant_commitment"]
        out["claimant_check"] = {"matches": ok}
        checks.append(_check("CLAIMANT", "Claimant commitment", CHECK_PASS if ok else CHECK_FAIL,
                             "keccak(salt | normalized name) equals the on-chain claimant commitment." if ok else "The name and salt do not reproduce the on-chain claimant commitment."))
    else:
        checks.append(_check("CLAIMANT", "Claimant commitment", CHECK_SKIP, "Requires the claimant name and the private salt held by the claimant."))

    out["limitations"] = [
        "The ledger runs on the network shown above. On a local development chain, these checks are reproducible only by someone with access to that chain.",
        "The registrar (this server's operator) submitted the record; claimants did not sign it.",
        "Hash checks show documents are unchanged since registration, not that their contents are accurate.",
    ]
    return out

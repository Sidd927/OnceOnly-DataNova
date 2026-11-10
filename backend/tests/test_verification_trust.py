"""Verification trust boundary: on-chain proofs, off-chain lookups and network safety are kept separate."""
import hashlib
import json

import pytest

D1, D2, D3 = (hashlib.sha256(x).hexdigest() for x in (b"doc-one", b"doc-two", b"doc-three"))


def _root(digests):
    from app.service import evidence_root

    return evidence_root(digests)


# ----------------------------------------------------------------- pure commitment logic

def test_single_document_matches_onchain_root():
    from app.service import assess_document

    r = assess_document(D1, "0x" + D1, [D1])
    assert r["status"] == "ONCHAIN_ROOT_MATCH" and r["matches_onchain_commitment"]


def test_single_document_matches_without_any_offchain_record():
    from app.service import assess_document

    r = assess_document(D1, "0x" + D1, None)
    assert r["status"] == "ONCHAIN_ROOT_MATCH" and r["offchain_record_match"] is False


def test_multi_document_membership_proven_when_leaves_recompute_root():
    from app.service import assess_document

    r = assess_document(D2, _root([D1, D2]), [D2, D1])
    assert r["status"] == "ONCHAIN_MEMBERSHIP_PROVEN" and r["matches_onchain_commitment"]
    assert r["proof"]["leaves"] == sorted([D1, D2]) and r["proof"]["recomputed_matches_onchain"] is True


def test_offchain_record_alone_never_counts_as_onchain_match():
    """Regression: a digest listed in SQLite used to set matches_onchain_commitment=True on its own."""
    from app.service import assess_document

    onchain = _root([D1, D3])  # chain committed a different document set
    r = assess_document(D2, onchain, [D1, D2])
    assert r["status"] == "OFFCHAIN_RECORD_ONLY"
    assert r["offchain_record_match"] is True
    assert r["matches_onchain_commitment"] is False
    assert r["proof"]["recomputed_matches_onchain"] is False


def test_unrelated_document_is_no_match():
    from app.service import assess_document

    r = assess_document(D3, _root([D1, D2]), [D1, D2])
    assert r["status"] == "NO_MATCH" and not r["matches_onchain_commitment"] and not r["offchain_record_match"]


def test_root_mismatch_for_single_document():
    from app.service import assess_document

    r = assess_document(D1, "0x" + D2, [D1])
    assert r["status"] == "OFFCHAIN_RECORD_ONLY" and not r["matches_onchain_commitment"]


# ----------------------------------------------------------------- network safety

def _dev_key(i=0):
    from eth_account import Account

    from app.chain import HARDHAT_MNEMONIC

    Account.enable_unaudited_hdwallet_features()
    return Account.from_mnemonic(HARDHAT_MNEMONIC, account_path=f"m/44'/60'/0'/0/{i}")


def test_dev_keys_allowed_only_on_local_chain():
    from app.chain import ChainUnavailable, assert_signers_allowed

    addr = _dev_key().address
    assert_signers_allowed(31337, [addr])
    with pytest.raises(ChainUnavailable) as e:
        assert_signers_allowed(11155111, [addr])
    assert e.value.code == "DEV_KEY_ON_NON_LOCAL_CHAIN"
    assert_signers_allowed(11155111, ["0x000000000000000000000000000000000000dEaD"])


def test_network_kind():
    from app.chain import network_kind

    assert network_kind(31337) == "LOCAL_DEVELOPMENT_CHAIN"
    assert network_kind(1) == "NON_LOCAL_CHAIN"


def test_missing_deployment_metadata_is_coded(tmp_env, monkeypatch):
    monkeypatch.setenv("CHAIN_DEPLOYMENT", str(tmp_env / "missing.json"))
    from app.chain import try_ledger_detailed

    ledger, code, msg = try_ledger_detailed()
    assert ledger is None and code == "DEPLOYMENT_MISSING" and "make deploy" in msg


class _Eth:
    def __init__(self, chain_id):
        self.chain_id = chain_id
        self.block_number = 1

    def get_code(self, _):
        return b"\x60\x80"

    def contract(self, **_):
        return object()


class _W3:
    chain_id = 31337

    def __init__(self, *_a, **_k):
        self.eth = _Eth(type(self).chain_id)

    @staticmethod
    def HTTPProvider(*_a, **_k):
        return None

    def is_connected(self):
        return True


def _stub_chain(tmp_env, monkeypatch, rpc_chain_id, deployment_chain_id, key):
    dep = tmp_env / "deployment.json"
    dep.write_text(json.dumps({"chainId": deployment_chain_id, "address": "0x5FbDB2315678afecb367f032d93F642f64180aa3", "abi": []}))
    monkeypatch.setenv("CHAIN_DEPLOYMENT", str(dep))
    monkeypatch.setenv("REGISTRAR_PRIVATE_KEY", key)
    import sys

    for m in [m for m in sys.modules if m.startswith("app")]:  # settings are read at import time
        del sys.modules[m]
    from app import chain

    assert chain.settings.deployment_file == dep

    _W3.chain_id = rpc_chain_id
    monkeypatch.setattr(chain, "Web3", _W3)
    return chain


def test_wrong_chain_id_is_network_mismatch(tmp_env, monkeypatch):
    chain = _stub_chain(tmp_env, monkeypatch, rpc_chain_id=1, deployment_chain_id=31337, key=_dev_key().key.hex())
    ledger, code, _ = chain.try_ledger_detailed()
    assert ledger is None and code == "NETWORK_MISMATCH"


def test_dev_key_refused_on_non_local_deployment(tmp_env, monkeypatch):
    chain = _stub_chain(tmp_env, monkeypatch, rpc_chain_id=11155111, deployment_chain_id=11155111, key=_dev_key(2).key.hex())
    ledger, code, _ = chain.try_ledger_detailed()
    assert ledger is None and code == "DEV_KEY_ON_NON_LOCAL_CHAIN"


# ----------------------------------------------------------------- verify() composition

class _Ledger:
    address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

    def __init__(self, evidence_hash, ranges):
        self.evidence_hash, self.ranges = evidence_hash, ranges

    def info(self):
        return {"chain_id": 31337, "deployment_chain_id": 31337, "address": self.address, "network_kind": "LOCAL_DEVELOPMENT_CHAIN"}

    def code_verification(self):
        return {"status": "ARTIFACT_UNAVAILABLE"}

    def claim_id_by_ref(self, ref):
        return 1

    def get_claim(self, cid):
        return {"claim_id": cid, "evidence_hash": self.evidence_hash, "claimant_commitment": "0x00", "status": "active", "ranges": self.ranges}


@pytest.fixture()
def two_doc_claim(tmp_env):
    from app import db, service
    from app.chain import namespace
    from app.reference import Reference

    con = db.connect()
    serial = "18453-896309560-896319559-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0"
    ups = [service.Upload("a.txt", f"Serial Number: {serial}\nQuantity: 10,000".encode(), "text/plain"),
           service.Upload("b.txt", b"Board approval letter (no serials)", "text/plain")]
    cid = service.create_claim(con, Reference.open(), claimant="Northwind Foods (SYNTHETIC)", claim_date=None, period="FY2025",
                               statement=None, pasted_text=None, uploads=ups)
    con.execute("UPDATE claims SET chain_claim_id=1, contract_address=? WHERE id=?", (_Ledger.address, cid))
    con.commit()
    row = con.execute("SELECT evidence_hash FROM claims WHERE id=?", (cid,)).fetchone()
    ranges = [{"namespace": "0x" + namespace(b["registry"], b["batch_id"]).hex(), "unit_start": b["unit_start"], "unit_end": b["unit_end"]}
              for b in con.execute("SELECT * FROM claim_blocks WHERE claim_id=?", (cid,))]
    return service, con, row["evidence_hash"], ranges, ups


def _run(monkeypatch, service, con, ledger, upload):
    from app import chain

    monkeypatch.setattr(chain, "try_ledger_detailed", lambda: (ledger, None, None))
    return service.verify(con, "OO-2026-0001", None, upload)


def test_verify_proves_membership_of_second_document(two_doc_claim, monkeypatch):
    service, con, root, ranges, ups = two_doc_claim
    out = _run(monkeypatch, service, con, _Ledger(root, ranges), ups[1])
    checks = {c["id"]: c["status"] for c in out["checks"]}
    assert out["document"]["status"] == "ONCHAIN_MEMBERSHIP_PROVEN"
    assert checks["DOCUMENT"] == "PASS" and checks["EVIDENCE_COMMITMENT"] == "PASS" and checks["RANGES_RECONCILE"] == "PASS"
    assert checks["DEPLOYMENT_CODE"] == "NOT_PERFORMED" and checks["CLAIMANT"] == "NOT_PERFORMED"


def test_verify_never_passes_on_offchain_record_when_chain_disagrees(two_doc_claim, monkeypatch):
    service, con, _root_ok, ranges, ups = two_doc_claim
    tampered_chain_root = "0x" + "ab" * 32
    out = _run(monkeypatch, service, con, _Ledger(tampered_chain_root, ranges), ups[0])
    checks = {c["id"]: c["status"] for c in out["checks"]}
    assert out["document"]["status"] == "OFFCHAIN_RECORD_ONLY"
    assert out["document"]["matches_onchain_commitment"] is False
    assert checks["DOCUMENT"] == "WARN" and checks["EVIDENCE_COMMITMENT"] == "FAIL"


def test_verify_flags_range_disagreement(two_doc_claim, monkeypatch):
    service, con, root, ranges, ups = two_doc_claim
    shifted = [{**r, "unit_end": r["unit_end"] + 1} for r in ranges]
    out = _run(monkeypatch, service, con, _Ledger(root, shifted), None)
    checks = {c["id"]: c["status"] for c in out["checks"]}
    assert checks["RANGES_RECONCILE"] == "FAIL" and checks["DOCUMENT"] == "NOT_PERFORMED"


def test_verify_without_ledger_reports_code(tmp_env, monkeypatch):
    from app import chain, db, service

    monkeypatch.setattr(chain, "try_ledger_detailed", lambda: (None, "NETWORK_MISMATCH", "RPC chainId 1 != deployment chainId 31337"))
    with pytest.raises(service.ServiceError) as e:
        service.verify(db.connect(), "OO-2026-0001", None, None)
    assert e.value.status == 503 and e.value.detail["code"] == "NETWORK_MISMATCH"

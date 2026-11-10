import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, CircleDashed, FileText, OctagonX, Upload, X } from "lucide-react";
import { api, fmt, type ClaimSummary, type VerifyCheckStatus, type VerifyDocument, type VerifyResult } from "../api";
import { Button, CopyValue, Disclosure, ErrorBox, Mono, OutcomeToken, PageHeader, SectionHeader } from "../components/primitives";
import type { Outcome } from "../lib/outcomes";
import demoTargets from "../lib/demoTargets.json";

const STATUS_OUTCOME: Record<string, { outcome: Outcome; label: string; text: string }> = {
  active: { outcome: "anchored", label: "Active on ClaimLedger", text: "Its unit ranges are locked to this claim; the contract refuses any other claim that overlaps them." },
  challenged: { outcome: "review", label: "Challenged", text: "Someone has contested the claim. Its units stay locked until a reviewer decides." },
  revoked: { outcome: "not-established", label: "Revoked", text: "A challenge was upheld. Its units are released." },
  withdrawn: { outcome: "not-established", label: "Withdrawn", text: "The registrar withdrew it. Its units are released." },
};

const CHECK_STYLE: Record<VerifyCheckStatus, { icon: typeof CheckCircle2; label: string; cls: string }> = {
  PASS: { icon: CheckCircle2, label: "Pass", cls: "text-lichen" },
  FAIL: { icon: OctagonX, label: "Fail", cls: "text-crimson" },
  WARN: { icon: AlertTriangle, label: "Warning", cls: "text-ochre" },
  NOT_PERFORMED: { icon: CircleDashed, label: "Not performed", cls: "text-muted" },
};

const DOC_STATUS: Record<VerifyDocument["status"], { outcome: Outcome; label: string; panel: string }> = {
  ONCHAIN_ROOT_MATCH: { outcome: "fingerprint-match", label: "Matches the on-chain commitment", panel: "border-glacier/40 bg-glacier-wash" },
  ONCHAIN_MEMBERSHIP_PROVEN: { outcome: "fingerprint-match", label: "Proven part of the on-chain commitment", panel: "border-glacier/40 bg-glacier-wash" },
  OFFCHAIN_RECORD_ONLY: { outcome: "review", label: "Off-chain record only, not an on-chain proof", panel: "border-ochre/50 bg-ochre-wash" },
  NO_MATCH: { outcome: "fingerprint-differs", label: "Not a committed document", panel: "border-crimson/50 bg-sheet" },
};

/** Seeded synthetic claims whose committed statement is served by /api/samples (single-document claims). */
const SAMPLE_FOR_REF: Record<string, string> = Object.fromEntries(demoTargets.claims.map((c) => [c.ref, c.seed_file]));

async function tamperedCopy(f: File): Promise<File> {
  const bytes = new Uint8Array(await f.arrayBuffer());
  bytes[bytes.length - 1] ^= 0x01; // flip one bit of the last byte
  return new File([bytes], `tampered-${f.name}`, { type: f.type });
}

export default function Verify() {
  const [params, setParams] = useSearchParams();
  const [ref, setRef] = useState(params.get("ref") ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [res, setRes] = useState<VerifyResult | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [fieldErr, setFieldErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [anchored, setAnchored] = useState<ClaimSummary[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);
  const refInput = useRef<HTMLInputElement>(null);

  useEffect(() => { api.claims().then((cs) => setAnchored(cs.filter((c) => c.chain_claim_id))).catch(() => {}); }, []);

  const verify = async (r = ref, f: File | null = file) => {
    setErr(null);
    setRes(null);
    if (!r.trim()) { setFieldErr("Enter a claim reference such as OO-2026-0001, or an on-chain claim number."); refInput.current?.focus(); return; }
    setFieldErr(null);
    const form = new FormData();
    if (/^\d+$/.test(r.trim())) form.set("chain_claim_id", r.trim()); else form.set("ref", r.trim());
    if (f) form.set("file", f);
    setBusy(true);
    try {
      setRes(await api.verify(form));
      setParams(r.trim() ? { ref: r.trim() } : {}, { replace: true });
    } catch (e) { setErr(e); } finally { setBusy(false); }
  };

  const runSample = async (tamper: boolean) => {
    const sample = SAMPLE_FOR_REF[ref.trim()];
    if (!sample) return;
    try {
      const original = await api.sampleFile(sample);
      const f = tamper ? await tamperedCopy(original) : original;
      setFile(f);
      await verify(ref, f);
    } catch (e) { setErr(e); }
  };

  const oc = res?.onchain;
  const st = oc ? STATUS_OUTCOME[oc.status] ?? { outcome: "note" as Outcome, label: oc.status, text: "" } : null;
  const sampleForRef = SAMPLE_FOR_REF[ref.trim()];

  return (
    <div>
      <PageHeader
        title="Public verification portal"
        lede="Read a claim's record from the ClaimLedger contract, reconcile it with this server's records, and check a document against the on-chain evidence commitment. Each check is reported separately: a database lookup never counts as an on-chain proof."
      />
      <div className="grid gap-10 lg:grid-cols-[24rem_minmax(0,1fr)]">
        <form onSubmit={(e) => { e.preventDefault(); verify(); }} className="space-y-5" noValidate>
          <label className="block space-y-1.5">
            <span className="text-sm font-semibold">Claim reference</span>
            <input ref={refInput} value={ref} onChange={(e) => { setRef(e.target.value); setFieldErr(null); }} placeholder="OO-2026-0001" aria-invalid={!!fieldErr} aria-describedby={fieldErr ? "ref-err" : "ref-hint"} className="w-full rounded-[7px] border border-rule-strong bg-sheet px-3 py-2.5 font-mono text-[15px]" />
            {fieldErr ? <span id="ref-err" className="text-sm text-crimson">{fieldErr}</span> : <span id="ref-hint" className="text-xs text-muted">A reference like OO-2026-0001, or the ledger claim number.</span>}
          </label>
          {anchored.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-xs text-muted">Claims on this ledger</div>
              <div className="flex flex-wrap gap-1.5">
                {anchored.map((c) => (
                  <button key={c.id} type="button" onClick={() => { setRef(c.ref); setFile(null); verify(c.ref, null); }} className="press rounded-full border border-rule-strong bg-sheet px-3 py-1 font-mono text-xs hover:border-ink">{c.ref}</button>
                ))}
              </div>
            </div>
          )}
          <div className="space-y-1.5">
            <span className="text-sm font-semibold">Document to check <span className="font-normal text-muted">(optional)</span></span>
            {file ? (
              <div className="flex items-center gap-3 rounded-panel border border-rule bg-sheet px-3 py-2.5 text-sm">
                <FileText size={16} className="shrink-0 text-ink-soft" aria-hidden /><span className="min-w-0 flex-1 truncate">{file.name}</span>
                <button type="button" onClick={() => setFile(null)} aria-label={`Remove ${file.name}`} className="press rounded p-1 text-muted hover:text-ink"><X size={15} aria-hidden /></button>
              </div>
            ) : (
              <Button type="button" variant="secondary" onClick={() => fileInput.current?.click()}><Upload size={15} aria-hidden /> Choose a document</Button>
            )}
            <input ref={fileInput} type="file" accept=".pdf,.txt,.md" className="sr-only" tabIndex={-1} aria-hidden onChange={(e) => { setFile(e.target.files?.[0] ?? null); e.target.value = ""; }} />
            <p className="text-xs text-muted">The file is hashed on the server and compared with the commitment. It is not stored.</p>
          </div>
          {sampleForRef && (
            <div className="space-y-2 rounded-panel border border-rule bg-fog-2/40 p-3">
              <div className="text-xs font-semibold text-ink">Try it with the seeded synthetic document</div>
              <p className="text-xs text-muted">{ref.trim()} was seeded from <Mono>{sampleForRef}</Mono>. Check that file, or a copy with a single bit flipped.</p>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="secondary" onClick={() => runSample(false)} disabled={busy}>Original document</Button>
                <Button type="button" variant="secondary" onClick={() => runSample(true)} disabled={busy}>Tampered copy</Button>
              </div>
            </div>
          )}
          <ErrorBox error={err} title="Verification failed" />
          <Button type="submit" busy={busy}>Verify</Button>
        </form>

        <div className="min-w-0" aria-live="polite">
          {!res && (
            <div className="rounded-sheet border border-dashed border-rule-strong bg-sheet p-6 text-sm text-ink-soft">
              <h2 className="mb-3 font-semibold text-ink">What this portal checks</h2>
              <ul className="space-y-2.5">
                <li className="flex gap-3"><OutcomeToken outcome="anchored" label="Ledger record" /><span>The claim's status, unit ranges and commitments, read from the contract, plus the network and deployed code they were read from.</span></li>
                <li className="flex gap-3"><OutcomeToken outcome="fingerprint-match" label="Document" /><span>Whether your copy is byte-identical to a document covered by the on-chain evidence commitment, with the arithmetic shown so you can redo it.</span></li>
                <li className="flex gap-3"><OutcomeToken outcome="not-established" label="Not covered" /><span>Whether a document's content is true, whether the credits are high quality, or who has the better claim to them.</span></li>
              </ul>
            </div>
          )}
          {res && !res.found && (
            <div className="seal-in space-y-2 rounded-sheet border border-rule bg-sheet p-6">
              <OutcomeToken outcome="not-established" label="Not on the ledger" />
              <p className="text-sm text-ink-soft">{res.message}</p>
            </div>
          )}
          {res?.found && oc && st && res.chain && (
            <article className="seal-in space-y-6 rounded-sheet border border-rule bg-sheet p-5 sm:p-6">
              <header className="space-y-2">
                <div className="text-xs text-muted">Ledger claim #{oc.claim_id}{res.local?.ref && <> · <Mono>{res.local.ref}</Mono></>}{res.local?.synthetic && " · synthetic demo claim"}</div>
                <OutcomeToken outcome={st.outcome} label={st.label} size="md" />
                <p className="text-[15px]">{st.text}</p>
                <p className="text-xs text-muted">Registered {new Date(oc.registered_at * 1000).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })} by registrar <Mono>{oc.registrar}</Mono></p>
              </header>

              {res.checks && (
                <section aria-labelledby="checks-h">
                  <SectionHeader id="checks-h" title="Verification checks" level={3} aside={`${res.checks.filter((c) => c.status === "PASS").length} of ${res.checks.length} passed`} />
                  <ul className="divide-y divide-rule rounded-panel border border-rule">
                    {res.checks.map((c) => {
                      const s = CHECK_STYLE[c.status];
                      const Icon = s.icon;
                      return (
                        <li key={c.id} className="grid gap-x-3 gap-y-0.5 px-3.5 py-2.5 text-sm sm:grid-cols-[9.5rem_minmax(0,1fr)]" data-check={c.id} data-status={c.status}>
                          <span className={`inline-flex items-center gap-1.5 font-semibold ${s.cls}`}><Icon size={15} aria-hidden />{s.label}</span>
                          <span><span className="font-semibold text-ink">{c.label}.</span> <span className="text-ink-soft">{c.detail}</span></span>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}

              {res.document && (
                <DocumentPanel doc={res.document} />
              )}

              <div>
                <h2 className="mb-2 text-sm font-semibold">Unit ranges held by this claim</h2>
                <ul className="divide-y divide-rule rounded-panel border border-rule">
                  {oc.ranges.map((r, i) => (
                    <li key={i} className="grid gap-1 px-3.5 py-2.5 text-sm sm:grid-cols-[1fr_auto] sm:items-center">
                      <span><span className="font-semibold">{fmt(r.unit_start)}–{fmt(r.unit_end)}</span> <span className="text-ink-soft">({fmt(r.unit_end - r.unit_start + 1)} units)</span></span>
                      <span className="text-xs text-muted">namespace <Mono>{r.namespace.slice(0, 10)}…</Mono></span>
                    </li>
                  ))}
                </ul>
                <p className="mt-1.5 text-xs text-muted">The namespace is keccak256 of “registry:batch”, e.g. keccak256("VCS:18453"). Unit numbers restart in every batch, so ranges are only compared within one namespace.</p>
              </div>

              <dl className="grid gap-4 text-sm sm:grid-cols-2">
                <div><dt className="text-xs text-muted">Evidence commitment</dt><dd><CopyValue value={oc.evidence_hash} label="evidence commitment" /></dd></div>
                <div><dt className="text-xs text-muted">Report hash</dt><dd><CopyValue value={oc.report_hash} label="report hash" /></dd></div>
                <div><dt className="text-xs text-muted">Claimant commitment</dt><dd><CopyValue value={oc.claimant_commitment} label="claimant commitment" /></dd></div>
                <div><dt className="text-xs text-muted">Registration transaction</dt><dd>{res.local?.tx_hash ? <CopyValue value={res.local.tx_hash} label="transaction hash" /> : <span className="text-muted">Not recorded on this server</span>}</dd></div>
              </dl>

              <section aria-labelledby="net-h" className="space-y-2">
                <SectionHeader id="net-h" title="Network and deployment" level={3} />
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div><dt className="text-xs text-muted">Network</dt><dd>Chain ID <Mono>{res.chain.chain_id}</Mono>: {res.chain.network_kind === "LOCAL_DEVELOPMENT_CHAIN" ? "local Hardhat development chain (not a public blockchain)" : "non-local chain"}</dd></div>
                  <div><dt className="text-xs text-muted">Contract</dt><dd><CopyValue value={res.chain.address} label="contract address" /></dd></div>
                  <div><dt className="text-xs text-muted">Deployed code</dt><dd>{res.code_verification?.status === "CODE_MATCHES_ARTIFACT" ? "Identical to the compiled ClaimLedger artifact" : res.code_verification?.status === "CODE_DIFFERS_FROM_ARTIFACT" ? "Differs from the compiled artifact" : "Not compared (artifact unavailable)"}</dd></div>
                  <div><dt className="text-xs text-muted">Runtime code keccak256</dt><dd><CopyValue value={res.code_verification?.runtime_code_keccak} label="runtime code hash" /></dd></div>
                </dl>
              </section>

              {res.limitations && (
                <div className="border-t border-rule pt-4 text-xs leading-relaxed text-muted">
                  <div className="mb-1 font-semibold text-ink-soft">What these checks do not establish</div>
                  <ul className="list-disc space-y-1 pl-4">{res.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
                </div>
              )}
            </article>
          )}
        </div>
      </div>
    </div>
  );
}

function DocumentPanel({ doc }: { doc: VerifyDocument }) {
  const s = DOC_STATUS[doc.status];
  return (
    <div key={doc.sha256} className={`seal-in space-y-2 rounded-panel border p-4 ${s.panel}`} data-document-status={doc.status}>
      <OutcomeToken outcome={s.outcome} label={s.label} size="md" />
      <p className="text-sm">{doc.explanation}</p>
      <div className="text-xs text-ink-soft">{doc.filename}</div>
      <CopyValue value={doc.sha256} label="document SHA-256" />
      <p className="text-xs text-muted">{doc.does_not_prove}</p>
      <Disclosure summary="Recompute this yourself">
        <div className="space-y-2 text-xs">
          <p className="text-ink-soft">{doc.proof.scheme}</p>
          {doc.proof.leaves.length > 0 ? (
            <div>
              <div className="text-muted">Committed document digests held by this server (sorted)</div>
              <ul className="font-mono break-all">{doc.proof.leaves.map((l) => <li key={l} className={l === doc.sha256 ? "font-bold text-ink" : ""}>{l}</li>)}</ul>
            </div>
          ) : <p className="text-muted">This server holds no digest list for the claim; only a direct single-document comparison is possible.</p>}
          <div><span className="text-muted">Recomputed commitment: </span><Mono className="break-all">{doc.proof.recomputed_root ?? "—"}</Mono></div>
          <div><span className="text-muted">On-chain commitment: </span><Mono className="break-all">{doc.proof.onchain_root}</Mono></div>
        </div>
      </Disclosure>
    </div>
  );
}

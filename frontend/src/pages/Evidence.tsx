import { useEffect, useState } from "react";
import { api, fmt, type PopulationAnalyticsSummary } from "../api";
import { ErrorBox, OutcomeToken, PageHeader, SectionHeader } from "../components/primitives";

const pct = (x: number | null | undefined) => (x == null ? "—" : `${(x * 100).toFixed(1)}%`);
const dec = (x: number | null | undefined) => (x == null ? "—" : x.toFixed(2));

export default function Evidence() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<unknown>(null);
  const [pop, setPop] = useState<PopulationAnalyticsSummary | null>(null);
  const [popErr, setPopErr] = useState<unknown>(null);
  useEffect(() => { api.evaluation().then(setD).catch(setErr); }, []);
  useEffect(() => { api.getPopulationSummary().then(setPop).catch(setPopErr); }, []);
  const er = d?.entity_resolution;
  const rc = d?.reconciliation;
  const a = d?.registry_audit;
  const e = d?.latest;
  const g = d?.gas;
  const du = e?.double_use;
  const parser = e?.extraction?.methods?.parser;
  const totalRows = a ? a.verra_retirements.rows + a.verra_issuances.rows + a.gold_retirements.rows : null;
  const totalParsed = a ? a.verra_retirements.parsed + a.verra_issuances.parsed + a.gold_retirements.parsed : null;
  const gasHinted = g?.rows?.slice(1).map((r: any) => r.hinted);
  const gasLast = g?.rows?.[g.rows.length - 1];

  return (
    <div>
      <PageHeader
        title="Evidence and methodology"
        lede={<>Where the data comes from, how each analysis works, and what the prototype has measured. Every figure on this page is read from the live API or from result files produced by the repository's scripts (<span className="font-mono text-[13px]">make eval</span>, <span className="font-mono text-[13px]">make test</span>). Benchmarks are synthetic or curated and are labelled as such; none of them measures real-world fraud-detection accuracy.</>}
      />

      <section aria-labelledby="prov-h" className="mb-12">
        <SectionHeader id="prov-h" title="Data provenance and coverage" aside={a ? `${a.source.version} · ${a.source.license}` : undefined} />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="space-y-3 text-sm leading-relaxed text-ink-soft">
            <p><strong className="text-ink">Registry records are real.</strong> Source: {a ? <a className="underline decoration-rule-strong underline-offset-2 hover:text-ink" href={a.source.url} target="_blank" rel="noreferrer">{a.source.dataset}</a> : "Berkeley Carbon Trading Project, Voluntary Registry Offsets Database"}, {a?.source.version ?? "v2026-08"}, released by Berkeley under CC BY 4.0. It is a static snapshot, not a live registry connection: retirements after 31 August 2026 are reported as "not found".</p>
            <p><strong className="text-ink">Claimants are synthetic.</strong> The five demo companies (Northwind, Helios, Arbor, Lumen, Kestrel) and their statements are fictional and labelled SYNTHETIC; their serial ranges are real registry ranges.</p>
            <p><strong className="text-ink">Rights.</strong> The committed rows originate from the Verra and Gold Standard registries, whose terms we could not confirm permit redistribution. They are included for demonstration and evaluation only and will be removed on request (see <span className="font-mono text-[13px]">data/LICENSE</span>).</p>
            {a?.source.citation && <p className="text-xs text-muted">Citation: {a.source.citation}</p>}
          </div>
          <div className="rounded-panel border border-rule bg-sheet p-4 text-sm">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Analytics population (live)</div>
            <ErrorBox error={popErr} title="Could not load the population summary" />
            {pop ? (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5">
                <div><dt className="text-xs text-muted">Retirement records</dt><dd className="font-mono font-semibold">{fmt(pop.total_retirement_records)}</dd></div>
                <div><dt className="text-xs text-muted">Retired tonnes</dt><dd className="font-mono font-semibold">{fmt(pop.total_retirement_quantity)}</dd></div>
                <div><dt className="text-xs text-muted">Issuance batches</dt><dd className="font-mono font-semibold">{fmt(pop.total_batches)}</dd></div>
                <div><dt className="text-xs text-muted">Disclosed beneficiary records</dt><dd className="font-mono font-semibold">{pct(pop.coverage.record_disclosure_rate)}</dd></div>
              </dl>
            ) : !popErr && <p className="text-muted">Loading…</p>}
            <p className="mt-3 text-xs leading-relaxed text-muted">The analytics run on the committed demo subset (Verra and Gold Standard records for the demo projects), not the whole market. Issuance records are excluded from retirement denominators. The full 493,518-row registry is used for the parsing audit below when built with <span className="font-mono">make data</span>.</p>
          </div>
        </div>
      </section>

      <ErrorBox error={err} title="Could not load results" />

      {/* headline results */}
      <ol className="mb-12 grid gap-px overflow-hidden rounded-sheet border border-rule bg-rule md:grid-cols-2 xl:grid-cols-4">
        <Headline n="01" title="Serials become unit ranges" value={a ? `${fmt(totalParsed)} / ${fmt(totalRows)}` : "…"} detail="Real Verra and Gold Standard registry rows parsed into (batch, first unit, last unit); every range size matches the stated quantity." token={<OutcomeToken outcome="passed" label="Real data" />} />
        <Headline n="02" title="Intervals catch what hashes miss" value={du ? `${dec(du.onceonly.recall)} vs ${dec(du.baseline.recall)}` : "…"} detail={du ? `Recall on ${fmt(du.n)} synthetic claim pairs built on real registry ranges: interval check vs exact serial/hash match. Ground truth uses the same interval definition, so OnceOnly\u2019s 1.00 is expected; the baseline gap is the finding.` : ""} token={<OutcomeToken outcome="review" label="Synthetic pairs" />} />
        <Headline n="03" title="Contract cost stays flat" value={gasHinted ? `${fmt(gasHinted[0])} gas` : "…"} detail={gasLast ? `Registering into a batch with 10 to ${gasLast.existing} active ranges. A linear scan grew to ${fmt(gasLast.linear)} gas.` : "Run the contract tests to generate gas results."} token={<OutcomeToken outcome="passed" label="Measured" />} />
        <Headline n="04" title="Serial extraction, parser only" value={parser ? `${pct(parser.doc_exact)} exact` : "…"} detail={parser ? `Share of ${parser.n} synthetic snippets (real serial ranges, 8 layouts) where the deterministic parser recovered every block exactly; block precision ${dec(parser.block_precision)}. In-sample: the table, prose and OCR handling was built against these same 8 layouts, so this is not an estimate of accuracy on real documents.` : ""} token={<OutcomeToken outcome="review" label="In-sample" />} />
      </ol>

      <div className="space-y-14">
        <section aria-labelledby="reg-h">
          <SectionHeader id="reg-h" title="Real registry data: can serials be parsed into unit ranges?" aside={a ? `${a.source.version} · ${a.source.license}` : undefined} />
          {a ? (
            <>
              <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="border-b border-rule text-left text-xs text-muted">
                    <tr><th className="px-4 py-2.5 font-medium">Records</th><th className="px-4 py-2.5 text-right font-medium">Rows</th><th className="px-4 py-2.5 text-right font-medium">Serials parsed</th><th className="px-4 py-2.5 text-right font-medium">Range size = quantity</th><th className="px-4 py-2.5 text-right font-medium">Overlaps within a batch</th></tr>
                  </thead>
                  <tbody className="divide-y divide-rule">
                    {[["Verra retirements", a.verra_retirements], ["Verra issuances", a.verra_issuances], ["Gold Standard retirements", a.gold_retirements]].map(([label, r]: any) => (
                      <tr key={label}>
                        <th scope="row" className="px-4 py-2.5 text-left font-medium">{label}</th>
                        <td className="px-4 py-2.5 text-right">{fmt(r.rows)}</td>
                        <td className="px-4 py-2.5 text-right">{fmt(r.parsed)} <span className="text-muted">({pct(r.parsed / r.rows)})</span></td>
                        <td className="px-4 py-2.5 text-right">{fmt(r.qty_consistent)} <span className="text-muted">({pct(r.qty_consistent / r.parsed)})</span></td>
                        <td className="px-4 py-2.5 text-right">{r.overlapping_adjacent_pairs_within_namespace == null ? "—" : fmt(r.overlapping_adjacent_pairs_within_namespace)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 max-w-[80ch] text-sm leading-relaxed text-ink-soft">
                Overlaps are counted as adjacent overlapping pairs after sorting each batch's records by first unit (zero adjacent pairs means no two records in a batch overlap at all).
                Unit numbers are unique only inside an issuance batch. Sorting all Verra retirements by unit number <em>without</em> the batch produces <strong className="text-ink">{fmt(a.verra_retirements.overlapping_adjacent_pairs_if_batch_ignored)}</strong> adjacent "overlapping" pairs, every one between records of different batches: collisions created by the wrong key, not overlaps. That is why every ledger range is keyed by registry and batch.
                Of the {a.gold_retirements.overlapping_adjacent_pairs_within_namespace} Gold Standard pairs, 3 are exact duplicate rows and 2 come from one 10,000-unit record whose range exactly equals two other records combined. We report them as registry data inconsistencies to clarify, not as double retirements or as findings about any organisation. Source: {a.source.dataset}.
              </p>
            </>
          ) : <p className="text-sm text-muted">Registry audit not found. Run <span className="font-mono">make data</span>.</p>}
        </section>

        <section aria-labelledby="du-h">
          <SectionHeader id="du-h" title="Double-use detection on labelled claim pairs" aside={e ? `generated ${e.generated_at}` : undefined} />
          {du ? (
            <div className="space-y-5">
              <p className="max-w-[80ch] text-sm leading-relaxed text-ink-soft">{du.description}</p>
              <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
                <table className="w-full min-w-[620px] text-sm">
                  <thead className="border-b border-rule text-left text-xs text-muted"><tr><th className="px-4 py-2.5 font-medium">Method</th><th className="px-4 py-2.5 text-right font-medium">Precision</th><th className="px-4 py-2.5 text-right font-medium">Recall</th><th className="px-4 py-2.5 text-right font-medium">False positives</th><th className="px-4 py-2.5 text-right font-medium">False negatives</th></tr></thead>
                  <tbody className="divide-y divide-rule">
                    {[["OnceOnly rules engine", du.onceonly], ["ClaimLedger contract (replayed on chain)", du.contract], ["Baseline: exact serial or document hash", du.baseline], ["Ablation: interval overlap ignoring the batch", du.numbers_only]].filter(([, m]) => m && "tp" in m).map(([label, m]: any) => (
                      <tr key={label}><th scope="row" className="px-4 py-2.5 text-left font-medium">{label}</th><td className="px-4 py-2.5 text-right">{dec(m.precision)}</td><td className={`px-4 py-2.5 text-right ${m.recall < 0.5 ? "font-semibold text-crimson" : ""}`}>{dec(m.recall)}</td><td className={`px-4 py-2.5 text-right ${m.fp > 0 ? "font-semibold text-crimson" : ""}`}>{m.fp}</td><td className={`px-4 py-2.5 text-right ${m.fn > 0 ? "font-semibold text-crimson" : ""}`}>{m.fn}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {du.contract_agrees_with_engine != null && <p className="text-sm text-ink-soft">Contract and rules engine agree on {(du.contract_agrees_with_engine * 100).toFixed(1)}% of cases.</p>}
              <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
                <table className="w-full min-w-[640px] text-sm">
                  <caption className="px-4 pt-3 text-left text-xs text-muted">Correct out of 30, by case type</caption>
                  <thead className="border-b border-rule text-left text-xs text-muted"><tr><th className="px-4 py-2.5 font-medium">Case type</th><th className="px-4 py-2.5 font-medium">Truth</th><th className="px-4 py-2.5 text-right font-medium">OnceOnly</th><th className="px-4 py-2.5 text-right font-medium">Contract</th><th className="px-4 py-2.5 text-right font-medium">Baseline</th><th className="px-4 py-2.5 text-right font-medium">Ignoring batch</th></tr></thead>
                  <tbody className="divide-y divide-rule">
                    {Object.values(du.by_category).map((v: any) => (
                      <tr key={v.label}>
                        <th scope="row" className="px-4 py-2.5 text-left font-normal">{v.label}</th>
                        <td className="px-4 py-2.5 text-ink-soft">{v.truth ? "double use" : "not double use"}</td>
                        <Cell v={v.onceonly_correct} n={v.n} /><Cell v={v.contract_correct} n={v.n} /><Cell v={v.baseline_correct} n={v.n} /><Cell v={v.numbers_only_correct} n={v.n} />
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : <p className="text-sm text-muted">Not run yet. Run <span className="font-mono">make eval</span>.</p>}
        </section>

        <section aria-labelledby="gas-h">
          <SectionHeader id="gas-h" title="On-chain cost as a batch fills" aside="Hardhat · solc 0.8.24 · optimizer 200" />
          {g?.rows ? (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start">
              <GasChart rows={g.rows} />
              <div className="space-y-3 text-sm leading-relaxed text-ink-soft">
                <p>{g.note}</p>
                <p>ClaimLedger keeps each batch's active ranges in a sorted linked list. The caller supplies the predecessor and the contract checks only the two neighbours, so cost does not grow with the number of claims. A wrong hint can only cause a revert, never an accepted overlap (tested with 300 adversarial random hints).</p>
                <p>The largest real Verra batch has {a ? fmt(a.verra_retirements.retirements_per_namespace.max) : "tens of thousands of"} retirements, which is why the linear scan of the first version was replaced.</p>
              </div>
            </div>
          ) : <p className="text-sm text-muted">Run <span className="font-mono">make test-contracts</span> to generate gas results.</p>}
        </section>

        <section aria-labelledby="ex-h">
          <SectionHeader id="ex-h" title="Serial extraction from documents" />
          {e?.extraction ? (
            <div className="space-y-4">
              <p className="max-w-[80ch] text-sm leading-relaxed text-ink-soft">{e.extraction.description}</p>
              <div className="max-w-[80ch] space-y-2 text-sm leading-relaxed text-ink-soft">
                <p><strong className="text-ink">What the parser supports.</strong> Verra and Gold Standard serial formats, serials wrapped across lines or with spaced or en dashes, several blocks in one document, simple table columns (batch, first and last unit in separate cells), prose ranges with an explicit batch ("units 896,309,560 to …"), and letter-O-for-zero OCR errors. Every extracted block keeps its source text and the transformations applied.</p>
                <p><strong className="text-ink">How it was tested.</strong> The 60-snippet benchmark is in-sample: the layout handling was developed against these templates, so the 100% shown is a regression check, not a real-world accuracy estimate. Fifteen separate adversarial tests (inverted ranges, truncated serials, ISBNs, phone numbers, currency ranges, invoice codes, missing batches, incomplete tables) check that the parser does not invent blocks; they run in the backend test suite.</p>
                <p><strong className="text-ink">What is not supported or not measured.</strong> Scanned images without a text layer (there is no OCR engine), complex multi-page tables, ranges without a batch identifier, and other registries. The optional AI extractor is implemented but has not been evaluated; the offline "mock" extractor calls the parser, so it cannot validate anything.</p>
              </div>
              <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="border-b border-rule text-left text-xs text-muted"><tr><th className="px-4 py-2.5 font-medium">Extractor</th><th className="px-4 py-2.5 text-right font-medium">Documents</th><th className="px-4 py-2.5 text-right font-medium">All blocks exact</th><th className="px-4 py-2.5 text-right font-medium">Block precision</th><th className="px-4 py-2.5 text-right font-medium">Block recall</th></tr></thead>
                  <tbody className="divide-y divide-rule">
                    {Object.entries(e.extraction.methods).map(([k, m]: any) => (
                      <tr key={k}><th scope="row" className="px-4 py-2.5 text-left font-medium">{m.label}</th>{m.status === "ok" ? <><td className="px-4 py-2.5 text-right">{m.n}</td><td className="px-4 py-2.5 text-right">{pct(m.doc_exact)}</td><td className="px-4 py-2.5 text-right">{dec(m.block_precision)}</td><td className="px-4 py-2.5 text-right">{dec(m.block_recall)}</td></> : <td colSpan={4} className="px-4 py-2.5 text-right text-ink-soft">{m.status}</td>}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {parser?.per_variant && (
                <ul className="flex flex-wrap gap-2 text-xs" aria-label="Parser results by layout">
                  {Object.entries(parser.per_variant).map(([k, v]: any) => (
                    <li key={k} className={`rounded-token border px-2 py-1 ${v.correct === v.n ? "border-lichen/30 bg-lichen-wash text-lichen" : "border-crimson/40 bg-crimson-wash text-crimson"}`}>{k.replaceAll("_", " ")} <span className="font-mono">{v.correct}/{v.n}</span></li>
                  ))}
                </ul>
              )}
            </div>
          ) : <p className="text-sm text-muted">Not run yet. Run <span className="font-mono">make eval</span>.</p>}
        </section>

        <section aria-labelledby="bench-h">
          <SectionHeader id="bench-h" title="Entity resolution and allocation reconciliation benchmarks" aside="curated cases · internal splits" />
          <div className="grid gap-6 lg:grid-cols-2">
            <BenchmarkTable
              title={`Entity resolution: ${er?.total_cases ?? "…"} curated name pairs`}
              models={er?.models}
              note={er ? `Pairs cover legal-suffix and abbreviation variants, broker "on behalf of" delegations, parent/subsidiary pairs and hard negatives. Candidate blocking evaluated ${fmt(er.blocking_efficiency?.candidates_evaluated)} of ${fmt(er.blocking_efficiency?.all_pairs)} possible pairs. Positive means "refers to the same entity or a disclosed delegation"; a match never establishes legal identity.` : undefined}
            />
            <BenchmarkTable
              title={`Allocation reconciliation: ${rc?.total_cases ?? "…"} curated scenarios`}
              models={rc?.models}
              note={rc?.semantic ? `On the binary "conflict" label a naive interval matcher also scores 1.00, so the binary score does not distinguish the methods. What OnceOnly adds is the allocation class: ${rc.semantic.allocation_class_exact}/${rc.semantic.n} scenarios receive the expected class (legitimate split, intermediary attribution, related claimants, unresolved beneficiary, cross-namespace, conflict…), and ${rc.semantic.geometry_exact}/${rc.semantic.n} the expected interval geometry. The "held-out" split is an internally constructed reserve, not field data.` : undefined}
            />
          </div>
          <p className="mt-3 max-w-[90ch] text-xs leading-relaxed text-muted">Both benchmarks were written by the project team, so they test that the implementation behaves as specified on representative cases; they are not independent measurements of real-world accuracy.</p>
        </section>

        <section aria-labelledby="meth-h">
          <SectionHeader id="meth-h" title="Methodology documents" aside="detailed reports in the repository" />
          <ul className="grid gap-px overflow-hidden rounded-sheet border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-3">
            {METHODS.map((m) => (
              <li key={m.doc} className="bg-sheet p-4">
                <div className="text-sm font-semibold">{m.title}</div>
                <p className="mt-1 text-xs leading-relaxed text-ink-soft">{m.summary}</p>
                <a className="mt-2 inline-block font-mono text-[11px] text-glacier underline underline-offset-2" href={`${DOCS}/${m.doc}`} target="_blank" rel="noreferrer">{m.doc}</a>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="lim-h">
          <SectionHeader id="lim-h" title="Limits of this evidence" />
          <ul className="grid max-w-[90ch] gap-x-10 gap-y-2.5 text-sm leading-relaxed text-ink-soft md:grid-cols-2">
            <li>Every risk signal is an investigative indicator for human review, not a finding of fraud or of competing legal claims.</li>
            <li>The labelled claim pairs are synthetic and their ground truth uses the engine's interval definition, so they verify the implementation, not real-world accuracy or prevalence.</li>
            <li>Analytics describe a curated subset of two registries, not the global voluntary carbon market.</li>
            <li>A missing or undisclosed beneficiary is a disclosure fact, not evidence of misconduct. Similar names, parent/subsidiary links and broker delegations do not establish legal identity.</li>
            <li>Registry data stops at 31 August 2026 and is not connected live; private contracts between brokers and buyers were not inspected.</li>
            <li>The contract runs on a local development chain with a trusted registrar key; it is not deployed to a public network.</li>
            <li>AI extraction accuracy, cost and latency are not measured; parser results are in-sample.</li>
            <li>We found no documented public case of two companies citing the same retirement, so the prevalence of double use is unmeasured.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}

function Headline({ n, title, value, detail, token }: { n: string; title: string; value: string; detail: string; token: React.ReactNode }) {
  return (
    <li className="flex flex-col gap-2 bg-sheet p-5">
      <div className="flex items-center justify-between gap-2"><span className="font-mono text-xs text-muted">{n}</span>{token}</div>
      <div className="text-sm font-semibold">{title}</div>
      <div className="text-[26px] leading-tight font-bold tracking-tight">{value}</div>
      <p className="text-xs leading-relaxed text-ink-soft">{detail}</p>
    </li>
  );
}

function Cell({ v, n }: { v: number | undefined; n: number }) {
  if (v == null) return <td className="px-4 py-2.5 text-right text-muted">—</td>;
  return <td className={`px-4 py-2.5 text-right font-mono text-[13px] ${v < n ? "font-semibold text-crimson" : ""}`}>{v}/{n}</td>;
}

function GasChart({ rows }: { rows: { existing: number; hinted: number; linear: number }[] }) {
  const max = Math.max(...rows.map((r) => Math.max(r.hinted, r.linear)));
  return (
    <figure className="rounded-panel border border-rule bg-sheet p-4">
      <figcaption className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm"><span className="font-semibold">Gas per registration</span>
        <span className="flex gap-4 text-xs text-ink-soft"><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-4 rounded-[2px] bg-ink" aria-hidden />Sorted list (current)</span><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-4 rounded-[2px] border border-slate hatch-slate" aria-hidden />Linear scan (v0)</span></span>
      </figcaption>
      <table className="w-full text-sm">
        <thead className="sr-only"><tr><th>Active ranges in batch</th><th>Sorted list gas</th><th>Linear gas</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.existing}>
              <th scope="row" className="w-24 py-1.5 pr-3 text-left text-xs font-normal text-ink-soft">{r.existing} existing</th>
              <td className="py-1.5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2"><div className="h-2.5 rounded-[2px] bg-ink" style={{ width: `${(r.hinted / max) * 78}%` }} /><span className="font-mono text-[11px] text-ink-soft">{fmt(r.hinted)}</span></div>
                  <div className="flex items-center gap-2"><div className="h-2.5 rounded-[2px] border border-slate hatch-slate" style={{ width: `${(r.linear / max) * 78}%` }} /><span className="font-mono text-[11px] text-ink-soft">{fmt(r.linear)}</span></div>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

const DOCS = "https://github.com/Sidd927/OnceOnly-DataNova/blob/datanova/phase-0-baseline/docs";

const METHODS = [
  { title: "Data quality and ingestion", doc: "DATANOVA_DATA_QUALITY.md", summary: "Row counts, mojibake repair, date provenance, and why unit ranges must be keyed by registry and batch." },
  { title: "Serial extraction", doc: "DATANOVA_EXTRACTION_EVALUATION.md", summary: "Parser passes, provenance on every block, in-sample benchmark and adversarial tests." },
  { title: "Entity resolution", doc: "DATANOVA_ENTITY_RESOLUTION_METHODOLOGY.md", summary: "Non-destructive name normalization, intermediary parsing, blocking and explainable multi-feature matching." },
  { title: "Allocation-aware reconciliation", doc: "DATANOVA_ALLOCATION_RECONCILIATION_METHODOLOGY.md", summary: "Closed-interval algebra, six geometric and eight semantic allocation classes." },
  { title: "Concentration and fragmentation", doc: "DATANOVA_PHASE_2C_STAGE_1_METHODOLOGY.md", summary: "HHI and entropy over disclosed volume, pooled vs within-batch Gini, absolute and relative small allocations." },
  { title: "Statistical specification", doc: "DATANOVA_PHASE_2C_MATHEMATICAL_SPECIFICATION.md", summary: "Formal definitions for the Phase 2C concentration, fragmentation, temporal and cross-registry metrics." },
  { title: "Temporal intelligence", doc: "DATANOVA_PHASE_2C_STAGE_2_FINAL_CORRECTIONS_REPORT.md", summary: "Continuous calendars, leave-one-out MAD bursts, and why zero activity is not proof of dormancy." },
  { title: "Cross-registry intelligence", doc: "DATANOVA_PHASE_2C_STAGE_3_IMPLEMENTATION_REPORT.md", summary: "Project correlation, identifier-collision handling and comparative retirement dynamics." },
  { title: "Explainable risk assessment", doc: "DATANOVA_EXPLAINABLE_ASSESSMENT_METHODOLOGY.md", summary: "Sixteen deterministic rules, dependency groups, counterevidence and non-accusatory statuses." },
  { title: "Population metrics audit", doc: "DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md", summary: "Independent reproduction of the Observatory population figures and the corrections it led to." },
  { title: "Verification trust model", doc: "PROJECT_MASTER_CONTEXT.md", summary: "What on-chain verification proves, what is an off-chain lookup, and the network assumptions." },
  { title: "Release QA", doc: "FINAL_RELEASE_QA_REPORT.md", summary: "Commands, results and skipped checks for this release." },
];

function BenchmarkTable({ title, models, note }: { title: string; models?: Record<string, any>; note?: string }) {
  return (
    <div className="min-w-0 space-y-2">
      <div className="text-sm font-semibold">{title}</div>
      <div className="overflow-x-auto rounded-panel border border-rule bg-sheet">
        <table className="w-full min-w-[420px] text-sm">
          <thead className="border-b border-rule text-left text-xs text-muted"><tr><th className="px-4 py-2.5 font-medium">Method</th><th className="px-4 py-2.5 text-right font-medium">Precision</th><th className="px-4 py-2.5 text-right font-medium">Recall</th><th className="px-4 py-2.5 text-right font-medium">F1</th></tr></thead>
          <tbody className="divide-y divide-rule">
            {models ? Object.entries(models).map(([name, m]) => (
              <tr key={name}><th scope="row" className="px-4 py-2.5 text-left font-medium">{name}</th><td className="px-4 py-2.5 text-right">{dec(m.precision)}</td><td className="px-4 py-2.5 text-right">{dec(m.recall)}</td><td className="px-4 py-2.5 text-right">{dec(m.f1)}</td></tr>
            )) : <tr><td colSpan={4} className="px-4 py-2.5 text-muted">Result file not found.</td></tr>}
          </tbody>
        </table>
      </div>
      {note && <p className="text-xs leading-relaxed text-ink-soft">{note}</p>}
    </div>
  );
}

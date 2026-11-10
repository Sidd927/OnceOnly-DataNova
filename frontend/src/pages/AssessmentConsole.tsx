import { useState, useEffect, useCallback, useId } from "react";
import demoTargets from "../lib/demoTargets.json";
import { useSearchParams } from "react-router-dom";
import {
  Play,
  BookOpen,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";
import {
  api,
  type AssessmentScope,
  type RiskAssessmentRequest,
  type RiskAssessmentResponse,
  fmt,
} from "../api";
import {
  PageHeader,
  SectionHeader,
  ErrorBox,
  Button,
  Mono,
  PriorityBadge,
  AssessmentStatusBadge,
  SeverityBadge,
  EvidenceStrengthBadge,
  CategoryBadge,
  SourceStageBadge,
  MetricTile,
} from "../components/primitives";
import { RulesCatalogModal } from "../components/RulesCatalogModal";

export default function AssessmentConsole() {
  const [searchParams] = useSearchParams();
  const formId = useId();

  // Query parameter pre-fills
  const initialScope = (searchParams.get("scope") as AssessmentScope) || "PROJECT";
  const initialProjectId = searchParams.get("project_id") || demoTargets.project.project_id;
  const initialRegistry = searchParams.get("registry") || "VCS";
  const initialClaimId = searchParams.get("claim_id") || "";

  // State
  const [scope, setScope] = useState<AssessmentScope>(initialScope);
  const [registry, setRegistry] = useState(initialRegistry);
  const [projectId, setProjectId] = useState(initialProjectId);
  const [batchId, setBatchId] = useState("");
  const [claimId, setClaimId] = useState(initialClaimId);
  const [entityA, setEntityA] = useState("");
  const [entityB, setEntityB] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<RiskAssessmentResponse | null>(null);

  // Expanded evidence drawer state
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [selectedRuleForCatalog, setSelectedRuleForCatalog] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const toggleExpand = (id: string) => {
    setExpandedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const copyJson = () => {
    if (!result) return;
    navigator.clipboard.writeText(JSON.stringify(result, null, 2)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const runAssessment = useCallback(async (overrideReq?: RiskAssessmentRequest) => {
    setBusy(true);
    setError(null);
    try {
      let req: RiskAssessmentRequest;
      if (overrideReq) {
        req = overrideReq;
      } else {
        req = { scope };
        if (scope === "PROJECT") {
          req.registry = registry;
          req.project_id = projectId.trim();
        } else if (scope === "CLAIM") {
          req.claim_id = parseInt(claimId, 10);
        } else if (scope === "BATCH") {
          req.registry = registry;
          req.batch_id = batchId.trim();
        } else if (scope === "ENTITY") {
          req.entity_a = entityA.trim();
          req.entity_b = entityB.trim();
        }
      }

      const res = await api.assessment.assessRisk(req);
      setResult(res);
      // Auto-expand high/critical items
      const initialExp: Record<string, boolean> = {};
      res.evidence_items.forEach((item) => {
        if (item.severity === "CRITICAL" || item.severity === "HIGH") {
          initialExp[item.id] = true;
        }
      });
      setExpandedItems(initialExp);
    } catch (e) {
      setError(e);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }, [scope, registry, projectId, claimId, batchId, entityA, entityB]);

  // Auto-run if query params provide full input
  useEffect(() => {
    const qScope = searchParams.get("scope") as AssessmentScope;
    if (qScope === "CLAIM" && searchParams.get("claim_id")) {
      const cid = parseInt(searchParams.get("claim_id")!, 10);
      let alive = true;
      api.assessment
        .assessRisk({ scope: "CLAIM", claim_id: cid })
        .then((res) => {
          if (alive) setResult(res);
        })
        .catch((e) => {
          if (alive) setError(e);
        });
      return () => {
        alive = false;
      };
    } else if (qScope === "PROJECT" && searchParams.get("project_id")) {
      const pid = searchParams.get("project_id")!;
      const reg = searchParams.get("registry") || "VCS";
      let alive = true;
      api.assessment
        .assessRisk({ scope: "PROJECT", registry: reg, project_id: pid })
        .then((res) => {
          if (alive) setResult(res);
        })
        .catch((e) => {
          if (alive) setError(e);
        });
      return () => {
        alive = false;
      };
    }
  }, [searchParams]);

  const handlePreset = (presetScope: AssessmentScope, reg: string, idVal: string) => {
    setScope(presetScope);
    setRegistry(reg);
    if (presetScope === "PROJECT") {
      setProjectId(idVal);
      runAssessment({ scope: "PROJECT", registry: reg, project_id: idVal });
    } else if (presetScope === "CLAIM") {
      setClaimId(idVal);
      runAssessment({ scope: "CLAIM", claim_id: parseInt(idVal, 10) });
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Unified Risk Assessment Console"
        lede="Combine allocation conflicts, beneficiary concentration, batch fragmentation, timing anomalies and cross-registry signals into one explainable assessment. Every finding shows its rule, threshold, evidence, counterevidence and missing information. A review priority is a triage aid for an investigator; it is not a determination of fraud or of who holds a valid claim."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setSelectedRuleForCatalog(null);
                setCatalogOpen(true);
              }}
              className="py-2! text-xs"
            >
              <BookOpen size={14} aria-hidden />
              Rules Catalog
            </Button>
            {result && (
              <Button
                variant="secondary"
                onClick={copyJson}
                className="py-2! text-xs"
                title="Copy assessment report JSON"
              >
                {copied ? <Check size={14} className="text-lichen" /> : <Copy size={14} />}
                {copied ? "Copied JSON" : "Export JSON"}
              </Button>
            )}
          </div>
        }
      />

      <RulesCatalogModal
        isOpen={catalogOpen}
        onClose={() => setCatalogOpen(false)}
        initialRuleId={selectedRuleForCatalog}
      />

      {/* Target configuration panel */}
      <section aria-labelledby="scope-cfg-h" className="rounded-sheet border border-rule bg-sheet p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-rule pb-4">
          <div>
            <h2 id="scope-cfg-h" className="text-base font-bold text-ink">
              Assessment Scope & Parameters
            </h2>
            <p className="text-xs text-muted">
              Select an investigative target. Evaluates all 16 versioned deterministic rules.
            </p>
          </div>

          {/* Quick presets */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-muted font-medium">Demo Targets:</span>
            <button
              type="button"
              onClick={() => handlePreset("PROJECT", demoTargets.project.registry, demoTargets.project.project_id)}
              className="press rounded border border-rule-strong bg-fog px-2 py-1 font-mono hover:border-ink hover:bg-sheet text-[11px]"
            >
              {demoTargets.project.label}
            </button>
            {demoTargets.claims.map((t) => (
              <button
                key={t.claim_id}
                type="button"
                onClick={() => handlePreset("CLAIM", "VCS", String(t.claim_id))}
                className="press rounded border border-rule-strong bg-fog px-2 py-1 font-mono hover:border-ink hover:bg-sheet text-[11px]"
                title={`Seeded synthetic claim ${t.ref}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <form
          id={formId}
          onSubmit={(e) => {
            e.preventDefault();
            runAssessment();
          }}
          className="mt-5 space-y-4"
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="block text-xs font-semibold text-ink-soft mb-1">
                Target Scope
              </label>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value as AssessmentScope)}
                className="w-full rounded-panel border border-rule-strong bg-sheet px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
              >
                <option value="PROJECT">PROJECT (Census & Dynamics)</option>
                <option value="CLAIM">CLAIM (Ledger & Interval Conflicts)</option>
                <option value="BATCH">BATCH (Issuance Fragmentation & HHI)</option>
                <option value="ENTITY">ENTITY (Fuzzy Resolution & Broker)</option>
              </select>
            </div>

            {(scope === "PROJECT" || scope === "BATCH") && (
              <div>
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Registry Namespace
                </label>
                <select
                  value={registry}
                  onChange={(e) => setRegistry(e.target.value)}
                  className="w-full rounded-panel border border-rule-strong bg-sheet px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                >
                  <option value="VCS">Verra (VCS)</option>
                  <option value="GS">Gold Standard (GS)</option>
                </select>
              </div>
            )}

            {scope === "PROJECT" && (
              <div>
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Project Identifier
                </label>
                <input
                  type="text"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  placeholder="e.g. 1904, 1845, 2284"
                  required
                  className="w-full rounded-panel border border-rule-strong bg-sheet px-3 py-2 font-mono text-sm text-ink focus:border-ink focus:outline-none"
                />
              </div>
            )}

            {scope === "CLAIM" && (
              <div>
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Claim ID (OnceOnly Ledger)
                </label>
                <input
                  type="number"
                  value={claimId}
                  onChange={(e) => setClaimId(e.target.value)}
                  placeholder="e.g. 1, 2, 3"
                  required
                  min={1}
                  className="w-full rounded-panel border border-rule-strong bg-sheet px-3 py-2 font-mono text-sm text-ink focus:border-ink focus:outline-none"
                />
              </div>
            )}

            {scope === "BATCH" && (
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Issuance Batch ID
                </label>
                <input
                  type="text"
                  value={batchId}
                  onChange={(e) => setBatchId(e.target.value)}
                  placeholder="e.g. 10452-45210-45215-VCS-VCU..."
                  required
                  className="w-full rounded-panel border border-rule-strong bg-sheet px-3 py-2 font-mono text-sm text-ink focus:border-ink focus:outline-none"
                />
              </div>
            )}

            {scope === "ENTITY" && (
              <>
                <div>
                  <label className="block text-xs font-semibold text-ink-soft mb-1">
                    Entity A (Claimant / Buyer)
                  </label>
                  <input
                    type="text"
                    value={entityA}
                    onChange={(e) => setEntityA(e.target.value)}
                    placeholder="e.g. Delta Air Lines, Inc."
                    required
                    className="w-full rounded-panel border border-rule-strong bg-sheet px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-ink-soft mb-1">
                    Entity B (Registry Record)
                  </label>
                  <input
                    type="text"
                    value={entityB}
                    onChange={(e) => setEntityB(e.target.value)}
                    placeholder="e.g. Delta Air Lines LLC"
                    required
                    className="w-full rounded-panel border border-rule-strong bg-sheet px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                  />
                </div>
              </>
            )}
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-[11px] text-muted">
              Evaluates multi-phase evidence items and flags independent vs reinforcing signals.
            </span>
            <Button type="submit" busy={busy} className="py-2! px-5!">
              <Play size={14} aria-hidden />
              Run Assessment
            </Button>
          </div>
        </form>
      </section>

      <ErrorBox error={error} title="Assessment Evaluation Error" />

      {/* Results view */}
      {result && (
        <div className="space-y-8 fade-in">
          {/* Executive scorecard banner */}
          <section
            aria-labelledby="synth-h"
            className="rounded-sheet border border-rule bg-sheet p-6 shadow-sm space-y-6"
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-rule pb-5">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold uppercase tracking-wider text-muted">
                    Assessment Target:
                  </span>
                  <span className="font-mono text-sm font-bold text-ink bg-fog px-2 py-0.5 rounded border border-rule">
                    {result.target.scope}{" "}
                    {result.target.project_id
                      ? `${result.target.registry} Project ${result.target.project_id}`
                      : result.target.claim_id
                      ? `Claim #${result.target.claim_id}`
                      : result.target.batch_id
                      ? `Batch ${result.target.batch_id}`
                      : result.target.entity_a}
                  </span>
                  <span className="text-xs text-muted">
                    Evaluated at <Mono>{new Date(result.assessment_timestamp).toLocaleTimeString()}</Mono>
                  </span>
                </div>
                <h3 id="synth-h" className="mt-2 text-xl font-bold tracking-tight text-ink">
                  {result.target.description || "Multi-Phase Evidence Assessment"}
                </h3>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <AssessmentStatusBadge status={result.overall_status} size="md" />
                <PriorityBadge priority={result.review_priority} size="md" />
              </div>
            </div>

            {/* Priority explanation */}
            <div className="rounded-panel border border-rule bg-fog-2/40 p-4 text-xs leading-relaxed text-ink">
              <span className="font-bold text-ink-soft uppercase tracking-wider text-[10px] block mb-1">
                Triage Explanation
              </span>
              {result.priority_explanation}
            </div>

            {/* High-level metrics grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricTile
                label="Triggered Rules"
                value={result.triggered_rule_ids.length}
                subtext={`Out of 16 versioned rules`}
                token={
                  result.triggered_rule_ids.length > 0 ? (
                    <SeverityBadge severity="HIGH" size="sm" />
                  ) : (
                    <SeverityBadge severity="INFORMATIONAL" size="sm" />
                  )
                }
              />
              <MetricTile
                label="Total Evidence Items"
                value={result.evidence_items.length}
                subtext="Structured analytical findings"
              />
              <MetricTile
                label="Independent Signal Groups"
                value={result.independent_evidence_count}
                subtext="Safeguard against double-counting"
              />
              <MetricTile
                label="Correlated Findings"
                value={result.correlated_evidence_count}
                subtext={`${result.dependency_groups.length} clusters identified`}
              />
            </div>
          </section>

          {/* Evidence Dependency Groups & Structured Findings */}
          <section aria-labelledby="evidence-h" className="space-y-4">
            <SectionHeader
              id="evidence-h"
              title="Evidence Items & Cluster Analysis"
              aside={`${result.evidence_items.length} finding${result.evidence_items.length === 1 ? "" : "s"}`}
            />

            {result.evidence_items.length === 0 && (
              <div className="rounded-panel border border-dashed border-rule-strong bg-sheet p-8 text-center text-sm text-ink-soft">
                No elevated risk findings detected for this target under the versioned ruleset.
              </div>
            )}

            {/* Dependency groups explanation if present */}
            {result.dependency_groups.length > 0 && (
              <div className="rounded-panel border border-glacier/30 bg-glacier-wash/40 p-4 text-xs text-glacier space-y-2">
                <div className="font-semibold flex items-center gap-1.5">
                  <Info size={14} aria-hidden />
                  Correlated Evidence Clusters Active
                </div>
                <p>
                  To prevent artificial inflation of review severity, correlated findings sharing the same root data artifact (such as identical serial intervals or shared entity records) are grouped into dependency clusters rather than treated as independent proof.
                </p>
              </div>
            )}

            {/* Evidence items list */}
            <div className="space-y-3">
              {result.evidence_items.map((item) => {
                const isExpanded = expandedItems[item.id];
                const depGroup = result.dependency_groups.find(
                  (g) => g.group_id === item.dependency_group_id
                );

                return (
                  <article
                    key={item.id}
                    className={`rounded-panel border bg-sheet transition-all ${
                      item.severity === "CRITICAL"
                        ? "border-crimson/50 shadow-sm"
                        : item.severity === "HIGH"
                        ? "border-crimson/30"
                        : "border-rule"
                    }`}
                  >
                    <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedRuleForCatalog(item.rule_id);
                              setCatalogOpen(true);
                            }}
                            className="font-mono text-xs font-bold text-ink bg-fog hover:bg-sheet px-2 py-0.5 rounded border border-rule-strong underline decoration-dotted"
                            title="Click to view rule definition in Rules Catalog"
                          >
                            {item.rule_id}
                          </button>
                          <h4 className="font-bold text-sm text-ink">
                            {item.title}
                          </h4>
                          {depGroup && (
                            <span className="font-mono text-[10.5px] rounded bg-fog-2 px-1.5 py-0.5 text-muted border border-rule" title={depGroup.explanation}>
                              Cluster: {depGroup.group_id}
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                          <CategoryBadge category={item.category} />
                          <SourceStageBadge stage={item.source_stage} />
                          <EvidenceStrengthBadge strength={item.evidence_strength} />
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
                        <SeverityBadge severity={item.severity} size="md" />
                        <button
                          type="button"
                          onClick={() => toggleExpand(item.id)}
                          className="press inline-flex h-8 w-8 items-center justify-center rounded border border-rule hover:border-rule-strong"
                          aria-label={isExpanded ? "Collapse item" : "Expand item"}
                          aria-expanded={isExpanded}
                        >
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      </div>
                    </div>

                    {/* Explanatory summary */}
                    <div className="px-4 pb-3 text-xs leading-relaxed text-ink-soft">
                      {item.explanation}
                    </div>

                    {/* Expandable forensic details */}
                    {isExpanded && (
                      <div className="border-t border-rule bg-fog/30 p-4 space-y-4 text-xs leading-relaxed">
                        {/* Metrics and thresholds */}
                        {(Object.keys(item.metrics).length > 0 || Object.keys(item.thresholds).length > 0) && (
                          <div className="grid sm:grid-cols-2 gap-3">
                            {Object.keys(item.metrics).length > 0 && (
                              <div className="rounded border border-rule bg-sheet p-3">
                                <div className="font-semibold text-ink-soft uppercase text-[10px] tracking-wider mb-2">
                                  Evaluated Metrics
                                </div>
                                <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 font-mono text-[11.5px]">
                                  {Object.entries(item.metrics).map(([k, v]) => (
                                    <div key={k} className="contents">
                                      <dt className="text-muted">{k}:</dt>
                                      <dd className="font-bold text-ink">{typeof v === "number" ? fmt(v) : String(v)}</dd>
                                    </div>
                                  ))}
                                </dl>
                              </div>
                            )}

                            {Object.keys(item.thresholds).length > 0 && (
                              <div className="rounded border border-rule bg-sheet p-3">
                                <div className="font-semibold text-ink-soft uppercase text-[10px] tracking-wider mb-2">
                                  Benchmark Thresholds Applied
                                </div>
                                <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 font-mono text-[11.5px]">
                                  {Object.entries(item.thresholds).map(([k, v]) => (
                                    <div key={k} className="contents">
                                      <dt className="text-muted">{k}:</dt>
                                      <dd className="text-ink-soft">{typeof v === "number" ? fmt(v) : String(v)}</dd>
                                    </div>
                                  ))}
                                </dl>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Supporting records */}
                        {item.supporting_records && item.supporting_records.length > 0 && (
                          <div>
                            <span className="font-semibold text-ink-soft uppercase text-[10px] tracking-wider block mb-1">
                              Supporting Unit Ranges / Records
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {item.supporting_records.map((rec, i) => (
                                <Mono key={i} className="rounded bg-sheet border border-rule px-2 py-0.5 text-[11px] text-ink">
                                  {rec}
                                </Mono>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Recommended action */}
                        {item.recommended_action && (
                          <div className="rounded border border-lichen/30 bg-lichen-wash/30 p-3">
                            <span className="font-bold text-lichen uppercase text-[10px] tracking-wider block mb-0.5">
                              Recommended Investigative Action
                            </span>
                            <p className="text-ink">{item.recommended_action}</p>
                          </div>
                        )}

                        {/* Contextual caveats, limitations, counterevidence */}
                        <div className="grid sm:grid-cols-2 gap-3 pt-1">
                          {item.limitations && item.limitations.length > 0 && (
                            <div>
                              <span className="font-semibold text-muted uppercase text-[10px] tracking-wider block mb-1">
                                Analytical Limitations
                              </span>
                              <ul className="list-disc pl-4 space-y-0.5 text-muted text-[11px]">
                                {item.limitations.map((lim, i) => (
                                  <li key={i}>{lim}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {item.counterevidence && item.counterevidence.length > 0 && (
                            <div>
                              <span className="font-semibold text-lichen uppercase text-[10px] tracking-wider block mb-1">
                                Mitigating Facts / Counterevidence
                              </span>
                              <ul className="list-disc pl-4 space-y-0.5 text-ink-soft text-[11px]">
                                {item.counterevidence.map((c, i) => (
                                  <li key={i}>{c}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>

                        {/* Missing Information */}
                        {item.missing_information && item.missing_information.length > 0 && (
                          <div>
                            <span className="font-semibold text-ochre uppercase text-[10px] tracking-wider block mb-1">
                              Identified Missing Information
                            </span>
                            <ul className="list-disc pl-4 space-y-0.5 text-ink-soft text-[11px]">
                              {item.missing_information.map((m, i) => (
                                <li key={i}>{m}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </section>

          {/* Next steps and methodology limitations */}
          <section aria-labelledby="steps-h" className="grid sm:grid-cols-2 gap-6">
            <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-3">
              <h3 id="steps-h" className="text-sm font-bold text-ink">
                Recommended Investigative Next Steps
              </h3>
              <ol className="list-decimal pl-4 space-y-2 text-xs text-ink-soft">
                {result.recommended_next_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>

            <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-3">
              <h3 className="text-sm font-bold text-ink">
                Methodological Safeguards & Limitations
              </h3>
              <ul className="list-disc pl-4 space-y-2 text-xs text-muted">
                {result.methodology_limitations.map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
            </div>
          </section>

          {/* Institutional disclaimer */}
          <div className="rounded-panel border border-rule bg-fog p-4 text-xs text-muted leading-relaxed">
            <span className="font-semibold text-ink-soft">Methodological Disclaimer: </span>
            {result.disclaimer}
          </div>
        </div>
      )}
    </div>
  );
}

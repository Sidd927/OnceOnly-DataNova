import { useEffect, useRef, useState } from "react";
import { X, Search, BookOpen, ChevronDown, ChevronUp } from "lucide-react";
import {
  api,
  type AssessmentRuleDefinition,
  type EvidenceCategory,
  type EvidenceSeverity,
} from "../api";
import {
  CategoryBadge,
  ErrorBox,
  Mono,
  SeverityBadge,
  SourceStageBadge,
  EvidenceStrengthBadge,
} from "./primitives";

export function RulesCatalogModal({
  isOpen,
  onClose,
  initialRuleId,
}: {
  isOpen: boolean;
  onClose: () => void;
  initialRuleId?: string | null;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [rules, setRules] = useState<AssessmentRuleDefinition[]>([]);
  const [version, setVersion] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [expandedRule, setExpandedRule] = useState<string | null>(initialRuleId || null);

  const [prevInitial, setPrevInitial] = useState(initialRuleId);
  if (initialRuleId !== prevInitial) {
    setPrevInitial(initialRuleId);
    setExpandedRule(initialRuleId || null);
    if (initialRuleId) setSearch(initialRuleId);
  }

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.showModal();
      if (rules.length === 0) {
        let active = true;
        api.assessment
          .getRulesCatalog()
          .then((res) => {
            if (active) {
              setRules(res.rules);
              setVersion(res.ruleset_version);
              setLoading(false);
            }
          })
          .catch((e) => {
            if (active) {
              setErr(e);
              setLoading(false);
            }
          });
        return () => {
          active = false;
        };
      }
    } else {
      dialogRef.current?.close();
    }
  }, [isOpen, rules.length]);

  const filteredRules = rules.filter((r) => {
    if (categoryFilter !== "ALL" && r.category !== categoryFilter) return false;
    if (severityFilter !== "ALL" && r.default_severity !== severityFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchId = r.rule_id.toLowerCase().includes(q);
      const matchName = r.name.toLowerCase().includes(q);
      const matchDesc = r.description.toLowerCase().includes(q);
      const matchCat = r.category.toLowerCase().includes(q);
      if (!matchId && !matchName && !matchDesc && !matchCat) return false;
    }
    return true;
  });

  const categories: EvidenceCategory[] = [
    "ALLOCATION_RECONCILIATION",
    "ENTITY_IDENTITY",
    "BENEFICIARY_CONCENTRATION",
    "BATCH_FRAGMENTATION",
    "TEMPORAL_DYNAMICS",
    "CROSS_REGISTRY",
  ];

  const severities: EvidenceSeverity[] = [
    "CRITICAL",
    "HIGH",
    "MODERATE",
    "LOW",
    "INFORMATIONAL",
  ];

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="m-auto h-[90vh] max-h-[850px] w-[95vw] max-w-[1000px] overflow-hidden rounded-sheet border border-rule bg-sheet text-ink shadow-[var(--shadow-float)] backdrop:bg-night/50"
      aria-labelledby="rules-modal-title"
    >
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-rule px-6 py-4 bg-fog/40">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-panel bg-ink text-white">
              <BookOpen size={18} aria-hidden />
            </div>
            <div>
              <h2 id="rules-modal-title" className="text-lg font-bold tracking-tight">
                Deterministic Risk Rules Catalog
              </h2>
              <div className="text-xs text-muted">
                Ruleset Version <Mono className="font-semibold text-ink">{version || "2026.1"}</Mono> · {rules.length} Versioned Evaluation Rules
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="press inline-flex h-9 w-9 items-center justify-center rounded-panel border border-rule-strong hover:bg-fog"
            aria-label="Close dialog"
          >
            <X size={18} aria-hidden />
          </button>
        </div>

        {/* Filters and search */}
        <div className="shrink-0 border-b border-rule bg-sheet p-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-2.5 text-muted" aria-hidden />
              <input
                type="text"
                placeholder="Search by rule ID (e.g. RULE-REC-001), name, or keyword..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-panel border border-rule-strong bg-sheet py-2 pl-9 pr-3 text-sm focus:border-ink focus:outline-none"
              />
            </div>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              aria-label="Filter by category"
              className="rounded-panel border border-rule-strong bg-sheet px-3 py-2 text-sm text-ink-soft focus:border-ink focus:outline-none"
            >
              <option value="ALL">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, " ")}
                </option>
              ))}
            </select>

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              aria-label="Filter by severity"
              className="rounded-panel border border-rule-strong bg-sheet px-3 py-2 text-sm text-ink-soft focus:border-ink focus:outline-none"
            >
              <option value="ALL">All Severities</option>
              {severities.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-wrap items-center justify-between text-xs text-muted">
            <span>
              Showing {filteredRules.length} of {rules.length} rules
            </span>
            <span className="italic">
              Deterministic, mathematical conditions — zero black-box scoring
            </span>
          </div>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          <ErrorBox error={err} title="Could not load rules catalog" />

          {loading && (
            <div className="py-16 text-center text-sm text-muted">
              Loading rules catalog from backend...
            </div>
          )}

          {!loading && filteredRules.length === 0 && (
            <div className="rounded-panel border border-dashed border-rule-strong p-8 text-center text-sm text-muted">
              No rules match your active search filters.
            </div>
          )}

          {!loading &&
            filteredRules.map((rule) => {
              const isExpanded = expandedRule === rule.rule_id;
              return (
                <div
                  key={rule.rule_id}
                  className={`rounded-panel border transition-colors ${
                    isExpanded ? "border-ink bg-sheet shadow-sm" : "border-rule bg-sheet hover:border-rule-strong"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setExpandedRule(isExpanded ? null : rule.rule_id)}
                    className="w-full text-left p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-ink bg-fog px-2 py-0.5 rounded border border-rule">
                          {rule.rule_id}
                        </span>
                        <span className="font-semibold text-sm text-ink">
                          {rule.name}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 pt-0.5">
                        <CategoryBadge category={rule.category} />
                        <SourceStageBadge stage={rule.source_stage} />
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
                      <EvidenceStrengthBadge strength={rule.default_strength} />
                      <SeverityBadge severity={rule.default_severity} />
                      <span className="text-muted">
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </span>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-rule bg-fog/20 p-4 space-y-3 text-xs leading-relaxed">
                      <div>
                        <div className="font-semibold text-ink-soft uppercase tracking-wider text-[10px]">
                          Detection Description
                        </div>
                        <p className="mt-1 text-ink">{rule.description}</p>
                      </div>

                      {rule.rationale && (
                        <div>
                          <div className="font-semibold text-ink-soft uppercase tracking-wider text-[10px]">
                            Methodological Rationale
                          </div>
                          <p className="mt-1 text-ink-soft">{rule.rationale}</p>
                        </div>
                      )}

                      {rule.limitations && rule.limitations.length > 0 && (
                        <div>
                          <div className="font-semibold text-ochre uppercase tracking-wider text-[10px]">
                            Stated Limitations & Caveats
                          </div>
                          <ul className="mt-1 list-disc pl-4 space-y-1 text-ink-soft">
                            {rule.limitations.map((lim, idx) => (
                              <li key={idx}>{lim}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t border-rule bg-fog-2/40 px-6 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="press inline-flex items-center justify-center rounded-panel border border-rule-strong bg-sheet px-4 py-2 text-xs font-semibold hover:border-ink"
          >
            Close Catalog
          </button>
        </div>
      </div>
    </dialog>
  );
}

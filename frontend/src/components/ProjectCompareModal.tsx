import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  X,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import type { CrossRegistryProjectComparison } from "../api";
import {
  EvidenceStrengthBadge,
  ProjectCorrelationCategoryBadge,
} from "./AnalyticalPrimitives";

interface ProjectCompareModalProps {
  comparison: CrossRegistryProjectComparison;
  onClose: () => void;
}

export function ProjectCompareModal({
  comparison,
  onClose,
}: ProjectCompareModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const pA = comparison.project_a;
  const pB = comparison.project_b;

  // Intersecting tokens
  const setA = new Set((comparison.name_tokens_a || []).map((t) => t.toLowerCase()));
  const setB = new Set((comparison.name_tokens_b || []).map((t) => t.toLowerCase()));

  const isCollision =
    comparison.correlation_category === "CROSS_REGISTRY_IDENTIFIER_COLLISION" ||
    (comparison.is_cross_registry && comparison.identifier_match);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Cross-Registry Project Comparison Detail"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4 backdrop-blur-xs overflow-y-auto animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        className="relative my-8 w-full max-w-3xl rounded-sheet border border-rule-strong bg-sheet p-6 shadow-modal space-y-6 max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-rule pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold uppercase text-glacier">
                Investigative Comparison
              </span>
              <span className="text-muted">·</span>
              <ProjectCorrelationCategoryBadge category={comparison.correlation_category} />
              <EvidenceStrengthBadge strength={comparison.evidence_strength} />
            </div>
            <h2 className="text-lg font-bold text-ink mt-1">
              Cross-Registry Pairwise Analysis
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="press rounded-panel p-1.5 text-muted hover:bg-fog hover:text-ink transition-colors"
            aria-label="Close comparison modal"
          >
            <X size={18} aria-hidden />
          </button>
        </div>

        {/* Identifier Collision Safety Banner */}
        {isCollision && (
          <div className="rounded-panel border border-crimson/40 bg-crimson-wash p-4 text-xs space-y-1.5 text-crimson">
            <div className="flex items-center gap-2 font-bold text-sm">
              <ShieldAlert size={16} aria-hidden />
              <span>Independent Namespace Collision Invariant</span>
            </div>
            <p className="leading-relaxed">
              Matching project identifier <strong className="font-mono">"{pA.project_id || pB.project_id}"</strong> detected across{" "}
              <strong>{pA.registry}</strong> and <strong>{pB.registry}</strong>. Because voluntary carbon registries maintain uncoordinated,
              independent numeric ID allocations, identical identifier strings do <em>not</em> prove project identity, dual-listing, or credit duplication.
            </p>
          </div>
        )}

        {/* Side-by-side Project Profiles */}
        <div className="grid sm:grid-cols-2 gap-4">
          {/* Project A */}
          <div className="rounded-panel border border-rule bg-fog-2/30 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-rule/60 pb-2">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-glacier">
                {pA.registry} — Registry A
              </span>
              <span className="font-mono text-xs text-muted">
                ID: <strong>{pA.project_id || "Unspecified"}</strong>
              </span>
            </div>
            <div>
              <div className="text-[11px] font-semibold text-muted uppercase">Project Title</div>
              <div className="text-sm font-semibold text-ink mt-0.5 leading-snug">
                {pA.project_name}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-rule/60 font-mono">
              <div>
                <span className="text-[10px] text-muted block">COUNTRY</span>
                <span className="text-ink font-medium">{pA.country || "Unspecified"}</span>
              </div>
              <div>
                <span className="text-[10px] text-muted block">VINTAGE</span>
                <span className="text-ink font-medium">{pA.vintage || "Unspecified"}</span>
              </div>
            </div>
            {pA.developer && (
              <div className="text-xs pt-1 border-t border-rule/60">
                <span className="text-[10px] font-mono text-muted block uppercase">Developer</span>
                <span className="text-ink font-medium">{pA.developer}</span>
              </div>
            )}
          </div>

          {/* Project B */}
          <div className="rounded-panel border border-rule bg-fog-2/30 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-rule/60 pb-2">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-lichen">
                {pB.registry} — Registry B
              </span>
              <span className="font-mono text-xs text-muted">
                ID: <strong>{pB.project_id || "Unspecified"}</strong>
              </span>
            </div>
            <div>
              <div className="text-[11px] font-semibold text-muted uppercase">Project Title</div>
              <div className="text-sm font-semibold text-ink mt-0.5 leading-snug">
                {pB.project_name}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-rule/60 font-mono">
              <div>
                <span className="text-[10px] text-muted block">COUNTRY</span>
                <span className="text-ink font-medium">{pB.country || "Unspecified"}</span>
              </div>
              <div>
                <span className="text-[10px] text-muted block">VINTAGE</span>
                <span className="text-ink font-medium">{pB.vintage || "Unspecified"}</span>
              </div>
            </div>
            {pB.developer && (
              <div className="text-xs pt-1 border-t border-rule/60">
                <span className="text-[10px] font-mono text-muted block uppercase">Developer</span>
                <span className="text-ink font-medium">{pB.developer}</span>
              </div>
            )}
          </div>
        </div>

        {/* Mathematical Name Similarity Metrics */}
        <div className="rounded-panel border border-rule bg-sheet p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-ink uppercase tracking-wider">
              Deterministic Lexical Metrics
            </span>
            <span className="font-mono text-xs font-semibold text-glacier">
              Formula: 0.40×Set + 0.30×Sort + 0.30×Jaro
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="rounded border border-rule bg-fog/50 p-2.5">
              <span className="text-[10.5px] font-medium text-muted block">Composite Score</span>
              <span className="font-mono text-lg font-bold text-ink">
                {(comparison.name_similarity_score * 100).toFixed(1)}%
              </span>
            </div>
            <div className="rounded border border-rule bg-fog/50 p-2.5">
              <span className="text-[10.5px] font-medium text-muted block">Token Set Ratio</span>
              <span className="font-mono text-lg font-bold text-ink">
                {(comparison.token_set_ratio * 100).toFixed(1)}%
              </span>
            </div>
            <div className="rounded border border-rule bg-fog/50 p-2.5">
              <span className="text-[10.5px] font-medium text-muted block">Token Sort Ratio</span>
              <span className="font-mono text-lg font-bold text-ink">
                {(comparison.token_sort_ratio * 100).toFixed(1)}%
              </span>
            </div>
            <div className="rounded border border-rule bg-fog/50 p-2.5">
              <span className="text-[10.5px] font-medium text-muted block">Jaro-Winkler</span>
              <span className="font-mono text-lg font-bold text-ink">
                {(comparison.jaro_winkler_similarity * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Token Breakdown */}
          <div className="pt-2 space-y-2 border-t border-rule/60 text-xs">
            <span className="text-muted font-medium block">Tokenized Substrings (green highlights shared tokens):</span>
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-mono text-[10px] text-muted uppercase w-14 shrink-0">{pA.registry} Tokens:</span>
                {(comparison.name_tokens_a || []).map((tok, i) => {
                  const isShared = setB.has(tok.toLowerCase());
                  return (
                    <span
                      key={i}
                      className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                        isShared
                          ? "bg-lichen-wash text-lichen border-lichen/40 font-semibold"
                          : "bg-fog text-ink-soft border-rule"
                      }`}
                    >
                      {tok}
                    </span>
                  );
                })}
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-mono text-[10px] text-muted uppercase w-14 shrink-0">{pB.registry} Tokens:</span>
                {(comparison.name_tokens_b || []).map((tok, i) => {
                  const isShared = setA.has(tok.toLowerCase());
                  return (
                    <span
                      key={i}
                      className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                        isShared
                          ? "bg-lichen-wash text-lichen border-lichen/40 font-semibold"
                          : "bg-fog text-ink-soft border-rule"
                      }`}
                    >
                      {tok}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Attribute Correlation Matrix */}
        <div className="rounded-panel border border-rule bg-sheet p-4 space-y-3">
          <span className="font-mono text-xs font-bold text-ink uppercase tracking-wider block">
            Attribute Relation Matrix
          </span>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="rounded border border-rule bg-paper p-2.5">
              <span className="text-muted block text-[10.5px]">Project ID</span>
              <div className="flex items-center gap-1.5 font-mono font-bold mt-1">
                {comparison.identifier_match ? (
                  isCollision ? (
                    <span className="text-crimson flex items-center gap-1">
                      <AlertTriangle size={13} aria-hidden /> Collision
                    </span>
                  ) : (
                    <span className="text-lichen flex items-center gap-1">
                      <CheckCircle2 size={13} aria-hidden /> Match
                    </span>
                  )
                ) : (
                  <span className="text-ink-soft">Independent</span>
                )}
              </div>
            </div>

            <div className="rounded border border-rule bg-paper p-2.5">
              <span className="text-muted block text-[10.5px]">Jurisdiction</span>
              <div className="flex items-center gap-1.5 font-mono font-bold mt-1">
                {comparison.country_relation === "MATCH" && (
                  <span className="text-lichen flex items-center gap-1">
                    <CheckCircle2 size={13} aria-hidden /> Match ({pA.country})
                  </span>
                )}
                {comparison.country_relation === "CONFLICT" && (
                  <span className="text-crimson flex items-center gap-1">
                    <XCircle size={13} aria-hidden /> Conflict
                  </span>
                )}
                {comparison.country_relation === "MISSING" && (
                  <span className="text-muted flex items-center gap-1">
                    <HelpCircle size={13} aria-hidden /> Unlisted
                  </span>
                )}
              </div>
            </div>

            <div className="rounded border border-rule bg-paper p-2.5">
              <span className="text-muted block text-[10.5px]">Vintage Span</span>
              <div className="flex items-center gap-1.5 font-mono font-bold mt-1">
                {comparison.vintage_relation === "OVERLAP" && (
                  <span className="text-lichen flex items-center gap-1">
                    <CheckCircle2 size={13} aria-hidden /> Overlap
                  </span>
                )}
                {comparison.vintage_relation === "ADJACENT" && (
                  <span className="text-glacier flex items-center gap-1">Adjacent</span>
                )}
                {comparison.vintage_relation === "DISJOINT" && (
                  <span className="text-ochre flex items-center gap-1">
                    <AlertTriangle size={13} aria-hidden /> Disjoint
                  </span>
                )}
                {comparison.vintage_relation === "MISSING" && (
                  <span className="text-muted flex items-center gap-1">
                    <HelpCircle size={13} aria-hidden /> Unspecified
                  </span>
                )}
              </div>
            </div>

            <div className="rounded border border-rule bg-paper p-2.5">
              <span className="text-muted block text-[10.5px]">Developer Similarity</span>
              <div className="font-mono font-bold mt-1 text-ink">
                {comparison.developer_similarity != null
                  ? `${(comparison.developer_similarity * 100).toFixed(1)}%`
                  : "Not comparable"}
              </div>
            </div>
          </div>

          {/* Evidence Lists */}
          <div className="grid sm:grid-cols-2 gap-3 pt-2 text-xs">
            {comparison.matching_attributes?.length > 0 && (
              <div className="rounded border border-lichen/30 bg-lichen-wash/40 p-2.5 space-y-1">
                <span className="font-semibold text-lichen flex items-center gap-1">
                  <CheckCircle2 size={13} aria-hidden /> Corroborating Signals
                </span>
                <ul className="list-disc list-inside space-y-0.5 text-ink-soft">
                  {comparison.matching_attributes.map((attr, idx) => (
                    <li key={idx}>{attr}</li>
                  ))}
                </ul>
              </div>
            )}

            {comparison.conflicting_attributes?.length > 0 && (
              <div className="rounded border border-crimson/30 bg-crimson-wash/40 p-2.5 space-y-1">
                <span className="font-semibold text-crimson flex items-center gap-1">
                  <AlertTriangle size={13} aria-hidden /> Contradictory Signals
                </span>
                <ul className="list-disc list-inside space-y-0.5 text-crimson">
                  {comparison.conflicting_attributes.map((attr, idx) => (
                    <li key={idx}>{attr}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Narrative Explanation & Limitations */}
        <div className="space-y-3 text-xs">
          <div className="rounded-panel border border-rule bg-fog-2/30 p-3.5 space-y-1.5">
            <span className="font-mono text-[11px] font-bold text-muted uppercase">
              Investigative Synthesis
            </span>
            <p className="text-ink leading-relaxed font-sans">{comparison.explanation}</p>
          </div>

          <div className="rounded-panel border border-rule bg-sheet p-3.5 space-y-1 text-muted text-[11px] leading-relaxed">
            <span className="font-semibold text-ink-soft block">Analytical Limitations & Caveats:</span>
            <p>{comparison.limitations}</p>
            <p className="pt-1 italic">{comparison.disclaimer}</p>
          </div>
        </div>

        {/* Action Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-rule pt-4">
          <Link
            to={`/assessment?scope=PROJECT&registry=${encodeURIComponent(pA.registry)}&project_id=${encodeURIComponent(pA.project_id || "")}`}
            className="press inline-flex items-center gap-1.5 text-xs font-semibold text-glacier hover:underline"
            onClick={onClose}
          >
            Launch Project Assessment in Risk Console <ArrowRight size={13} aria-hidden />
          </Link>

          <button
            type="button"
            onClick={onClose}
            className="press rounded-panel border border-rule-strong bg-sheet px-4 py-2 text-xs font-semibold text-ink hover:bg-fog transition-colors"
          >
            Close Detail
          </button>
        </div>
      </div>
    </div>
  );
}

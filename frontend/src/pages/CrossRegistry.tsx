import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, AlertTriangle } from "lucide-react";
import {
  api,
  type CrossRegistryRetirementSummary,
  type CrossRegistryProjectComparison,
  fmt,
} from "../api";
import {
  PageHeader,
  SectionHeader,
  ErrorBox,
  MetricTile,
  EvidenceStrengthBadge,
} from "../components/primitives";

export default function CrossRegistry() {
  const [summary, setSummary] = useState<CrossRegistryRetirementSummary | null>(null);
  const [correlations, setCorrelations] = useState<CrossRegistryProjectComparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<unknown>(null);
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(0.5);

  useEffect(() => {
    let alive = true;
    Promise.all([
      api.crossRegistry.getRetirementSummary().catch(() => null),
      api.crossRegistry.getProjectCorrelations({ min_similarity: similarityThreshold, limit: 20 }).catch(() => null),
    ])
      .then(([s, c]) => {
        if (!alive) return;
        if (s) setSummary(s);
        if (c) setCorrelations(c.correlations);
        setLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setErr(e);
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [similarityThreshold]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Cross-Registry Intelligence"
        lede="Identify, correlate, and analyze project listings and entity relationships across Verra VCS and Gold Standard. Investigates potential split credits and dual-registry listings."
      />

      <ErrorBox error={err} title="Could not load cross-registry intelligence" />

      {/* Comparative macro summary */}
      {summary && (
        <section aria-labelledby="macro-h" className="space-y-4">
          <SectionHeader id="macro-h" title="Comparative Voluntary Registry Census" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricTile
              label="Verra VCS Retired Volume"
              value={`${fmt(summary.vcs.total_units)} t`}
              subtext={`${fmt(summary.vcs.total_records)} records across ${fmt(summary.vcs.unique_projects)} projects`}
            />
            <MetricTile
              label="Gold Standard Retired Volume"
              value={`${fmt(summary.gs.total_units)} t`}
              subtext={`${fmt(summary.gs.total_records)} records across ${fmt(summary.gs.unique_projects)} projects`}
            />
            <MetricTile
              label="Shared Geographic Jurisdictions"
              value={summary.shared_countries.length}
              subtext="Overlapping countries hosting projects in both registries"
            />
            <MetricTile
              label="Census Timestamp"
              value="v2026-08"
              subtext="Berkeley Carbon Trading Project (VROD)"
            />
          </div>
        </section>
      )}

      {/* Candidate project correlations */}
      <section aria-labelledby="corr-h" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <SectionHeader
            id="corr-h"
            title="Candidate Project Correlations"
            aside={`Showing top ${correlations.length} candidate pairs`}
          />
          <div className="flex items-center gap-2 text-xs">
            <label className="text-muted font-medium">Min Similarity:</label>
            <select
              value={similarityThreshold}
              onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
              className="rounded-panel border border-rule-strong bg-sheet px-2.5 py-1 text-xs text-ink focus:border-ink focus:outline-none"
            >
              <option value="0.75">High (≥ 0.75)</option>
              <option value="0.50">Moderate (≥ 0.50)</option>
              <option value="0.30">Broad (≥ 0.30)</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-muted">
            Analyzing cross-registry project correlations...
          </div>
        ) : correlations.length === 0 ? (
          <div className="rounded-panel border border-dashed border-rule-strong bg-sheet p-8 text-center text-sm text-muted">
            No cross-registry project pairs meet the selected similarity threshold.
          </div>
        ) : (
          <div className="divide-y divide-rule rounded-sheet border border-rule bg-sheet overflow-hidden">
            {correlations.map((pair, idx) => (
              <div key={idx} className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-fog/20 transition-colors">
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold bg-fog px-2 py-0.5 rounded border border-rule">
                      {pair.category.replace(/_/g, " ")}
                    </span>
                    <EvidenceStrengthBadge strength={pair.evidence_strength} />
                    {pair.collision_warning && (
                      <span className="inline-flex items-center gap-1 rounded bg-crimson-wash border border-crimson/30 px-2 py-0.5 font-mono text-[11px] font-semibold text-crimson" title={pair.collision_warning}>
                        <AlertTriangle size={12} aria-hidden />
                        ID Collision
                      </span>
                    )}
                  </div>

                  <div className="grid sm:grid-cols-2 gap-3 text-xs pt-1">
                    <div className="rounded border border-rule bg-fog-2/30 p-2.5">
                      <span className="font-mono text-[10.5px] font-bold text-muted uppercase">Verra (VCS)</span>
                      <div className="font-semibold text-ink mt-0.5">{pair.project_a.project_name}</div>
                      <div className="font-mono text-muted text-[11px]">ID: {pair.project_a.project_id} · {pair.project_a.country || "Country unlisted"}</div>
                    </div>

                    <div className="rounded border border-rule bg-fog-2/30 p-2.5">
                      <span className="font-mono text-[10.5px] font-bold text-muted uppercase">Gold Standard (GS)</span>
                      <div className="font-semibold text-ink mt-0.5">{pair.project_b.project_name}</div>
                      <div className="font-mono text-muted text-[11px]">ID: {pair.project_b.project_id} · {pair.project_b.country || "Country unlisted"}</div>
                    </div>
                  </div>

                  <p className="text-xs text-ink-soft leading-relaxed pt-1">
                    {pair.explanation}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <div className="text-right">
                    <div className="text-xs text-muted">Name Similarity</div>
                    <div className="font-mono text-xl font-bold text-ink">
                      {(pair.combined_similarity * 100).toFixed(1)}%
                    </div>
                  </div>

                  <Link
                    to={`/assessment?scope=PROJECT&registry=${encodeURIComponent(pair.project_a.registry)}&project_id=${encodeURIComponent(pair.project_a.project_id)}`}
                    className="press inline-flex items-center gap-1 text-xs font-semibold text-glacier hover:underline"
                  >
                    Assess in Console <ArrowRight size={13} aria-hidden />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Activity, Flame } from "lucide-react";
import {
  api,
  type PopulationAnalyticsSummary,
  type TemporalBurstsResponse,
  type TemporalGapsResponse,
  fmt,
  pct,
} from "../api";
import {
  PageHeader,
  SectionHeader,
  ErrorBox,
  Mono,
  MetricTile,
  SeverityBadge,
} from "../components/primitives";

export default function Observatory() {
  const [pop, setPop] = useState<PopulationAnalyticsSummary | null>(null);
  const [bursts, setBursts] = useState<TemporalBurstsResponse | null>(null);
  const [gaps, setGaps] = useState<TemporalGapsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<unknown>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      api.analytics.getPopulationSummary().catch(() => null),
      api.temporal.getBursts({ sensitivity: 3.0, min_history: 5 }).catch(() => null),
      api.temporal.getGaps().catch(() => null),
    ])
      .then(([p, b, g]) => {
        if (!alive) return;
        if (p) setPop(p);
        if (b) setBursts(b);
        if (g) setGaps(g);
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
  }, []);

  const cov = pop?.coverage;
  const conc = pop?.concentration;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Market Analytics & Temporal Observatory"
        lede="Observe market-wide concentration, disclosure transparency, and temporal transaction dynamics across voluntary carbon offset registries."
      />

      <ErrorBox error={err} title="Could not load observatory analytics" />

      {/* Population & Dual-Track Disclosure */}
      {pop && cov && (
        <section aria-labelledby="pop-h" className="space-y-4">
          <SectionHeader
            id="pop-h"
            title="Dual-Track Beneficiary Disclosure Census"
            aside={`${fmt(pop.total_projects)} projects · ${fmt(pop.total_batches)} issuance batches`}
          />

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricTile
              label="Record Disclosure Rate"
              value={pct(cov.record_disclosure_rate)}
              subtext={`${fmt(cov.disclosed_records)} of ${fmt(cov.total_records)} records disclose beneficiaries`}
            />
            <MetricTile
              label="Volume Disclosure Rate"
              value={pct(cov.quantity_disclosure_rate)}
              subtext={`${fmt(cov.disclosed_quantity)} of ${fmt(cov.total_quantity)} tonnes disclosed`}
            />
            <MetricTile
              label="Market Concentration (HHI)"
              value={conc ? fmt(Math.round(conc.hhi)) : "—"}
              subtext={conc ? conc.tier.replace(/_/g, " ") : "Herfindahl-Hirschman Index"}
              token={
                conc?.tier === "HIGH_CONCENTRATION" || conc?.tier === "SINGLE_LABEL_DOMINANCE" ? (
                  <SeverityBadge severity="HIGH" size="sm" />
                ) : (
                  <SeverityBadge severity="INFORMATIONAL" size="sm" />
                )
              }
            />
            <MetricTile
              label="Micro-Claim Ratio"
              value={pop.fragmentation ? pct(pop.fragmentation.micro_claim_ratio) : "—"}
              subtext={pop.fragmentation ? `${fmt(pop.fragmentation.micro_claim_count)} claims under 10 tonnes` : "Interval fragmentation"}
            />
          </div>

          <div className="rounded-panel border border-rule bg-fog-2/40 p-4 text-xs text-muted leading-relaxed">
            <span className="font-semibold text-ink-soft">Dual-Track Transparency Note: </span>
            {cov.classification_definition}
          </div>
        </section>
      )}

      {/* Temporal Anomaly Feeds */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Bursts */}
        <section aria-labelledby="burst-h" className="rounded-sheet border border-rule bg-sheet p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-rule pb-3">
            <div className="flex items-center gap-2">
              <Flame size={18} className="text-crimson" aria-hidden />
              <h3 id="burst-h" className="text-base font-bold text-ink">
                Temporal Liquidation Bursts
              </h3>
            </div>
            {bursts && (
              <span className="font-mono text-xs font-semibold text-muted">
                {bursts.summary.total_bursts} flagged anomaly periods
              </span>
            )}
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-muted">Scanning temporal activity for volume surges...</div>
          ) : !bursts || bursts.bursts.filter((b) => b.is_burst).length === 0 ? (
            <p className="text-xs text-muted py-4">No anomalous liquidation bursts detected at 3.0× MAD sensitivity.</p>
          ) : (
            <div className="divide-y divide-rule max-h-[320px] overflow-y-auto pr-1">
              {bursts.bursts
                .filter((b) => b.is_burst)
                .slice(0, 5)
                .map((b, i) => (
                  <div key={i} className="py-3 flex items-start justify-between gap-3 text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <Mono className="font-bold text-ink">{b.period_label}</Mono>
                        <SeverityBadge severity="HIGH" size="sm" />
                      </div>
                      <div className="text-ink-soft mt-1 leading-snug">{b.explanation}</div>
                      <div className="text-muted font-mono text-[11px] mt-0.5">
                        {fmt(b.units)} t · {fmt(b.records)} records · {b.mad_multiplier.toFixed(1)}× MAD
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </section>

        {/* Gaps */}
        <section aria-labelledby="gap-h" className="rounded-sheet border border-rule bg-sheet p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-rule pb-3">
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-glacier" aria-hidden />
              <h3 id="gap-h" className="text-base font-bold text-ink">
                Reporting Coverage Inactivity
              </h3>
            </div>
            {gaps && (
              <span className="font-mono text-xs font-semibold text-muted">
                {gaps.summary.total_gaps} inactive periods
              </span>
            )}
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-muted">Scanning for coverage blackouts and gaps...</div>
          ) : !gaps || gaps.gaps.length === 0 ? (
            <p className="text-xs text-muted py-4">Continuous reporting coverage observed across calendar periods.</p>
          ) : (
            <div className="divide-y divide-rule max-h-[320px] overflow-y-auto pr-1">
              {gaps.gaps.slice(0, 5).map((g, i) => (
                <div key={i} className="py-3 flex items-start justify-between gap-3 text-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <Mono className="font-bold text-ink">{g.gap_start} to {g.gap_end}</Mono>
                      <span className="rounded bg-fog px-1.5 py-0.5 font-mono text-[10.5px] text-muted border border-rule">
                        {g.gap_duration_days} days
                      </span>
                    </div>
                    <div className="text-ink-soft mt-1 leading-snug">{g.explanation}</div>
                    <div className="text-muted text-[11px] mt-0.5">
                      Prior volume: {fmt(g.prior_units)} t
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

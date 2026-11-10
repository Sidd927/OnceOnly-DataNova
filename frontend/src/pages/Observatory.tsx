import { useEffect, useState } from "react";
import {
  Activity,
  Flame,
  Search,
  CheckCircle2,
  AlertTriangle,
  Info,
  Layers,
  PieChart,
  BarChart2,
} from "lucide-react";
import {
  api,
  type PopulationAnalyticsSummary,
  type CrossRegistryRetirementSummary,
  type BatchAnalyticsResult,
  type TemporalActivityResponse,
  type TemporalTrendsResponse,
  type TemporalBurstsResponse,
  type TemporalGapsResponse,
  type AggregationPeriod,
  fmt,
  pct,
} from "../api";
import {
  PageHeader,
  SectionHeader,
  ErrorBox,
  MetricTile,
  ConcentrationTierBadge,
  BurstTypeBadge,
} from "../components/primitives";
import { LorenzCurveChart } from "../components/LorenzCurveChart";
import { TemporalActivityChart } from "../components/TemporalActivityChart";

type ObservatoryTrack = "census" | "concentration" | "fragmentation" | "temporal";

// Batch inspection presets: identifiers only. Every figure shown after selection comes from
// GET /api/analytics/batches/{registry}/{batch_id}; no metric values are hard-coded here.
const BATCH_PRESETS = [
  {
    label: "VCS 10918",
    desc: "Guanaré forest plantations, Uruguay: many small retail-scale retirements",
    registry: "VCS",
    batchId: "10918",
  },
  {
    label: "GS GS1-1-TR-GS707-21-2016-20993",
    desc: "Landfill gas extraction and electricity generation, Istanbul, Turkey",
    registry: "GS",
    batchId: "GS1-1-TR-GS707-21-2016-20993",
  },
  {
    label: "VCS 5972",
    desc: "Hydroelectric project, Kinnaur District, Himachal Pradesh, India",
    registry: "VCS",
    batchId: "5972",
  },
  {
    label: "GS GS1-1-IN-GS5673-12-2021-22771",
    desc: "Renewable energy power project (DDWL), India",
    registry: "GS",
    batchId: "GS1-1-IN-GS5673-12-2021-22771",
  },
];

export default function Observatory() {
  const [activeTrack, setActiveTrack] = useState<ObservatoryTrack>("census");

  // Track 1 & 2: Population census & concentration
  const [pop, setPop] = useState<PopulationAnalyticsSummary | null>(null);
  const [registrySummary, setRegistrySummary] = useState<CrossRegistryRetirementSummary | null>(null);
  const [popErr, setPopErr] = useState<unknown>(null);

  // Track 3: Batch Fragmentation Explorer State
  const [batchRegistry, setBatchRegistry] = useState<string>("VCS");
  const [batchIdInput, setBatchIdInput] = useState<string>("10918");
  const [batchData, setBatchData] = useState<BatchAnalyticsResult | null>(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchErr, setBatchErr] = useState<unknown>(null);

  // Track 4: Temporal Activity State
  const [temporalPeriod, setTemporalPeriod] = useState<AggregationPeriod>("monthly");
  const [activityData, setActivityData] = useState<TemporalActivityResponse | null>(null);
  const [trendsData, setTrendsData] = useState<TemporalTrendsResponse | null>(null);
  const [burstsData, setBurstsData] = useState<TemporalBurstsResponse | null>(null);
  const [gapsData, setGapsData] = useState<TemporalGapsResponse | null>(null);
  const [temporalLoading, setTemporalLoading] = useState(true);
  const [temporalErr, setTemporalErr] = useState<unknown>(null);

  // Temporal filters
  const [tempRegistryFilter, setTempRegistryFilter] = useState<string>("");
  const [tempStartDate, setTempStartDate] = useState<string>("");
  const [tempEndDate, setTempEndDate] = useState<string>("");

  // Load initial population summary and registry census
  useEffect(() => {
    let alive = true;
    // Each request reports its own failure; a failed request never leaves the page silently empty.
    api.analytics
      .getPopulationSummary()
      .then((p) => { if (alive) setPop(p); })
      .catch((e) => { if (alive) setPopErr(e); });
    api.crossRegistry
      .getRetirementSummary()
      .then((r) => { if (alive) setRegistrySummary(r); })
      .catch((e) => { if (alive) setPopErr((prev: unknown) => prev ?? e); });
    return () => {
      alive = false;
    };
  }, []);

  // Fetch initial batch (VCS 10918)
  useEffect(() => {
    let alive = true;
    api.analytics
      .getBatchAnalytics("VCS", "10918")
      .then((b) => {
        if (!alive) return;
        setBatchData(b);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // Fetch temporal feeds when temporal parameters change
  useEffect(() => {
    let alive = true;
    Promise.all([
      api.temporal.getActivity({
        period: temporalPeriod,
        registry: tempRegistryFilter || undefined,
        start_date: tempStartDate || undefined,
        end_date: tempEndDate || undefined,
      }).catch(() => null),
      api.temporal.getTrends({
        period: temporalPeriod,
        registry: tempRegistryFilter || undefined,
        start_date: tempStartDate || undefined,
        end_date: tempEndDate || undefined,
      }).catch(() => null),
      api.temporal.getBursts({
        period: temporalPeriod,
        registry: tempRegistryFilter || undefined,
        sensitivity: 3.0,
        min_history: 5,
      }).catch(() => null),
      api.temporal.getGaps({
        period: temporalPeriod,
        registry: tempRegistryFilter || undefined,
      }).catch(() => null),
    ])
      .then(([act, tr, bu, ga]) => {
        if (!alive) return;
        if (act) setActivityData(act);
        if (tr) setTrendsData(tr);
        if (bu) setBurstsData(bu);
        if (ga) setGapsData(ga);
        setTemporalLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setTemporalErr(e);
        setTemporalLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [temporalPeriod, tempRegistryFilter, tempStartDate, tempEndDate]);

  // Handle batch inspection search
  const handleInspectBatch = async (reg: string, bId: string) => {
    if (!bId.trim()) return;
    setBatchLoading(true);
    setBatchErr(null);
    try {
      const res = await api.analytics.getBatchAnalytics(reg, bId.trim());
      setBatchData(res);
    } catch (e) {
      setBatchErr(e);
    } finally {
      setBatchLoading(false);
    }
  };

  const cov = pop?.coverage;
  const conc = pop?.overall_concentration;

  // Sorted top disclosed beneficiaries
  const topBeneficiaries = conc?.disclosed_shares
    ? Object.entries(conc.disclosed_shares)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
    : [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Market Population & Temporal Dynamics Observatory"
        lede="Beneficiary concentration, disclosure coverage, batch fragmentation and retirement timing, computed live from real Verra and Gold Standard retirement records in the committed demo subset. The figures describe this sample, not the whole voluntary carbon market."
      />

      <ErrorBox error={popErr} title="Could not load population intelligence" />

      {/* Top Track Navigation Bar */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-rule pb-3">
        <SectionHeader
          id="observatory-tracks-h"
          title="Observatory Intelligence Feeds"
          aside={pop ? `Computed live from ${fmt(pop.total_retirement_records)} retirement records in the demo reference subset` : undefined}
        />

        <div
          role="tablist"
          aria-label="Observatory Feeds"
          className="inline-flex max-w-full flex-wrap xl:flex-nowrap xl:shrink-0 rounded-panel border border-rule-strong bg-fog p-0.5 text-xs font-semibold"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTrack === "census"}
            onClick={() => setActiveTrack("census")}
            className={`press rounded-[5px] px-3.5 py-1.5 transition-colors flex items-center gap-1.5 ${
              activeTrack === "census"
                ? "bg-sheet text-ink shadow-sm"
                : "text-muted hover:text-ink"
            }`}
          >
            <BarChart2 size={13} aria-hidden />
            Population Census
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTrack === "concentration"}
            onClick={() => setActiveTrack("concentration")}
            className={`press rounded-[5px] px-3.5 py-1.5 transition-colors flex items-center gap-1.5 ${
              activeTrack === "concentration"
                ? "bg-sheet text-ink shadow-sm"
                : "text-muted hover:text-ink"
            }`}
          >
            <PieChart size={13} aria-hidden />
            Concentration & Lorenz
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTrack === "fragmentation"}
            onClick={() => setActiveTrack("fragmentation")}
            className={`press rounded-[5px] px-3.5 py-1.5 transition-colors flex items-center gap-1.5 ${
              activeTrack === "fragmentation"
                ? "bg-sheet text-ink shadow-sm"
                : "text-muted hover:text-ink"
            }`}
          >
            <Layers size={13} aria-hidden />
            Batch Fragmentation
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTrack === "temporal"}
            onClick={() => setActiveTrack("temporal")}
            className={`press rounded-[5px] px-3.5 py-1.5 transition-colors flex items-center gap-1.5 ${
              activeTrack === "temporal"
                ? "bg-sheet text-ink shadow-sm"
                : "text-muted hover:text-ink"
            }`}
          >
            <Activity size={13} aria-hidden />
            Temporal Dynamics
          </button>
        </div>
      </div>

      {/* ============================================================== */}
      {/* TRACK 1: POPULATION CENSUS & DUAL-TRACK DISCLOSURE              */}
      {/* ============================================================== */}
      {activeTrack === "census" && pop && cov && (
        <div className="space-y-6 animate-fade-in">
          {/* Key Macro Census Metrics */}
          <section aria-labelledby="census-metrics-h" className="space-y-4">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricTile
                label="Retirement Population Volume"
                value={`${fmt(pop.total_retirement_quantity)} t`}
                subtext={`Across ${fmt(pop.total_retirement_records)} validated retirement transactions`}
              />
              <MetricTile
                label="Issuance Batches Surveyed"
                value={fmt(pop.total_batches)}
                subtext={`${fmt(pop.multi_record_batches)} multi-claimant · ${fmt(pop.single_record_batches)} single-claimant`}
              />
              <MetricTile
                label="Beneficiary Record Disclosure"
                value={pct(cov.record_disclosure_rate)}
                subtext={`${fmt(cov.disclosed_records)} records disclose beneficiary labels`}
              />
              <MetricTile
                label="Beneficiary Volume Disclosure"
                value={pct(cov.quantity_disclosure_rate)}
                subtext={`${fmt(cov.disclosed_quantity)} tonnes attributed to identified buyers`}
              />
            </div>
          </section>

          {/* Registry-Level Volume Breakdown */}
          {registrySummary && (
            <section aria-labelledby="reg-breakdown-h" className="space-y-3">
              <SectionHeader
                id="reg-breakdown-h"
                title="Registry-Level Population Breakdown"
                aside="Retirement events only; issuance records are excluded from every denominator"
              />
              <div className="grid sm:grid-cols-2 gap-4">
                {/* Verra VCS */}
                <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-3">
                  <div className="flex items-center justify-between border-b border-rule pb-2">
                    <span className="font-mono text-xs font-bold text-glacier uppercase">
                      Verra (VCS) Registry Population
                    </span>
                    <span className="font-mono text-xs font-bold text-ink">
                      {fmt(registrySummary.registries.VCS?.total_retired_tonnes ?? 0)} t
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 font-mono text-xs">
                    <div>
                      <span className="text-[10px] text-muted block">RECORDS</span>
                      <span className="font-bold text-ink">{fmt(registrySummary.registries.VCS?.total_retirement_records ?? 0)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted block">PROJECTS</span>
                      <span className="font-bold text-ink">{registrySummary.registries.VCS?.active_projects_count ?? 0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted block">DISCLOSURE RATE</span>
                      <span className="font-bold text-glacier">
                        {pct((registrySummary.registries.VCS?.beneficiary_record_disclosure_rate_pct ?? 0) / 100)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Gold Standard */}
                <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-3">
                  <div className="flex items-center justify-between border-b border-rule pb-2">
                    <span className="font-mono text-xs font-bold text-lichen uppercase">
                      Gold Standard (GS) Registry Population
                    </span>
                    <span className="font-mono text-xs font-bold text-ink">
                      {fmt(registrySummary.registries.GS?.total_retired_tonnes ?? 0)} t
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 font-mono text-xs">
                    <div>
                      <span className="text-[10px] text-muted block">RECORDS</span>
                      <span className="font-bold text-ink">{fmt(registrySummary.registries.GS?.total_retirement_records ?? 0)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted block">PROJECTS</span>
                      <span className="font-bold text-ink">{registrySummary.registries.GS?.active_projects_count ?? 0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted block">DISCLOSURE RATE</span>
                      <span className="font-bold text-lichen">
                        {pct((registrySummary.registries.GS?.beneficiary_record_disclosure_rate_pct ?? 0) / 100)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Dual-Track Beneficiary Classification Breakdown */}
          <section aria-labelledby="dual-track-h" className="rounded-sheet border border-rule bg-sheet p-5 sm:p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rule pb-3">
              <div>
                <h3 id="dual-track-h" className="text-base font-bold text-ink">
                  Dual-Track Beneficiary Disclosure Census
                </h3>
                <p className="text-xs text-ink-soft mt-0.5">
                  Four-tier syntactic taxonomy distinguishing non-placeholder disclosed entities from unpopulated and placeholder records.
                </p>
              </div>
              <span className="font-mono text-xs font-semibold px-2.5 py-1 rounded bg-fog border border-rule text-ink">
                Unresolved Identity: {pct(cov.quantity_unresolved_rate)} of volume
              </span>
            </div>

            <div className="grid sm:grid-cols-3 gap-4 text-xs font-mono">
              <div className="rounded-panel border border-lichen/40 bg-lichen-wash/30 p-3.5 space-y-1">
                <span className="font-bold text-lichen block text-[11px] uppercase">
                  Non-Placeholder Disclosed
                </span>
                <div className="text-lg font-bold text-ink">{fmt(cov.disclosed_records)} records</div>
                <div className="text-muted text-[11px]">{fmt(cov.disclosed_quantity)} t ({pct(cov.quantity_disclosure_rate)})</div>
              </div>

              <div className="rounded-panel border border-ochre/40 bg-ochre-wash/30 p-3.5 space-y-1">
                <span className="font-bold text-ochre block text-[11px] uppercase">
                  Explicitly Undisclosed
                </span>
                <div className="text-lg font-bold text-ink">{fmt(cov.explicitly_undisclosed_records)} records</div>
                <div className="text-muted text-[11px]">{fmt(cov.explicitly_undisclosed_quantity)} t ({pct(cov.explicitly_undisclosed_quantity / cov.total_quantity)})</div>
              </div>

              <div className="rounded-panel border border-crimson/40 bg-crimson-wash/30 p-3.5 space-y-1">
                <span className="font-bold text-crimson block text-[11px] uppercase">
                  Invalid or Placeholder
                </span>
                <div className="text-lg font-bold text-ink">{fmt(cov.invalid_placeholder_records)} records</div>
                <div className="text-muted text-[11px]">{fmt(cov.invalid_placeholder_quantity)} t ({pct(cov.invalid_placeholder_quantity / cov.total_quantity)})</div>
              </div>
            </div>

            {/* Mandatory Transparency Caveat */}
            <div className="rounded-panel border border-rule bg-fog-2/40 p-3.5 text-xs text-muted leading-relaxed space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-ink-soft">
                <Info size={13} className="text-glacier" aria-hidden />
                <span>Methodological Principle — Disclosure Field Presence</span>
              </div>
              <p>{cov.classification_definition}</p>
              <p className="text-[11px] italic pt-1">
                Note: Disclosure-field presence indicates populated metadata in registry filings and does not establish verified corporate identity, legal entity status, or end-beneficiary claim entitlement.
              </p>
            </div>
          </section>
        </div>
      )}

      {/* ============================================================== */}
      {/* TRACK 2: BENEFICIARY CONCENTRATION & LORENZ CURVE               */}
      {/* ============================================================== */}
      {activeTrack === "concentration" && pop && conc && (
        <div className="space-y-6 animate-fade-in">
          {/* Concentration Index Tiles */}
          <section aria-labelledby="conc-tiles-h" className="space-y-4">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricTile
                label="Herfindahl-Hirschman Index (HHI)"
                value={fmt(Math.round(conc.hhi_disclosed))}
                subtext={`Scale 0–10,000 · ${fmt(conc.unique_disclosed_beneficiaries)} distinct disclosed labels (not resolved to legal entities)`}
                token={<ConcentrationTierBadge tier={conc.tier} />}
              />
              <MetricTile
                label="Largest Disclosed Label"
                value={pct(conc.dominant_disclosed_share)}
                subtext={conc.dominant_disclosed_beneficiary || "None"}
              />
              <MetricTile
                label="Combined Top 3 Share"
                value={pct(conc.top3_disclosed_share)}
                subtext="Share of disclosed volume held by the 3 largest labels"
              />
              <MetricTile
                label="Shannon Equitability"
                value={conc.entropy_normalized.toFixed(3)}
                subtext={`Base-2 entropy: ${conc.entropy_shannon_disclosed.toFixed(2)} bits`}
              />
            </div>
          </section>

          {/* Inequality Distinction: Pooled Gini vs Across-Batch Mean Gini */}
          <section aria-labelledby="gini-distinction-h" className="rounded-sheet border border-rule bg-sheet p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-rule pb-2">
              <h3 id="gini-distinction-h" className="text-sm font-bold text-ink">
                Inequality Duality: Portfolio Pooled Gini vs Across-Batch Mean Gini
              </h3>
              <span className="font-mono text-xs font-semibold text-glacier">
                Stage 1 Mathematical Foundation
              </span>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 text-xs font-mono">
              <div className="rounded-panel border border-glacier/30 bg-glacier-wash/20 p-4 space-y-1">
                <span className="text-[11px] font-bold text-glacier uppercase block">
                  Pooled Allocation Gini (Macro Inequality)
                </span>
                <div className="text-2xl font-bold text-ink">{pop.pooled_allocation_gini.toFixed(4)}</div>
                <p className="text-muted text-[11px] leading-snug">
                  Measures overall credit sizing inequality across all <strong>{fmt(pop.pooled_allocation_count)}</strong> credit allocations in the voluntary registry portfolio (mean size: {fmt(pop.pooled_allocation_mean_size)} t).
                </p>
              </div>

              <div className="rounded-panel border border-lichen/30 bg-lichen-wash/20 p-4 space-y-1">
                <span className="text-[11px] font-bold text-lichen uppercase block">
                  Across-Batch Mean Gini (Micro Uniformity)
                </span>
                <div className="text-2xl font-bold text-ink">
                  {typeof pop.batch_gini_distribution?.mean === "number" ? pop.batch_gini_distribution.mean.toFixed(4) : <span className="text-base text-muted">Unavailable</span>}
                </div>
                <p className="text-muted text-[11px] leading-snug">
                  Reports the average of within-batch Gini coefficients across all <strong>{fmt(pop.total_batches)}</strong> issuance batches, measuring allocation uniformity within individual project distributions.
                </p>
              </div>
            </div>

            <div className="rounded-panel border border-rule bg-fog-2/40 p-3 text-xs text-muted leading-relaxed">
              <span className="font-semibold text-ink-soft">Mathematical Interpretation: </span>
              {pop.batch_gini_interpretation}
            </div>
          </section>

          {/* Bespoke Lorenz Curve Component */}
          {conc.disclosed_shares && (
            <LorenzCurveChart
              shares={conc.disclosed_shares}
              title="Disclosed Beneficiary Lorenz Curve"
              subtitle={`Cumulative share of ${fmt(conc.unique_disclosed_beneficiaries)} disclosed beneficiary labels against cumulative share of disclosed retired volume (${fmt(conc.disclosed_units)} t). Undisclosed volume is excluded. The Gini shown is computed from this plotted distribution; it is not the pooled allocation Gini above.`}
            />
          )}

          {/* Top 10 Disclosed Beneficiaries Ranking Table */}
          <section aria-labelledby="top-ten-h" className="rounded-sheet border border-rule bg-sheet overflow-hidden">
            <div className="px-5 py-3 bg-fog border-b border-rule flex items-center justify-between">
              <h3 id="top-ten-h" className="text-xs font-mono font-bold text-ink uppercase">
                Top Disclosed Beneficiaries by Claimed Volume
              </h3>
              <span className="text-xs text-muted">
                Showing top 10 of {conc.unique_disclosed_beneficiaries} disclosed entities
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-fog-2/60 text-muted text-[11px] border-b border-rule">
                  <tr>
                    <th className="px-4 py-2 w-12 text-center">Rank</th>
                    <th className="px-4 py-2">Beneficiary Label</th>
                    <th className="px-4 py-2 text-right">Disclosed Share</th>
                    <th className="px-4 py-2 text-right">Estimated Volume</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule">
                  {topBeneficiaries.map(([name, share], idx) => (
                    <tr key={idx} className="hover:bg-fog/30">
                      <td className="px-4 py-2 text-center text-muted font-bold">{idx + 1}</td>
                      <td className="px-4 py-2 font-semibold text-ink">{name}</td>
                      <td className="px-4 py-2 text-right text-glacier font-bold">{pct(share, 2)}</td>
                      <td className="px-4 py-2 text-right text-ink">
                        {fmt(Math.round(share * conc.disclosed_units))} t
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-3 bg-fog-2/20 border-t border-rule text-[11px] text-muted italic">
              {conc.disclaimer}
            </div>
          </section>
        </div>
      )}

      {/* ============================================================== */}
      {/* TRACK 3: BATCH FRAGMENTATION EXPLORER                           */}
      {/* ============================================================== */}
      {activeTrack === "fragmentation" && (
        <div className="space-y-6 animate-fade-in">
          {/* Batch Selector & Presets */}
          <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-rule pb-3">
              <div>
                <h3 className="text-sm font-bold text-ink">Batch Fragmentation & Interval Structure Inspector</h3>
                <p className="text-xs text-ink-soft mt-0.5">
                  Inspect credit tranche sizing, absolute micro-claims, and interval overlap collision structures for any issuance batch.
                </p>
              </div>
            </div>

            {/* Demonstration Presets */}
            <div className="space-y-2">
              <span className="font-mono text-xs font-bold text-muted uppercase">
                Demonstration Presets:
              </span>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {BATCH_PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setBatchRegistry(p.registry);
                      setBatchIdInput(p.batchId);
                      handleInspectBatch(p.registry, p.batchId);
                    }}
                    className="press rounded-panel border border-rule bg-fog-2/40 p-3 text-left hover:border-ink hover:bg-fog transition-colors space-y-1"
                  >
                    <div className="font-semibold text-xs text-ink">{p.label}</div>
                    <p className="text-[11px] text-muted leading-snug">{p.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Manual Batch Search Form */}
            <div className="pt-2 flex flex-wrap items-center gap-3">
              <select
                value={batchRegistry}
                onChange={(e) => setBatchRegistry(e.target.value)}
                className="rounded border border-rule-strong bg-paper px-3 py-1.5 text-xs font-mono font-bold text-ink"
              >
                <option value="VCS">VCS (Verra)</option>
                <option value="GS">GS (Gold Standard)</option>
              </select>

              <input
                type="text"
                placeholder="Batch ID (e.g. 10918)..."
                value={batchIdInput}
                onChange={(e) => setBatchIdInput(e.target.value)}
                className="flex-1 min-w-[200px] rounded border border-rule-strong bg-paper px-3 py-1.5 text-xs font-mono text-ink"
              />

              <button
                type="button"
                onClick={() => handleInspectBatch(batchRegistry, batchIdInput)}
                disabled={batchLoading || !batchIdInput.trim()}
                className="press inline-flex items-center gap-1.5 rounded-panel bg-ink px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#0b2429] disabled:opacity-40"
              >
                <Search size={13} aria-hidden />
                {batchLoading ? "Analyzing..." : "Inspect Batch"}
              </button>
            </div>
          </div>

          <ErrorBox error={batchErr} title="Could not inspect batch" />

          {/* Inspected Batch Results */}
          {batchData && (
            <div className="space-y-6">
              {/* Batch Metadata Header */}
              <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule pb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-glacier-wash text-glacier border border-glacier/30 uppercase">
                      {batchData.registry} · Batch {batchData.batch_id}
                    </span>
                    <span className="text-muted">·</span>
                    <span className="text-xs text-ink font-semibold">{batchData.country || "Jurisdiction unlisted"}</span>
                    <span className="text-muted">·</span>
                    <span className="font-mono text-xs text-muted">Vintage {batchData.vintage || "—"}</span>
                  </div>

                  <div className="font-mono text-xs font-bold text-ink">
                    Total Volume: {fmt(batchData.total_quantity)} t ({fmt(batchData.total_events)} events)
                  </div>
                </div>

                <div className="text-sm font-semibold text-ink">
                  {batchData.project_name || "Project title unlisted"}
                </div>
              </div>

              {/* Statistical Fragmentation & Micro-Claims Tiles */}
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricTile
                  label="Within-Batch Gini Coefficient"
                  value={batchData.fragmentation.gini_coefficient.toFixed(4)}
                  subtext={`Finite-sample corrected: ${batchData.fragmentation.gini_sample_corrected.toFixed(4)}`}
                />
                <MetricTile
                  label="Median Allocation Size"
                  value={`${fmt(batchData.fragmentation.median_event_size)} t`}
                  subtext={`Mean: ${fmt(batchData.fragmentation.mean_event_size)} t (IQR: ${fmt(batchData.fragmentation.iqr_event_size)} t)`}
                />
                <MetricTile
                  label="Absolute Micro-Claims (≤ 10 t)"
                  value={fmt(batchData.fragmentation.micro_claim_count)}
                  subtext={`${pct(batchData.fragmentation.micro_claim_record_share)} of records · ${pct(batchData.fragmentation.micro_claim_quantity_share)} of volume`}
                />
                <MetricTile
                  label="Relative Small Tranches (≤ 1%)"
                  value={fmt(batchData.fragmentation.small_tranche_count)}
                  subtext={`Threshold: ${fmt(batchData.fragmentation.small_tranche_threshold_used)} t (1% of batch)`}
                />
              </div>

              {/* Threshold Definition Callout */}
              <div className="grid sm:grid-cols-2 gap-4 text-xs font-mono">
                <div className="rounded-panel border border-rule bg-fog-2/30 p-4 space-y-1">
                  <span className="font-bold text-ink uppercase block text-[11px]">
                    Absolute Micro-Claim Standard (≤ 10.0 Tonnes)
                  </span>
                  <p className="text-muted text-[11px] leading-relaxed">
                    Identifies de minimis retail or consumer transactions fixed at an absolute volume threshold regardless of batch size. High micro-claim counts indicate retail offset fragmentation.
                  </p>
                </div>

                <div className="rounded-panel border border-rule bg-fog-2/30 p-4 space-y-1">
                  <span className="font-bold text-ink uppercase block text-[11px]">
                    Relative Small Allocation Standard (≤ 1.0% of Batch)
                  </span>
                  <p className="text-muted text-[11px] leading-relaxed">
                    Evaluates transactions scaled relative to total batch size. Accounts for batch scale variances, flagging allocations disproportionately small relative to total project issuance.
                  </p>
                </div>
              </div>

              {/* Interval Structure & Validation Matrix */}
              {batchData.fragmentation.intervals && (
                <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-3">
                  <div className="flex items-center justify-between border-b border-rule pb-2">
                    <span className="font-mono text-xs font-bold text-ink uppercase">
                      Batch Interval Topology & Integrity Check
                    </span>
                    <span className="font-mono text-xs text-muted">
                      {batchData.fragmentation.intervals.total_intervals} Allocation Intervals
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="rounded border border-rule bg-paper p-2.5">
                      <span className="text-muted text-[10.5px] block">Density</span>
                      <span className="font-bold text-ink mt-0.5 block">
                        {pct(batchData.fragmentation.intervals.interval_density)}
                      </span>
                    </div>

                    <div className="rounded border border-rule bg-paper p-2.5">
                      <span className="text-muted text-[10.5px] block">Contiguous Blocks</span>
                      <span className="font-bold text-lichen mt-0.5 block">
                        {fmt(batchData.fragmentation.intervals.contiguous_intervals_count)}
                      </span>
                    </div>

                    <div className="rounded border border-rule bg-paper p-2.5">
                      <span className="text-muted text-[10.5px] block">Disjoint Gaps</span>
                      <span className="font-bold text-ink mt-0.5 block">
                        {fmt(batchData.fragmentation.intervals.disjoint_gaps_count)}
                      </span>
                    </div>

                    <div className="rounded border border-rule bg-paper p-2.5">
                      <span className="text-muted text-[10.5px] block">Overlapping Intervals</span>
                      <span className="font-bold mt-0.5 block">
                        {batchData.fragmentation.intervals.overlapping_intervals_count === 0 ? (
                          <span className="text-lichen flex items-center gap-1">
                            <CheckCircle2 size={13} aria-hidden /> 0 Overlaps
                          </span>
                        ) : (
                          <span className="text-crimson flex items-center gap-1">
                            <AlertTriangle size={13} aria-hidden /> {batchData.fragmentation.intervals.overlapping_intervals_count} Conflicts
                          </span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Batch-Level Lorenz Curve */}
              {batchData.concentration.disclosed_shares && Object.keys(batchData.concentration.disclosed_shares).length > 1 && (
                <LorenzCurveChart
                  shares={batchData.concentration.disclosed_shares}
                  title={`Batch ${batchData.batch_id} Disclosed Beneficiary Lorenz Curve`}
                  subtitle={`Disclosed volume across ${batchData.fragmentation.distinct_disclosed_beneficiaries} disclosed beneficiary labels in this batch. The Gini shown is computed from this plotted distribution; the allocation-size Gini above covers every retirement event in the batch.`}
                  label={`Batch ${batchData.batch_id}`}
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TRACK 4: TEMPORAL DYNAMICS, VELOCITY BURSTS & GAPS             */}
      {/* ============================================================== */}
      {activeTrack === "temporal" && (
        <div className="space-y-6 animate-fade-in">
          {/* Temporal Filter Bar */}
          <div className="rounded-sheet border border-rule bg-sheet p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <span className="font-mono text-xs font-bold text-ink uppercase">
                Temporal Filtering Parameters:
              </span>

              <div className="flex flex-wrap items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5">
                  <label className="text-muted font-medium">Registry:</label>
                  <select
                    value={tempRegistryFilter}
                    onChange={(e) => setTempRegistryFilter(e.target.value)}
                    className="rounded border border-rule bg-paper px-2 py-1 font-mono text-xs text-ink"
                  >
                    <option value="">All Registries</option>
                    <option value="VCS">Verra (VCS)</option>
                    <option value="GS">Gold Standard (GS)</option>
                  </select>
                </div>

                <div className="flex items-center gap-1.5">
                  <label className="text-muted font-medium">Start Date:</label>
                  <input
                    type="date"
                    value={tempStartDate}
                    onChange={(e) => setTempStartDate(e.target.value)}
                    className="rounded border border-rule bg-paper px-2 py-1 font-mono text-xs text-ink"
                  />
                </div>

                <div className="flex items-center gap-1.5">
                  <label className="text-muted font-medium">End Date:</label>
                  <input
                    type="date"
                    value={tempEndDate}
                    onChange={(e) => setTempEndDate(e.target.value)}
                    className="rounded border border-rule bg-paper px-2 py-1 font-mono text-xs text-ink"
                  />
                </div>

                {(tempRegistryFilter || tempStartDate || tempEndDate) && (
                  <button
                    type="button"
                    onClick={() => {
                      setTempRegistryFilter("");
                      setTempStartDate("");
                      setTempEndDate("");
                    }}
                    className="press text-xs text-glacier font-semibold hover:underline"
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            </div>
          </div>

          <ErrorBox error={temporalErr} title="Could not load temporal feeds" />

          {/* Bespoke Interactive SVG Activity Chart */}
          {activityData && (
            <TemporalActivityChart
              activityPeriods={activityData.periods}
              trendPeriods={trendsData?.trends}
              currentPeriod={temporalPeriod}
              onPeriodChange={(p) => setTemporalPeriod(p)}
              isLoading={temporalLoading}
            />
          )}

          {/* Temporal Anomaly Feeds: Bursts & Inactivity Gaps */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Bursts Inspector */}
            <section aria-labelledby="bursts-h" className="rounded-sheet border border-rule bg-sheet p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between border-b border-rule pb-3">
                <div className="flex items-center gap-2">
                  <Flame size={18} className="text-crimson" aria-hidden />
                  <h3 id="bursts-h" className="text-base font-bold text-ink">
                    MAD-Based Liquidation Bursts
                  </h3>
                </div>
                {burstsData && (
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-crimson-wash text-crimson border border-crimson/30">
                    {burstsData.burst_periods_count} Anomaly Periods Detected
                  </span>
                )}
              </div>

              <p className="text-xs text-ink-soft leading-relaxed">
                Flags periods where retirement volume or transaction counts exceed <strong>3.0× Median Absolute Deviation (MAD)</strong> over a 12-period moving baseline.
              </p>

              {burstsData && burstsData.bursts.filter((b) => b.is_burst).length > 0 ? (
                <div className="divide-y divide-rule max-h-[360px] overflow-y-auto pr-1">
                  {burstsData.bursts
                    .filter((b) => b.is_burst)
                    .map((b, idx) => (
                      <div key={idx} className="py-3 flex items-start justify-between gap-3 text-xs">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-ink">{b.period_label}</span>
                            <BurstTypeBadge burstType={b.burst_type} />
                          </div>
                          <p className="text-ink-soft leading-snug">{b.explanation}</p>
                          <div className="font-mono text-[11px] text-muted">
                            Observed: <strong className="text-glacier">{fmt(b.observed_tonnes)} t</strong> ({fmt(b.observed_records)} rec) · Baseline: {fmt(b.baseline_median_tonnes)} t
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-muted">
                  No anomalous transaction surges detected at current threshold parameters.
                </div>
              )}

              <div className="rounded-panel border border-rule bg-fog-2/30 p-3 text-[11px] text-muted leading-relaxed">
                <span className="font-semibold text-ink-soft block">Analytical Caveat:</span>
                Statistical bursts reflect dispersion anomalies relative to moving baselines and do NOT constitute evidence of fraud, double-counting, or regulatory non-compliance.
              </div>
            </section>

            {/* Zero-Activity Gaps Inspector */}
            <section aria-labelledby="gaps-h" className="rounded-sheet border border-rule bg-sheet p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between border-b border-rule pb-3">
                <div className="flex items-center gap-2">
                  <Activity size={18} className="text-glacier" aria-hidden />
                  <h3 id="gaps-h" className="text-base font-bold text-ink">
                    Reporting Inactivity Intervals
                  </h3>
                </div>
                {gapsData && (
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-fog border border-rule text-ink">
                    {gapsData.total_gaps_count} Gaps (Mean: {gapsData.mean_gap_duration_days} days)
                  </span>
                )}
              </div>

              <p className="text-xs text-ink-soft leading-relaxed">
                Monitors calendar intervals with zero recorded retirement transactions, tracking blackout spans between active events.
              </p>

              {gapsData && gapsData.gaps.length > 0 ? (
                <div className="divide-y divide-rule max-h-[360px] overflow-y-auto pr-1">
                  {gapsData.gaps.map((g, idx) => (
                    <div key={idx} className="py-3 flex items-start justify-between gap-3 text-xs font-mono">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-ink">{g.gap_start} to {g.gap_end}</span>
                          <span className="px-2 py-0.5 rounded bg-fog border border-rule text-muted text-[10.5px]">
                            {g.gap_duration_days} days
                          </span>
                        </div>
                        <p className="font-sans text-ink-soft text-[11px] leading-snug">
                          {g.coverage_limitation_note}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-muted">
                  Continuous reporting activity observed across calendar periods.
                </div>
              )}

              <div className="rounded-panel border border-rule bg-fog-2/30 p-3 text-[11px] text-muted leading-relaxed">
                <span className="font-semibold text-ink-soft block">Coverage Boundary Caveat:</span>
                Zero observed records reflects transactions within the ingested project dataset and does NOT establish market-wide dormancy, missing data, or lack of secondary transactions outside this registry.
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}

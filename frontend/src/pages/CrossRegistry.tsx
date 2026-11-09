import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  AlertTriangle,
  Search,
  CheckCircle2,
  ShieldAlert,
  GitCompare,
  Users,
  Building2,
  FileText,
  Info,
} from "lucide-react";
import {
  api,
  type CrossRegistryRetirementSummary,
  type CrossRegistryProjectComparison,
  type CrossRegistryTrendsResponse,
  type CrossRegistryEntityComparison,
  type IntermediaryExtractionResult,
  type ProjectProfile,
  fmt,
  pct,
} from "../api";
import {
  PageHeader,
  SectionHeader,
  ErrorBox,
  MetricTile,
  EvidenceStrengthBadge,
  ProjectCorrelationCategoryBadge,
} from "../components/primitives";
import { ComparativePacingChart } from "../components/ComparativePacingChart";
import { ProjectCompareModal } from "../components/ProjectCompareModal";

type ActiveTab = "explorer" | "compare" | "entities";

// Presets for Project Comparison Studio
const PROJECT_PRESETS = [
  {
    label: "Attribute Correlation (VCS 1904 vs GS 3044)",
    desc: "Wind Power Project in Tamil Nadu, India — matching jurisdiction & overlapping vintage",
    projectA: {
      registry: "VCS",
      project_id: "1904",
      project_name: "Wind Power Project in Tamil Nadu by Green Infra Renewable Energy Limited",
      country: "India",
      vintage: "2018-2020",
      developer: "Green Infra Renewable Energy Limited",
    },
    projectB: {
      registry: "GS",
      project_id: "3044",
      project_name: "Wind Power Project in Tamil Nadu, India",
      country: "India",
      vintage: "2019",
      developer: "Green Infra",
    },
  },
  {
    label: "Identifier Collision (VCS 1845 vs GS 1845)",
    desc: "Identical numeric ID 1845 in disjoint namespaces — Rimba Raya (ID) vs Kasigau (KE)",
    projectA: {
      registry: "VCS",
      project_id: "1845",
      project_name: "Rimba Raya Biodiversity Reserve",
      country: "Indonesia",
      vintage: "2020",
      developer: "InfiniteEARTH",
    },
    projectB: {
      registry: "GS",
      project_id: "1845",
      project_name: "Kasigau Corridor REDD Project",
      country: "Kenya",
      vintage: "2019",
      developer: "Wildlife Works",
    },
  },
  {
    label: "Conflicting Jurisdiction (VCS 2284 vs GS 3044)",
    desc: "Identical project title text with contradictory countries (Brazil vs India)",
    projectA: {
      registry: "VCS",
      project_id: "2284",
      project_name: "Renewable Energy Power project by DDWL",
      country: "Brazil",
      vintage: "2020",
    },
    projectB: {
      registry: "GS",
      project_id: "3044",
      project_name: "Renewable Energy Power project by DDWL",
      country: "India",
      vintage: "2020",
    },
  },
];

// Presets for Entity Comparison
const ENTITY_PRESETS = [
  {
    label: "Canonical Variant",
    entityA: "Microsoft Corporation",
    registryA: "VCS",
    entityB: "Microsoft Corp.",
    registryB: "GS",
  },
  {
    label: "Suffix / Corporate Form",
    entityA: "Acme Carbon Trading LLC",
    registryA: "VCS",
    entityB: "Acme Carbon Trading Inc.",
    registryB: "GS",
  },
  {
    label: "Different Jurisdictions",
    entityA: "EcoAct UK",
    registryA: "VCS",
    entityB: "EcoAct France",
    registryB: "GS",
  },
];

// Presets for Intermediary Parser
const INTERMEDIARY_PRESETS = [
  {
    label: "Broker Delegation",
    text: "Retired by South Pole Carbon Asset Management Ltd on behalf of Apple Inc.",
  },
  {
    label: "Direct Corporate Action",
    text: "Delta Air Lines, Inc. - 2021 Scope 3 Mitigation Retirement",
  },
  {
    label: "Customer Retail Pool",
    text: "Retired on behalf of various retail clients by Klimate Co.",
  },
];

export default function CrossRegistry() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("explorer");

  // Summary & Trends data
  const [summary, setSummary] = useState<CrossRegistryRetirementSummary | null>(null);
  const [yearlyTrends, setYearlyTrends] = useState<CrossRegistryTrendsResponse | null>(null);
  const [monthlyTrends, setMonthlyTrends] = useState<CrossRegistryTrendsResponse | null>(null);
  const [initialErr, setInitialErr] = useState<unknown>(null);

  // Correlation Explorer filters & data
  const [correlations, setCorrelations] = useState<CrossRegistryProjectComparison[]>([]);
  const [corrLoading, setCorrLoading] = useState(true);
  const [corrErr, setCorrErr] = useState<unknown>(null);
  const [minSimilarity, setMinSimilarity] = useState<number>(0.50);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [countryFilter, setCountryFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Modal inspection
  const [inspectComparison, setInspectComparison] = useState<CrossRegistryProjectComparison | null>(null);

  // Tab 2: Project Comparator State
  const [projectA, setProjectA] = useState<ProjectProfile>(PROJECT_PRESETS[0].projectA);
  const [projectB, setProjectB] = useState<ProjectProfile>(PROJECT_PRESETS[0].projectB);
  const [comparatorResult, setComparatorResult] = useState<CrossRegistryProjectComparison | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareErr, setCompareErr] = useState<unknown>(null);

  // Tab 3: Entity Resolution State
  const [entityA, setEntityA] = useState(ENTITY_PRESETS[0].entityA);
  const [entityB, setEntityB] = useState(ENTITY_PRESETS[0].entityB);
  const [entityRegA, setEntityRegA] = useState(ENTITY_PRESETS[0].registryA);
  const [entityRegB, setEntityRegB] = useState(ENTITY_PRESETS[0].registryB);
  const [entityResult, setEntityResult] = useState<CrossRegistryEntityComparison | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);
  const [entityErr, setEntityErr] = useState<unknown>(null);

  // Tab 3: Intermediary Narrative Parser State
  const [narrativeText, setNarrativeText] = useState(INTERMEDIARY_PRESETS[0].text);
  const [intermediaryResult, setIntermediaryResult] = useState<IntermediaryExtractionResult | null>(null);
  const [intermediaryLoading, setIntermediaryLoading] = useState(false);
  const [intermediaryErr, setIntermediaryErr] = useState<unknown>(null);

  // Load summary and pacing trends once on mount
  useEffect(() => {
    let alive = true;
    Promise.all([
      api.crossRegistry.getRetirementSummary().catch(() => null),
      api.crossRegistry.getRetirementTrends("yearly").catch(() => null),
      api.crossRegistry.getRetirementTrends("monthly").catch(() => null),
    ])
      .then(([s, y, m]) => {
        if (!alive) return;
        if (s) setSummary(s);
        if (y) setYearlyTrends(y);
        if (m) setMonthlyTrends(m);
      })
      .catch((e) => {
        if (!alive) return;
        setInitialErr(e);
      });
    return () => {
      alive = false;
    };
  }, []);

  // Fetch correlations whenever explorer filters change
  useEffect(() => {
    let alive = true;
    api.crossRegistry
      .getProjectCorrelations({
        min_similarity: minSimilarity,
        category: selectedCategory || undefined,
        country: countryFilter.trim() || undefined,
        limit: 100,
      })
      .then((res) => {
        if (!alive) return;
        setCorrelations(res.correlations);
        setCorrLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setCorrErr(e);
        setCorrLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [minSimilarity, selectedCategory, countryFilter]);

  // Execute Pairwise Comparison
  const handleRunProjectCompare = async () => {
    setCompareLoading(true);
    setCompareErr(null);
    try {
      const res = await api.crossRegistry.compareProjects(projectA, projectB);
      setComparatorResult(res);
    } catch (e) {
      setCompareErr(e);
    } finally {
      setCompareLoading(false);
    }
  };

  // Execute Entity Comparison
  const handleRunEntityCompare = async () => {
    setEntityLoading(true);
    setEntityErr(null);
    try {
      const res = await api.crossRegistry.compareEntities({
        entity_a: entityA.trim(),
        entity_b: entityB.trim(),
        registry_a: entityRegA,
        registry_b: entityRegB,
      });
      setEntityResult(res);
    } catch (e) {
      setEntityErr(e);
    } finally {
      setEntityLoading(false);
    }
  };

  // Execute Intermediary Extraction
  const handleRunIntermediaryExtract = async () => {
    setIntermediaryLoading(true);
    setIntermediaryErr(null);
    try {
      const res = await api.crossRegistry.extractIntermediary(narrativeText.trim());
      setIntermediaryResult(res);
    } catch (e) {
      setIntermediaryErr(e);
    } finally {
      setIntermediaryLoading(false);
    }
  };

  // Filter correlations locally by search query
  const filteredCorrelations = correlations.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.project_a.project_name.toLowerCase().includes(q) ||
      c.project_b.project_name.toLowerCase().includes(q) ||
      (c.project_a.project_id && c.project_a.project_id.toLowerCase().includes(q)) ||
      (c.project_b.project_id && c.project_b.project_id.toLowerCase().includes(q)) ||
      (c.project_a.country && c.project_a.country.toLowerCase().includes(q)) ||
      (c.project_b.country && c.project_b.country.toLowerCase().includes(q))
    );
  });

  const vcsStats = summary?.registries?.VCS;
  const gsStats = summary?.registries?.GS;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Cross-Registry Intelligence"
        lede="Identify, correlate, and analyze project listings, retirement pacing, and entity relationships across Verra VCS and Gold Standard. Investigates potential split credits, dual-registry listings, and broker intermediaries."
      />

      <ErrorBox error={initialErr} title="Could not load initial cross-registry intelligence" />

      {/* 1. Macro Census Summary Banner */}
      {summary && (
        <section aria-labelledby="macro-h" className="space-y-4">
          <SectionHeader
            id="macro-h"
            title="Comparative Voluntary Registry Census"
            aside="Census basis: Berkeley Carbon Trading Project (VROD) · v2026-08"
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricTile
              label="Verra VCS Retired Volume"
              value={`${fmt(vcsStats?.total_retired_tonnes ?? 0)} t`}
              subtext={`${fmt(vcsStats?.total_retirement_records ?? 0)} records · ${vcsStats?.active_projects_count ?? 0} projects · ${pct((vcsStats?.beneficiary_record_disclosure_rate_pct ?? 0) / 100)} beneficiary disclosure`}
            />
            <MetricTile
              label="Gold Standard Retired Volume"
              value={`${fmt(gsStats?.total_retired_tonnes ?? 0)} t`}
              subtext={`${fmt(gsStats?.total_retirement_records ?? 0)} records · ${gsStats?.active_projects_count ?? 0} projects · ${pct((gsStats?.beneficiary_record_disclosure_rate_pct ?? 0) / 100)} beneficiary disclosure`}
            />
            <MetricTile
              label="Combined Retired Volume"
              value={`${fmt(summary.combined_retired_tonnes)} t`}
              subtext={`Across ${fmt(summary.combined_retirement_records)} validated retirement events`}
            />
            <MetricTile
              label="Pure Retirement Accounting"
              value={`${fmt(summary.total_issuance_records_excluded)} Excluded`}
              subtext="Issuance transactions strictly excluded from retirement volume calculations"
            />
          </div>

          {/* Comparability Notes Accordion / Box */}
          {summary.comparability_notes?.length > 0 && (
            <div className="rounded-panel border border-rule bg-fog-2/40 p-3.5 text-xs text-ink-soft space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-ink">
                <Info size={14} className="text-glacier" aria-hidden />
                <span>Registry Comparability Standards & Data Caveats</span>
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-muted pl-1">
                {summary.comparability_notes.map((note, idx) => (
                  <li key={idx}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* 2. Comparative Retirement Pacing Time-Series */}
      {yearlyTrends && monthlyTrends && (
        <ComparativePacingChart
          yearlyTrends={yearlyTrends.trends}
          monthlyTrends={monthlyTrends.trends}
          initialPeriod="yearly"
        />
      )}

      {/* 3. Primary Investigator Workspace Tabs */}
      <section aria-labelledby="workspace-h" className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-rule pb-3">
          <SectionHeader
            id="workspace-h"
            title="Investigator Intelligence Workspaces"
            aside="Explore candidate relationships, inspect project pairs, and resolve broker entities"
          />

          <div
            role="tablist"
            aria-label="Cross-Registry Workspaces"
            className="inline-flex rounded-panel border border-rule-strong bg-fog p-0.5 text-xs font-semibold"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "explorer"}
              onClick={() => setActiveTab("explorer")}
              className={`press rounded-[5px] px-3.5 py-1.5 transition-colors flex items-center gap-1.5 ${
                activeTab === "explorer"
                  ? "bg-sheet text-ink shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
            >
              <GitCompare size={13} aria-hidden />
              Correlation Explorer
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "compare"}
              onClick={() => setActiveTab("compare")}
              className={`press rounded-[5px] px-3.5 py-1.5 transition-colors flex items-center gap-1.5 ${
                activeTab === "compare"
                  ? "bg-sheet text-ink shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
            >
              <Building2 size={13} aria-hidden />
              Project Comparator
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "entities"}
              onClick={() => setActiveTab("entities")}
              className={`press rounded-[5px] px-3.5 py-1.5 transition-colors flex items-center gap-1.5 ${
                activeTab === "entities"
                  ? "bg-sheet text-ink shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
            >
              <Users size={13} aria-hidden />
              Entity & Broker Studio
            </button>
          </div>
        </div>

        {/* ============================================================== */}
        {/* TAB 1: CORRELATION EXPLORER                                     */}
        {/* ============================================================== */}
        {activeTab === "explorer" && (
          <div className="space-y-5">
            {/* Explorer Filter Bar */}
            <div className="rounded-sheet border border-rule bg-sheet p-4 space-y-4">
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                {/* Search query */}
                <div className="space-y-1">
                  <label className="font-semibold text-muted">Search Projects:</label>
                  <div className="relative">
                    <Search size={14} className="absolute left-2.5 top-2.5 text-muted" aria-hidden />
                    <input
                      type="text"
                      placeholder="Title, ID, or country..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full rounded-panel border border-rule-strong bg-paper pl-8 pr-3 py-1.5 text-xs text-ink placeholder:text-muted focus:border-ink focus:outline-none"
                    />
                  </div>
                </div>

                {/* Similarity threshold */}
                <div className="space-y-1">
                  <label className="font-semibold text-muted">Min Similarity Threshold:</label>
                  <select
                    value={minSimilarity}
                    onChange={(e) => {
                      setCorrLoading(true);
                      setMinSimilarity(parseFloat(e.target.value));
                    }}
                    className="w-full rounded-panel border border-rule-strong bg-paper px-2.5 py-1.5 text-xs text-ink focus:border-ink focus:outline-none"
                  >
                    <option value="0.75">High (≥ 0.75)</option>
                    <option value="0.65">Moderate-High (≥ 0.65)</option>
                    <option value="0.50">Standard (≥ 0.50)</option>
                    <option value="0.30">Broad (≥ 0.30)</option>
                  </select>
                </div>

                {/* Category filter */}
                <div className="space-y-1">
                  <label className="font-semibold text-muted">Evidence Category:</label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => {
                      setCorrLoading(true);
                      setSelectedCategory(e.target.value);
                    }}
                    className="w-full rounded-panel border border-rule-strong bg-paper px-2.5 py-1.5 text-xs text-ink focus:border-ink focus:outline-none"
                  >
                    <option value="">All Categories</option>
                    <option value="CROSS_REGISTRY_IDENTIFIER_COLLISION">ID Collision</option>
                    <option value="STRONG_ATTRIBUTE_CORRELATION">Strong Attribute Correlation</option>
                    <option value="PARTIAL_ATTRIBUTE_CORRELATION">Partial Attribute Correlation</option>
                    <option value="NAME_SIMILARITY_ONLY">Name Similarity Only</option>
                    <option value="CONFLICTING_ATTRIBUTES">Conflicting Attributes</option>
                    <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence</option>
                  </select>
                </div>

                {/* Country filter */}
                <div className="space-y-1">
                  <label className="font-semibold text-muted">Country Jurisdiction:</label>
                  <input
                    type="text"
                    placeholder="e.g. India, Brazil..."
                    value={countryFilter}
                    onChange={(e) => setCountryFilter(e.target.value)}
                    className="w-full rounded-panel border border-rule-strong bg-paper px-2.5 py-1.5 text-xs text-ink placeholder:text-muted focus:border-ink focus:outline-none"
                  />
                </div>
              </div>

              {/* Status & count */}
              <div className="flex items-center justify-between text-xs text-muted border-t border-rule/60 pt-2.5">
                <span>
                  Showing <strong>{filteredCorrelations.length}</strong> matching candidate pairs (from {correlations.length} evaluated at threshold {minSimilarity})
                </span>
                {corrLoading && <span className="font-mono text-glacier">Refreshing correlations...</span>}
              </div>
            </div>

            <ErrorBox error={corrErr} title="Could not load project correlations" />

            {/* Candidate List */}
            {corrLoading && correlations.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted">
                Evaluating cross-registry candidate project pairs...
              </div>
            ) : filteredCorrelations.length === 0 ? (
              <div className="rounded-panel border border-dashed border-rule-strong bg-sheet p-8 text-center text-sm text-muted space-y-2">
                <p>No cross-registry project correlations match the selected filters.</p>
                <button
                  type="button"
                  onClick={() => {
                    setMinSimilarity(0.30);
                    setSelectedCategory("");
                    setCountryFilter("");
                    setSearchQuery("");
                  }}
                  className="press text-xs font-semibold text-glacier hover:underline"
                >
                  Reset all filters to broad search
                </button>
              </div>
            ) : (
              <div className="divide-y divide-rule rounded-sheet border border-rule bg-sheet overflow-hidden">
                {filteredCorrelations.map((pair, idx) => {
                  const isCollision =
                    pair.correlation_category === "CROSS_REGISTRY_IDENTIFIER_COLLISION" ||
                    (pair.is_cross_registry && pair.identifier_match);

                  return (
                    <div
                      key={idx}
                      className="p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-5 hover:bg-fog/20 transition-colors"
                    >
                      <div className="space-y-3 flex-1">
                        {/* Top Category Badges */}
                        <div className="flex flex-wrap items-center gap-2">
                          <ProjectCorrelationCategoryBadge category={pair.correlation_category} />
                          <EvidenceStrengthBadge strength={pair.evidence_strength} />

                          {isCollision && (
                            <span
                              className="inline-flex items-center gap-1 rounded-token bg-crimson-wash border border-crimson/30 px-2 py-0.5 font-mono text-[11px] font-bold text-crimson"
                              title="Identifier Collision: disjoint namespaces share identical ID strings"
                            >
                              <AlertTriangle size={12} aria-hidden />
                              Disjoint Namespace Collision
                            </span>
                          )}

                          <span className="font-mono text-xs text-muted">
                            Jurisdiction:{" "}
                            {pair.country_relation === "MATCH" ? (
                              <strong className="text-lichen">Match ({pair.project_a.country})</strong>
                            ) : pair.country_relation === "CONFLICT" ? (
                              <strong className="text-crimson">Conflicting</strong>
                            ) : (
                              "Unlisted"
                            )}
                          </span>
                        </div>

                        {/* Side-by-side Project Previews */}
                        <div className="grid sm:grid-cols-2 gap-3 text-xs">
                          {/* Project A */}
                          <div className="rounded border border-rule bg-fog-2/30 p-3 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[10.5px] font-bold text-glacier uppercase">
                                {pair.project_a.registry} Project
                              </span>
                              <span className="font-mono text-muted text-[11px]">
                                ID: <strong>{pair.project_a.project_id || "—"}</strong>
                              </span>
                            </div>
                            <div className="font-semibold text-ink leading-snug">
                              {pair.project_a.project_name}
                            </div>
                            <div className="font-mono text-muted text-[11px]">
                              {pair.project_a.country || "Country unlisted"} · Vintage: {pair.project_a.vintage || "Unspecified"}
                            </div>
                          </div>

                          {/* Project B */}
                          <div className="rounded border border-rule bg-fog-2/30 p-3 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[10.5px] font-bold text-lichen uppercase">
                                {pair.project_b.registry} Project
                              </span>
                              <span className="font-mono text-muted text-[11px]">
                                ID: <strong>{pair.project_b.project_id || "—"}</strong>
                              </span>
                            </div>
                            <div className="font-semibold text-ink leading-snug">
                              {pair.project_b.project_name}
                            </div>
                            <div className="font-mono text-muted text-[11px]">
                              {pair.project_b.country || "Country unlisted"} · Vintage: {pair.project_b.vintage || "Unspecified"}
                            </div>
                          </div>
                        </div>

                        {/* Explanation Snippet */}
                        <p className="text-xs text-ink-soft leading-relaxed line-clamp-2">
                          {pair.explanation}
                        </p>
                      </div>

                      {/* Right Column: Similarity Score & Actions */}
                      <div className="flex flex-row lg:flex-col items-center lg:items-end justify-between lg:justify-center gap-3 shrink-0 pt-3 lg:pt-0 border-t lg:border-t-0 border-rule">
                        <div className="text-left lg:text-right">
                          <div className="text-[11px] text-muted">Name Similarity</div>
                          <div className="font-mono text-xl font-bold text-ink">
                            {(pair.name_similarity_score * 100).toFixed(1)}%
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setInspectComparison(pair)}
                            className="press rounded-panel border border-rule-strong bg-paper px-3 py-1.5 text-xs font-semibold text-ink hover:bg-fog transition-colors"
                          >
                            Inspect Pair
                          </button>

                          <Link
                            to={`/assessment?scope=PROJECT&registry=${encodeURIComponent(pair.project_a.registry)}&project_id=${encodeURIComponent(pair.project_a.project_id || "")}`}
                            className="press inline-flex items-center gap-1 rounded-panel bg-ink px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0b2429] transition-colors"
                            title="Assess Project A in Risk Console"
                          >
                            Assess <ArrowRight size={12} aria-hidden />
                          </Link>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 2: PROJECT COMPARATOR STUDIO                                */}
        {/* ============================================================== */}
        {activeTab === "compare" && (
          <div className="space-y-6">
            {/* Presets Selector */}
            <div className="rounded-sheet border border-rule bg-sheet p-4 space-y-3">
              <span className="font-mono text-xs font-bold text-ink uppercase tracking-wider block">
                Quick Demonstration Presets:
              </span>
              <div className="grid sm:grid-cols-3 gap-3">
                {PROJECT_PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setProjectA(p.projectA);
                      setProjectB(p.projectB);
                      setComparatorResult(null);
                    }}
                    className="press rounded-panel border border-rule bg-fog-2/40 p-3 text-left hover:border-ink hover:bg-fog transition-colors space-y-1"
                  >
                    <div className="font-semibold text-xs text-ink">{p.label}</div>
                    <p className="text-[11px] text-muted leading-snug">{p.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Input Form for Pairwise Comparison */}
            <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-5">
              <div className="grid sm:grid-cols-2 gap-5">
                {/* Project A Form */}
                <div className="rounded-panel border border-glacier/30 bg-glacier-wash/20 p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-glacier/20 pb-2">
                    <span className="font-mono text-xs font-bold text-glacier uppercase">Project Profile A</span>
                    <input
                      type="text"
                      placeholder="Registry (e.g. VCS)"
                      value={projectA.registry}
                      onChange={(e) => setProjectA({ ...projectA, registry: e.target.value.toUpperCase() })}
                      className="w-20 rounded border border-rule bg-sheet px-2 py-0.5 text-xs font-mono font-bold text-ink text-center"
                    />
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <label className="text-muted block text-[11px]">Project ID:</label>
                      <input
                        type="text"
                        value={projectA.project_id || ""}
                        onChange={(e) => setProjectA({ ...projectA, project_id: e.target.value })}
                        className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs font-mono text-ink"
                        placeholder="e.g. 1904"
                      />
                    </div>
                    <div>
                      <label className="text-muted block text-[11px]">Project Title:</label>
                      <input
                        type="text"
                        value={projectA.project_name}
                        onChange={(e) => setProjectA({ ...projectA, project_name: e.target.value })}
                        className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                        placeholder="Project title..."
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-muted block text-[11px]">Country:</label>
                        <input
                          type="text"
                          value={projectA.country || ""}
                          onChange={(e) => setProjectA({ ...projectA, country: e.target.value })}
                          className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                          placeholder="e.g. India"
                        />
                      </div>
                      <div>
                        <label className="text-muted block text-[11px]">Vintage:</label>
                        <input
                          type="text"
                          value={projectA.vintage || ""}
                          onChange={(e) => setProjectA({ ...projectA, vintage: e.target.value })}
                          className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                          placeholder="e.g. 2018-2020"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-muted block text-[11px]">Developer:</label>
                      <input
                        type="text"
                        value={projectA.developer || ""}
                        onChange={(e) => setProjectA({ ...projectA, developer: e.target.value })}
                        className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                        placeholder="Proponent / developer..."
                      />
                    </div>
                  </div>
                </div>

                {/* Project B Form */}
                <div className="rounded-panel border border-lichen/30 bg-lichen-wash/20 p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-lichen/20 pb-2">
                    <span className="font-mono text-xs font-bold text-lichen uppercase">Project Profile B</span>
                    <input
                      type="text"
                      placeholder="Registry (e.g. GS)"
                      value={projectB.registry}
                      onChange={(e) => setProjectB({ ...projectB, registry: e.target.value.toUpperCase() })}
                      className="w-20 rounded border border-rule bg-sheet px-2 py-0.5 text-xs font-mono font-bold text-ink text-center"
                    />
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <label className="text-muted block text-[11px]">Project ID:</label>
                      <input
                        type="text"
                        value={projectB.project_id || ""}
                        onChange={(e) => setProjectB({ ...projectB, project_id: e.target.value })}
                        className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs font-mono text-ink"
                        placeholder="e.g. 3044"
                      />
                    </div>
                    <div>
                      <label className="text-muted block text-[11px]">Project Title:</label>
                      <input
                        type="text"
                        value={projectB.project_name}
                        onChange={(e) => setProjectB({ ...projectB, project_name: e.target.value })}
                        className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                        placeholder="Project title..."
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-muted block text-[11px]">Country:</label>
                        <input
                          type="text"
                          value={projectB.country || ""}
                          onChange={(e) => setProjectB({ ...projectB, country: e.target.value })}
                          className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                          placeholder="e.g. India"
                        />
                      </div>
                      <div>
                        <label className="text-muted block text-[11px]">Vintage:</label>
                        <input
                          type="text"
                          value={projectB.vintage || ""}
                          onChange={(e) => setProjectB({ ...projectB, vintage: e.target.value })}
                          className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                          placeholder="e.g. 2019"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-muted block text-[11px]">Developer:</label>
                      <input
                        type="text"
                        value={projectB.developer || ""}
                        onChange={(e) => setProjectB({ ...projectB, developer: e.target.value })}
                        className="w-full rounded border border-rule bg-sheet px-2.5 py-1 text-xs text-ink"
                        placeholder="Proponent / developer..."
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={handleRunProjectCompare}
                  disabled={compareLoading || !projectA.project_name.trim() || !projectB.project_name.trim()}
                  className="press inline-flex items-center gap-2 rounded-panel bg-ink px-5 py-2 text-xs font-semibold text-white hover:bg-[#0b2429] disabled:opacity-40 transition-colors"
                >
                  <GitCompare size={14} aria-hidden />
                  {compareLoading ? "Evaluating Project Pair..." : "Compare Project Profiles"}
                </button>
              </div>
            </div>

            <ErrorBox error={compareErr} title="Could not compare project pair" />

            {/* Inline Comparison Result View */}
            {comparatorResult && (
              <div className="rounded-sheet border border-rule-strong bg-sheet p-6 space-y-6">
                <div className="flex items-start justify-between gap-4 border-b border-rule pb-4">
                  <div>
                    <span className="font-mono text-xs font-semibold text-muted uppercase">Comparison Evaluation Result</span>
                    <h3 className="text-base font-bold text-ink mt-0.5">
                      Pairwise Project Synthesis
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <ProjectCorrelationCategoryBadge category={comparatorResult.correlation_category} />
                    <EvidenceStrengthBadge strength={comparatorResult.evidence_strength} />
                  </div>
                </div>

                {/* Safety warning if collision */}
                {(comparatorResult.correlation_category === "CROSS_REGISTRY_IDENTIFIER_COLLISION" ||
                  (comparatorResult.is_cross_registry && comparatorResult.identifier_match)) && (
                  <div className="rounded-panel border border-crimson/40 bg-crimson-wash p-4 text-xs space-y-1.5 text-crimson">
                    <div className="flex items-center gap-2 font-bold text-sm">
                      <ShieldAlert size={16} aria-hidden />
                      <span>Cross-Registry Identifier Collision Detected</span>
                    </div>
                    <p className="leading-relaxed">
                      Matching project identifier "{projectA.project_id || projectB.project_id}" detected across independent registries.
                      Voluntary standards operate uncoordinated identifier namespaces. A collision alone does not establish project identity or wrongdoing.
                    </p>
                  </div>
                )}

                {/* Mathematical Scores */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div className="rounded border border-rule bg-fog/50 p-2.5">
                    <span className="text-[10.5px] font-medium text-muted block">Composite Similarity</span>
                    <span className="font-mono text-lg font-bold text-ink">
                      {(comparatorResult.name_similarity_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="rounded border border-rule bg-fog/50 p-2.5">
                    <span className="text-[10.5px] font-medium text-muted block">Token Set Ratio</span>
                    <span className="font-mono text-lg font-bold text-ink">
                      {(comparatorResult.token_set_ratio * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="rounded border border-rule bg-fog/50 p-2.5">
                    <span className="text-[10.5px] font-medium text-muted block">Token Sort Ratio</span>
                    <span className="font-mono text-lg font-bold text-ink">
                      {(comparatorResult.token_sort_ratio * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="rounded border border-rule bg-fog/50 p-2.5">
                    <span className="text-[10.5px] font-medium text-muted block">Jaro-Winkler</span>
                    <span className="font-mono text-lg font-bold text-ink">
                      {(comparatorResult.jaro_winkler_similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Attribute Matrix */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="rounded border border-rule bg-paper p-2.5">
                    <span className="text-muted block text-[10.5px]">Project ID Relation</span>
                    <div className="font-mono font-bold mt-1 text-ink">
                      {comparatorResult.identifier_match ? "Identical ID String" : "Disjoint IDs"}
                    </div>
                  </div>
                  <div className="rounded border border-rule bg-paper p-2.5">
                    <span className="text-muted block text-[10.5px]">Jurisdiction Relation</span>
                    <div className="font-mono font-bold mt-1">
                      {comparatorResult.country_relation === "MATCH" && (
                        <span className="text-lichen">Match ({projectA.country})</span>
                      )}
                      {comparatorResult.country_relation === "CONFLICT" && (
                        <span className="text-crimson">Conflicting</span>
                      )}
                      {comparatorResult.country_relation === "MISSING" && (
                        <span className="text-muted">Unspecified</span>
                      )}
                    </div>
                  </div>
                  <div className="rounded border border-rule bg-paper p-2.5">
                    <span className="text-muted block text-[10.5px]">Vintage Relation</span>
                    <div className="font-mono font-bold mt-1">
                      {comparatorResult.vintage_relation === "OVERLAP" && (
                        <span className="text-lichen">Overlapping</span>
                      )}
                      {comparatorResult.vintage_relation === "ADJACENT" && (
                        <span className="text-glacier">Adjacent</span>
                      )}
                      {comparatorResult.vintage_relation === "DISJOINT" && (
                        <span className="text-ochre">Disjoint</span>
                      )}
                      {comparatorResult.vintage_relation === "MISSING" && (
                        <span className="text-muted">Unspecified</span>
                      )}
                    </div>
                  </div>
                  <div className="rounded border border-rule bg-paper p-2.5">
                    <span className="text-muted block text-[10.5px]">Developer Similarity</span>
                    <div className="font-mono font-bold mt-1 text-ink">
                      {comparatorResult.developer_similarity != null
                        ? `${(comparatorResult.developer_similarity * 100).toFixed(1)}%`
                        : "Not comparable"}
                    </div>
                  </div>
                </div>

                {/* Narrative Explanation */}
                <div className="space-y-2 text-xs">
                  <div className="rounded-panel border border-rule bg-fog-2/40 p-3.5 space-y-1">
                    <span className="font-mono font-bold text-ink block text-[11px]">Explanation:</span>
                    <p className="text-ink leading-relaxed font-sans">{comparatorResult.explanation}</p>
                  </div>
                  <p className="text-[11px] text-muted italic">{comparatorResult.disclaimer}</p>
                </div>

                <div className="flex items-center justify-between border-t border-rule pt-4">
                  <button
                    type="button"
                    onClick={() => setInspectComparison(comparatorResult)}
                    className="press rounded-panel border border-rule-strong bg-sheet px-3.5 py-1.5 text-xs font-semibold text-ink hover:bg-fog"
                  >
                    Open Full Inspection Modal
                  </button>

                  <Link
                    to={`/assessment?scope=PROJECT&registry=${encodeURIComponent(projectA.registry)}&project_id=${encodeURIComponent(projectA.project_id || "")}`}
                    className="press inline-flex items-center gap-1.5 text-xs font-semibold text-glacier hover:underline"
                  >
                    Assess {projectA.registry} Project in Risk Console <ArrowRight size={13} aria-hidden />
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 3: ENTITY RESOLUTION & INTERMEDIARY BROKER STUDIO          */}
        {/* ============================================================== */}
        {activeTab === "entities" && (
          <div className="space-y-8">
            {/* Core Legal Disambiguation Principle */}
            <div className="rounded-sheet border border-glacier/30 bg-glacier-wash/20 p-4 text-xs space-y-1.5 text-ink">
              <div className="flex items-center gap-2 font-bold text-glacier text-sm">
                <Info size={16} aria-hidden />
                <span>Entity Resolution & Legal Non-Equivalence Mandate</span>
              </div>
              <p className="leading-relaxed text-ink-soft">
                In voluntary carbon markets, similar organization names across registries do <strong>not</strong> establish corporate or legal-entity equivalence.
                Brokers, aggregators, trading desks, corporate parents, and subsidiaries must remain distinctly identified to prevent erroneous double-claim allegations.
              </p>
            </div>

            {/* Sub-tool A: Pairwise Entity Comparison */}
            <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-rule pb-3">
                <div>
                  <h3 className="text-sm font-bold text-ink">Cross-Registry Entity Resolution</h3>
                  <p className="text-xs text-ink-soft mt-0.5">
                    Compare organization names across registry accounts with canonical normalization and suffix peeling.
                  </p>
                </div>
                {/* Presets */}
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  <span className="text-muted font-medium">Presets:</span>
                  {ENTITY_PRESETS.map((p, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setEntityA(p.entityA);
                        setEntityB(p.entityB);
                        setEntityRegA(p.registryA);
                        setEntityRegB(p.registryB);
                        setEntityResult(null);
                      }}
                      className="press rounded border border-rule-strong bg-fog px-2 py-0.5 font-mono text-[11px] text-ink hover:bg-sheet"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 text-xs">
                {/* Entity A */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="font-semibold text-muted">Entity A Name:</label>
                    <select
                      value={entityRegA}
                      onChange={(e) => setEntityRegA(e.target.value)}
                      className="rounded border border-rule bg-paper px-2 py-0.5 font-mono text-[11px] text-ink"
                    >
                      <option value="VCS">Verra VCS</option>
                      <option value="GS">Gold Standard</option>
                      <option value="ACR">ACR</option>
                      <option value="CAR">CAR</option>
                    </select>
                  </div>
                  <input
                    type="text"
                    value={entityA}
                    onChange={(e) => setEntityA(e.target.value)}
                    className="w-full rounded border border-rule-strong bg-paper px-3 py-1.5 text-xs text-ink focus:border-ink focus:outline-none"
                    placeholder="e.g. Microsoft Corporation"
                  />
                </div>

                {/* Entity B */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="font-semibold text-muted">Entity B Name:</label>
                    <select
                      value={entityRegB}
                      onChange={(e) => setEntityRegB(e.target.value)}
                      className="rounded border border-rule bg-paper px-2 py-0.5 font-mono text-[11px] text-ink"
                    >
                      <option value="GS">Gold Standard</option>
                      <option value="VCS">Verra VCS</option>
                      <option value="ACR">ACR</option>
                      <option value="CAR">CAR</option>
                    </select>
                  </div>
                  <input
                    type="text"
                    value={entityB}
                    onChange={(e) => setEntityB(e.target.value)}
                    className="w-full rounded border border-rule-strong bg-paper px-3 py-1.5 text-xs text-ink focus:border-ink focus:outline-none"
                    placeholder="e.g. Microsoft Corp."
                  />
                </div>
              </div>

              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={handleRunEntityCompare}
                  disabled={entityLoading || !entityA.trim() || !entityB.trim()}
                  className="press inline-flex items-center gap-2 rounded-panel bg-ink px-4 py-2 text-xs font-semibold text-white hover:bg-[#0b2429] disabled:opacity-40 transition-colors"
                >
                  <Users size={14} aria-hidden />
                  {entityLoading ? "Resolving Entities..." : "Compare Entity Names"}
                </button>
              </div>

              <ErrorBox error={entityErr} title="Entity comparison failed" />

              {/* Entity Comparison Result */}
              {entityResult && (
                <div className="rounded-panel border border-rule bg-fog-2/30 p-4 space-y-4 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/60 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold uppercase text-glacier">
                        Resolution Scorecard
                      </span>
                      <span className="text-muted">·</span>
                      <span
                        className={`font-mono text-xs font-bold px-2 py-0.5 rounded border ${
                          entityResult.is_match
                            ? "bg-lichen-wash text-lichen border-lichen/40"
                            : "bg-ochre-wash text-ochre border-ochre/40"
                        }`}
                      >
                        {entityResult.is_match ? "Candidate Match" : "Non-Matching Entities"}
                      </span>
                      <span className="font-mono text-xs font-semibold text-ink bg-fog px-2 py-0.5 rounded border border-rule">
                        {entityResult.relationship_type.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="font-mono text-sm font-bold text-ink">
                      Score: {entityResult.overall_score}% ({entityResult.match_tier})
                    </div>
                  </div>

                  {/* Normalized comparison */}
                  <div className="grid sm:grid-cols-2 gap-3">
                    <div className="rounded border border-rule bg-sheet p-2.5 space-y-1">
                      <span className="text-[10px] font-mono text-muted uppercase block">
                        {entityResult.registry_a} Entity Normalized
                      </span>
                      <div className="font-semibold text-ink">{entityResult.entity_raw_a}</div>
                      <div className="font-mono text-[11px] text-muted">Canonical: {entityResult.entity_normalized_a}</div>
                    </div>
                    <div className="rounded border border-rule bg-sheet p-2.5 space-y-1">
                      <span className="text-[10px] font-mono text-muted uppercase block">
                        {entityResult.registry_b} Entity Normalized
                      </span>
                      <div className="font-semibold text-ink">{entityResult.entity_raw_b}</div>
                      <div className="font-mono text-[11px] text-muted">Canonical: {entityResult.entity_normalized_b}</div>
                    </div>
                  </div>

                  {/* Signals */}
                  <div className="grid sm:grid-cols-2 gap-3">
                    {entityResult.positive_signals?.length > 0 && (
                      <div className="rounded border border-lichen/30 bg-lichen-wash/30 p-2.5 space-y-1">
                        <span className="font-semibold text-lichen flex items-center gap-1">
                          <CheckCircle2 size={13} aria-hidden /> Corroborating Signals
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-ink-soft">
                          {entityResult.positive_signals.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {entityResult.contradictory_signals?.length > 0 && (
                      <div className="rounded border border-crimson/30 bg-crimson-wash/30 p-2.5 space-y-1">
                        <span className="font-semibold text-crimson flex items-center gap-1">
                          <AlertTriangle size={13} aria-hidden /> Contradictory Signals
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-crimson">
                          {entityResult.contradictory_signals.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Legal disclaimer */}
                  <div className="text-[11px] text-muted italic border-t border-rule/60 pt-2">
                    {entityResult.legal_disclaimer}
                  </div>
                </div>
              )}
            </div>

            {/* Sub-tool B: Intermediary & Broker Narrative Parser */}
            <div className="rounded-sheet border border-rule bg-sheet p-5 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-rule pb-3">
                <div>
                  <h3 className="text-sm font-bold text-ink">Intermediary & Broker Allocation Parser</h3>
                  <p className="text-xs text-ink-soft mt-0.5">
                    Extract on-behalf-of delegations, custodial accounts, and broker-trader relationships from retirement narrative records.
                  </p>
                </div>
                {/* Presets */}
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  <span className="text-muted font-medium">Presets:</span>
                  {INTERMEDIARY_PRESETS.map((p, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setNarrativeText(p.text);
                        setIntermediaryResult(null);
                      }}
                      className="press rounded border border-rule-strong bg-fog px-2 py-0.5 font-mono text-[11px] text-ink hover:bg-sheet"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <label className="font-semibold text-muted block">Retirement Beneficiary / Details String:</label>
                <textarea
                  rows={2}
                  value={narrativeText}
                  onChange={(e) => setNarrativeText(e.target.value)}
                  className="w-full rounded border border-rule-strong bg-paper px-3 py-2 text-xs text-ink focus:border-ink focus:outline-none font-mono"
                  placeholder="e.g. Retired by South Pole Carbon Asset Management Ltd on behalf of Apple Inc."
                />
              </div>

              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={handleRunIntermediaryExtract}
                  disabled={intermediaryLoading || !narrativeText.trim()}
                  className="press inline-flex items-center gap-2 rounded-panel bg-ink px-4 py-2 text-xs font-semibold text-white hover:bg-[#0b2429] disabled:opacity-40 transition-colors"
                >
                  <FileText size={14} aria-hidden />
                  {intermediaryLoading ? "Parsing Narrative..." : "Extract Intermediary Structure"}
                </button>
              </div>

              <ErrorBox error={intermediaryErr} title="Intermediary extraction failed" />

              {/* Extraction Result View */}
              {intermediaryResult && (
                <div className="rounded-panel border border-rule bg-fog-2/30 p-4 space-y-4 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/60 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold uppercase text-glacier">
                        Structured Extraction
                      </span>
                      <span className="text-muted">·</span>
                      <span
                        className={`font-mono text-xs font-bold px-2 py-0.5 rounded border ${
                          intermediaryResult.is_delegated
                            ? "bg-glacier-wash text-glacier border-glacier/40"
                            : "bg-fog text-ink-soft border-rule"
                        }`}
                      >
                        {intermediaryResult.is_delegated ? "Delegated Retirement" : "Direct Retirement"}
                      </span>
                      <span className="font-mono text-xs font-semibold bg-fog px-2 py-0.5 rounded border border-rule text-ink">
                        Role: {intermediaryResult.role.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="font-mono text-xs text-muted">
                      Confidence: <strong>{(intermediaryResult.confidence * 100).toFixed(0)}%</strong>
                    </div>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-3">
                    {/* Intermediary Party */}
                    <div className="rounded border border-rule bg-sheet p-3 space-y-1">
                      <span className="text-[10px] font-mono text-glacier uppercase font-bold block">
                        Intermediary / Retiring Party
                      </span>
                      <div className="font-semibold text-ink text-sm">
                        {intermediaryResult.intermediary_raw || "None identified (Direct)"}
                      </div>
                      {intermediaryResult.intermediary_entity && (
                        <div className="font-mono text-[11px] text-muted">
                          Canonical: {intermediaryResult.intermediary_entity.canonical_name}
                        </div>
                      )}
                    </div>

                    {/* Principal Beneficiary */}
                    <div className="rounded border border-rule bg-sheet p-3 space-y-1">
                      <span className="text-[10px] font-mono text-lichen uppercase font-bold block">
                        Principal Beneficiary Party
                      </span>
                      <div className="font-semibold text-ink text-sm">
                        {intermediaryResult.principal_raw || "None identified"}
                      </div>
                      {intermediaryResult.principal_entity && (
                        <div className="font-mono text-[11px] text-muted">
                          Canonical: {intermediaryResult.principal_entity.canonical_name}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Extraction Notes */}
                  {intermediaryResult.notes?.length > 0 && (
                    <div className="text-[11px] text-muted space-y-1 border-t border-rule/60 pt-2">
                      <span className="font-semibold text-ink-soft block">Extraction Notes:</span>
                      <ul className="list-disc list-inside space-y-0.5">
                        {intermediaryResult.notes.map((note, idx) => (
                          <li key={idx}>{note}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Detail Modal for inspectComparison */}
      {inspectComparison && (
        <ProjectCompareModal
          comparison={inspectComparison}
          onClose={() => setInspectComparison(null)}
        />
      )}
    </div>
  );
}

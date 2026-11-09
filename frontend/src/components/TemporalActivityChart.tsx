import { useState, useId, useMemo } from "react";
import { Table, Calendar, TrendingUp } from "lucide-react";
import type {
  TemporalActivityPeriod,
  TemporalTrendPeriod,
  AggregationPeriod,
} from "../api";
import { fmt } from "../api";
import { TrendDirectionBadge } from "./AnalyticalPrimitives";

interface TemporalActivityChartProps {
  activityPeriods: TemporalActivityPeriod[];
  trendPeriods?: TemporalTrendPeriod[];
  currentPeriod: AggregationPeriod;
  onPeriodChange: (p: AggregationPeriod) => void;
  isLoading?: boolean;
}

export function TemporalActivityChart({
  activityPeriods,
  trendPeriods = [],
  currentPeriod,
  onPeriodChange,
  isLoading = false,
}: TemporalActivityChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const [metricMode, setMetricMode] = useState<"volume" | "records" | "both">("both");

  const titleId = useId();
  const descId = useId();

  // Map trends by period label for fast lookup
  const trendMap = useMemo(() => {
    const m = new Map<string, TemporalTrendPeriod>();
    for (const t of trendPeriods) {
      m.set(t.period_label, t);
    }
    return m;
  }, [trendPeriods]);

  // Window or downsample if daily/weekly is very dense
  // For monthly (192 periods), show all. For weekly (828), window recent 104 weeks (2 yrs) or full scrollable.
  // We can render full SVG with scroll or recent window.
  const displayPeriods = useMemo(() => {
    if (currentPeriod === "daily" && activityPeriods.length > 365) {
      // Recent 365 days for daily view to keep SVG responsive
      return activityPeriods.slice(-365);
    }
    if (currentPeriod === "weekly" && activityPeriods.length > 156) {
      // Recent 156 weeks (3 years) for weekly view
      return activityPeriods.slice(-156);
    }
    return activityPeriods;
  }, [activityPeriods, currentPeriod]);

  // Compute maximums for scaling
  const { maxTonnes, maxRecords, totalTonnes, totalRecords } = useMemo(() => {
    let maxT = 1;
    let maxR = 1;
    let sumT = 0;
    let sumR = 0;
    for (const p of displayPeriods) {
      if (p.total_tonnes > maxT) maxT = p.total_tonnes;
      if (p.record_count > maxR) maxR = p.record_count;
      sumT += p.total_tonnes;
      sumR += p.record_count;
    }
    return {
      maxTonnes: maxT,
      maxRecords: maxR,
      totalTonnes: sumT,
      totalRecords: sumR,
    };
  }, [displayPeriods]);

  // SVG Geometry
  const width = 900;
  const height = 300;
  const margin = { top: 25, right: 60, bottom: 45, left: 70 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const formatTonnes = (val: number): string => {
    if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M t`;
    if (val >= 1_000) return `${(val / 1_000).toFixed(0)}k t`;
    return `${val.toFixed(0)} t`;
  };

  const hoveredPeriod = hoverIndex !== null && hoverIndex >= 0 && hoverIndex < displayPeriods.length ? displayPeriods[hoverIndex] : null;
  const hoveredTrend = hoveredPeriod ? trendMap.get(hoveredPeriod.period_label) : null;

  return (
    <section
      role="region"
      aria-labelledby={titleId}
      aria-describedby={descId}
      className="rounded-sheet border border-rule bg-sheet p-5 space-y-4"
    >
      {/* Chart Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-rule pb-3">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-glacier" aria-hidden />
            <h4 id={titleId} className="text-sm font-bold text-ink">
              Temporal Activity & Velocity Trends
            </h4>
          </div>
          <p id={descId} className="text-xs text-ink-soft mt-0.5">
            Continuous calendar timeline displaying retired credit volume (tonnes) and transaction frequency across {currentPeriod} periods.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Period Toggle */}
          <div className="inline-flex rounded-panel border border-rule-strong bg-fog p-0.5 text-xs font-semibold">
            {(["monthly", "weekly", "daily"] as AggregationPeriod[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => onPeriodChange(p)}
                className={`press rounded-[5px] px-2.5 py-1 capitalize transition-colors ${
                  currentPeriod === p
                    ? "bg-sheet text-ink shadow-sm"
                    : "text-muted hover:text-ink"
                }`}
                aria-pressed={currentPeriod === p}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Metric display mode */}
          <div className="inline-flex rounded-panel border border-rule-strong bg-fog p-0.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setMetricMode("both")}
              className={`press rounded-[5px] px-2 py-1 text-[11px] ${
                metricMode === "both" ? "bg-sheet text-ink shadow-sm" : "text-muted hover:text-ink"
              }`}
            >
              Dual Axis
            </button>
            <button
              type="button"
              onClick={() => setMetricMode("volume")}
              className={`press rounded-[5px] px-2 py-1 text-[11px] ${
                metricMode === "volume" ? "bg-sheet text-ink shadow-sm" : "text-muted hover:text-ink"
              }`}
            >
              Tonnes
            </button>
            <button
              type="button"
              onClick={() => setMetricMode("records")}
              className={`press rounded-[5px] px-2 py-1 text-[11px] ${
                metricMode === "records" ? "bg-sheet text-ink shadow-sm" : "text-muted hover:text-ink"
              }`}
            >
              Records
            </button>
          </div>

          <button
            type="button"
            onClick={() => setShowTable(!showTable)}
            className="press inline-flex items-center gap-1 rounded border border-rule-strong bg-paper px-2.5 py-1 text-xs font-medium text-ink hover:bg-fog"
            aria-expanded={showTable}
          >
            <Table size={12} aria-hidden />
            {showTable ? "Hide Data" : "Data Table"}
          </button>
        </div>
      </div>

      {/* Summary Micro Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="rounded border border-rule bg-fog-2/30 p-2.5">
          <span className="text-muted block text-[10.5px]">Observed Window Volume</span>
          <span className="font-mono text-sm font-bold text-glacier mt-0.5 block">
            {formatTonnes(totalTonnes)}
          </span>
          <span className="text-muted text-[10.5px]">Across {displayPeriods.length} {currentPeriod} periods</span>
        </div>

        <div className="rounded border border-rule bg-fog-2/30 p-2.5">
          <span className="text-muted block text-[10.5px]">Observed Window Events</span>
          <span className="font-mono text-sm font-bold text-lichen mt-0.5 block">
            {fmt(totalRecords)} records
          </span>
          <span className="text-muted text-[10.5px]">Mean: {displayPeriods.length > 0 ? (totalRecords / displayPeriods.length).toFixed(1) : 0}/period</span>
        </div>

        <div className="rounded border border-rule bg-fog-2/30 p-2.5">
          <span className="text-muted block text-[10.5px]">Peak Interval Tonnes</span>
          <span className="font-mono text-sm font-bold text-ink mt-0.5 block">
            {formatTonnes(maxTonnes)}
          </span>
          <span className="text-muted text-[10.5px]">Single period maximum</span>
        </div>

        <div className="rounded border border-rule bg-fog-2/30 p-2.5">
          <span className="text-muted block text-[10.5px]">Peak Interval Events</span>
          <span className="font-mono text-sm font-bold text-ink mt-0.5 block">
            {fmt(maxRecords)} records
          </span>
          <span className="text-muted text-[10.5px]">Single period maximum</span>
        </div>
      </div>

      {/* Bespoke Interactive SVG Timeline */}
      <div className="relative rounded-panel border border-rule bg-paper p-3 overflow-hidden select-none">
        {/* Legend */}
        <div className="flex items-center justify-end gap-4 text-xs mb-2">
          {(metricMode === "volume" || metricMode === "both") && (
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-xs bg-glacier border border-glacier-border" />
              <span className="font-medium text-ink">Volume (Tonnes)</span>
            </div>
          )}
          {(metricMode === "records" || metricMode === "both") && (
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-lichen border border-lichen-border" />
              <span className="font-medium text-ink">Frequency (Records)</span>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="h-64 flex items-center justify-center text-xs text-muted">
            Aggregating {currentPeriod} transaction timeline...
          </div>
        ) : displayPeriods.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-xs text-muted">
            No temporal retirement activity observed for the selected criteria.
          </div>
        ) : (
          <div className="w-full overflow-x-auto">
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="w-full h-auto min-w-[640px] overflow-visible text-muted"
              aria-hidden="true"
            >
              {/* Horizontal Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1.0].map((step, idx) => {
                const yVal = margin.top + plotHeight * (1 - step);
                return (
                  <g key={idx}>
                    <line
                      x1={margin.left}
                      y1={yVal}
                      x2={margin.left + plotWidth}
                      y2={yVal}
                      stroke="var(--color-rule)"
                      strokeWidth="1"
                      strokeDasharray={step === 0 ? "none" : "3,3"}
                    />
                    {/* Left Axis: Volume */}
                    {(metricMode === "volume" || metricMode === "both") && (
                      <text
                        x={margin.left - 8}
                        y={yVal + 3.5}
                        textAnchor="end"
                        className="font-mono text-[9px] fill-glacier font-semibold"
                      >
                        {formatTonnes(maxTonnes * step)}
                      </text>
                    )}
                    {/* Right Axis: Records */}
                    {(metricMode === "records" || metricMode === "both") && (
                      <text
                        x={margin.left + plotWidth + 8}
                        y={yVal + 3.5}
                        textAnchor="start"
                        className="font-mono text-[9px] fill-lichen font-semibold"
                      >
                        {fmt(Math.round(maxRecords * step))}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Bars (Volume) */}
              {(metricMode === "volume" || metricMode === "both") &&
                displayPeriods.map((p, i) => {
                  const stepX = plotWidth / displayPeriods.length;
                  const x = margin.left + i * stepX;
                  const barW = Math.max(1, stepX - 1);
                  const barH = Math.max(0, (p.total_tonnes / maxTonnes) * plotHeight);
                  const y = margin.top + plotHeight - barH;
                  const isHov = hoverIndex === i;

                  return (
                    <rect
                      key={p.period_label}
                      x={x}
                      y={y}
                      width={barW}
                      height={barH}
                      fill="var(--color-glacier)"
                      opacity={hoverIndex === null || isHov ? 0.85 : 0.4}
                      rx="1"
                    />
                  );
                })}

              {/* Line / Points (Records) */}
              {(metricMode === "records" || metricMode === "both") && (
                <g>
                  {(() => {
                    const pts = displayPeriods.map((p, i) => {
                      const stepX = plotWidth / displayPeriods.length;
                      const x = margin.left + i * stepX + stepX / 2;
                      const y = margin.top + plotHeight - (p.record_count / maxRecords) * plotHeight;
                      return { x, y };
                    });
                    const pathStr = pts.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");
                    return (
                      <path
                        d={pathStr}
                        fill="none"
                        stroke="var(--color-lichen)"
                        strokeWidth="1.8"
                        opacity="0.9"
                      />
                    );
                  })()}
                </g>
              )}

              {/* X Axis Labels (sparse) */}
              {displayPeriods.map((p, i) => {
                const stepCount = Math.max(1, Math.floor(displayPeriods.length / 10));
                if (i % stepCount === 0 || i === displayPeriods.length - 1) {
                  const stepX = plotWidth / displayPeriods.length;
                  const x = margin.left + i * stepX + stepX / 2;
                  return (
                    <g key={i}>
                      <line
                        x1={x}
                        y1={margin.top + plotHeight}
                        x2={x}
                        y2={margin.top + plotHeight + 4}
                        stroke="var(--color-rule-strong)"
                      />
                      <text
                        x={x}
                        y={margin.top + plotHeight + 16}
                        textAnchor="middle"
                        className="font-mono text-[9px] fill-muted"
                      >
                        {p.period_label.length > 7 ? p.period_label.slice(2) : p.period_label}
                      </text>
                    </g>
                  );
                }
                return null;
              })}

              {/* Interactive Hover Columns */}
              {displayPeriods.map((_, i) => {
                const stepX = plotWidth / displayPeriods.length;
                const x = margin.left + i * stepX;
                return (
                  <rect
                    key={i}
                    x={x}
                    y={margin.top}
                    width={stepX}
                    height={plotHeight}
                    fill="transparent"
                    className="cursor-crosshair"
                    onMouseEnter={() => setHoverIndex(i)}
                    onMouseLeave={() => setHoverIndex(null)}
                  />
                );
              })}

              {/* Hover Cursor Highlight */}
              {hoverIndex !== null && (
                <line
                  x1={margin.left + hoverIndex * (plotWidth / displayPeriods.length) + (plotWidth / displayPeriods.length) / 2}
                  y1={margin.top}
                  x2={margin.left + hoverIndex * (plotWidth / displayPeriods.length) + (plotWidth / displayPeriods.length) / 2}
                  y2={margin.top + plotHeight}
                  stroke="var(--color-ink)"
                  strokeWidth="1.2"
                  strokeDasharray="2,2"
                />
              )}
            </svg>
          </div>
        )}

        {/* Hover Inspector Banner */}
        {hoveredPeriod && (
          <div className="mt-2.5 rounded-panel border border-rule-strong bg-sheet p-3 flex flex-wrap items-center justify-between gap-4 text-xs font-mono shadow-sm">
            <div className="flex items-center gap-2">
              <Calendar size={13} className="text-muted" aria-hidden />
              <span className="font-bold text-ink">
                {hoveredPeriod.period_label}
              </span>
              <span className="text-muted text-[11px]">
                ({hoveredPeriod.period_start} to {hoveredPeriod.period_end})
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div>
                <span className="text-muted">Volume: </span>
                <strong className="text-glacier">{fmt(hoveredPeriod.total_tonnes)} t</strong>
              </div>
              <div>
                <span className="text-muted">Records: </span>
                <strong className="text-lichen">{fmt(hoveredPeriod.record_count)}</strong>
              </div>
              <div>
                <span className="text-muted">Avg/Event: </span>
                <strong className="text-ink">{fmt(hoveredPeriod.average_tonnes_per_record)} t</strong>
              </div>
              {hoveredTrend && (
                <div className="flex items-center gap-1.5 pl-2 border-l border-rule">
                  <span className="text-muted">Rolling Velocity:</span>
                  <TrendDirectionBadge direction={hoveredTrend.direction} />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Accessible Fallback Data Table */}
      {showTable && displayPeriods.length > 0 && (
        <div className="rounded-panel border border-rule bg-sheet overflow-hidden text-xs">
          <div className="px-3.5 py-2 bg-fog border-b border-rule font-mono font-semibold text-ink flex items-center justify-between">
            <span>Temporal Activity Table ({currentPeriod.toUpperCase()} · {displayPeriods.length} periods)</span>
            <span className="text-[11px] text-muted">Execution-date aggregation</span>
          </div>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-left font-mono">
              <thead className="bg-fog-2/40 text-muted text-[11px] border-b border-rule sticky top-0">
                <tr>
                  <th className="px-3 py-1.5">Period</th>
                  <th className="px-3 py-1.5 text-right">Volume (Tonnes)</th>
                  <th className="px-3 py-1.5 text-right">Record Count</th>
                  <th className="px-3 py-1.5 text-right">Avg Tonnes / Record</th>
                  <th className="px-3 py-1.5 text-right">Velocity Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule text-[11px]">
                {displayPeriods.map((p) => {
                  const t = trendMap.get(p.period_label);
                  return (
                    <tr key={p.period_label} className="hover:bg-fog/30">
                      <td className="px-3 py-1.5 font-bold text-ink">{p.period_label}</td>
                      <td className="px-3 py-1.5 text-right text-glacier">{fmt(p.total_tonnes)}</td>
                      <td className="px-3 py-1.5 text-right text-lichen">{fmt(p.record_count)}</td>
                      <td className="px-3 py-1.5 text-right text-muted">{fmt(p.average_tonnes_per_record)}</td>
                      <td className="px-3 py-1.5 text-right">
                        {t ? <TrendDirectionBadge direction={t.direction} /> : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

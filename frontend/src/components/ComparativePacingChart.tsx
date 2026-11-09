import { useState, useId, useMemo } from "react";
import { type CrossRegistryTrendsPeriod, fmt } from "../api";
import { Table, Calendar, TrendingUp } from "lucide-react";

interface ComparativePacingChartProps {
  yearlyTrends: CrossRegistryTrendsPeriod[];
  monthlyTrends: CrossRegistryTrendsPeriod[];
  initialPeriod?: "yearly" | "monthly";
}

export function ComparativePacingChart({
  yearlyTrends,
  monthlyTrends,
  initialPeriod = "yearly",
}: ComparativePacingChartProps) {
  const [period, setPeriod] = useState<"yearly" | "monthly">(initialPeriod);
  const [showTable, setShowTable] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const titleId = useId();
  const descId = useId();

  const data = period === "yearly" ? yearlyTrends : monthlyTrends;

  // Compute summary stats
  const { maxTonnes, totalVcsTonnes, totalGsTonnes, peakVcs, peakGs } = useMemo(() => {
    let maxT = 1;
    let sumVcs = 0;
    let sumGs = 0;
    let pVcs: CrossRegistryTrendsPeriod | null = null;
    let pGs: CrossRegistryTrendsPeriod | null = null;

    for (const d of data) {
      if (d.vcs_total_tonnes > maxT) maxT = d.vcs_total_tonnes;
      if (d.gs_total_tonnes > maxT) maxT = d.gs_total_tonnes;
      sumVcs += d.vcs_total_tonnes;
      sumGs += d.gs_total_tonnes;
      if (!pVcs || d.vcs_total_tonnes > pVcs.vcs_total_tonnes) pVcs = d;
      if (!pGs || d.gs_total_tonnes > pGs.gs_total_tonnes) pGs = d;
    }
    return {
      maxTonnes: maxT,
      totalVcsTonnes: sumVcs,
      totalGsTonnes: sumGs,
      peakVcs: pVcs,
      peakGs: pGs,
    };
  }, [data]);

  // SVG dimensions
  const svgWidth = 900;
  const svgHeight = 320;
  const margin = { top: 30, right: 25, bottom: 45, left: 75 };
  const plotWidth = svgWidth - margin.left - margin.right;
  const plotHeight = svgHeight - margin.top - margin.bottom;

  // Format tonnes compactly
  const formatTonnes = (val: number): string => {
    if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M t`;
    if (val >= 1_000) return `${(val / 1_000).toFixed(0)}k t`;
    return `${val.toFixed(0)} t`;
  };

  // Grid steps (4 horizontal intervals)
  const gridSteps = [0, 0.25, 0.5, 0.75, 1.0];

  const hoveredItem = hoveredIndex != null && hoveredIndex >= 0 && hoveredIndex < data.length ? data[hoveredIndex] : null;

  return (
    <section
      role="region"
      aria-labelledby={titleId}
      aria-describedby={descId}
      className="rounded-sheet border border-rule bg-sheet p-5 sm:p-6 space-y-5"
    >
      {/* Header with Title and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp size={18} className="text-glacier" aria-hidden />
            <h3 id={titleId} className="text-base font-bold text-ink">
              Comparative Retirement Pacing & Volume Trends
            </h3>
          </div>
          <p id={descId} className="text-xs text-ink-soft mt-1">
            Standard-by-standard time-series pacing showing retired tonnes across Verra VCS and Gold Standard.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Period Toggle */}
          <div className="inline-flex rounded-panel border border-rule-strong bg-fog p-0.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => {
                setPeriod("yearly");
                setHoveredIndex(null);
              }}
              className={`press rounded-[5px] px-3 py-1 transition-colors ${
                period === "yearly"
                  ? "bg-sheet text-ink shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
              aria-pressed={period === "yearly"}
            >
              Yearly ({yearlyTrends.length})
            </button>
            <button
              type="button"
              onClick={() => {
                setPeriod("monthly");
                setHoveredIndex(null);
              }}
              className={`press rounded-[5px] px-3 py-1 transition-colors ${
                period === "monthly"
                  ? "bg-sheet text-ink shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
              aria-pressed={period === "monthly"}
            >
              Monthly ({monthlyTrends.length})
            </button>
          </div>

          {/* Table Toggle Button */}
          <button
            type="button"
            onClick={() => setShowTable(!showTable)}
            className="press inline-flex items-center gap-1.5 rounded-panel border border-rule-strong bg-sheet px-3 py-1 text-xs font-medium text-ink hover:bg-fog transition-colors"
            aria-expanded={showTable}
          >
            <Table size={13} aria-hidden />
            {showTable ? "Hide Table" : "Show Table"}
          </button>
        </div>
      </div>

      {/* Summary Chips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="rounded-panel border border-rule bg-fog-2/40 p-2.5">
          <div className="flex items-center gap-1.5 text-muted">
            <span className="h-2 w-2 rounded-full bg-glacier" />
            <span className="font-semibold">Verra VCS Pacing</span>
          </div>
          <div className="font-mono text-sm font-bold text-ink mt-1">
            {formatTonnes(totalVcsTonnes)}
          </div>
          {peakVcs && (
            <div className="text-[11px] text-muted">
              Peak: {peakVcs.period_label} ({formatTonnes(peakVcs.vcs_total_tonnes)})
            </div>
          )}
        </div>

        <div className="rounded-panel border border-rule bg-fog-2/40 p-2.5">
          <div className="flex items-center gap-1.5 text-muted">
            <span className="h-2 w-2 rounded-full bg-lichen" />
            <span className="font-semibold">Gold Standard Pacing</span>
          </div>
          <div className="font-mono text-sm font-bold text-ink mt-1">
            {formatTonnes(totalGsTonnes)}
          </div>
          {peakGs && (
            <div className="text-[11px] text-muted">
              Peak: {peakGs.period_label} ({formatTonnes(peakGs.gs_total_tonnes)})
            </div>
          )}
        </div>

        <div className="rounded-panel border border-rule bg-fog-2/40 p-2.5">
          <span className="text-muted font-medium">Combined Volume</span>
          <div className="font-mono text-sm font-bold text-ink mt-1">
            {formatTonnes(totalVcsTonnes + totalGsTonnes)}
          </div>
          <div className="text-[11px] text-muted">
            Across {data.length} tracked {period === "yearly" ? "calendar years" : "months"}
          </div>
        </div>

        <div className="rounded-panel border border-rule bg-fog-2/40 p-2.5">
          <span className="text-muted font-medium">Reporting Standard</span>
          <div className="font-mono text-sm font-bold text-ink mt-1">
            Pure Retirements
          </div>
          <div className="text-[11px] text-muted">
            669 issuances strictly excluded
          </div>
        </div>
      </div>

      {/* Interactive Bespoke Chart */}
      <div className="relative rounded-panel border border-rule bg-paper p-3 overflow-hidden select-none">
        {/* Legend */}
        <div className="flex items-center justify-end gap-4 text-xs mb-2">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-xs bg-glacier border border-glacier-border" />
            <span className="font-medium text-ink">Verra VCS</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-xs bg-lichen border border-lichen-border" />
            <span className="font-medium text-ink">Gold Standard</span>
          </div>
        </div>

        <div className="w-full overflow-x-auto">
          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="w-full h-auto min-w-[640px] text-muted overflow-visible"
            aria-hidden="true"
          >
            {/* Background horizontal grid lines */}
            {gridSteps.map((step, idx) => {
              const yVal = margin.top + plotHeight * (1 - step);
              const tonnesVal = maxTonnes * step;
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
                  <text
                    x={margin.left - 8}
                    y={yVal + 3.5}
                    textAnchor="end"
                    className="font-mono text-[10px] fill-muted"
                  >
                    {formatTonnes(tonnesVal)}
                  </text>
                </g>
              );
            })}

            {/* Render Bars (Yearly) or Area Paths (Monthly) */}
            {period === "yearly" ? (
              // Yearly Grouped Bars
              data.map((item, idx) => {
                const groupStep = plotWidth / data.length;
                const groupX = margin.left + idx * groupStep;
                const barWidth = Math.max(4, Math.min(18, (groupStep - 6) / 2));
                const barGap = 2;
                const xCenter = groupX + groupStep / 2;

                const vcsHeight = Math.max(0, (item.vcs_total_tonnes / maxTonnes) * plotHeight);
                const gsHeight = Math.max(0, (item.gs_total_tonnes / maxTonnes) * plotHeight);

                const vcsX = xCenter - barWidth - barGap / 2;
                const gsX = xCenter + barGap / 2;

                const vcsY = margin.top + plotHeight - vcsHeight;
                const gsY = margin.top + plotHeight - gsHeight;

                const isHovered = hoveredIndex === idx;

                return (
                  <g
                    key={item.period_label}
                    onMouseEnter={() => setHoveredIndex(idx)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    className="cursor-pointer transition-opacity"
                    opacity={hoveredIndex === null || isHovered ? 1 : 0.45}
                  >
                    {/* Hover column background highlight */}
                    {isHovered && (
                      <rect
                        x={groupX}
                        y={margin.top}
                        width={groupStep}
                        height={plotHeight}
                        fill="var(--color-fog)"
                        opacity="0.6"
                        rx="4"
                      />
                    )}

                    {/* VCS Bar */}
                    <rect
                      x={vcsX}
                      y={vcsY}
                      width={barWidth}
                      height={vcsHeight}
                      fill="var(--color-glacier)"
                      rx="2"
                    />

                    {/* GS Bar */}
                    <rect
                      x={gsX}
                      y={gsY}
                      width={barWidth}
                      height={gsHeight}
                      fill="var(--color-lichen)"
                      rx="2"
                    />

                    {/* Period Label on X Axis */}
                    <text
                      x={xCenter}
                      y={margin.top + plotHeight + 18}
                      textAnchor="middle"
                      className={`font-mono text-[10px] ${
                        isHovered ? "font-bold fill-ink" : "fill-muted"
                      }`}
                    >
                      {item.period_label}
                    </text>
                  </g>
                );
              })
            ) : (
              // Monthly Area Chart
              <g>
                {/* VCS Path */}
                {(() => {
                  const ptsVcs = data.map((d, i) => {
                    const x = margin.left + (i / (data.length - 1)) * plotWidth;
                    const y = margin.top + plotHeight - (d.vcs_total_tonnes / maxTonnes) * plotHeight;
                    return { x, y };
                  });
                  const pathVcs = ptsVcs.reduce((acc, p, i) => `${acc} ${i === 0 ? "M" : "L"} ${p.x} ${p.y}`, "");
                  const areaVcs = `${pathVcs} L ${margin.left + plotWidth} ${margin.top + plotHeight} L ${margin.left} ${margin.top + plotHeight} Z`;

                  const ptsGs = data.map((d, i) => {
                    const x = margin.left + (i / (data.length - 1)) * plotWidth;
                    const y = margin.top + plotHeight - (d.gs_total_tonnes / maxTonnes) * plotHeight;
                    return { x, y };
                  });
                  const pathGs = ptsGs.reduce((acc, p, i) => `${acc} ${i === 0 ? "M" : "L"} ${p.x} ${p.y}`, "");
                  const areaGs = `${pathGs} L ${margin.left + plotWidth} ${margin.top + plotHeight} L ${margin.left} ${margin.top + plotHeight} Z`;

                  return (
                    <>
                      {/* VCS Area */}
                      <path d={areaVcs} fill="var(--color-glacier)" fillOpacity="0.12" />
                      <path d={pathVcs} fill="none" stroke="var(--color-glacier)" strokeWidth="1.8" />

                      {/* GS Area */}
                      <path d={areaGs} fill="var(--color-lichen)" fillOpacity="0.18" />
                      <path d={pathGs} fill="none" stroke="var(--color-lichen)" strokeWidth="1.8" />

                      {/* X Axis sparse ticks for monthly */}
                      {data.map((d, i) => {
                        // Show tick roughly once a year (e.g. month ending in -01)
                        if (d.period_label.endsWith("-01") || i === 0 || i === data.length - 1) {
                          const x = margin.left + (i / (data.length - 1)) * plotWidth;
                          return (
                            <g key={i}>
                              <line
                                x1={x}
                                y1={margin.top + plotHeight}
                                x2={x}
                                y2={margin.top + plotHeight + 5}
                                stroke="var(--color-rule-strong)"
                              />
                              <text
                                x={x}
                                y={margin.top + plotHeight + 18}
                                textAnchor="middle"
                                className="font-mono text-[9px] fill-muted"
                              >
                                {d.period_label.slice(0, 4)}
                              </text>
                            </g>
                          );
                        }
                        return null;
                      })}

                      {/* Interactive hover overlay lines for monthly */}
                      {data.map((_d, i) => {
                        const x = margin.left + (i / (data.length - 1)) * plotWidth;
                        const w = plotWidth / data.length;
                        return (
                          <rect
                            key={i}
                            x={x - w / 2}
                            y={margin.top}
                            width={w}
                            height={plotHeight}
                            fill="transparent"
                            className="cursor-crosshair"
                            onMouseEnter={() => setHoveredIndex(i)}
                            onMouseLeave={() => setHoveredIndex(null)}
                          />
                        );
                      })}

                      {/* Hover cursor */}
                      {hoveredIndex !== null && (
                        <g>
                          <line
                            x1={margin.left + (hoveredIndex / (data.length - 1)) * plotWidth}
                            y1={margin.top}
                            x2={margin.left + (hoveredIndex / (data.length - 1)) * plotWidth}
                            y2={margin.top + plotHeight}
                            stroke="var(--color-ink)"
                            strokeWidth="1.2"
                            strokeDasharray="2,2"
                          />
                          <circle
                            cx={margin.left + (hoveredIndex / (data.length - 1)) * plotWidth}
                            cy={margin.top + plotHeight - (data[hoveredIndex].vcs_total_tonnes / maxTonnes) * plotHeight}
                            r="3.5"
                            fill="var(--color-glacier)"
                            stroke="#fff"
                            strokeWidth="1.5"
                          />
                          <circle
                            cx={margin.left + (hoveredIndex / (data.length - 1)) * plotWidth}
                            cy={margin.top + plotHeight - (data[hoveredIndex].gs_total_tonnes / maxTonnes) * plotHeight}
                            r="3.5"
                            fill="var(--color-lichen)"
                            stroke="#fff"
                            strokeWidth="1.5"
                          />
                        </g>
                      )}
                    </>
                  );
                })()}
              </g>
            )}
          </svg>
        </div>

        {/* Floating Tooltip Card */}
        {hoveredItem && (
          <div className="mt-3 rounded-panel border border-rule-strong bg-sheet px-3.5 py-2.5 shadow-sm text-xs flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Calendar size={14} className="text-muted" aria-hidden />
              <span className="font-mono font-bold text-ink">
                Period: {hoveredItem.period_label}
              </span>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-glacier" />
                <span className="text-muted">VCS:</span>
                <span className="font-mono font-bold text-ink">
                  {fmt(hoveredItem.vcs_total_tonnes)} t
                </span>
                <span className="text-muted font-mono text-[11px]">
                  ({fmt(hoveredItem.vcs_record_count)} records)
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-lichen" />
                <span className="text-muted">GS:</span>
                <span className="font-mono font-bold text-ink">
                  {fmt(hoveredItem.gs_total_tonnes)} t
                </span>
                <span className="text-muted font-mono text-[11px]">
                  ({fmt(hoveredItem.gs_record_count)} records)
                </span>
              </div>

              <div className="border-l border-rule pl-3 text-muted">
                Combined:{" "}
                <span className="font-mono font-bold text-ink">
                  {fmt(hoveredItem.combined_total_tonnes)} t
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Accessible Fallback Data Table */}
      {showTable && (
        <div className="rounded-panel border border-rule bg-sheet overflow-hidden">
          <div className="px-4 py-2.5 bg-fog border-b border-rule flex items-center justify-between">
            <span className="font-mono text-xs font-semibold text-ink">
              Data Table — {period.toUpperCase()} PACING ({data.length} periods)
            </span>
            <span className="text-xs text-muted">Retirement-only tonnes</span>
          </div>
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-fog-2/60 text-muted font-mono text-[11px] sticky top-0 border-b border-rule">
                <tr>
                  <th className="px-3 py-2">Period</th>
                  <th className="px-3 py-2 text-right">VCS Tonnes</th>
                  <th className="px-3 py-2 text-right">VCS Records</th>
                  <th className="px-3 py-2 text-right">GS Tonnes</th>
                  <th className="px-3 py-2 text-right">GS Records</th>
                  <th className="px-3 py-2 text-right">Combined Tonnes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule font-mono">
                {data.map((row) => (
                  <tr key={row.period_label} className="hover:bg-fog/40">
                    <td className="px-3 py-1.5 font-bold text-ink">{row.period_label}</td>
                    <td className="px-3 py-1.5 text-right text-glacier">{fmt(row.vcs_total_tonnes)}</td>
                    <td className="px-3 py-1.5 text-right text-muted">{fmt(row.vcs_record_count)}</td>
                    <td className="px-3 py-1.5 text-right text-lichen">{fmt(row.gs_total_tonnes)}</td>
                    <td className="px-3 py-1.5 text-right text-muted">{fmt(row.gs_record_count)}</td>
                    <td className="px-3 py-1.5 text-right font-bold text-ink">{fmt(row.combined_total_tonnes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

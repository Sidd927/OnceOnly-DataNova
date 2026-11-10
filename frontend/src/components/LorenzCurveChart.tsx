import { useState, useId, useMemo } from "react";
import { Table, Info, Activity } from "lucide-react";
import { pct } from "../api";

interface LorenzCurveChartProps {
  shares: Record<string, number> | number[];
  title?: string;
  subtitle?: string;
  giniOverride?: number;
  label?: string;
}

export function LorenzCurveChart({
  shares,
  title = "Beneficiary Allocation Lorenz Curve",
  subtitle = "Cumulative population share versus cumulative allocation-volume share under sorted distribution.",
  giniOverride,
  label = "Portfolio Disclosed Beneficiaries",
}: LorenzCurveChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);

  const titleId = useId();
  const descId = useId();

  // Compute sorted observations and cumulative coordinates
  const { points, gini, deciles, totalObservations } = useMemo(() => {
    let vals: number[] = [];
    if (Array.isArray(shares)) {
      vals = shares.filter((x) => x > 0);
    } else if (typeof shares === "object" && shares !== null) {
      vals = Object.values(shares).filter((x) => x > 0);
    }

    if (vals.length === 0) {
      return {
        points: [{ p: 0, L: 0 }, { p: 1, L: 1 }],
        gini: 0,
        deciles: [],
        totalObservations: 0,
      };
    }

    // Sort ascending
    vals.sort((a, b) => a - b);
    const n = vals.length;
    const total = vals.reduce((acc, x) => acc + x, 0);

    // Compute empirical Gini if not overridden
    let calcGini = 0;
    if (total > 0 && n > 1) {
      const weightedSum = vals.reduce((acc, y, idx) => acc + (idx + 1) * y, 0);
      calcGini = (2.0 * weightedSum) / (n * total) - (n + 1.0) / n;
    }
    const finalGini = giniOverride != null ? giniOverride : Math.max(0, Math.min(1, calcGini));

    // Sample ~60 points for smooth SVG curve
    const pts: { p: number; L: number }[] = [{ p: 0, L: 0 }];
    const sampleCount = Math.min(60, n);
    let runningSum = 0;
    let nextSampleIdx = Math.floor(n / sampleCount);

    for (let i = 0; i < n; i++) {
      runningSum += vals[i];
      if (i === nextSampleIdx || i === n - 1) {
        pts.push({
          p: (i + 1) / n,
          L: runningSum / total,
        });
        nextSampleIdx += Math.floor(n / sampleCount);
      }
    }
    // Ensure final point is exactly (1, 1)
    if (pts[pts.length - 1].p < 1) {
      pts.push({ p: 1, L: 1 });
    }

    // Compute deciles (10%, 20%, ..., 90%, 99%)
    const decileThresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99];
    const decileList = decileThresholds.map((targetP) => {
      // Bottom floor(p·n) observations; the previous slice included one extra observation.
      const count = Math.min(n, Math.floor(targetP * n));
      const cumVol = vals.slice(0, count).reduce((acc, x) => acc + x, 0);
      return {
        populationShare: targetP,
        volumeShare: total > 0 ? cumVol / total : 0,
      };
    });

    return {
      points: pts,
      gini: finalGini,
      deciles: decileList,
      totalObservations: n,
    };
  }, [shares, giniOverride]);

  // Displays "—" when there are no observations instead of a fabricated 0 %.
  const shareAt = (p: number, top = false) => {
    const d = deciles.find((x) => x.populationShare === p);
    if (!d || totalObservations === 0) return "—";
    return pct(top ? 1 - d.volumeShare : d.volumeShare, 2);
  };

  // SVG Geometry
  const width = 500;
  const height = 360;
  const margin = { top: 25, right: 30, bottom: 45, left: 60 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  // Coordinate transforms: (p, L) in [0, 1] -> (x, y)
  const getX = (p: number) => margin.left + p * plotWidth;
  const getY = (L: number) => margin.top + (1 - L) * plotHeight;

  // Build SVG Path for Lorenz Curve
  const lorenzPath = points.reduce(
    (acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${getX(pt.p)} ${getY(pt.L)}`,
    ""
  );

  // Area between diagonal (perfect equality) and curve
  const inequalityAreaPath = `${lorenzPath} L ${getX(1)} ${getY(1)} L ${getX(0)} ${getY(0)} Z`;

  const activePoint = hoverIndex !== null && hoverIndex >= 0 && hoverIndex < points.length ? points[hoverIndex] : null;

  return (
    <div
      role="region"
      aria-labelledby={titleId}
      aria-describedby={descId}
      className="rounded-sheet border border-rule bg-sheet p-5 space-y-4"
    >
      {/* Header with Title and Gini Token */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-rule pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-glacier" aria-hidden />
            <h4 id={titleId} className="text-sm font-bold text-ink">
              {title}
            </h4>
          </div>
          <p id={descId} className="text-xs text-ink-soft mt-0.5">
            {subtitle}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold px-2.5 py-1 rounded bg-glacier-wash text-glacier border border-glacier/30">
            Gini: {gini.toFixed(4)}
          </span>
          <button
            type="button"
            onClick={() => setShowTable(!showTable)}
            className="press inline-flex items-center gap-1 rounded border border-rule-strong bg-paper px-2.5 py-1 text-xs font-medium text-ink hover:bg-fog"
            aria-expanded={showTable}
          >
            <Table size={12} aria-hidden />
            {showTable ? "Hide Deciles" : "Decile Table"}
          </button>
        </div>
      </div>

      {/* SVG Canvas and Metrics */}
      <div className="grid lg:grid-cols-3 gap-5 items-center">
        {/* Left 2 Cols: Bespoke SVG Chart */}
        <div className="lg:col-span-2 relative rounded-panel border border-rule bg-paper p-3 overflow-hidden select-none">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-auto overflow-visible"
            aria-hidden="true"
          >
            {/* Grid Lines */}
            {[0, 0.25, 0.5, 0.75, 1.0].map((step, idx) => {
              const xVal = getX(step);
              const yVal = getY(step);
              return (
                <g key={idx}>
                  {/* Vertical grid */}
                  <line
                    x1={xVal}
                    y1={margin.top}
                    x2={xVal}
                    y2={margin.top + plotHeight}
                    stroke="var(--color-rule)"
                    strokeWidth="1"
                    strokeDasharray={step === 0 || step === 1 ? "none" : "2,2"}
                  />
                  <text
                    x={xVal}
                    y={margin.top + plotHeight + 16}
                    textAnchor="middle"
                    className="font-mono text-[9px] fill-muted"
                  >
                    {pct(step, 0)}
                  </text>

                  {/* Horizontal grid */}
                  <line
                    x1={margin.left}
                    y1={yVal}
                    x2={margin.left + plotWidth}
                    y2={yVal}
                    stroke="var(--color-rule)"
                    strokeWidth="1"
                    strokeDasharray={step === 0 || step === 1 ? "none" : "2,2"}
                  />
                  <text
                    x={margin.left - 8}
                    y={yVal + 3}
                    textAnchor="end"
                    className="font-mono text-[9px] fill-muted"
                  >
                    {pct(step, 0)}
                  </text>
                </g>
              );
            })}

            {/* Line of Perfect Equality (Diagonal) */}
            <line
              x1={getX(0)}
              y1={getY(0)}
              x2={getX(1)}
              y2={getY(1)}
              stroke="var(--color-ink-soft)"
              strokeWidth="1.5"
              strokeDasharray="4,4"
            />

            {/* Inequality Gap Area */}
            <path
              d={inequalityAreaPath}
              fill="var(--color-glacier)"
              fillOpacity="0.12"
            />

            {/* Empirical Lorenz Curve */}
            <path
              d={lorenzPath}
              fill="none"
              stroke="var(--color-glacier)"
              strokeWidth="2.4"
            />

            {/* Axis Titles */}
            <text
              x={margin.left + plotWidth / 2}
              y={margin.top + plotHeight + 35}
              textAnchor="middle"
              className="font-mono text-[10px] font-semibold fill-ink"
            >
              Cumulative Share of Population (ascending order)
            </text>
            <text
              x={-(margin.top + plotHeight / 2)}
              y={margin.left - 42}
              textAnchor="middle"
              transform="rotate(-90)"
              className="font-mono text-[10px] font-semibold fill-ink"
            >
              Cumulative Share of Allocation Volume
            </text>

            {/* Interactive Hover Nodes */}
            {points.map((pt, i) => (
              <circle
                key={i}
                cx={getX(pt.p)}
                cy={getY(pt.L)}
                r="4.5"
                fill="transparent"
                className="cursor-crosshair"
                onMouseEnter={() => setHoverIndex(i)}
                onMouseLeave={() => setHoverIndex(null)}
              />
            ))}

            {/* Hover Cursor Highlight */}
            {activePoint && (
              <g>
                <line
                  x1={getX(activePoint.p)}
                  y1={margin.top}
                  x2={getX(activePoint.p)}
                  y2={margin.top + plotHeight}
                  stroke="var(--color-ink)"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
                <circle
                  cx={getX(activePoint.p)}
                  cy={getY(activePoint.L)}
                  r="4"
                  fill="var(--color-glacier)"
                  stroke="#fff"
                  strokeWidth="2"
                />
              </g>
            )}
          </svg>

          {/* Hover Status Display */}
          {activePoint ? (
            <div className="mt-2 text-center text-xs font-mono bg-fog/80 py-1 px-2 rounded text-ink">
              Bottom <strong>{pct(activePoint.p, 1)}</strong> of claimants hold{" "}
              <strong className="text-glacier">{pct(activePoint.L, 2)}</strong> of total volume.
            </div>
          ) : (
            <div className="mt-2 text-center text-[11px] text-muted italic">
              Hover across the curve to inspect cumulative concentration coordinates.
            </div>
          )}
        </div>

        {/* Right 1 Col: Key Concentration Coordinates */}
        <div className="space-y-3 text-xs">
          <div className="rounded-panel border border-rule bg-fog-2/30 p-3 space-y-2">
            <span className="font-mono text-[11px] font-bold uppercase text-ink block">
              Inequality Distribution Metrics
            </span>
            <div className="space-y-1.5 font-mono text-ink-soft">
              <div className="flex justify-between border-b border-rule/60 pb-1">
                <span className="text-muted">Labels plotted:</span>
                <span className="font-bold text-ink">{totalObservations.toLocaleString()}</span>
              </div>
              <div className="flex justify-between border-b border-rule/60 pb-1">
                <span className="text-muted">Gini Coefficient:</span>
                <span className="font-bold text-glacier">{gini.toFixed(4)}</span>
              </div>
              <div className="flex justify-between border-b border-rule/60 pb-1">
                <span className="text-muted">Bottom 50% Share:</span>
                <span className="font-bold text-ink">
                  {shareAt(0.5)}
                </span>
              </div>
              <div className="flex justify-between border-b border-rule/60 pb-1">
                <span className="text-muted">Bottom 90% Share:</span>
                <span className="font-bold text-ink">
                  {shareAt(0.9)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Top 1% Share:</span>
                <span className="font-bold text-crimson">
                  {shareAt(0.99, true)}
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-panel border border-rule bg-sheet p-3 text-[11px] text-muted leading-relaxed">
            <div className="flex items-center gap-1 font-semibold text-ink-soft mb-1">
              <Info size={12} className="text-glacier" aria-hidden />
              <span>Lorenz Curve Interpretation</span>
            </div>
            The Lorenz curve plots cumulative population percentage against cumulative credit volume.
            The shaded area between the line of perfect equality ($y = x$) and the curve measures concentration.
          </div>
        </div>
      </div>

      {/* Decile Table Fallback */}
      {showTable && deciles.length > 0 && (
        <div className="rounded-panel border border-rule bg-sheet overflow-hidden text-xs">
          <div className="px-3.5 py-2 bg-fog border-b border-rule font-mono font-semibold text-ink">
            Empirical Decile Distribution Breakdown ({label})
          </div>
          <table className="w-full text-left font-mono">
            <thead className="bg-fog-2/40 text-muted text-[11px] border-b border-rule">
              <tr>
                <th className="px-3 py-1.5">Population Percentile</th>
                <th className="px-3 py-1.5 text-right">Cumulative Volume Share</th>
                <th className="px-3 py-1.5 text-right">Top Residual Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule text-[11px]">
              {deciles.map((d, i) => (
                <tr key={i} className="hover:bg-fog/30">
                  <td className="px-3 py-1 text-ink font-semibold">
                    Bottom {pct(d.populationShare, 0)}
                  </td>
                  <td className="px-3 py-1 text-right text-glacier">
                    {pct(d.volumeShare, 3)}
                  </td>
                  <td className="px-3 py-1 text-right text-muted">
                    Top {pct(1 - d.populationShare, 0)} holds {pct(1 - d.volumeShare, 3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

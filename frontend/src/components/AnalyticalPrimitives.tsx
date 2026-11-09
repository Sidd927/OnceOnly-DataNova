import { type ReactNode } from "react";
import { AlertTriangle, AlertOctagon, CheckCircle2, HelpCircle, Info, ShieldAlert, Sparkles, Layers } from "lucide-react";
import type {
  EvidenceSeverity,
  EvidenceStrength,
  AssessmentStatus,
  ReviewPriority,
  EvidenceCategory,
  SourceStage,
} from "../api";

export function SeverityBadge({
  severity,
  size = "sm",
}: {
  severity: EvidenceSeverity | string;
  size?: "sm" | "md";
}) {
  const sev = (severity || "INFORMATIONAL").toUpperCase();
  const pad = size === "md" ? "px-2.5 py-1 text-xs" : "px-2 py-0.5 text-[11px]";

  switch (sev) {
    case "CRITICAL":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-crimson/40 bg-crimson-wash font-semibold text-crimson ${pad}`} title="Critical: direct structural clash or blocking finding">
          <AlertOctagon size={size === "md" ? 14 : 12} aria-hidden strokeWidth={2.2} />
          CRITICAL
        </span>
      );
    case "HIGH":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-crimson/30 bg-crimson-wash/70 font-semibold text-crimson ${pad}`} title="High: significant anomaly warranting priority review">
          <AlertTriangle size={size === "md" ? 14 : 12} aria-hidden strokeWidth={2.2} />
          HIGH
        </span>
      );
    case "MODERATE":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-ochre/40 bg-ochre-wash font-semibold text-ochre ${pad}`} title="Moderate: material deviation warranting standard verification">
          <AlertTriangle size={size === "md" ? 14 : 12} aria-hidden strokeWidth={2.2} />
          MODERATE
        </span>
      );
    case "LOW":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-slate/40 bg-slate-wash font-semibold text-ink-soft ${pad}`} title="Low: minor anomaly or routine data sparsity">
          <Info size={size === "md" ? 14 : 12} aria-hidden strokeWidth={2.2} />
          LOW
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-glacier/30 bg-glacier-wash font-semibold text-glacier ${pad}`} title="Informational: structural context or benign observation">
          <Info size={size === "md" ? 14 : 12} aria-hidden strokeWidth={2.2} />
          INFO
        </span>
      );
  }
}

export function PriorityBadge({
  priority,
  size = "sm",
}: {
  priority: ReviewPriority | string;
  size?: "sm" | "md";
}) {
  const prio = (priority || "NONE").toUpperCase();
  const pad = size === "md" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs";

  switch (prio) {
    case "URGENT":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-crimson bg-crimson font-bold text-white shadow-sm ${pad}`} title="Urgent: immediate hold pending evidence clearance">
          <ShieldAlert size={size === "md" ? 15 : 13} aria-hidden strokeWidth={2.4} />
          URGENT PRIORITY
        </span>
      );
    case "HIGH":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-crimson/50 bg-crimson-wash font-bold text-crimson ${pad}`} title="High: priority investigative inquiry">
          <AlertOctagon size={size === "md" ? 15 : 13} aria-hidden strokeWidth={2.2} />
          HIGH PRIORITY
        </span>
      );
    case "MEDIUM":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-ochre/40 bg-ochre-wash font-semibold text-ochre ${pad}`} title="Medium: standard compliance review">
          <AlertTriangle size={size === "md" ? 15 : 13} aria-hidden strokeWidth={2.2} />
          MEDIUM PRIORITY
        </span>
      );
    case "LOW":
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-slate/40 bg-slate-wash font-medium text-ink-soft ${pad}`} title="Low: background informational monitoring">
          <Info size={size === "md" ? 15 : 13} aria-hidden strokeWidth={2} />
          LOW PRIORITY
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-token border border-lichen/40 bg-lichen-wash font-semibold text-lichen ${pad}`} title="None: routine clearance, no elevated review triggers">
          <CheckCircle2 size={size === "md" ? 15 : 13} aria-hidden strokeWidth={2.2} />
          ROUTINE / CLEAR
        </span>
      );
  }
}

export function AssessmentStatusBadge({
  status,
  size = "md",
}: {
  status: AssessmentStatus | string;
  size?: "sm" | "md";
}) {
  const s = (status || "NO_MATERIAL_SIGNAL").toUpperCase();
  const pad = size === "md" ? "px-3 py-1.5 text-sm" : "px-2 py-0.5 text-xs";

  switch (s) {
    case "ELEVATED_REVIEW_PRIORITY":
      return (
        <span className={`inline-flex items-center gap-2 rounded-token border border-crimson/40 bg-crimson-wash font-bold text-crimson ${pad}`}>
          <AlertOctagon size={16} aria-hidden strokeWidth={2.2} />
          Elevated Review Priority
        </span>
      );
    case "REVIEW_RECOMMENDED":
      return (
        <span className={`inline-flex items-center gap-2 rounded-token border border-ochre/40 bg-ochre-wash font-semibold text-ochre ${pad}`}>
          <AlertTriangle size={16} aria-hidden strokeWidth={2.2} />
          Review Recommended
        </span>
      );
    case "CONFLICTING_EVIDENCE":
      return (
        <span className={`inline-flex items-center gap-2 rounded-token border border-ochre/40 bg-ochre-wash font-semibold text-ochre ${pad}`}>
          <HelpCircle size={16} aria-hidden strokeWidth={2.2} />
          Conflicting Evidence
        </span>
      );
    case "INSUFFICIENT_EVIDENCE":
      return (
        <span className={`inline-flex items-center gap-2 rounded-token border border-slate/40 bg-slate-wash font-medium text-ink-soft ${pad}`}>
          <HelpCircle size={16} aria-hidden strokeWidth={2} />
          Insufficient Evidence
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-2 rounded-token border border-lichen/40 bg-lichen-wash font-semibold text-lichen ${pad}`}>
          <CheckCircle2 size={16} aria-hidden strokeWidth={2.2} />
          No Material Signal Detected
        </span>
      );
  }
}

export function EvidenceStrengthBadge({ strength }: { strength: EvidenceStrength | string }) {
  const st = (strength || "MODERATE").toUpperCase();
  switch (st) {
    case "STRONG":
      return (
        <span className="inline-flex items-center gap-1 rounded-token border border-lichen/40 bg-lichen-wash px-1.5 py-0.5 text-[10.5px] font-semibold text-lichen" title="Strong: mathematical proof or exact immutable fact">
          Strong Evidence
        </span>
      );
    case "CONTRADICTORY":
      return (
        <span className="inline-flex items-center gap-1 rounded-token border border-ochre/40 bg-ochre-wash px-1.5 py-0.5 text-[10.5px] font-semibold text-ochre" title="Contradictory: directly counters equivalent concern">
          Contradictory
        </span>
      );
    case "WEAK":
      return (
        <span className="inline-flex items-center gap-1 rounded-token border border-slate/30 bg-slate-wash px-1.5 py-0.5 text-[10.5px] font-medium text-muted" title="Weak: indirect heuristic or token similarity">
          Weak Evidence
        </span>
      );
    case "UNRESOLVED":
      return (
        <span className="inline-flex items-center gap-1 rounded-token border border-slate/30 bg-slate-wash px-1.5 py-0.5 text-[10.5px] font-medium text-muted" title="Unresolved: missing attributes prevent full confidence">
          Unresolved
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-token border border-glacier/30 bg-glacier-wash px-1.5 py-0.5 text-[10.5px] font-semibold text-glacier" title="Moderate: solid corroboration across standard metrics">
          Moderate
        </span>
      );
  }
}

export function CategoryBadge({ category }: { category: EvidenceCategory | string }) {
  const cat = (category || "").toUpperCase();
  const labelMap: Record<string, string> = {
    ENTITY_IDENTITY: "Entity Resolution",
    ALLOCATION_RECONCILIATION: "Interval Overlap",
    BENEFICIARY_CONCENTRATION: "Concentration",
    BATCH_FRAGMENTATION: "Fragmentation",
    TEMPORAL_DYNAMICS: "Temporal Dynamics",
    CROSS_REGISTRY: "Cross-Registry",
  };
  const label = labelMap[cat] || cat.replace(/_/g, " ");

  return (
    <span className="inline-flex items-center gap-1 rounded-token border border-rule-strong bg-fog px-1.5 py-0.5 font-mono text-[10.5px] font-medium text-ink-soft">
      <Layers size={11} aria-hidden className="text-muted" />
      {label}
    </span>
  );
}

export function SourceStageBadge({ stage }: { stage: SourceStage | string }) {
  const st = (stage || "").toUpperCase();
  const labelMap: Record<string, string> = {
    PHASE_2A_ENTITY_RESOLUTION: "Phase 2A: Entity Resolution",
    PHASE_2B_RECONCILIATION: "Phase 2B: Reconciliation",
    PHASE_2C_STAGE_1_CONCENTRATION: "Phase 2C.1: Concentration",
    PHASE_2C_STAGE_1_FRAGMENTATION: "Phase 2C.1: Fragmentation",
    PHASE_2C_STAGE_2_TEMPORAL: "Phase 2C.2: Temporal",
    PHASE_2C_STAGE_3_CROSS_REGISTRY: "Phase 2C.3: Cross-Registry",
  };
  const label = labelMap[st] || st.replace(/_/g, " ");

  return (
    <span className="inline-flex items-center gap-1 rounded-token border border-glacier/25 bg-glacier-wash/50 px-1.5 py-0.5 font-mono text-[10px] text-glacier">
      <Sparkles size={10} aria-hidden />
      {label}
    </span>
  );
}

export function MetricTile({
  label,
  value,
  subtext,
  token,
}: {
  label: string;
  value: ReactNode;
  subtext?: ReactNode;
  token?: ReactNode;
}) {
  return (
    <div className="rounded-panel border border-rule bg-sheet p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted">{label}</span>
        {token}
      </div>
      <div className="mt-1 font-mono text-2xl font-bold tracking-tight text-ink">
        {value}
      </div>
      {subtext && (
        <div className="mt-1.5 text-xs text-ink-soft leading-relaxed">
          {subtext}
        </div>
      )}
    </div>
  );
}

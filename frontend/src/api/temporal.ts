import { request } from "./client";

export type AggregationPeriod = "daily" | "weekly" | "monthly";

export type TrendDirection =
  | "ACCELERATING"
  | "DECELERATING"
  | "STABLE"
  | "INSUFFICIENT_HISTORY";

export type BurstType =
  | "VOLUME_SPIKE"
  | "FREQUENCY_SPIKE"
  | "DUAL_BURST"
  | "NO_BURST";

export type GapClassification =
  | "MONITORING_INACTIVITY_INTERVAL"
  | "DATA_COLLECTION_COVERAGE_GAP"
  | "NORMAL_PACING"
  | "INSUFFICIENT_OBSERVATION_SPAN";

export interface TemporalPeriodActivity {
  period_label: string;
  start_date: string;
  end_date: string;
  total_units: number;
  record_count: number;
  active_days: number;
}

export interface TemporalActivityResponse {
  registry?: string | null;
  project_id?: string | null;
  period_type: AggregationPeriod;
  timeline: TemporalPeriodActivity[];
  summary: {
    total_units: number;
    total_records: number;
    total_periods: number;
    active_periods: number;
    earliest_date?: string | null;
    latest_date?: string | null;
  };
}

export interface TemporalTrendPeriod {
  period_label: string;
  current_units: number;
  rolling_avg: number;
  change_pct: number;
  direction: TrendDirection;
}

export interface TemporalTrendsResponse {
  registry?: string | null;
  project_id?: string | null;
  period_type: AggregationPeriod;
  window_size: number;
  trends: TemporalTrendPeriod[];
  summary: {
    overall_direction: TrendDirection;
    mean_volume: number;
    std_volume: number;
  };
}

export interface TemporalBurstPeriod {
  period_label: string;
  units: number;
  records: number;
  burst_type: BurstType;
  mad_multiplier: number;
  is_burst: boolean;
  explanation: string;
}

export interface TemporalBurstsResponse {
  registry?: string | null;
  project_id?: string | null;
  sensitivity: number;
  baseline_mad: number;
  bursts: TemporalBurstPeriod[];
  summary: {
    total_bursts: number;
    burst_periods: string[];
    max_mad_multiplier: number;
  };
}

export interface TemporalGapItem {
  gap_start: string;
  gap_end: string;
  gap_duration_days: number;
  prior_units: number;
  classification: GapClassification;
  explanation: string;
}

export interface TemporalGapsResponse {
  registry?: string | null;
  project_id?: string | null;
  period_type: AggregationPeriod;
  gaps: TemporalGapItem[];
  summary: {
    total_gaps: number;
    longest_gap_days: number;
    total_gap_days: number;
  };
}

export const temporalApi = {
  getActivity: (params?: {
    registry?: string;
    project_id?: string;
    start_date?: string;
    end_date?: string;
    period?: AggregationPeriod;
  }) => {
    const q = new URLSearchParams();
    if (params?.registry) q.set("registry", params.registry);
    if (params?.project_id) q.set("project_id", params.project_id);
    if (params?.start_date) q.set("start_date", params.start_date);
    if (params?.end_date) q.set("end_date", params.end_date);
    if (params?.period) q.set("period", params.period);
    const qs = q.toString();
    return request<TemporalActivityResponse>(`/api/analytics/temporal/activity${qs ? `?${qs}` : ""}`);
  },
  getTrends: (params?: {
    registry?: string;
    project_id?: string;
    start_date?: string;
    end_date?: string;
    period?: AggregationPeriod;
    window?: number;
    threshold_pct?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.registry) q.set("registry", params.registry);
    if (params?.project_id) q.set("project_id", params.project_id);
    if (params?.start_date) q.set("start_date", params.start_date);
    if (params?.end_date) q.set("end_date", params.end_date);
    if (params?.period) q.set("period", params.period);
    if (params?.window != null) q.set("window", String(params.window));
    if (params?.threshold_pct != null) q.set("threshold_pct", String(params.threshold_pct));
    const qs = q.toString();
    return request<TemporalTrendsResponse>(`/api/analytics/temporal/trends${qs ? `?${qs}` : ""}`);
  },
  getBursts: (params?: {
    registry?: string;
    project_id?: string;
    start_date?: string;
    end_date?: string;
    period?: AggregationPeriod;
    sensitivity?: number;
    min_history?: number;
    min_tonne_threshold?: number;
    min_record_threshold?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.registry) q.set("registry", params.registry);
    if (params?.project_id) q.set("project_id", params.project_id);
    if (params?.start_date) q.set("start_date", params.start_date);
    if (params?.end_date) q.set("end_date", params.end_date);
    if (params?.period) q.set("period", params.period);
    if (params?.sensitivity != null) q.set("sensitivity", String(params.sensitivity));
    if (params?.min_history != null) q.set("min_history", String(params.min_history));
    if (params?.min_tonne_threshold != null) q.set("min_tonne_threshold", String(params.min_tonne_threshold));
    if (params?.min_record_threshold != null) q.set("min_record_threshold", String(params.min_record_threshold));
    const qs = q.toString();
    return request<TemporalBurstsResponse>(`/api/analytics/temporal/bursts${qs ? `?${qs}` : ""}`);
  },
  getGaps: (params?: {
    registry?: string;
    project_id?: string;
    start_date?: string;
    end_date?: string;
    period?: AggregationPeriod;
  }) => {
    const q = new URLSearchParams();
    if (params?.registry) q.set("registry", params.registry);
    if (params?.project_id) q.set("project_id", params.project_id);
    if (params?.start_date) q.set("start_date", params.start_date);
    if (params?.end_date) q.set("end_date", params.end_date);
    if (params?.period) q.set("period", params.period);
    const qs = q.toString();
    return request<TemporalGapsResponse>(`/api/analytics/temporal/gaps${qs ? `?${qs}` : ""}`);
  },
};

import { request } from "./client";

export type AggregationPeriod = "daily" | "weekly" | "monthly";

export type TrendDirection =
  | "increasing"
  | "decreasing"
  | "stable"
  | "INSUFFICIENT_HISTORY"
  | string;

export type BurstType =
  | "VOLUME"
  | "RECORD_COUNT"
  | "DUAL"
  | "BOTH"
  | "NONE"
  | string;

export type GapClassification =
  | "EXTENDED_INACTIVITY_INTERVAL"
  | "INTERMITTENT_ZERO_ACTIVITY_INTERVAL"
  | "SUSTAINED_ZERO_ACTIVITY_INTERVAL"
  | string;

export interface TemporalActivityPeriod {
  period_start: string;
  period_end: string;
  period_label: string;
  record_count: number;
  total_tonnes: number;
  average_tonnes_per_record: number;
  records_with_usable_dates: number;
  records_with_missing_or_invalid_dates: number;
  usable_date_quantity: number;
  excluded_date_quantity: number;
}

export interface TemporalActivityResponse {
  registry?: string | null;
  project_id?: string | null;
  period_type: AggregationPeriod | string;
  total_periods: number;
  total_records: number;
  total_tonnes: number;
  active_periods_count: number;
  zero_activity_periods_count: number;
  earliest_date_observed?: string | null;
  latest_date_observed?: string | null;
  disclaimer: string;
  periods: TemporalActivityPeriod[];
}

export interface TemporalTrendPeriod {
  period_start: string;
  period_end: string;
  period_label: string;
  record_count: number;
  total_tonnes: number;
  average_tonnes_per_record: number;
  rolling_average_records?: number | null;
  rolling_average_tonnes?: number | null;
  record_count_change?: number | null;
  tonne_quantity_change?: number | null;
  record_count_pct_change?: number | null;
  tonne_quantity_pct_change?: number | null;
  direction: TrendDirection;
  has_sufficient_history: boolean;
  data_coverage_status: string;
}

export interface TemporalTrendsResponse {
  registry?: string | null;
  project_id?: string | null;
  period_type: AggregationPeriod | string;
  rolling_window: number;
  direction_threshold_pct: number;
  total_periods: number;
  sufficient_history_periods: number;
  insufficient_history_periods: number;
  disclaimer: string;
  trends: TemporalTrendPeriod[];
}

export interface TemporalBurstPeriod {
  period_start: string;
  period_end: string;
  period_label: string;
  observed_records: number;
  baseline_median_records: number;
  baseline_mad_records: number;
  record_burst_threshold: number;
  record_burst_flag: boolean;
  record_dispersion_method: string;
  observed_tonnes: number;
  baseline_median_tonnes: number;
  baseline_mad_tonnes: number;
  tonne_burst_threshold: number;
  tonne_burst_flag: boolean;
  tonne_dispersion_method: string;
  burst_type: BurstType;
  is_burst: boolean;
  has_sufficient_history: boolean;
  explanation: string;
}

export interface TemporalBurstsResponse {
  registry?: string | null;
  project_id?: string | null;
  period_type: AggregationPeriod | string;
  sensitivity: number;
  baseline_window: number;
  total_periods_evaluated: number;
  burst_periods_count: number;
  disclaimer: string;
  bursts: TemporalBurstPeriod[];
}

export interface TemporalGapItem {
  gap_start: string;
  gap_end: string;
  gap_duration_days: number;
  gap_duration_periods: number;
  previous_activity_period: TemporalActivityPeriod;
  next_activity_period: TemporalActivityPeriod;
  gap_classification: GapClassification;
  coverage_limitation_note: string;
}

export interface TemporalGapsResponse {
  registry?: string | null;
  project_id?: string | null;
  period_type: AggregationPeriod | string;
  total_gaps_count: number;
  max_gap_duration_days: number;
  mean_gap_duration_days: number;
  disclaimer: string;
  gaps: TemporalGapItem[];
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

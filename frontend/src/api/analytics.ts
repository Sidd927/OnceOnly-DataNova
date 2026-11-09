import { request, json } from "./client";

export type BeneficiaryCategory =
  | "NON_PLACEHOLDER_DISCLOSED"
  | "EXPLICITLY_UNDISCLOSED"
  | "INVALID_OR_PLACEHOLDER"
  | "UNRESOLVED_IDENTITY";

export type ConcentrationTier =
  | "SINGLE_LABEL_DOMINANCE"
  | "HIGH_CONCENTRATION"
  | "MODERATE_CONCENTRATION"
  | "BROAD_DISTRIBUTION"
  | "HIGH_DISPERSION"
  | "NOT_CLASSIFIED";

export interface DualTrackCoverage {
  total_records: number;
  total_quantity: number;
  disclosed_records: number;
  disclosed_quantity: number;
  explicitly_undisclosed_records: number;
  explicitly_undisclosed_quantity: number;
  invalid_placeholder_records: number;
  invalid_placeholder_quantity: number;
  unresolved_records: number;
  unresolved_quantity: number;
  record_disclosure_rate: number;
  quantity_disclosure_rate: number;
  record_unresolved_rate: number;
  quantity_unresolved_rate: number;
  classification_definition: string;
}

export interface ConcentrationMetrics {
  coverage: DualTrackCoverage;
  total_units: number;
  disclosed_units: number;
  unresolved_units: number;
  hhi: number;
  top_claimants: [string, number][];
  tier: ConcentrationTier;
  entropy?: number | null;
  lorenz_curve?: [number, number][];
}

export interface FragmentationMetrics {
  total_units: number;
  total_events: number;
  interval_count: number;
  micro_claim_count: number;
  micro_claim_volume: number;
  micro_claim_ratio: number;
  mean_interval_span: number;
  coverage_density: number;
}

export interface BatchAnalyticsResult {
  registry: string;
  batch_id: string;
  project_id?: string | null;
  project_name?: string | null;
  country?: string | null;
  vintage?: string | null;
  total_quantity: number;
  total_events: number;
  concentration: ConcentrationMetrics;
  fragmentation: FragmentationMetrics;
  computed_at: string;
}

export interface PopulationAnalyticsSummary {
  coverage: DualTrackCoverage;
  concentration: ConcentrationMetrics;
  fragmentation: FragmentationMetrics;
  total_projects: number;
  total_batches: number;
  generated_at: string;
}

export interface ConcentrationRequest {
  records: Record<string, any>[];
  total_units_override?: number;
}

export interface BatchFragmentationRequest {
  records: Record<string, any>[];
  registry: string;
  batch_id: string;
  project_id?: string;
  micro_threshold?: number;
}

export interface BatchAnalyticsRequest {
  records: Record<string, any>[];
  registry: string;
  batch_id: string;
  project_id?: string;
  project_name?: string;
  country?: string;
  vintage?: string;
}

export const analyticsApi = {
  getPopulationSummary: () =>
    request<PopulationAnalyticsSummary>("/api/analytics/population/summary"),
  getBatchAnalytics: (registry: string, batchId: string) =>
    request<BatchAnalyticsResult>(`/api/analytics/batches/${encodeURIComponent(registry)}/${encodeURIComponent(batchId)}`),
  analyzeConcentration: (req: ConcentrationRequest) =>
    request<ConcentrationMetrics>("/api/analytics/concentration", json(req)),
  analyzeFragmentation: (req: BatchFragmentationRequest) =>
    request<FragmentationMetrics>("/api/analytics/fragmentation", json(req)),
  analyzeBatch: (req: BatchAnalyticsRequest) =>
    request<BatchAnalyticsResult>("/api/analytics/batch", json(req)),
};

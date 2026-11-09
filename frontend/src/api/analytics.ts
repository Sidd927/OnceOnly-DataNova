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
  beneficiary_coverage_ratio: number;
  unresolved_share: number;
  unique_disclosed_beneficiaries: number;
  hhi_disclosed: number;
  hhi_normalized: number;
  entropy_shannon_disclosed: number;
  entropy_normalized: number;
  dominant_disclosed_beneficiary?: string | null;
  dominant_disclosed_share: number;
  top3_disclosed_share: number;
  tier: ConcentrationTier | string;
  disclosed_shares: Record<string, number>;
  disclaimer: string;
}

export interface BatchIntervalStructure {
  total_intervals: number;
  min_unit_start?: number | null;
  max_unit_end?: number | null;
  interval_span?: number | null;
  interval_density: number;
  exact_duplicate_intervals_count: number;
  overlapping_intervals_count: number;
  pairwise_overlap_count: number;
  contiguous_intervals_count: number;
  disjoint_gaps_count: number;
  has_invalid_intervals: boolean;
}

export interface FragmentationMetrics {
  total_events: number;
  total_units: number;
  gini_coefficient: number;
  gini_sample_corrected: number;
  mean_event_size: number;
  median_event_size: number;
  min_event_size: number;
  max_event_size: number;
  p25_event_size: number;
  p75_event_size: number;
  std_dev_event_size: number;
  iqr_event_size: number;
  micro_claim_count: number;
  micro_claim_units: number;
  micro_claim_record_share: number;
  micro_claim_quantity_share: number;
  micro_claim_threshold_used: number;
  small_tranche_count: number;
  small_tranche_units: number;
  small_tranche_record_share: number;
  small_tranche_quantity_share: number;
  small_tranche_threshold_used: number;
  classification_counts: Record<string, number>;
  classification_quantities: Record<string, number>;
  classification_record_shares: Record<string, number>;
  classification_quantity_shares: Record<string, number>;
  distinct_disclosed_beneficiaries: number;
  intervals?: BatchIntervalStructure | null;
}

export interface BatchAnalyticsResult {
  registry: string;
  batch_id: string;
  project_id?: string | null;
  project_name?: string | null;
  country?: string | null;
  vintage?: number | string | null;
  total_quantity: number;
  total_events: number;
  concentration: ConcentrationMetrics;
  fragmentation: FragmentationMetrics;
  computed_at: string;
}

export interface PopulationAnalyticsSummary {
  total_retirement_records: number;
  total_retirement_quantity: number;
  total_batches: number;
  coverage: DualTrackCoverage;
  overall_concentration: ConcentrationMetrics;
  batch_record_counts: Record<string, number>;
  batch_quantities: Record<string, number>;
  batch_gini_distribution: Record<string, number>;
  pooled_allocation_count: number;
  pooled_allocation_quantity: number;
  pooled_allocation_mean_size: number;
  pooled_allocation_gini: number;
  batches_with_micro_claims: number;
  batches_with_small_tranches: number;
  batches_with_overlaps: number;
  single_record_batches: number;
  multi_record_batches: number;
  batch_gini_interpretation: string;
  computed_at: string;
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
    request<BatchAnalyticsResult>(
      `/api/analytics/batches/${encodeURIComponent(registry)}/${encodeURIComponent(batchId)}`
    ),
  analyzeConcentration: (req: ConcentrationRequest) =>
    request<ConcentrationMetrics>("/api/analytics/concentration", json(req)),
  analyzeFragmentation: (req: BatchFragmentationRequest) =>
    request<FragmentationMetrics>("/api/analytics/fragmentation", json(req)),
  analyzeBatch: (req: BatchAnalyticsRequest) =>
    request<BatchAnalyticsResult>("/api/analytics/batch", json(req)),
};

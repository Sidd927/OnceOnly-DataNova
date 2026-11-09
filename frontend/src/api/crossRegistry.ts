import { request, json } from "./client";

export type ProjectCorrelationCategory =
  | "EXACT_IDENTIFIER_MATCH"
  | "CROSS_REGISTRY_IDENTIFIER_COLLISION"
  | "STRONG_ATTRIBUTE_CORRELATION"
  | "PARTIAL_ATTRIBUTE_CORRELATION"
  | "NAME_SIMILARITY_ONLY"
  | "CONFLICTING_ATTRIBUTES"
  | "INSUFFICIENT_EVIDENCE";

export type CrossRegistryEvidenceStrength =
  | "STRONG"
  | "MODERATE"
  | "WEAK"
  | "CONTRADICTORY"
  | "INSUFFICIENT";

export interface ProjectProfile {
  registry: string;
  project_id?: string | null;
  project_name: string;
  country?: string | null;
  vintage?: string | number | null;
  developer?: string | null;
  project_type?: string | null;
  methodology?: string | null;
  provenance?: string;
}

export interface CrossRegistryProjectComparison {
  project_a: ProjectProfile;
  project_b: ProjectProfile;
  is_cross_registry: boolean;
  correlation_category: ProjectCorrelationCategory | string;
  evidence_strength: CrossRegistryEvidenceStrength | string;
  name_similarity_score: number;
  name_tokens_a: string[];
  name_tokens_b: string[];
  token_set_ratio: number;
  token_sort_ratio: number;
  jaro_winkler_similarity: number;
  identifier_match: boolean;
  country_relation: "MATCH" | "CONFLICT" | "MISSING" | string;
  vintage_relation: "OVERLAP" | "ADJACENT" | "DISJOINT" | "MISSING" | string;
  developer_similarity: number | null;
  matching_attributes: string[];
  conflicting_attributes: string[];
  missing_attributes: string[];
  explanation: string;
  limitations: string;
  disclaimer: string;
}

export interface CrossRegistryProjectCompareRequest {
  project_a: ProjectProfile;
  project_b: ProjectProfile;
}

export interface CrossRegistryCorrelationsResponse {
  total_candidates_evaluated: number;
  matched_candidates_count: number;
  min_similarity_threshold: number;
  category_filter?: string | null;
  country_filter?: string | null;
  correlations: CrossRegistryProjectComparison[];
  disclaimer: string;
}

export interface CrossRegistryEntityCompareRequest {
  entity_a: string;
  entity_b: string;
  registry_a?: string;
  registry_b?: string;
}

export interface CrossRegistryEntityComparison {
  registry_a: string;
  entity_raw_a: string;
  entity_normalized_a: string;
  registry_b: string;
  entity_raw_b: string;
  entity_normalized_b: string;
  is_match: boolean;
  relationship_type: string;
  match_tier: string;
  overall_score: number;
  positive_signals: string[];
  contradictory_signals: string[];
  missing_information: string[];
  explanation: string;
  legal_disclaimer: string;
  disclaimer: string;
}

export interface EntityResolutionResult {
  entity_a: {
    raw_value: string | null;
    normalized_value: string | null;
    canonical_name: string;
    tokens: string[];
    legal_suffix: string | null;
    corporate_qualifiers: string[];
    is_placeholder: boolean;
    placeholder_type: string | null;
  };
  entity_b: {
    raw_value: string | null;
    normalized_value: string | null;
    canonical_name: string;
    tokens: string[];
    legal_suffix: string | null;
    corporate_qualifiers: string[];
    is_placeholder: boolean;
    placeholder_type: string | null;
  };
  overall_score: number;
  match_tier: string;
  relationship_type: string;
  is_match: boolean;
  positive_signals: string[];
  contradictory_signals: string[];
  missing_information: string[];
  explanation: string;
}

export interface IntermediaryExtractionResult {
  is_delegated: boolean;
  principal_raw: string | null;
  principal_entity: {
    canonical_name: string;
    normalized_value: string | null;
  } | null;
  intermediary_raw: string | null;
  intermediary_entity: {
    canonical_name: string;
    normalized_value: string | null;
  } | null;
  role: string;
  pattern_matched: string | null;
  raw_text: string;
  confidence: number;
  notes: string[];
}

export interface RegistryRetirementStats {
  registry: string;
  total_retirement_records: number;
  total_retired_tonnes: number;
  active_projects_count: number;
  earliest_retirement_date?: string | null;
  latest_retirement_date?: string | null;
  disclosed_records_count: number;
  beneficiary_record_disclosure_rate_pct: number;
  beneficiary_quantity_disclosure_rate_pct: number;
  record_disclosure_rate_pct?: number;
  disclosed_tonnes_quantity: number;
  quantity_disclosure_rate_pct?: number;
  issuance_records_excluded: number;
  available_source_fields: string[];
  unpopulated_or_sparse_fields: string[];
}

export interface CrossRegistryRetirementSummary {
  registries: Record<string, RegistryRetirementStats>;
  combined_retirement_records: number;
  combined_retired_tonnes: number;
  total_issuance_records_excluded: number;
  comparability_notes: string[];
  disclaimer: string;
}

export interface CrossRegistryTrendsPeriod {
  period_start: string;
  period_end: string;
  period_label: string;
  vcs_record_count: number;
  vcs_total_tonnes: number;
  gs_record_count: number;
  gs_total_tonnes: number;
  combined_record_count: number;
  combined_total_tonnes: number;
}

export interface CrossRegistryTrendsResponse {
  period_type: "yearly" | "monthly" | string;
  total_periods: number;
  trends: CrossRegistryTrendsPeriod[];
  disclaimer: string;
}

export const crossRegistryApi = {
  compareProjects: (projectA: ProjectProfile, projectB: ProjectProfile) =>
    request<CrossRegistryProjectComparison>(
      "/api/cross-registry/projects/compare",
      json({ project_a: projectA, project_b: projectB })
    ),
  getProjectCorrelations: (params?: {
    min_similarity?: number;
    category?: string;
    country?: string;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.min_similarity != null) q.set("min_similarity", String(params.min_similarity));
    if (params?.category) q.set("category", params.category);
    if (params?.country) q.set("country", params.country);
    if (params?.limit != null) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<CrossRegistryCorrelationsResponse>(
      `/api/cross-registry/projects/correlations${qs ? `?${qs}` : ""}`
    );
  },
  compareEntities: (req: CrossRegistryEntityCompareRequest) =>
    request<CrossRegistryEntityComparison>("/api/cross-registry/entities/compare", json(req)),
  resolveEntityPair: (nameA: string, nameB: string) =>
    request<EntityResolutionResult>("/api/resolve/entity-pair", json({ name_a: nameA, name_b: nameB })),
  extractIntermediary: (text: string) =>
    request<IntermediaryExtractionResult>("/api/resolve/intermediary", json({ text })),
  getRetirementSummary: () =>
    request<CrossRegistryRetirementSummary>("/api/cross-registry/retirements/summary"),
  getRetirementTrends: (period: "yearly" | "monthly" = "yearly") =>
    request<CrossRegistryTrendsResponse>(
      `/api/cross-registry/retirements/trends?period=${encodeURIComponent(period)}`
    ),
};

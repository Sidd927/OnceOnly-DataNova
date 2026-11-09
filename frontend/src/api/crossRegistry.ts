import { request, json } from "./client";

export type ProjectCorrelationCategory =
  | "HIGH_CONFIDENCE_CROSS_REGISTRY_PAIR"
  | "STRONG_ATTRIBUTE_CORRELATION"
  | "PARTIAL_SIMILARITY"
  | "CROSS_REGISTRY_IDENTIFIER_COLLISION"
  | "INDEPENDENT_PROJECTS";

export type CrossRegistryEvidenceStrength =
  | "STRONG"
  | "MODERATE"
  | "WEAK"
  | "COLLISION_ONLY";

export interface ProjectProfile {
  registry: string;
  project_id: string;
  project_name: string;
  country?: string | null;
  developer?: string | null;
  status?: string | null;
}

export interface CrossRegistryProjectComparison {
  project_a: ProjectProfile;
  project_b: ProjectProfile;
  token_similarity: number;
  fuzzy_similarity: number;
  combined_similarity: number;
  category: ProjectCorrelationCategory;
  evidence_strength: CrossRegistryEvidenceStrength;
  shared_attributes: string[];
  conflicting_attributes: string[];
  explanation: string;
  collision_warning?: string | null;
}

export interface CrossRegistryProjectCompareRequest {
  project_a: Record<string, any>;
  project_b: Record<string, any>;
}

export interface CrossRegistryCorrelationsResponse {
  correlations: CrossRegistryProjectComparison[];
  total_evaluated: number;
  high_confidence_count: number;
  generated_at: string;
}

export interface CrossRegistryEntityCompareRequest {
  entity_a: string;
  entity_b: string;
  registry_a?: string;
  registry_b?: string;
}

export interface CrossRegistryEntityComparison {
  entity_a: string;
  entity_b: string;
  registry_a?: string | null;
  registry_b?: string | null;
  normalized_a: string;
  normalized_b: string;
  fuzzy_score: number;
  token_score: number;
  combined_score: number;
  is_match: boolean;
  match_tier: string;
  explanation: string;
}

export interface RegistryRetirementStats {
  registry: string;
  total_records: number;
  total_units: number;
  earliest_retirement?: string | null;
  latest_retirement?: string | null;
  unique_projects: number;
  unique_beneficiaries: number;
}

export interface CrossRegistryRetirementSummary {
  vcs: RegistryRetirementStats;
  gs: RegistryRetirementStats;
  shared_countries: string[];
  generated_at: string;
}

export interface CrossRegistryTrendsPeriod {
  period_label: string;
  vcs_units: number;
  gs_units: number;
  vcs_records: number;
  gs_records: number;
}

export interface CrossRegistryTrendsResponse {
  period_type: "yearly" | "monthly";
  trends: CrossRegistryTrendsPeriod[];
  generated_at: string;
}

export const crossRegistryApi = {
  compareProjects: (projectA: Record<string, any>, projectB: Record<string, any>) =>
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
  getRetirementSummary: () =>
    request<CrossRegistryRetirementSummary>("/api/cross-registry/retirements/summary"),
  getRetirementTrends: (period: "yearly" | "monthly" = "yearly") =>
    request<CrossRegistryTrendsResponse>(
      `/api/cross-registry/retirements/trends?period=${encodeURIComponent(period)}`
    ),
};

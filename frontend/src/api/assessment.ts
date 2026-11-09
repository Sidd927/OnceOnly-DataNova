import { request, json } from "./client";

export type AssessmentScope =
  | "BATCH"
  | "PROJECT"
  | "CLAIM"
  | "ENTITY"
  | "CROSS_REGISTRY"
  | "AD_HOC";

export type EvidenceCategory =
  | "ENTITY_IDENTITY"
  | "ALLOCATION_RECONCILIATION"
  | "BENEFICIARY_CONCENTRATION"
  | "BATCH_FRAGMENTATION"
  | "TEMPORAL_DYNAMICS"
  | "CROSS_REGISTRY";

export type SourceStage =
  | "PHASE_2A_ENTITY_RESOLUTION"
  | "PHASE_2B_RECONCILIATION"
  | "PHASE_2C_STAGE_1_CONCENTRATION"
  | "PHASE_2C_STAGE_1_FRAGMENTATION"
  | "PHASE_2C_STAGE_2_TEMPORAL"
  | "PHASE_2C_STAGE_3_CROSS_REGISTRY";

export type EvidenceSeverity =
  | "INFORMATIONAL"
  | "LOW"
  | "MODERATE"
  | "HIGH"
  | "CRITICAL";

export type EvidenceStrength =
  | "WEAK"
  | "MODERATE"
  | "STRONG"
  | "CONTRADICTORY"
  | "UNRESOLVED";

export type AssessmentStatus =
  | "NO_MATERIAL_SIGNAL"
  | "REVIEW_RECOMMENDED"
  | "ELEVATED_REVIEW_PRIORITY"
  | "INSUFFICIENT_EVIDENCE"
  | "CONFLICTING_EVIDENCE";

export type ReviewPriority =
  | "NONE"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "URGENT";

export interface EvidenceItem {
  id: string;
  category: EvidenceCategory;
  source_stage: SourceStage;
  rule_id: string;
  title: string;
  explanation: string;
  severity: EvidenceSeverity;
  evidence_strength: EvidenceStrength;
  supporting_records: string[];
  metrics: Record<string, any>;
  thresholds: Record<string, any>;
  provenance: string;
  limitations: string[];
  counterevidence: string[];
  contextual_caveats: string[];
  missing_information: string[];
  recommended_action: string;
  dependency_group_id: string | null;
}

export interface EvidenceDependencyGroup {
  group_id: string;
  primary_signal: string;
  correlated_evidence_ids: string[];
  shared_data_source: string;
  is_reinforcing_not_independent: boolean;
  explanation: string;
}

export interface AssessmentTarget {
  scope: AssessmentScope;
  registry?: string | null;
  batch_id?: string | null;
  project_id?: string | null;
  claim_id?: number | null;
  entity_a?: string | null;
  entity_b?: string | null;
  description?: string | null;
}

export interface RiskAssessmentRequest {
  scope: AssessmentScope;
  registry?: string;
  batch_id?: string;
  project_id?: string;
  claim_id?: number;
  entity_a?: string;
  entity_b?: string;
  records?: Record<string, any>[];
  project_a?: Record<string, any>;
  project_b?: Record<string, any>;
  candidate_range?: [number, number];
  claimant?: string;
}

export interface AssessmentRuleDefinition {
  rule_id: string;
  name: string;
  category: EvidenceCategory;
  source_stage: SourceStage;
  default_severity: EvidenceSeverity;
  default_strength: EvidenceStrength;
  description: string;
  rationale: string;
  limitations: string[];
}

export interface AssessmentRulesCatalogResponse {
  ruleset_version: string;
  total_rules: number;
  rules: AssessmentRuleDefinition[];
}

export interface RiskAssessmentResponse {
  assessment_id: string;
  ruleset_version: string;
  assessment_timestamp: string;
  target: AssessmentTarget;
  overall_status: AssessmentStatus;
  review_priority: ReviewPriority;
  priority_explanation: string;
  triggered_rule_ids: string[];
  evidence_items: EvidenceItem[];
  counterevidence_items: string[];
  contextual_caveats: string[];
  missing_information_items: string[];
  dependency_groups: EvidenceDependencyGroup[];
  independent_evidence_count: number;
  correlated_evidence_count: number;
  source_stages_consulted: SourceStage[];
  methodology_limitations: string[];
  recommended_next_steps: string[];
  disclaimer: string;
}

export const assessmentApi = {
  assessRisk: (req: RiskAssessmentRequest) =>
    request<RiskAssessmentResponse>("/api/analytics/assessment", json(req)),
  getRulesCatalog: () =>
    request<AssessmentRulesCatalogResponse>("/api/analytics/assessment/rules"),
};

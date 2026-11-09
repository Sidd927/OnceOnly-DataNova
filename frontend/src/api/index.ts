import { claimsApi } from "./claims";
import { assessmentApi } from "./assessment";
import { crossRegistryApi } from "./crossRegistry";
import { temporalApi } from "./temporal";
import { analyticsApi } from "./analytics";

export * from "./client";
export * from "./claims";
export * from "./assessment";
export * from "./crossRegistry";
export * from "./temporal";
export * from "./analytics";

export const api = {
  ...claimsApi,
  assessment: assessmentApi,
  crossRegistry: crossRegistryApi,
  temporal: temporalApi,
  analytics: analyticsApi,
  // Top-level aliases for direct ergonomic access
  assessRisk: assessmentApi.assessRisk,
  getRulesCatalog: assessmentApi.getRulesCatalog,
  getProjectCorrelations: crossRegistryApi.getProjectCorrelations,
  compareProjects: crossRegistryApi.compareProjects,
  compareEntities: crossRegistryApi.compareEntities,
  getTemporalActivity: temporalApi.getActivity,
  getTemporalTrends: temporalApi.getTrends,
  getTemporalBursts: temporalApi.getBursts,
  getTemporalGaps: temporalApi.getGaps,
  getPopulationSummary: analyticsApi.getPopulationSummary,
  getBatchAnalytics: analyticsApi.getBatchAnalytics,
};

export default api;

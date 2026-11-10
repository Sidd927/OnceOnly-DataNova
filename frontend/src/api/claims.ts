import { request, json } from "./client";

export type Severity = "blocking" | "review" | "info" | "pass";
export type ClaimStatus = "checked" | "blocked" | "anchored" | "challenged" | "revoked" | "withdrawn";

export interface Finding {
  id: number;
  rule_id: string;
  severity: Severity;
  title: string;
  explanation: string;
  uncertainty: string;
  next_action: string;
  evidence: Record<string, any>;
  block_index: number | null;
}

export interface Block {
  id: number;
  idx: number;
  registry: "VCS" | "GS";
  batch_id: string;
  unit_start: number;
  unit_end: number;
  quantity: number;
  namespace: string;
  serial: string;
  project_id: string | null;
  vintage: string | null;
  country: string | null;
  source: "parser" | "llm" | "both";
}

export interface ClaimEvent {
  id: number;
  kind: string;
  detail: Record<string, any>;
  tx_hash: string | null;
  block_number: number | null;
  created_at: string;
}

export interface StripRecord {
  unit_start: number;
  unit_end: number;
  kind: "retirement" | "issuance";
  event_date: string | null;
  beneficiary?: string | null;
  serial: string;
}

export interface StripOther {
  claim_id: number;
  ref: string;
  claimant: string;
  status: ClaimStatus;
  unit_start: number;
  unit_end: number;
}

export interface Strip {
  block_index: number;
  namespace: string;
  claim: { unit_start: number; unit_end: number };
  records: StripRecord[];
  others: StripOther[];
  domain: [number, number];
}

export interface ClaimSummary {
  id: number;
  ref: string;
  claimant: string;
  period: string | null;
  statement: string | null;
  status: ClaimStatus;
  verdict: "clear" | "review" | "blocked" | null;
  synthetic: boolean;
  total_units: number;
  block_count: number;
  finding_counts: Partial<Record<Severity, number>>;
  chain_claim_id: number | null;
  tx_hash: string | null;
  block_number: number | null;
  created_at: string;
}

export interface ClaimDetail extends ClaimSummary {
  claimant_commitment: string;
  report_hash: string | null;
  evidence_hash: string | null;
  chain_id: number | null;
  contract_address: string | null;
  llm_status: string;
  extraction: Record<string, any>;
  evidence: {
    id: number;
    filename: string;
    sha256: string;
    size: number;
    mime: string | null;
    text_excerpt: string;
  }[];
  blocks: Block[];
  findings: Finding[];
  events: ClaimEvent[];
  unit_strips: Strip[];
}

export interface Sample {
  file: string;
  claimant: string;
  title: string;
  story: string;
  statement: string;
  synthetic: boolean;
}

export interface AllocationReconciliationItem {
  candidate: {
    registry: string;
    batch_id: string;
    unit_start: number;
    unit_end: number;
    claimant: string;
    claim_id?: number;
    claim_ref?: string;
  };
  existing: {
    registry: string;
    batch_id: string;
    unit_start: number;
    unit_end: number;
    claimant: string;
    claim_id?: number;
    claim_ref?: string;
  };
  overlap: {
    has_overlap: boolean;
    overlap_start?: number;
    overlap_end?: number;
    overlap_quantity: number;
    is_conflict: boolean;
    conflict_reason?: string;
  };
}

export interface ClaimReconciliationReport {
  claim_id: number;
  claimant: string;
  total_blocks: number;
  total_units: number;
  active_ranges_evaluated: number;
  conflicts: AllocationReconciliationItem[];
  splits: AllocationReconciliationItem[];
  has_conflicts: boolean;
  conflict_units: number;
  reconciled_at: string;
}

export const claimsApi = {
  health: () => request<any>("/api/health"),
  overview: () => request<any>("/api/overview"),
  claims: () => request<ClaimSummary[]>("/api/claims"),
  claim: (id: number | string) => request<ClaimDetail>(`/api/claims/${id}`),
  createClaim: (form: FormData) => request<ClaimDetail>("/api/claims", { method: "POST", body: form }),
  recheck: (id: number) => request<ClaimDetail>(`/api/claims/${id}/recheck`, { method: "POST" }),
  anchor: (id: number, opts: { acknowledge_review?: boolean; force?: boolean }) =>
    request<{ result: any; claim: ClaimDetail }>(`/api/claims/${id}/anchor`, json(opts)),
  challenge: (id: number, reason: string) =>
    request<{ result: any; claim: ClaimDetail }>(`/api/claims/${id}/challenge`, json({ reason })),
  resolve: (id: number, upheld: boolean, note: string) =>
    request<{ result: any; claim: ClaimDetail }>(`/api/claims/${id}/resolve`, json({ upheld, note })),
  withdraw: (id: number) =>
    request<{ result: any; claim: ClaimDetail }>(`/api/claims/${id}/withdraw`, { method: "POST" }),
  verify: (form: FormData) => request<VerifyResult>("/api/verify", { method: "POST", body: form }),
  samples: () => request<Sample[]>("/api/samples"),
  sampleFile: async (name: string) => {
    const res = await fetch(`/api/samples/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error("Could not load the sample document");
    const blob = await res.blob();
    return new File([blob], name, { type: blob.type });
  },
  evaluation: () => request<any>("/api/eval"),
  evidenceLookup: (sha256: string) =>
    request<{
      sha256: string;
      claims: {
        claim_id: number;
        ref: string;
        claimant: string;
        status: ClaimStatus;
        filename: string;
      }[];
    }>(`/api/evidence/${sha256}`),
  reconciliation: (claimId: number | string) =>
    request<ClaimReconciliationReport>(`/api/claims/${claimId}/reconciliation`),
};

/* ------------------------------------------------------------ verification */

export type VerifyCheckStatus = "PASS" | "FAIL" | "WARN" | "NOT_PERFORMED";
export type DocumentStatus = "ONCHAIN_ROOT_MATCH" | "ONCHAIN_MEMBERSHIP_PROVEN" | "OFFCHAIN_RECORD_ONLY" | "NO_MATCH";

export interface VerifyCheck {
  id: "NETWORK" | "DEPLOYMENT_CODE" | "ONCHAIN_RECORD" | "RANGES_RECONCILE" | "EVIDENCE_COMMITMENT" | "DOCUMENT" | "CLAIMANT";
  label: string;
  status: VerifyCheckStatus;
  detail: string;
}

export interface VerifyChainInfo {
  rpc_url: string;
  chain_id: number;
  network: string | null;
  public_network: boolean;
  network_kind: "LOCAL_DEVELOPMENT_CHAIN" | "NON_LOCAL_CHAIN";
  deployment_chain_id: number;
  address: string;
  deploy_tx: string | null;
  deploy_block: number | null;
  block_number: number;
  claim_count: number;
  registrar: string;
}

export interface VerifyDocument {
  filename: string;
  sha256: string;
  status: DocumentStatus;
  matches_onchain_commitment: boolean;
  offchain_record_match: boolean;
  explanation: string;
  does_not_prove: string;
  proof: { scheme: string; leaves: string[]; recomputed_root: string | null; onchain_root: string; recomputed_matches_onchain: boolean | null };
}

export interface VerifyResult {
  found: boolean;
  message?: string;
  chain?: VerifyChainInfo;
  code_verification?: { status: "CODE_MATCHES_ARTIFACT" | "CODE_DIFFERS_FROM_ARTIFACT" | "ARTIFACT_UNAVAILABLE"; runtime_code_keccak: string; artifact: string };
  onchain?: {
    claim_id: number; ref_hash: string; claimant_commitment: string; evidence_hash: string; report_hash: string;
    registrar: string; registered_at: number; status: string;
    ranges: { namespace: string; unit_start: number; unit_end: number }[];
  };
  checks?: VerifyCheck[];
  commitment_scheme?: string;
  local?: { id: number; ref: string; tx_hash: string | null; block_number: number | null; synthetic: boolean };
  evidence_documents?: number;
  document?: VerifyDocument;
  claimant_check?: { matches: boolean };
  limitations?: string[];
}

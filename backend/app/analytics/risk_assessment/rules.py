"""Transparent, deterministic rule definitions for Unified Explainable Risk Assessment."""
from __future__ import annotations

from typing import Dict, List
from .models import (
    AssessmentRuleDefinition,
    EvidenceCategory,
    EvidenceSeverity,
    EvidenceStrength,
    SourceStage,
)

# Benchmark Threshold Constants
HHI_DOMINANCE_THRESHOLD = 8000.0
DOMINANT_SHARE_THRESHOLD = 0.90
HHI_HIGH_CONCENTRATION_THRESHOLD = 2500.0
UNRESOLVED_SHARE_MATERIAL_THRESHOLD = 0.50

GINI_HIGH_INEQUALITY_THRESHOLD = 0.70
MICRO_CLAIM_EVENT_COUNT_THRESHOLD = 20
MICRO_CLAIM_VOLUME_SHARE_THRESHOLD = 0.30
MICRO_CLAIM_TONNE_LIMIT = 10.0

TEMPORAL_BURST_Z_THRESHOLD = 3.0
TEMPORAL_BURST_MIN_TONNES = 100.0
TEMPORAL_GAP_MIN_PERIODS = 3

CROSS_REG_SIMILARITY_STRONG = 0.85
CROSS_REG_SIMILARITY_PARTIAL = 0.70


RULE_DEFINITIONS: Dict[str, AssessmentRuleDefinition] = {
    "RULE-REC-001": AssessmentRuleDefinition(
        rule_id="RULE-REC-001",
        name="Exact Serial Unit Overlap",
        category=EvidenceCategory.ALLOCATION_RECONCILIATION,
        source_stage=SourceStage.PHASE_2B_RECONCILIATION,
        default_severity=EvidenceSeverity.CRITICAL,
        default_strength=EvidenceStrength.STRONG,
        description="Candidate claim range exactly matches an already-anchored active serial range on the ledger.",
        rationale="Immutable ledger records show identical serial units in the same registry namespace have already been claimed.",
        limitations=[
            "Requires verified matching registry and batch namespaces; identical numbers in different registries/batches are isolated.",
            "Mathematical serial overlap establishes a ledger conflict requiring review, NOT legal fraud or criminal double claiming.",
            "Ledger status matters: only active or anchored prior claims constitute competing unit commitments.",
        ],
    ),
    "RULE-REC-002": AssessmentRuleDefinition(
        rule_id="RULE-REC-002",
        name="Partial Serial Unit Overlap",
        category=EvidenceCategory.ALLOCATION_RECONCILIATION,
        source_stage=SourceStage.PHASE_2B_RECONCILIATION,
        default_severity=EvidenceSeverity.HIGH,
        default_strength=EvidenceStrength.STRONG,
        description="Candidate claim range partially overlaps with an active serial range on the ledger.",
        rationale="A subset of claimed serial numbers intersects with active units held by a prior claimant.",
        limitations=[
            "Disjoint units within the same block remain valid for potential partial registration.",
            "Does not imply bad faith; often arises from miscalculated split lot retirements or unaligned broker tranches.",
        ],
    ),
    "RULE-REC-003": AssessmentRuleDefinition(
        rule_id="RULE-REC-003",
        name="Contained Serial Unit Overlap",
        category=EvidenceCategory.ALLOCATION_RECONCILIATION,
        source_stage=SourceStage.PHASE_2B_RECONCILIATION,
        default_severity=EvidenceSeverity.HIGH,
        default_strength=EvidenceStrength.STRONG,
        description="Candidate claim range is fully contained within a larger prior registered block.",
        rationale="The requested unit interval is entirely enveloped by units previously retired or committed.",
        limitations=[
            "Examine whether the candidate claimant is an authorized corporate subsidiary, retail customer, or broker delegate.",
            "Parent/subsidiary sub-allocations require verification of contractual authorization rather than fraud allegations.",
        ],
    ),
    "RULE-REC-004": AssessmentRuleDefinition(
        rule_id="RULE-REC-004",
        name="Legitimate Split Allocation",
        category=EvidenceCategory.ALLOCATION_RECONCILIATION,
        source_stage=SourceStage.PHASE_2B_RECONCILIATION,
        default_severity=EvidenceSeverity.INFORMATIONAL,
        default_strength=EvidenceStrength.STRONG,
        description="Candidate claim partitions a batch into strictly disjoint intervals without overlap.",
        rationale="Normal commercial retirement partitioning across separate buyers or departments.",
        limitations=[
            "This is contextual information confirming non-overlapping allocation, NOT an adverse signal.",
            "Legitimate split allocations must never be classified as competing claims merely because they share a parent batch.",
        ],
    ),
    "RULE-CON-001": AssessmentRuleDefinition(
        rule_id="RULE-CON-001",
        name="Single-Beneficiary Portfolio Dominance",
        category=EvidenceCategory.BENEFICIARY_CONCENTRATION,
        source_stage=SourceStage.PHASE_2C_STAGE_1_CONCENTRATION,
        default_severity=EvidenceSeverity.MODERATE,
        default_strength=EvidenceStrength.STRONG,
        description="A single disclosed entity accounts for >=90% of disclosed batch volume with HHI > 8,000.",
        rationale="Extreme concentration may indicate strategic cornering or off-market bilateral agreements.",
        limitations=[
            "Frequently reflects standard long-term off-take agreements by anchor corporate buyers.",
            "Calculated strictly over disclosed volume; does not impute undisclosed shares.",
        ],
    ),
    "RULE-CON-002": AssessmentRuleDefinition(
        rule_id="RULE-CON-002",
        name="High Beneficiary Concentration",
        category=EvidenceCategory.BENEFICIARY_CONCENTRATION,
        source_stage=SourceStage.PHASE_2C_STAGE_1_CONCENTRATION,
        default_severity=EvidenceSeverity.LOW,
        default_strength=EvidenceStrength.MODERATE,
        description="Batch volume is concentrated among few claimants (HHI > 2,500) across >=3 entities.",
        rationale="Moderately concentrated holdings warrant standard buyer identification checks.",
        limitations=[
            "HHI benchmarks reflect descriptive market concentration, not antitrust legal determinations.",
        ],
    ),
    "RULE-CON-003": AssessmentRuleDefinition(
        rule_id="RULE-CON-003",
        name="Material Undisclosed Beneficiary Share",
        category=EvidenceCategory.BENEFICIARY_CONCENTRATION,
        source_stage=SourceStage.PHASE_2C_STAGE_1_CONCENTRATION,
        default_severity=EvidenceSeverity.LOW,
        default_strength=EvidenceStrength.WEAK,
        description="Over 50% of retirement volume in the batch has missing, undisclosed, or placeholder beneficiaries.",
        rationale="High proportion of redacted or placeholder identities limits downstream transparency.",
        limitations=[
            "Often reflects registry-level platform policy (e.g. Gold Standard 'Not Disclosed' accounts for 92.7% of GS records).",
            "Missing beneficiary data is NOT evidence of illicit activity or fraudulent intent.",
        ],
    ),
    "RULE-FRG-001": AssessmentRuleDefinition(
        rule_id="RULE-FRG-001",
        name="Anomalous Micro-Claim Fragmentation",
        category=EvidenceCategory.BATCH_FRAGMENTATION,
        source_stage=SourceStage.PHASE_2C_STAGE_1_FRAGMENTATION,
        default_severity=EvidenceSeverity.MODERATE,
        default_strength=EvidenceStrength.MODERATE,
        description="Batch exhibits >=20 micro-claim events (<=10 tonnes) accounting for >=30% of total volume.",
        rationale="Heavy fragmentation into small units can indicate smurfing to evade transaction reporting thresholds.",
        limitations=[
            "Retail carbon offsetting platforms (e.g. flight offsets, e-commerce checkout add-ons) legitimately produce micro-claims.",
        ],
    ),
    "RULE-FRG-002": AssessmentRuleDefinition(
        rule_id="RULE-FRG-002",
        name="High Batch Sizing Inequality",
        category=EvidenceCategory.BATCH_FRAGMENTATION,
        source_stage=SourceStage.PHASE_2C_STAGE_1_FRAGMENTATION,
        default_severity=EvidenceSeverity.INFORMATIONAL,
        default_strength=EvidenceStrength.MODERATE,
        description="Batch retirement sizes exhibit high statistical inequality (finite-sample corrected Gini > 0.70).",
        rationale="Extreme dispersion between massive anchor claims and numerous tiny individual transactions.",
        limitations=[
            "Reflects non-uniform batch distribution; common when wholesale and retail retirements share one issuance batch.",
        ],
    ),
    "RULE-TMP-001": AssessmentRuleDefinition(
        rule_id="RULE-TMP-001",
        name="Anomalous Retirement Volume Burst",
        category=EvidenceCategory.TEMPORAL_DYNAMICS,
        source_stage=SourceStage.PHASE_2C_STAGE_2_TEMPORAL,
        default_severity=EvidenceSeverity.MODERATE,
        default_strength=EvidenceStrength.MODERATE,
        description="Retirement volume in a single calendar period deviates >=3.0 MAD from historical baseline.",
        rationale="Abrupt spikes in liquidation pacing can signal dumping, distressed selling, or fiscal year-end rushes.",
        limitations=[
            "Commercial accounting deadlines (e.g. Q4 CDP disclosures or EU ETS compliance cycles) create natural seasonal bursts.",
            "Requires at least 5 periods of prior history for robust baseline calculation.",
        ],
    ),
    "RULE-TMP-002": AssessmentRuleDefinition(
        rule_id="RULE-TMP-002",
        name="Prolonged Project Inactivity Gap",
        category=EvidenceCategory.TEMPORAL_DYNAMICS,
        source_stage=SourceStage.PHASE_2C_STAGE_2_TEMPORAL,
        default_severity=EvidenceSeverity.INFORMATIONAL,
        default_strength=EvidenceStrength.WEAK,
        description="Project exhibits >=3 consecutive zero-activity periods followed by sudden resumption.",
        rationale="Dormant projects reactivated after years of inactivity warrant verification of continuing additionality.",
        limitations=[
            "Registry data synchronization delays or market liquidity lulls frequently produce multi-month inactivity.",
        ],
    ),
    "RULE-ENT-001": AssessmentRuleDefinition(
        rule_id="RULE-ENT-001",
        name="Intermediary Attribution Ambiguity",
        category=EvidenceCategory.ENTITY_IDENTITY,
        source_stage=SourceStage.PHASE_2A_ENTITY_RESOLUTION,
        default_severity=EvidenceSeverity.LOW,
        default_strength=EvidenceStrength.MODERATE,
        description="Retirement text contains intermediary phrasing ('on behalf of', 'fbo') with ambiguous principal identity.",
        rationale="Broker/retailer aggregation can obscure the true beneficial owner claiming the climate benefit.",
        limitations=[
            "Intermediary purchasing is standard carbon market practice. Requires inspection of purchase agreement.",
        ],
    ),
    "RULE-ENT-002": AssessmentRuleDefinition(
        rule_id="RULE-ENT-002",
        name="Corporate Hierarchy / Subsidiary Variation",
        category=EvidenceCategory.ENTITY_IDENTITY,
        source_stage=SourceStage.PHASE_2A_ENTITY_RESOLUTION,
        default_severity=EvidenceSeverity.INFORMATIONAL,
        default_strength=EvidenceStrength.MODERATE,
        description="Entity names match on core root brand but differ in subsidiary, regional, or legal form qualifiers.",
        rationale="Parent/subsidiary relationships may lead to uncoordinated dual claiming across business units.",
        limitations=[
            "Shared brand tokens do NOT prove legal-entity equivalence or unauthorized claim duplication.",
        ],
    ),
    "RULE-XREG-001": AssessmentRuleDefinition(
        rule_id="RULE-XREG-001",
        name="Strong Cross-Registry Project Attribute Correlation",
        category=EvidenceCategory.CROSS_REGISTRY,
        source_stage=SourceStage.PHASE_2C_STAGE_3_CROSS_REGISTRY,
        default_severity=EvidenceSeverity.MODERATE,
        default_strength=EvidenceStrength.MODERATE,
        description="Projects in distinct registries have >=85% name similarity, matching country, and overlapping vintages.",
        rationale="High attribute similarity across registries warrants inquiry into potential uncoordinated dual registration.",
        limitations=[
            "Investigative triage signal only. Does NOT establish fraud or duplicate credit issuance.",
            "Independent registry verification is required to confirm whether dual-listing is authorized.",
        ],
    ),
    "RULE-XREG-002": AssessmentRuleDefinition(
        rule_id="RULE-XREG-002",
        name="Cross-Registry Identifier Collision",
        category=EvidenceCategory.CROSS_REGISTRY,
        source_stage=SourceStage.PHASE_2C_STAGE_3_CROSS_REGISTRY,
        default_severity=EvidenceSeverity.INFORMATIONAL,
        default_strength=EvidenceStrength.WEAK,
        description="Alphanumeric project ID matches across different registries (e.g. VCS vs Gold Standard).",
        rationale="Coincidental collision across independent, uncoordinated ID namespaces.",
        limitations=[
            "Registry namespaces are completely disjoint. Numeric coincidence alone does NOT indicate project identity.",
        ],
    ),
    "RULE-XREG-003": AssessmentRuleDefinition(
        rule_id="RULE-XREG-003",
        name="Contradictory Cross-Registry Project Attributes",
        category=EvidenceCategory.CROSS_REGISTRY,
        source_stage=SourceStage.PHASE_2C_STAGE_3_CROSS_REGISTRY,
        default_severity=EvidenceSeverity.INFORMATIONAL,
        default_strength=EvidenceStrength.CONTRADICTORY,
        description="Projects exhibit surface name similarity but contradict in national jurisdiction or vintage era (>5y).",
        rationale="Geographic and temporal contradictions constitute definitive counterevidence against project equivalence.",
        limitations=[
            "Direct exculpatory evidence establishing that candidates are distinct physical assets.",
        ],
    ),
}


"""Data models and taxonomy for Unified Explainable Risk Assessment (Phase 2C Stage 4).

Adheres strictly to the principle of transparent, non-accusatory investigative intelligence.
Analytical signals are structured as explainable evidence items with explicit counterevidence,
missing data declarations, and correlation/double-counting safeguards.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from ..models import MetadataProvenance

RULESET_VERSION = "2026.1.0-STAGE4"

ASSESSMENT_DISCLAIMER = (
    "INVESTIGATIVE ASSESSMENT DISCLAIMER: This unified risk assessment generates explainable, "
    "deterministic analytical signals for carbon-market investigators. It aggregates quantitative findings "
    "from serial reconciliation, entity resolution, concentration/fragmentation metrics, temporal activity, "
    "and cross-registry matching. It does NOT establish fraud, intentional wrongdoing, or legal culpability. "
    "Analytical anomalies (such as portfolio concentration or retirement bursts) frequently reflect legitimate "
    "commercial practices, distributor operations, or timing artifacts. Missing data must not be imputed. "
    "Independent verification and direct registry attestation are required before drawing adverse conclusions."
)


class AssessmentScope(str, Enum):
    """Target scope evaluated by the risk assessment engine."""
    BATCH = "BATCH"
    PROJECT = "PROJECT"
    CLAIM = "CLAIM"
    ENTITY = "ENTITY"
    CROSS_REGISTRY = "CROSS_REGISTRY"
    AD_HOC = "AD_HOC"


class EvidenceCategory(str, Enum):
    """Controlled taxonomy of analytical evidence categories."""
    ENTITY_IDENTITY = "ENTITY_IDENTITY"
    ALLOCATION_RECONCILIATION = "ALLOCATION_RECONCILIATION"
    BENEFICIARY_CONCENTRATION = "BENEFICIARY_CONCENTRATION"
    BATCH_FRAGMENTATION = "BATCH_FRAGMENTATION"
    TEMPORAL_DYNAMICS = "TEMPORAL_DYNAMICS"
    CROSS_REGISTRY = "CROSS_REGISTRY"


class SourceStage(str, Enum):
    """Underlying analytics stage producing the evidence."""
    PHASE_2A_ENTITY_RESOLUTION = "PHASE_2A_ENTITY_RESOLUTION"
    PHASE_2B_RECONCILIATION = "PHASE_2B_RECONCILIATION"
    PHASE_2C_STAGE_1_CONCENTRATION = "PHASE_2C_STAGE_1_CONCENTRATION"
    PHASE_2C_STAGE_1_FRAGMENTATION = "PHASE_2C_STAGE_1_FRAGMENTATION"
    PHASE_2C_STAGE_2_TEMPORAL = "PHASE_2C_STAGE_2_TEMPORAL"
    PHASE_2C_STAGE_3_CROSS_REGISTRY = "PHASE_2C_STAGE_3_CROSS_REGISTRY"


class EvidenceSeverity(str, Enum):
    """Categorical severity of analytical evidence (non-legal)."""
    INFORMATIONAL = "INFORMATIONAL"  # Contextual, structural, or benign observation
    LOW = "LOW"                      # Minor anomaly or routine data sparsity
    MODERATE = "MODERATE"            # Material deviation warranting standard verification
    HIGH = "HIGH"                    # Significant anomaly (e.g. partial serial clash or smurfing pattern)
    CRITICAL = "CRITICAL"            # Direct structural clash (e.g. exact duplicate serial claim)


class EvidenceStrength(str, Enum):
    """Categorical strength of the underlying observation."""
    WEAK = "WEAK"                    # Indirect heuristic or partial token similarity
    MODERATE = "MODERATE"            # Solid corroboration across standard metrics
    STRONG = "STRONG"                # Mathematical proof, exact match, or immutable ledger fact
    CONTRADICTORY = "CONTRADICTORY"  # Evidence directly contradicts equivalence or concern
    UNRESOLVED = "UNRESOLVED"        # Missing attributes prevent confidence evaluation


class AssessmentStatus(str, Enum):
    """High-level analytical status summarizing the balance of evidence."""
    NO_MATERIAL_SIGNAL = "NO_MATERIAL_SIGNAL"          # No elevated concerns detected in available data
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"          # One or more signals suggest investigative inquiry
    ELEVATED_REVIEW_PRIORITY = "ELEVATED_REVIEW_PRIORITY"  # Independent severe findings require expedited review
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"    # Pervasive missing attributes prevent meaningful evaluation
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"      # Material contradictory signals exist (e.g. matching name, distinct country)


class ReviewPriority(str, Enum):
    """Investigator triage queue prioritization level."""
    NONE = "NONE"      # Routine clearance
    LOW = "LOW"        # Background informational monitoring
    MEDIUM = "MEDIUM"  # Standard compliance review
    HIGH = "HIGH"      # Priority investigative desk inquiry
    URGENT = "URGENT"  # Immediate hold pending evidence clearance


class EvidenceItem(BaseModel):
    """Individual explainable evidence item traceable to underlying data."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable evidence identifier (e.g. 'EVD-REC-001')")
    category: EvidenceCategory = Field(..., description="Evidence category taxonomy")
    source_stage: SourceStage = Field(..., description="Analytics phase producing the observation")
    rule_id: str = Field(..., description="Deterministic detection rule identifier")
    title: str = Field(..., description="Short descriptive title of the finding")
    explanation: str = Field(..., description="Detailed, explainable description of what was observed")
    severity: EvidenceSeverity = Field(..., description="Analytical severity classification")
    evidence_strength: EvidenceStrength = Field(..., description="Strength of the underlying evidence")
    supporting_records: List[str] = Field(default_factory=list, description="IDs, unit ranges, or references")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative metrics (HHI, Gini, Z-score, etc.)")
    thresholds: Dict[str, Any] = Field(default_factory=dict, description="Benchmark thresholds applied")
    provenance: MetadataProvenance = Field(
        default=MetadataProvenance.DATABASE_CENSUS,
        description="Origin of underlying data",
    )
    limitations: List[str] = Field(default_factory=list, description="Analytical limits or caveats")
    counterevidence: List[str] = Field(default_factory=list, description="Exculpatory or mitigating facts observed")
    contextual_caveats: List[str] = Field(
        default_factory=list,
        description="General commercial domain practices and operational caveats (not verified against private contracts)",
    )
    missing_information: List[str] = Field(default_factory=list, description="Data absent from source records")
    recommended_action: str = Field(..., description="Recommended investigative follow-up")
    dependency_group_id: Optional[str] = Field(None, description="Identifier of correlated evidence cluster")


class EvidenceDependencyGroup(BaseModel):
    """Cluster of mutually correlated evidence items rooted in the same underlying facts.
    
    Prevents artificial inflation of review severity when multiple modules
    report on the exact same underlying event or field.
    """
    model_config = ConfigDict(frozen=True)

    group_id: str = Field(..., description="Unique cluster identifier (e.g. 'GRP-SERIAL-OVERLAP-1')")
    primary_signal: str = Field(..., description="Primary rule or observation leading the cluster")
    correlated_evidence_ids: List[str] = Field(..., description="IDs of all evidence items in this cluster")
    shared_data_source: str = Field(..., description="Common underlying data artifact (e.g. 'SERIAL_INTERVAL')")
    is_reinforcing_not_independent: bool = Field(
        True,
        description="True if signals reinforce each other rather than constituting independent proof",
    )
    explanation: str = Field(..., description="Why these items are correlated and not independent proof")


class AssessmentTarget(BaseModel):
    """Grounded target scope and identifiers under evaluation."""
    model_config = ConfigDict(frozen=True)

    scope: AssessmentScope
    registry: Optional[str] = None
    batch_id: Optional[str] = None
    project_id: Optional[str] = None
    claim_id: Optional[int] = None
    entity_a: Optional[str] = None
    entity_b: Optional[str] = None
    description: Optional[str] = None


class RiskAssessmentRequest(BaseModel):
    """API request payload for unified risk assessment."""
    scope: AssessmentScope = Field(..., description="Target scope ('BATCH', 'PROJECT', 'CLAIM', 'ENTITY', 'CROSS_REGISTRY', 'AD_HOC')")
    registry: Optional[str] = Field(None, description="Registry standard ('VCS', 'GS')")
    batch_id: Optional[str] = Field(None, description="Batch identifier string")
    project_id: Optional[str] = Field(None, description="Project identifier string")
    claim_id: Optional[int] = Field(None, description="Existing claim ID in ledger")
    entity_a: Optional[str] = Field(None, description="Primary entity name")
    entity_b: Optional[str] = Field(None, description="Secondary entity name for comparison")
    records: Optional[List[Dict[str, Any]]] = Field(None, description="Ad-hoc retirement records for batch/population evaluation")
    project_a: Optional[Dict[str, Any]] = Field(None, description="Project profile dict for cross-registry comparison")
    project_b: Optional[Dict[str, Any]] = Field(None, description="Project profile dict for cross-registry comparison")
    candidate_range: Optional[Tuple[int, int]] = Field(None, description="Optional unit range (start, end) for allocation check")
    claimant: Optional[str] = Field(None, description="Optional claimant name for allocation check")


class AssessmentRuleDefinition(BaseModel):
    """Catalog definition of a deterministic risk assessment rule."""
    model_config = ConfigDict(frozen=True)

    rule_id: str
    name: str
    category: EvidenceCategory
    source_stage: SourceStage
    default_severity: EvidenceSeverity
    default_strength: EvidenceStrength
    description: str
    rationale: str
    limitations: List[str]


class AssessmentRulesCatalogResponse(BaseModel):
    """Response containing the versioned ruleset catalog."""
    ruleset_version: str = Field(default=RULESET_VERSION)
    total_rules: int
    rules: List[AssessmentRuleDefinition]


class RiskAssessmentResponse(BaseModel):
    """Unified explainable risk assessment response for market investigators."""
    model_config = ConfigDict(frozen=True)

    assessment_id: str = Field(..., description="Deterministic assessment hash identifier")
    ruleset_version: str = Field(default=RULESET_VERSION, description="Version of assessment ruleset applied")
    assessment_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of evaluation")
    target: AssessmentTarget = Field(..., description="Target scope and identifiers")
    
    # Overall synthesis
    overall_status: AssessmentStatus = Field(..., description="Synthesized balance-of-evidence status")
    review_priority: ReviewPriority = Field(..., description="Investigator queue priority")
    priority_explanation: str = Field(..., description="Transparent explanation of why this priority was assigned")
    triggered_rule_ids: List[str] = Field(default_factory=list, description="Rules that produced positive findings")
    
    # Granular evidence
    evidence_items: List[EvidenceItem] = Field(default_factory=list, description="Structured evidence items")
    counterevidence_items: List[str] = Field(default_factory=list, description="Observed exculpatory and mitigating facts")
    contextual_caveats: List[str] = Field(
        default_factory=list,
        description="General commercial domain practices and operational caveats (not verified against private contracts)",
    )
    missing_information_items: List[str] = Field(default_factory=list, description="Missing data points in source records")
    
    # Double-counting safeguards
    dependency_groups: List[EvidenceDependencyGroup] = Field(
        default_factory=list,
        description="Correlated evidence clusters grouped by shared data source",
    )
    independent_evidence_count: int = Field(
        ...,
        description="Count of distinct independent evidence groups (safeguard against double-counting)",
    )
    correlated_evidence_count: int = Field(
        ...,
        description="Total evidence items falling into dependency clusters",
    )
    
    # Audit provenance & metadata
    source_stages_consulted: List[SourceStage] = Field(
        default_factory=list,
        description="Underlying analytical modules executed",
    )
    methodology_limitations: List[str] = Field(
        default_factory=list,
        description="Explicit methodological boundaries and caveats",
    )
    recommended_next_steps: List[str] = Field(
        default_factory=list,
        description="Concrete recommended investigative steps",
    )
    disclaimer: str = Field(default=ASSESSMENT_DISCLAIMER)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump()


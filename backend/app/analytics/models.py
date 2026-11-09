"""Data models for statistical, concentration, fragmentation, temporal, and cross-registry analytics."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BeneficiaryCategory(str, Enum):
    """Classification category for beneficiary values."""
    NON_PLACEHOLDER_DISCLOSED = "NON_PLACEHOLDER_DISCLOSED"
    EXPLICITLY_UNDISCLOSED = "EXPLICITLY_UNDISCLOSED"
    INVALID_OR_PLACEHOLDER = "INVALID_OR_PLACEHOLDER"
    UNRESOLVED_IDENTITY = "UNRESOLVED_IDENTITY"


class ConcentrationTier(str, Enum):
    """Descriptive portfolio concentration bands based on classical Herfindahl-Hirschman Index (HHI) ranges.

    Methodological Note: These tiers reflect descriptive distribution within the analyzed batch
    or population. They do not constitute market shares in an economically defined relevant antitrust
    market, and do not establish competition-law or regulatory conclusions.
    """
    SINGLE_LABEL_DOMINANCE = "SINGLE_LABEL_DOMINANCE"  # One disclosed label holds 100% of disclosed volume (HHI >= 9,999 or K=1)
    HIGH_CONCENTRATION = "HIGH_CONCENTRATION"          # HHI > 2,500: Disclosed volume concentrated among few entities
    MODERATE_CONCENTRATION = "MODERATE_CONCENTRATION"  # 1,500 <= HHI <= 2,500: Moderate distribution across claimants
    BROAD_DISTRIBUTION = "BROAD_DISTRIBUTION"          # 500 <= HHI < 1,500: Broad distribution across multiple claimants
    HIGH_DISPERSION = "HIGH_DISPERSION"                # HHI < 500: High dispersion across numerous small claimants
    NOT_CLASSIFIED = "NOT_CLASSIFIED"                  # Zero disclosed volume available to classify


class VelocityTier(str, Enum):
    """Retirement liquidation velocity tiers (Future Phase 2C extensibility)."""
    NORMAL = "NORMAL"
    ACCELERATED = "ACCELERATED"
    RAPID_BURST = "RAPID_BURST"
    DORMANT_LIQUIDATION = "DORMANT_LIQUIDATION"
    INSUFFICIENT_TEMPORAL_DATA = "INSUFFICIENT_TEMPORAL_DATA"


class DualTrackCoverage(BaseModel):
    """Dual-track coverage accounting comparing record-count and volume disclosure."""
    model_config = ConfigDict(frozen=True)

    total_records: int = Field(..., ge=0, description="Total retirement records in analyzed population")
    total_quantity: float = Field(..., ge=0.0, description="Total retirement tonnes in analyzed population")

    disclosed_records: int = Field(..., ge=0, description="Non-placeholder disclosed record count")
    disclosed_quantity: float = Field(..., ge=0.0, description="Non-placeholder disclosed quantity in tonnes")

    explicitly_undisclosed_records: int = Field(..., ge=0, description="Missing or explicitly undisclosed record count")
    explicitly_undisclosed_quantity: float = Field(..., ge=0.0, description="Missing or explicitly undisclosed quantity in tonnes")

    invalid_placeholder_records: int = Field(..., ge=0, description="Syntactic noise and placeholder record count")
    invalid_placeholder_quantity: float = Field(..., ge=0.0, description="Syntactic noise and placeholder quantity in tonnes")

    unresolved_records: int = Field(..., ge=0, description="Total unresolved records (undisclosed + placeholder)")
    unresolved_quantity: float = Field(..., ge=0.0, description="Total unresolved tonnes (undisclosed + placeholder)")

    record_disclosure_rate: float = Field(..., ge=0.0, le=1.0, description="Disclosed records / total records [0.0, 1.0]")
    quantity_disclosure_rate: float = Field(..., ge=0.0, le=1.0, description="Disclosed tonnes / total tonnes [0.0, 1.0]")

    record_unresolved_rate: float = Field(..., ge=0.0, le=1.0, description="Unresolved records / total records [0.0, 1.0]")
    quantity_unresolved_rate: float = Field(..., ge=0.0, le=1.0, description="Unresolved tonnes / total tonnes [0.0, 1.0]")

    classification_definition: str = Field(
        default="Records with missing, unknown, or explicitly undisclosed beneficiary information under the documented source-data classification policy. This classification does not independently establish the reason for non-disclosure or a legal or contractual privacy entitlement.",
        description="Formal policy definition of undisclosed category"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_records": self.total_records,
            "total_quantity": round(self.total_quantity, 2),
            "disclosed_records": self.disclosed_records,
            "disclosed_quantity": round(self.disclosed_quantity, 2),
            "explicitly_undisclosed_records": self.explicitly_undisclosed_records,
            "explicitly_undisclosed_quantity": round(self.explicitly_undisclosed_quantity, 2),
            "invalid_placeholder_records": self.invalid_placeholder_records,
            "invalid_placeholder_quantity": round(self.invalid_placeholder_quantity, 2),
            "unresolved_records": self.unresolved_records,
            "unresolved_quantity": round(self.unresolved_quantity, 2),
            "record_disclosure_rate": round(self.record_disclosure_rate, 6),
            "quantity_disclosure_rate": round(self.quantity_disclosure_rate, 6),
            "record_unresolved_rate": round(self.record_unresolved_rate, 6),
            "quantity_unresolved_rate": round(self.quantity_unresolved_rate, 6),
            "classification_definition": self.classification_definition,
        }


class ConcentrationMetrics(BaseModel):
    """Dual-track beneficiary concentration and diversity metrics."""
    model_config = ConfigDict(frozen=True)

    coverage: DualTrackCoverage = Field(..., description="Complete dual-track population disclosure coverage")

    total_units: float = Field(..., ge=0.0, description="Total retirement units analyzed")
    disclosed_units: float = Field(..., ge=0.0, description="Total units with identified non-placeholder beneficiaries")
    unresolved_units: float = Field(..., ge=0.0, description="Units with missing, undisclosed, or placeholder beneficiaries")
    beneficiary_coverage_ratio: float = Field(..., ge=0.0, le=1.0, description="Disclosed units / total units [0.0, 1.0]")
    unresolved_share: float = Field(..., ge=0.0, le=1.0, description="Unresolved units / total units [0.0, 1.0]")

    unique_disclosed_beneficiaries: int = Field(..., ge=0, description="Count of distinct disclosed normalized beneficiary labels")
    hhi_disclosed: float = Field(..., ge=0.0, le=10000.0, description="Herfindahl-Hirschman Index [0, 10000]")
    hhi_normalized: float = Field(..., ge=0.0, le=1.0, description="Finite-population normalized HHI [0.0, 1.0]")
    entropy_shannon_disclosed: float = Field(..., ge=0.0, description="Shannon entropy in bits (base-2)")
    entropy_normalized: float = Field(..., ge=0.0, le=1.0, description="Shannon equitability index [0.0, 1.0]")

    dominant_disclosed_beneficiary: Optional[str] = Field(None, description="Normalized label with highest disclosed volume")
    dominant_disclosed_share: float = Field(0.0, ge=0.0, le=1.0, description="Disclosed share of dominant entity [0.0, 1.0]")
    top3_disclosed_share: float = Field(0.0, ge=0.0, le=1.0, description="Combined disclosed share of top 3 entities [0.0, 1.0]")
    tier: str = Field(..., description="Descriptive concentration band classification (not an antitrust determination)")
    disclosed_shares: Dict[str, float] = Field(default_factory=dict, description="Share per disclosed normalized label")

    disclaimer: str = Field(
        default="Beneficiary concentration measures describe the distribution of disclosed retirement quantities among normalized beneficiary labels in the observed dataset. They do not establish relevant market shares, market power, competition, ownership, or legal relationships.",
        description="Methodological boundary disclaimer"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage": self.coverage.to_dict(),
            "total_units": round(self.total_units, 2),
            "disclosed_units": round(self.disclosed_units, 2),
            "unresolved_units": round(self.unresolved_units, 2),
            "beneficiary_coverage_ratio": round(self.beneficiary_coverage_ratio, 6),
            "unresolved_share": round(self.unresolved_share, 6),
            "unique_disclosed_beneficiaries": self.unique_disclosed_beneficiaries,
            "hhi_disclosed": round(self.hhi_disclosed, 2),
            "hhi_normalized": round(self.hhi_normalized, 4),
            "entropy_shannon_disclosed": round(self.entropy_shannon_disclosed, 4),
            "entropy_normalized": round(self.entropy_normalized, 4),
            "dominant_disclosed_beneficiary": self.dominant_disclosed_beneficiary,
            "dominant_disclosed_share": round(self.dominant_disclosed_share, 4),
            "top3_disclosed_share": round(self.top3_disclosed_share, 4),
            "tier": self.tier,
            "disclosed_shares": {k: round(v, 6) for k, v in self.disclosed_shares.items()},
            "disclaimer": self.disclaimer,
        }


class BatchIntervalStructure(BaseModel):
    """Structural interval metrics and boundary validation for a batch."""
    model_config = ConfigDict(frozen=True)

    total_intervals: int = Field(..., ge=0, description="Number of allocation intervals in batch")
    min_unit_start: Optional[int] = Field(None, description="Lowest serial number start")
    max_unit_end: Optional[int] = Field(None, description="Highest serial number end")
    interval_span: Optional[int] = Field(None, ge=0, description="Span from min start to max end")
    interval_density: float = Field(0.0, ge=0.0, description="Total units / interval span [0.0, 1.0]")

    exact_duplicate_intervals_count: int = Field(0, ge=0, description="Count of exact duplicate intervals")
    overlapping_intervals_count: int = Field(0, ge=0, description="Count of allocation intervals colliding with preceding active intervals in sweep-line order")
    pairwise_overlap_count: int = Field(0, ge=0, description="Exact count of distinct overlapping interval pairs")
    contiguous_intervals_count: int = Field(0, ge=0, description="Count of adjacent contiguous intervals")
    disjoint_gaps_count: int = Field(0, ge=0, description="Count of gaps between allocations")
    has_invalid_intervals: bool = Field(False, description="True if any start > end or negative bounds detected")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_intervals": self.total_intervals,
            "min_unit_start": self.min_unit_start,
            "max_unit_end": self.max_unit_end,
            "interval_span": self.interval_span,
            "interval_density": round(self.interval_density, 4),
            "exact_duplicate_intervals_count": self.exact_duplicate_intervals_count,
            "overlapping_intervals_count": self.overlapping_intervals_count,
            "pairwise_overlap_count": self.pairwise_overlap_count,
            "contiguous_intervals_count": self.contiguous_intervals_count,
            "disjoint_gaps_count": self.disjoint_gaps_count,
            "has_invalid_intervals": self.has_invalid_intervals,
        }


class FragmentationMetrics(BaseModel):
    """Batch sizing, dispersion, Gini inequality, and micro-claim metrics."""
    model_config = ConfigDict(frozen=True)

    total_events: int = Field(..., ge=0, description="Number of retirement events in batch")
    total_units: float = Field(..., ge=0.0, description="Sum of retired units in batch")

    gini_coefficient: float = Field(..., ge=0.0, le=1.0, description="Standard sample Gini coefficient [0.0, 1.0]")
    gini_sample_corrected: float = Field(..., ge=0.0, le=1.0, description="Finite-sample corrected Gini [0.0, 1.0]")

    mean_event_size: float = Field(..., ge=0.0, description="Arithmetic mean volume per event")
    median_event_size: float = Field(..., ge=0.0, description="Median volume per event")
    min_event_size: float = Field(..., ge=0.0, description="Minimum single event volume")
    max_event_size: float = Field(..., ge=0.0, description="Maximum single event volume")
    p25_event_size: float = Field(..., ge=0.0, description="25th percentile event volume")
    p75_event_size: float = Field(..., ge=0.0, description="75th percentile event volume")
    std_dev_event_size: float = Field(..., ge=0.0, description="Sample standard deviation of event sizes")
    iqr_event_size: float = Field(..., ge=0.0, description="Interquartile range (p75 - p25)")

    # Absolute de minimis micro-claims (default <= 10.0 tonnes)
    micro_claim_count: int = Field(..., ge=0, description="Count of absolute micro-claim events (<= micro_threshold)")
    micro_claim_units: float = Field(..., ge=0.0, description="Total units retired in absolute micro-claims")
    micro_claim_record_share: float = Field(..., ge=0.0, le=1.0, description="Micro-claim records / total records [0.0, 1.0]")
    micro_claim_quantity_share: float = Field(..., ge=0.0, le=1.0, description="Micro-claim volume / total volume [0.0, 1.0]")
    micro_claim_threshold_used: float = Field(..., ge=0.0, description="Absolute micro-claim threshold in tonnes")

    # Relative small allocations (<= 1% of batch volume)
    small_tranche_count: int = Field(0, ge=0, description="Count of relative small allocations (<= 1% of batch volume)")
    small_tranche_units: float = Field(0.0, ge=0.0, description="Total units retired in relative small allocations")
    small_tranche_record_share: float = Field(0.0, ge=0.0, le=1.0, description="Small tranche records / total records [0.0, 1.0]")
    small_tranche_quantity_share: float = Field(0.0, ge=0.0, le=1.0, description="Small tranche volume / total volume [0.0, 1.0]")
    small_tranche_threshold_used: float = Field(0.0, ge=0.0, description="Relative threshold in tonnes (1% of batch)")

    classification_counts: Dict[str, int] = Field(default_factory=dict, description="Record counts by beneficiary classification")
    classification_quantities: Dict[str, float] = Field(default_factory=dict, description="Volume by beneficiary classification")
    classification_record_shares: Dict[str, float] = Field(default_factory=dict, description="Record share by classification")
    classification_quantity_shares: Dict[str, float] = Field(default_factory=dict, description="Volume share by classification")

    distinct_disclosed_beneficiaries: int = Field(0, ge=0, description="Count of distinct disclosed normalized beneficiary labels in batch")
    intervals: Optional[BatchIntervalStructure] = Field(None, description="Interval structure and validation analysis")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_events": self.total_events,
            "total_units": round(self.total_units, 2),
            "gini_coefficient": round(self.gini_coefficient, 4),
            "gini_sample_corrected": round(self.gini_sample_corrected, 4),
            "mean_event_size": round(self.mean_event_size, 2),
            "median_event_size": round(self.median_event_size, 2),
            "min_event_size": round(self.min_event_size, 2),
            "max_event_size": round(self.max_event_size, 2),
            "p25_event_size": round(self.p25_event_size, 2),
            "p75_event_size": round(self.p75_event_size, 2),
            "std_dev_event_size": round(self.std_dev_event_size, 2),
            "iqr_event_size": round(self.iqr_event_size, 2),
            "micro_claim_count": self.micro_claim_count,
            "micro_claim_units": round(self.micro_claim_units, 2),
            "micro_claim_record_share": round(self.micro_claim_record_share, 4),
            "micro_claim_quantity_share": round(self.micro_claim_quantity_share, 4),
            "micro_claim_threshold_used": round(self.micro_claim_threshold_used, 2),
            "small_tranche_count": self.small_tranche_count,
            "small_tranche_units": round(self.small_tranche_units, 2),
            "small_tranche_record_share": round(self.small_tranche_record_share, 4),
            "small_tranche_quantity_share": round(self.small_tranche_quantity_share, 4),
            "small_tranche_threshold_used": round(self.small_tranche_threshold_used, 2),
            "classification_counts": self.classification_counts,
            "classification_quantities": {k: round(v, 2) for k, v in self.classification_quantities.items()},
            "classification_record_shares": {k: round(v, 6) for k, v in self.classification_record_shares.items()},
            "classification_quantity_shares": {k: round(v, 6) for k, v in self.classification_quantity_shares.items()},
            "distinct_disclosed_beneficiaries": self.distinct_disclosed_beneficiaries,
            "intervals": self.intervals.to_dict() if self.intervals else None,
        }


class BatchAnalyticsResult(BaseModel):
    """Unified container for all statistical, concentration, and fragmentation analytics for a batch."""
    registry: str
    batch_id: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    country: Optional[str] = None
    vintage: Optional[int] = None
    total_quantity: float
    total_events: int

    concentration: ConcentrationMetrics
    fragmentation: FragmentationMetrics
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry": self.registry,
            "batch_id": self.batch_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "country": self.country,
            "vintage": self.vintage,
            "total_quantity": round(self.total_quantity, 2),
            "total_events": self.total_events,
            "concentration": self.concentration.to_dict(),
            "fragmentation": self.fragmentation.to_dict(),
            "computed_at": self.computed_at.isoformat(),
        }


class PopulationAnalyticsSummary(BaseModel):
    """Summary of population-level concentration and batch fragmentation across reference dataset."""
    total_retirement_records: int
    total_retirement_quantity: float
    total_batches: int

    coverage: DualTrackCoverage
    overall_concentration: ConcentrationMetrics

    # Within-batch inequality distribution
    batch_record_counts: Dict[str, float]
    batch_quantities: Dict[str, float]
    batch_gini_distribution: Dict[str, float]

    # Portfolio-wide pooled allocation inequality
    pooled_allocation_count: int
    pooled_allocation_quantity: float
    pooled_allocation_mean_size: float
    pooled_allocation_gini: float

    batches_with_micro_claims: int
    batches_with_small_tranches: int
    batches_with_overlaps: int
    single_record_batches: int
    multi_record_batches: int

    batch_gini_interpretation: str = Field(
        default="batch_gini_distribution reports the across-batch distribution of within-batch Gini coefficients across 725 batches (mean 0.4924), measuring allocation uniformity within projects. pooled_allocation_gini (0.9605) measures overall credit sizing inequality across the entire 37,335-allocation registry portfolio.",
        description="Methodological distinction between micro-batch Gini and macro pooled Gini"
    )
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_retirement_records": self.total_retirement_records,
            "total_retirement_quantity": round(self.total_retirement_quantity, 2),
            "total_batches": self.total_batches,
            "coverage": self.coverage.to_dict(),
            "overall_concentration": self.overall_concentration.to_dict(),
            "batch_record_counts": {k: round(v, 2) for k, v in self.batch_record_counts.items()},
            "batch_quantities": {k: round(v, 2) for k, v in self.batch_quantities.items()},
            "batch_gini_distribution": {k: round(v, 4) for k, v in self.batch_gini_distribution.items()},
            "pooled_allocation_count": self.pooled_allocation_count,
            "pooled_allocation_quantity": round(self.pooled_allocation_quantity, 2),
            "pooled_allocation_mean_size": round(self.pooled_allocation_mean_size, 2),
            "pooled_allocation_gini": round(self.pooled_allocation_gini, 4),
            "batches_with_micro_claims": self.batches_with_micro_claims,
            "batches_with_small_tranches": self.batches_with_small_tranches,
            "batches_with_overlaps": self.batches_with_overlaps,
            "single_record_batches": self.single_record_batches,
            "multi_record_batches": self.multi_record_batches,
            "batch_gini_interpretation": self.batch_gini_interpretation,
            "computed_at": self.computed_at.isoformat(),
        }


# Request models
class ConcentrationRequest(BaseModel):
    """Input payload for ad-hoc beneficiary concentration analysis."""
    records: List[Dict[str, Any]] = Field(..., min_length=1, description="List of allocation/retirement records")
    total_units_override: Optional[float] = Field(None, ge=0.0, description="Optional total units denominator")


class BatchFragmentationRequest(BaseModel):
    """Input payload for ad-hoc batch fragmentation analysis."""
    registry: str = "ADHOC"
    batch_id: str = "ADHOC-BATCH"
    project_id: Optional[str] = None
    records: List[Dict[str, Any]] = Field(..., min_length=1, description="List of allocation/retirement records")
    micro_threshold: float = Field(10.0, ge=0.0, description="Absolute micro-claim threshold in tonnes (default 10.0)")


class BatchAnalyticsRequest(BaseModel):
    """Input payload for ad-hoc batch analytics combining concentration and fragmentation."""
    registry: str = "ADHOC"
    batch_id: str = "ADHOC-BATCH"
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    country: Optional[str] = None
    vintage: Optional[int] = None
    records: List[Dict[str, Any]] = Field(..., min_length=1, description="List of allocation/retirement records")

    @model_validator(mode="after")
    def validate_records(self) -> BatchAnalyticsRequest:
        for idx, rec in enumerate(self.records):
            if "unit_start" in rec and "unit_end" in rec:
                s = int(rec["unit_start"])
                e = int(rec["unit_end"])
                if s > e:
                    raise ValueError(f"Record at index {idx} has invalid interval: unit_start ({s}) > unit_end ({e})")
            elif "quantity" in rec and float(rec["quantity"]) < 0:
                raise ValueError(f"Record at index {idx} has negative quantity")
        return self


# Forward Extensibility Schemas (Phase 2C Future Capabilities)
class TemporalMetrics(BaseModel):
    """Retirement velocity, vintage dormancy, and liquidation burst metrics."""
    model_config = ConfigDict(frozen=True)

    first_event_date: Optional[date] = None
    last_event_date: Optional[date] = None
    timespan_days: int = 0
    total_volume: float = 0.0
    burn_rate_tonnes_per_day: float = 0.0
    peak_daily_volume: float = 0.0
    peak_event_date: Optional[date] = None

    vintage_year: Optional[int] = None
    mean_vintage_lag_days: Optional[float] = None
    median_vintage_lag_days: Optional[float] = None
    min_vintage_lag_days: Optional[int] = None
    max_vintage_lag_days: Optional[int] = None

    liquidation_burst_flag: bool = False
    fiscal_quarter_clustering_share: float = 0.0
    dominant_quarter: Optional[str] = None
    velocity_tier: str = VelocityTier.INSUFFICIENT_TEMPORAL_DATA.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "first_event_date": self.first_event_date.isoformat() if self.first_event_date else None,
            "last_event_date": self.last_event_date.isoformat() if self.last_event_date else None,
            "timespan_days": self.timespan_days,
            "total_volume": round(self.total_volume, 2),
            "burn_rate_tonnes_per_day": round(self.burn_rate_tonnes_per_day, 2),
            "peak_daily_volume": round(self.peak_daily_volume, 2),
            "peak_event_date": self.peak_event_date.isoformat() if self.peak_event_date else None,
            "vintage_year": self.vintage_year,
            "mean_vintage_lag_days": round(self.mean_vintage_lag_days, 1) if self.mean_vintage_lag_days is not None else None,
            "median_vintage_lag_days": round(self.median_vintage_lag_days, 1) if self.median_vintage_lag_days is not None else None,
            "min_vintage_lag_days": self.min_vintage_lag_days,
            "max_vintage_lag_days": self.max_vintage_lag_days,
            "liquidation_burst_flag": self.liquidation_burst_flag,
            "fiscal_quarter_clustering_share": round(self.fiscal_quarter_clustering_share, 4),
            "dominant_quarter": self.dominant_quarter,
            "velocity_tier": self.velocity_tier,
        }


class CrossRegistryMatch(BaseModel):
    """Similarity and duplicate issuance risk indicators between registries."""
    model_config = ConfigDict(frozen=True)

    registry_a: str = Field(..., description="First registry identifier (e.g. 'VCS')")
    project_id_a: str = Field(..., description="Project ID in registry A")
    project_name_a: str = Field(..., description="Project name in registry A")
    developer_a: Optional[str] = Field(None, description="Developer / proponent in registry A")
    country_a: Optional[str] = Field(None, description="Country in registry A")

    registry_b: str = Field(..., description="Second registry identifier (e.g. 'GS')")
    project_id_b: str = Field(..., description="Project ID in registry B")
    project_name_b: str = Field(..., description="Project name in registry B")
    developer_b: Optional[str] = Field(None, description="Developer / proponent in registry B")
    country_b: Optional[str] = Field(None, description="Country in registry B")

    project_name_similarity: float = Field(..., ge=0.0, le=1.0, description="Composite token and string similarity")
    country_match: bool = Field(..., description="True if country codes match exactly")
    developer_similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity between project developers/proponents")
    vintage_overlap: bool = Field(..., description="True if project vintage spans intersect")

    composite_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall cross-registry identity confidence [0, 1]")
    potential_duplicate_risk: bool = Field(..., description="Flag indicating potential dual-registry listing risk")
    explanation: str = Field(..., description="Human-readable explanation of the correlation")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry_a": self.registry_a,
            "project_id_a": self.project_id_a,
            "project_name_a": self.project_name_a,
            "developer_a": self.developer_a,
            "country_a": self.country_a,
            "registry_b": self.registry_b,
            "project_id_b": self.project_id_b,
            "project_name_b": self.project_name_b,
            "developer_b": self.developer_b,
            "country_b": self.country_b,
            "project_name_similarity": round(self.project_name_similarity, 4),
            "country_match": self.country_match,
            "developer_similarity": round(self.developer_similarity, 4),
            "vintage_overlap": self.vintage_overlap,
            "composite_confidence": round(self.composite_confidence, 4),
            "potential_duplicate_risk": self.potential_duplicate_risk,
            "explanation": self.explanation,
        }


class CrossRegistryRequest(BaseModel):
    """Input payload for cross-registry project correlation query."""
    project_name: str = Field(..., min_length=1, description="Candidate project name")
    country: Optional[str] = Field(None, description="Country code (ISO alpha-2)")
    vintage: Optional[int] = Field(None, description="Target vintage year")
    developer: Optional[str] = Field(None, description="Project developer / proponent")
    threshold: float = Field(0.80, ge=0.0, le=1.0, description="Minimum composite confidence threshold")


# ==============================================================================
# PHASE 2C STAGE 2: TEMPORAL RETIREMENT INTELLIGENCE SCHEMAS
# ==============================================================================

class AggregationPeriod(str, Enum):
    """Temporal aggregation granularity."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TrendDirection(str, Enum):
    """Direction of temporal retirement trend."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class BurstType(str, Enum):
    """Dimension of identified retirement burst."""
    TONNES = "TONNES"
    RECORDS = "RECORDS"
    BOTH = "BOTH"
    NONE = "NONE"


class GapClassification(str, Enum):
    """Classification of temporal inactivity interval within observed dataset population."""
    SUSTAINED_ZERO_ACTIVITY_INTERVAL = "SUSTAINED_ZERO_ACTIVITY_INTERVAL"
    INTERMITTENT_ZERO_ACTIVITY_INTERVAL = "INTERMITTENT_ZERO_ACTIVITY_INTERVAL"
    DATASET_BOUNDARY = "DATASET_BOUNDARY"


TEMPORAL_DISCLAIMER = (
    "Temporal retirement intelligence provides investigative signals regarding retirement pacing, "
    "clustering, and structural gaps based on registry transaction execution dates ('Retirement Date'). "
    "It does not establish fraud, market manipulation, contractual non-performance, or unrecorded OTC secondary trades."
)


class TemporalPeriodActivity(BaseModel):
    """Activity metrics for a single deterministic calendar period."""
    model_config = ConfigDict(frozen=True)

    period_start: date = Field(..., description="Start date of aggregation period (inclusive)")
    period_end: date = Field(..., description="End date of aggregation period (inclusive)")
    period_label: str = Field(..., description="Human-readable ISO period identifier (e.g. '2022-10', '2022-W42')")

    record_count: int = Field(..., ge=0, description="Count of retirement events in period")
    total_tonnes: float = Field(..., ge=0.0, description="Total units retired in period")
    average_tonnes_per_record: float = Field(..., ge=0.0, description="Mean volume per retirement record in period")

    records_with_usable_dates: int = Field(..., ge=0, description="Retirement records with parsed valid event_date")
    records_with_missing_or_invalid_dates: int = Field(0, ge=0, description="Retirement records with null/unparseable event_date")
    usable_date_quantity: float = Field(..., ge=0.0, description="Tonnes retired with valid event_date")
    excluded_date_quantity: float = Field(0.0, ge=0.0, description="Tonnes retired with null/unparseable event_date")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "period_label": self.period_label,
            "record_count": self.record_count,
            "total_tonnes": round(self.total_tonnes, 2),
            "average_tonnes_per_record": round(self.average_tonnes_per_record, 2),
            "records_with_usable_dates": self.records_with_usable_dates,
            "records_with_missing_or_invalid_dates": self.records_with_missing_or_invalid_dates,
            "usable_date_quantity": round(self.usable_date_quantity, 2),
            "excluded_date_quantity": round(self.excluded_date_quantity, 2),
        }


class TemporalActivityResponse(BaseModel):
    """Population or filtered retirement activity across time periods."""
    model_config = ConfigDict(frozen=True)

    registry: Optional[str] = None
    project_id: Optional[str] = None
    period_type: str = Field(..., description="Aggregation period: 'daily', 'weekly', 'monthly'")

    total_periods: int = Field(..., ge=0, description="Total calendar periods in evaluated span")
    total_records: int = Field(..., ge=0, description="Total retirement records in evaluated span")
    total_tonnes: float = Field(..., ge=0.0, description="Total units retired in evaluated span")
    active_periods_count: int = Field(..., ge=0, description="Periods with at least one retirement event")
    zero_activity_periods_count: int = Field(..., ge=0, description="Periods with zero observed retirements")

    earliest_date_observed: Optional[date] = None
    latest_date_observed: Optional[date] = None

    disclaimer: str = Field(default=TEMPORAL_DISCLAIMER, description="Methodological boundary disclaimer")
    periods: List[TemporalPeriodActivity] = Field(default_factory=list, description="Ordered time series of period activities")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry": self.registry,
            "project_id": self.project_id,
            "period_type": self.period_type,
            "total_periods": self.total_periods,
            "total_records": self.total_records,
            "total_tonnes": round(self.total_tonnes, 2),
            "active_periods_count": self.active_periods_count,
            "zero_activity_periods_count": self.zero_activity_periods_count,
            "earliest_date_observed": self.earliest_date_observed.isoformat() if self.earliest_date_observed else None,
            "latest_date_observed": self.latest_date_observed.isoformat() if self.latest_date_observed else None,
            "disclaimer": self.disclaimer,
            "periods": [p.to_dict() for p in self.periods],
        }


class TemporalTrendPeriod(BaseModel):
    """Rolling trend analysis for a single calendar period."""
    model_config = ConfigDict(frozen=True)

    period_start: date
    period_end: date
    period_label: str
    record_count: int
    total_tonnes: float
    average_tonnes_per_record: float

    rolling_average_records: Optional[float] = Field(None, description="Rolling mean of record counts over prior W completed periods")
    rolling_average_tonnes: Optional[float] = Field(None, description="Rolling mean of retired tonnes over prior W completed periods")

    record_count_change: Optional[int] = Field(None, description="Absolute change in records from previous period")
    tonne_quantity_change: Optional[float] = Field(None, description="Absolute change in tonnes from previous period")

    record_count_pct_change: Optional[float] = Field(None, description="Percentage change in records from previous period")
    tonne_quantity_pct_change: Optional[float] = Field(None, description="Percentage change in tonnes from previous period")

    direction: str = Field(
        ...,
        description="Direction of volume velocity ('increasing', 'decreasing', or 'stable') based on retired tonnes. Transaction count changes are reported separately in record_count_change.",
    )
    has_sufficient_history: bool = Field(..., description="True if at least W historical periods preceded this observation")
    data_coverage_status: str = Field(..., description="'COMPLETE_WINDOW' or 'INSUFFICIENT_HISTORY'")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "period_label": self.period_label,
            "record_count": self.record_count,
            "total_tonnes": round(self.total_tonnes, 2),
            "average_tonnes_per_record": round(self.average_tonnes_per_record, 2),
            "rolling_average_records": round(self.rolling_average_records, 2) if self.rolling_average_records is not None else None,
            "rolling_average_tonnes": round(self.rolling_average_tonnes, 2) if self.rolling_average_tonnes is not None else None,
            "record_count_change": self.record_count_change,
            "tonne_quantity_change": round(self.tonne_quantity_change, 2) if self.tonne_quantity_change is not None else None,
            "record_count_pct_change": round(self.record_count_pct_change, 2) if self.record_count_pct_change is not None else None,
            "tonne_quantity_pct_change": round(self.tonne_quantity_pct_change, 2) if self.tonne_quantity_pct_change is not None else None,
            "direction": self.direction,
            "has_sufficient_history": self.has_sufficient_history,
            "data_coverage_status": self.data_coverage_status,
        }


class TemporalTrendsResponse(BaseModel):
    """Historical rolling trends across time series."""
    model_config = ConfigDict(frozen=True)

    registry: Optional[str] = None
    project_id: Optional[str] = None
    period_type: str = Field(..., description="Aggregation period: 'daily', 'weekly', 'monthly'")
    rolling_window: int = Field(..., ge=1, description="Size of historical rolling window in periods")
    direction_threshold_pct: float = Field(..., ge=0.0, description="Percentage change threshold to classify increasing/decreasing")

    total_periods: int = Field(..., ge=0)
    sufficient_history_periods: int = Field(..., ge=0)
    insufficient_history_periods: int = Field(..., ge=0)

    disclaimer: str = Field(default=TEMPORAL_DISCLAIMER)
    trends: List[TemporalTrendPeriod] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry": self.registry,
            "project_id": self.project_id,
            "period_type": self.period_type,
            "rolling_window": self.rolling_window,
            "direction_threshold_pct": self.direction_threshold_pct,
            "total_periods": self.total_periods,
            "sufficient_history_periods": self.sufficient_history_periods,
            "insufficient_history_periods": self.insufficient_history_periods,
            "disclaimer": self.disclaimer,
            "trends": [t.to_dict() for t in self.trends],
        }


class TemporalBurstPeriod(BaseModel):
    """Burst detection analysis for a single calendar period."""
    model_config = ConfigDict(frozen=True)

    period_start: date
    period_end: date
    period_label: str

    observed_records: int
    baseline_median_records: float
    baseline_mad_records: float
    record_burst_threshold: float
    record_burst_flag: bool
    record_dispersion_method: str = Field("MAD", description="'MAD' or 'ZERO_MAD_FLOOR'")

    observed_tonnes: float
    baseline_median_tonnes: float
    baseline_mad_tonnes: float
    tonne_burst_threshold: float
    tonne_burst_flag: bool
    tonne_dispersion_method: str = Field("MAD", description="'MAD' or 'ZERO_MAD_FLOOR'")

    burst_type: str = Field(..., description="'BOTH', 'TONNES', 'RECORDS', or 'NONE'")
    is_burst: bool = Field(..., description="True if any burst dimension triggered")
    has_sufficient_history: bool = Field(..., description="True if minimum historical baseline exists")
    explanation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "period_label": self.period_label,
            "observed_records": self.observed_records,
            "baseline_median_records": round(self.baseline_median_records, 2),
            "baseline_mad_records": round(self.baseline_mad_records, 2),
            "record_burst_threshold": round(self.record_burst_threshold, 2),
            "record_burst_flag": self.record_burst_flag,
            "record_dispersion_method": self.record_dispersion_method,
            "observed_tonnes": round(self.observed_tonnes, 2),
            "baseline_median_tonnes": round(self.baseline_median_tonnes, 2),
            "baseline_mad_tonnes": round(self.baseline_mad_tonnes, 2),
            "tonne_burst_threshold": round(self.tonne_burst_threshold, 2),
            "tonne_burst_flag": self.tonne_burst_flag,
            "tonne_dispersion_method": self.tonne_dispersion_method,
            "burst_type": self.burst_type,
            "is_burst": self.is_burst,
            "has_sufficient_history": self.has_sufficient_history,
            "explanation": self.explanation,
        }


class TemporalBurstsResponse(BaseModel):
    """Explainable temporal burst detection results across evaluated time periods."""
    model_config = ConfigDict(frozen=True)

    registry: Optional[str] = None
    project_id: Optional[str] = None
    period_type: str = Field(..., description="Aggregation period: 'daily', 'weekly', 'monthly'")
    sensitivity: float = Field(..., description="Multiplier k applied to MAD (default 3.0)")
    baseline_window: int = Field(..., ge=1, description="Historical lookback window periods (evaluated period excluded)")

    total_periods_evaluated: int = Field(..., ge=0)
    burst_periods_count: int = Field(..., ge=0)

    disclaimer: str = Field(default=TEMPORAL_DISCLAIMER)
    bursts: List[TemporalBurstPeriod] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry": self.registry,
            "project_id": self.project_id,
            "period_type": self.period_type,
            "sensitivity": self.sensitivity,
            "baseline_window": self.baseline_window,
            "total_periods_evaluated": self.total_periods_evaluated,
            "burst_periods_count": self.burst_periods_count,
            "disclaimer": self.disclaimer,
            "bursts": [b.to_dict() for b in self.bursts],
        }


class TemporalGapItem(BaseModel):
    """Contiguous interval of observed inactivity in registry records."""
    model_config = ConfigDict(frozen=True)

    gap_start: date
    gap_end: date
    gap_duration_days: int = Field(..., ge=0)
    gap_duration_periods: int = Field(..., ge=1)

    previous_activity_period: Optional[Dict[str, Any]] = None
    next_activity_period: Optional[Dict[str, Any]] = None
    gap_classification: str = Field(
        ...,
        description="'SUSTAINED_ZERO_ACTIVITY_INTERVAL', 'INTERMITTENT_ZERO_ACTIVITY_INTERVAL', 'DATASET_BOUNDARY'",
    )
    coverage_limitation_note: str = Field(
        default="Zero observed records reflects activity within the ingested project dataset and does not establish market-wide dormancy, complete source coverage, or lack of secondary market transactions outside this registry."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_start": self.gap_start.isoformat(),
            "gap_end": self.gap_end.isoformat(),
            "gap_duration_days": self.gap_duration_days,
            "gap_duration_periods": self.gap_duration_periods,
            "previous_activity_period": self.previous_activity_period,
            "next_activity_period": self.next_activity_period,
            "gap_classification": self.gap_classification,
            "coverage_limitation_note": self.coverage_limitation_note,
        }


class TemporalGapsResponse(BaseModel):
    """Temporal gaps and inactivity intervals analysis."""
    model_config = ConfigDict(frozen=True)

    registry: Optional[str] = None
    project_id: Optional[str] = None
    period_type: str = Field(..., description="Aggregation period: 'daily', 'weekly', 'monthly'")

    total_gaps_count: int = Field(..., ge=0)
    max_gap_duration_days: int = Field(..., ge=0)
    mean_gap_duration_days: float = Field(..., ge=0.0)

    disclaimer: str = Field(default=TEMPORAL_DISCLAIMER)
    gaps: List[TemporalGapItem] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry": self.registry,
            "project_id": self.project_id,
            "period_type": self.period_type,
            "total_gaps_count": self.total_gaps_count,
            "max_gap_duration_days": self.max_gap_duration_days,
            "mean_gap_duration_days": round(self.mean_gap_duration_days, 1),
            "disclaimer": self.disclaimer,
            "gaps": [g.to_dict() for g in self.gaps],
        }


# ==============================================================================
# PHASE 2C STAGE 3: CROSS-REGISTRY INTELLIGENCE SCHEMAS
# ==============================================================================

CROSS_REGISTRY_DISCLAIMER = (
    "Cross-registry intelligence provides investigative signals regarding candidate relationships, "
    "attribute similarities, and comparative retirement patterns across voluntary standards. "
    "It does not establish legal-entity equivalence, prove fraudulent dual-listing, or demonstrate "
    "duplicate credit claims. Numerical serial numbers from distinct registries represent disjoint namespaces "
    "and are never equated."
)


class ProjectCorrelationCategory(str, Enum):
    """Transparent categories of cross-registry project correlation evidence."""
    EXACT_IDENTIFIER_MATCH = "EXACT_IDENTIFIER_MATCH"
    CROSS_REGISTRY_IDENTIFIER_COLLISION = "CROSS_REGISTRY_IDENTIFIER_COLLISION"
    STRONG_ATTRIBUTE_CORRELATION = "STRONG_ATTRIBUTE_CORRELATION"
    PARTIAL_ATTRIBUTE_CORRELATION = "PARTIAL_ATTRIBUTE_CORRELATION"
    NAME_SIMILARITY_ONLY = "NAME_SIMILARITY_ONLY"
    CONFLICTING_ATTRIBUTES = "CONFLICTING_ATTRIBUTES"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceStrength(str, Enum):
    """Categorical evidence strength levels (non-probabilistic)."""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    CONTRADICTORY = "CONTRADICTORY"
    INSUFFICIENT = "INSUFFICIENT"


class MetadataProvenance(str, Enum):
    """Constrained taxonomy of project metadata origin."""
    DATABASE_CENSUS = "DATABASE_CENSUS"
    AD_HOC_API_INPUT = "AD_HOC_API_INPUT"


class ProjectProfile(BaseModel):
    """Standardized representation of a carbon offset project across registries."""
    model_config = ConfigDict(frozen=True)

    registry: str = Field(..., description="Registry identifier ('VCS', 'GS', or other)")
    project_id: Optional[str] = Field(None, description="Registry-specific project identifier")
    project_name: str = Field(..., description="Official project name/title")
    country: Optional[str] = Field(None, description="Project country or jurisdiction")
    vintage: Optional[Union[str, int]] = Field(None, description="Vintage year or vintage range")
    developer: Optional[str] = Field(None, description="Optional developer/proponent name")
    project_type: Optional[str] = Field(None, description="Optional project type / sectoral scope")
    methodology: Optional[str] = Field(None, description="Optional methodology identifier")
    provenance: MetadataProvenance = Field(
        default=MetadataProvenance.AD_HOC_API_INPUT,
        description="Provenance of metadata: 'DATABASE_CENSUS' or 'AD_HOC_API_INPUT'",
    )


class CrossRegistryProjectComparison(BaseModel):
    """Detailed, explainable comparison between two projects."""
    model_config = ConfigDict(frozen=True)

    project_a: ProjectProfile
    project_b: ProjectProfile
    is_cross_registry: bool = Field(..., description="True if registries are distinct")
    correlation_category: str = Field(..., description="Transparent evidence category name")
    evidence_strength: str = Field(..., description="Evidence level: 'STRONG', 'MODERATE', 'WEAK', 'CONTRADICTORY', 'INSUFFICIENT'")

    # Name similarity metrics
    name_similarity_score: float = Field(..., ge=0.0, le=1.0, description="Normalized composite name similarity [0.0, 1.0]")
    name_tokens_a: List[str] = Field(default_factory=list, description="Normalized comparison tokens for project A")
    name_tokens_b: List[str] = Field(default_factory=list, description="Normalized comparison tokens for project B")
    token_set_ratio: float = Field(..., ge=0.0, le=1.0)
    token_sort_ratio: float = Field(..., ge=0.0, le=1.0)
    jaro_winkler_similarity: float = Field(..., ge=0.0, le=1.0)

    # Attribute comparisons
    identifier_match: bool = Field(False, description="True if identifier strings match exactly")
    country_relation: str = Field("MISSING", description="'MATCH', 'CONFLICT', or 'MISSING'")
    vintage_relation: str = Field("MISSING", description="'OVERLAP', 'ADJACENT', 'DISJOINT', or 'MISSING'")
    developer_similarity: Optional[float] = Field(None, description="Optional developer similarity if both provided")

    # Explanations
    matching_attributes: List[str] = Field(default_factory=list, description="Attributes with positive corroborating evidence")
    conflicting_attributes: List[str] = Field(default_factory=list, description="Attributes with contradictory values")
    missing_attributes: List[str] = Field(default_factory=list, description="Attributes missing from one or both projects")
    explanation: str = Field(..., description="Human-readable synthesis of the evidence")
    limitations: str = Field(
        default=(
            "Investigative triage signal only. Does NOT establish fraud, duplicate credit issuance, "
            "or legal-entity identity. Independent registry attestation is required to verify dual-listing."
        )
    )
    disclaimer: str = Field(default=CROSS_REGISTRY_DISCLAIMER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_a": self.project_a.model_dump(),
            "project_b": self.project_b.model_dump(),
            "is_cross_registry": self.is_cross_registry,
            "correlation_category": self.correlation_category,
            "evidence_strength": self.evidence_strength,
            "name_similarity_score": round(self.name_similarity_score, 4),
            "name_tokens_a": self.name_tokens_a,
            "name_tokens_b": self.name_tokens_b,
            "token_set_ratio": round(self.token_set_ratio, 4),
            "token_sort_ratio": round(self.token_sort_ratio, 4),
            "jaro_winkler_similarity": round(self.jaro_winkler_similarity, 4),
            "identifier_match": self.identifier_match,
            "country_relation": self.country_relation,
            "vintage_relation": self.vintage_relation,
            "developer_similarity": round(self.developer_similarity, 4) if self.developer_similarity is not None else None,
            "matching_attributes": self.matching_attributes,
            "conflicting_attributes": self.conflicting_attributes,
            "missing_attributes": self.missing_attributes,
            "explanation": self.explanation,
            "limitations": self.limitations,
            "disclaimer": self.disclaimer,
        }


class CrossRegistryProjectCompareRequest(BaseModel):
    """Payload for comparing two projects."""
    project_a: ProjectProfile
    project_b: ProjectProfile


class CrossRegistryCorrelationsResponse(BaseModel):
    """Response containing multiple cross-registry candidate project correlations."""
    model_config = ConfigDict(frozen=True)

    total_candidates_evaluated: int
    matched_candidates_count: int
    min_similarity_threshold: float
    category_filter: Optional[str] = None
    country_filter: Optional[str] = None
    correlations: List[CrossRegistryProjectComparison] = Field(default_factory=list)
    disclaimer: str = Field(default=CROSS_REGISTRY_DISCLAIMER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_candidates_evaluated": self.total_candidates_evaluated,
            "matched_candidates_count": self.matched_candidates_count,
            "min_similarity_threshold": self.min_similarity_threshold,
            "category_filter": self.category_filter,
            "country_filter": self.country_filter,
            "correlations": [c.to_dict() for c in self.correlations],
            "disclaimer": self.disclaimer,
        }


class CrossRegistryEntityCompareRequest(BaseModel):
    """Payload for cross-registry entity comparison."""
    entity_a: str = Field(..., min_length=1, description="Entity name from Registry A")
    entity_b: str = Field(..., min_length=1, description="Entity name from Registry B")
    registry_a: str = Field("VCS", description="Source registry of entity A")
    registry_b: str = Field("GS", description="Source registry of entity B")


class CrossRegistryEntityComparison(BaseModel):
    """Explainable entity resolution across registries."""
    model_config = ConfigDict(frozen=True)

    registry_a: str
    entity_raw_a: str
    entity_normalized_a: str
    registry_b: str
    entity_raw_b: str
    entity_normalized_b: str

    is_match: bool
    relationship_type: str
    match_tier: str
    overall_score: float
    positive_signals: List[str]
    contradictory_signals: List[str]
    missing_information: List[str]
    explanation: str
    legal_disclaimer: str = (
        "Shared organization names or matching text tokens do not prove legal-entity equivalence. "
        "Intermediary brokers, subsidiaries, and corporate affiliates remain distinct legal entities."
    )
    disclaimer: str = Field(default=CROSS_REGISTRY_DISCLAIMER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry_a": self.registry_a,
            "entity_raw_a": self.entity_raw_a,
            "entity_normalized_a": self.entity_normalized_a,
            "registry_b": self.registry_b,
            "entity_raw_b": self.entity_raw_b,
            "entity_normalized_b": self.entity_normalized_b,
            "is_match": self.is_match,
            "relationship_type": self.relationship_type,
            "match_tier": self.match_tier,
            "overall_score": round(self.overall_score, 2),
            "positive_signals": self.positive_signals,
            "contradictory_signals": self.contradictory_signals,
            "missing_information": self.missing_information,
            "explanation": self.explanation,
            "legal_disclaimer": self.legal_disclaimer,
            "disclaimer": self.disclaimer,
        }


class RegistryRetirementStats(BaseModel):
    """Retirement-only statistics for a specific registry."""
    model_config = ConfigDict(frozen=True)

    registry: str
    total_retirement_records: int
    total_retired_tonnes: float
    active_projects_count: int
    earliest_retirement_date: Optional[str] = None
    latest_retirement_date: Optional[str] = None
    disclosed_records_count: int
    beneficiary_record_disclosure_rate_pct: float = Field(
        ...,
        description="Proportion of retirement records with a non-placeholder beneficiary identity disclosed. Does NOT measure missing transaction quantity or missing registry metadata.",
    )
    beneficiary_quantity_disclosure_rate_pct: float = Field(
        ...,
        description="Proportion of retired tonnes associated with non-placeholder beneficiary identities. Does NOT measure missing transaction quantity or missing registry metadata.",
    )
    record_disclosure_rate_pct: float = Field(
        ...,
        description="DEPRECATED alias for beneficiary_record_disclosure_rate_pct. Measures beneficiary identity disclosure only, not general transaction data disclosure.",
    )
    disclosed_tonnes_quantity: float
    quantity_disclosure_rate_pct: float = Field(
        ...,
        description="DEPRECATED alias for beneficiary_quantity_disclosure_rate_pct. Measures beneficiary identity disclosure only, not general transaction data disclosure.",
    )
    issuance_records_excluded: int
    available_source_fields: List[str]
    unpopulated_or_sparse_fields: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registry": self.registry,
            "total_retirement_records": self.total_retirement_records,
            "total_retired_tonnes": round(self.total_retired_tonnes, 2),
            "active_projects_count": self.active_projects_count,
            "earliest_retirement_date": self.earliest_retirement_date,
            "latest_retirement_date": self.latest_retirement_date,
            "disclosed_records_count": self.disclosed_records_count,
            "record_disclosure_rate_pct": round(self.record_disclosure_rate_pct, 2),
            "beneficiary_record_disclosure_rate_pct": round(self.beneficiary_record_disclosure_rate_pct, 2),
            "disclosed_tonnes_quantity": round(self.disclosed_tonnes_quantity, 2),
            "quantity_disclosure_rate_pct": round(self.quantity_disclosure_rate_pct, 2),
            "beneficiary_quantity_disclosure_rate_pct": round(self.beneficiary_quantity_disclosure_rate_pct, 2),
            "issuance_records_excluded": self.issuance_records_excluded,
            "available_source_fields": self.available_source_fields,
            "unpopulated_or_sparse_fields": self.unpopulated_or_sparse_fields,
        }


class CrossRegistryRetirementSummary(BaseModel):
    """Comparative retirement summary across voluntary registries."""
    model_config = ConfigDict(frozen=True)

    registries: Dict[str, RegistryRetirementStats]
    combined_retirement_records: int
    combined_retired_tonnes: float
    total_issuance_records_excluded: int
    comparability_notes: List[str]
    disclaimer: str = Field(default=CROSS_REGISTRY_DISCLAIMER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registries": {k: v.to_dict() for k, v in self.registries.items()},
            "combined_retirement_records": self.combined_retirement_records,
            "combined_retired_tonnes": round(self.combined_retired_tonnes, 2),
            "total_issuance_records_excluded": self.total_issuance_records_excluded,
            "comparability_notes": self.comparability_notes,
            "disclaimer": self.disclaimer,
        }


class CrossRegistryTrendsPeriod(BaseModel):
    """Side-by-side volume and record count for a calendar period."""
    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    period_label: str
    vcs_record_count: int
    vcs_total_tonnes: float
    gs_record_count: int
    gs_total_tonnes: float
    combined_record_count: int
    combined_total_tonnes: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "period_label": self.period_label,
            "vcs_record_count": self.vcs_record_count,
            "vcs_total_tonnes": round(self.vcs_total_tonnes, 2),
            "gs_record_count": self.gs_record_count,
            "gs_total_tonnes": round(self.gs_total_tonnes, 2),
            "combined_record_count": self.combined_record_count,
            "combined_total_tonnes": round(self.combined_total_tonnes, 2),
        }


class CrossRegistryTrendsResponse(BaseModel):
    """Comparative retirement pacing trends across registries."""
    model_config = ConfigDict(frozen=True)

    period_type: str
    total_periods: int
    trends: List[CrossRegistryTrendsPeriod] = Field(default_factory=list)
    disclaimer: str = Field(default=CROSS_REGISTRY_DISCLAIMER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_type": self.period_type,
            "total_periods": self.total_periods,
            "trends": [t.to_dict() for t in self.trends],
            "disclaimer": self.disclaimer,
        }


ProjectProfile.model_rebuild()
CrossRegistryProjectComparison.model_rebuild()
CrossRegistryProjectCompareRequest.model_rebuild()
CrossRegistryCorrelationsResponse.model_rebuild()
CrossRegistryEntityCompareRequest.model_rebuild()
CrossRegistryEntityComparison.model_rebuild()
RegistryRetirementStats.model_rebuild()
CrossRegistryRetirementSummary.model_rebuild()
CrossRegistryTrendsPeriod.model_rebuild()
CrossRegistryTrendsResponse.model_rebuild()

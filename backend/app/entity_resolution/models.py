"""Data models for entity resolution, intermediary extraction, and explainable scoring."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class MatchTier(str, Enum):
    """Calibrated confidence tiers for entity match candidates."""
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RelationshipType(str, Enum):
    """Relationship categories between carbon-market entity names."""
    EXACT_MATCH = "EXACT_MATCH"
    CANONICAL_VARIANT = "CANONICAL_VARIANT"
    CORPORATE_HIERARCHY_OR_SUBSIDIARY = "CORPORATE_HIERARCHY_OR_SUBSIDIARY"
    INTERMEDIARY_DELEGATION = "INTERMEDIARY_DELEGATION"
    DIFFERENT_ENTITIES = "DIFFERENT_ENTITIES"
    UNRESOLVED = "UNRESOLVED"


class IntermediaryRole(str, Enum):
    """Role classification for intermediary parties in retirement transactions."""
    DIRECT = "DIRECT"
    BROKER_OR_TRADER = "BROKER_OR_TRADER"
    PLATFORM_OR_AGGREGATOR = "PLATFORM_OR_AGGREGATOR"
    CUSTOMER_POOL = "CUSTOMER_POOL"
    RETIRING_ACCOUNT_HOLDER = "RETIRING_ACCOUNT_HOLDER"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class EntityName:
    """Canonical representation of an entity name with full provenance tracking."""
    raw_value: str | None
    normalized_value: str | None
    canonical_name: str
    tokens: tuple[str, ...] = field(default_factory=tuple)
    legal_suffix: str | None = None
    raw_legal_suffix: str | None = None
    corporate_qualifiers: tuple[str, ...] = field(default_factory=tuple)
    is_placeholder: bool = False
    placeholder_type: str | None = None
    operations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "canonical_name": self.canonical_name,
            "tokens": list(self.tokens),
            "legal_suffix": self.legal_suffix,
            "raw_legal_suffix": self.raw_legal_suffix,
            "corporate_qualifiers": list(self.corporate_qualifiers),
            "is_placeholder": self.is_placeholder,
            "placeholder_type": self.placeholder_type,
            "operations": list(self.operations),
        }


@dataclass(frozen=True)
class IntermediaryRelationship:
    """Structured extraction of an on-behalf-of or broker allocation relationship."""
    is_delegated: bool
    principal_raw: str | None
    principal_entity: EntityName | None
    intermediary_raw: str | None
    intermediary_entity: EntityName | None
    role: str = IntermediaryRole.DIRECT.value
    pattern_matched: str | None = None
    raw_text: str = ""
    confidence: float = 0.0
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_delegated": self.is_delegated,
            "principal_raw": self.principal_raw,
            "principal_entity": self.principal_entity.to_dict() if self.principal_entity else None,
            "intermediary_raw": self.intermediary_raw,
            "intermediary_entity": self.intermediary_entity.to_dict() if self.intermediary_entity else None,
            "role": self.role,
            "pattern_matched": self.pattern_matched,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class FeatureScore:
    """Individual feature score contributing to the explainable match score."""
    name: str
    raw_score: float
    weight: float
    contribution: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MatchResult:
    """Explainable result of comparing two entity candidates."""
    entity_a: EntityName
    entity_b: EntityName
    overall_score: float
    match_tier: str
    relationship_type: str
    is_match: bool
    feature_scores: dict[str, FeatureScore] = field(default_factory=dict)
    positive_signals: list[str] = field(default_factory=list)
    contradictory_signals: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    intermediary_context: IntermediaryRelationship | None = None
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_a": self.entity_a.to_dict(),
            "entity_b": self.entity_b.to_dict(),
            "overall_score": round(self.overall_score, 2),
            "match_tier": self.match_tier,
            "relationship_type": self.relationship_type,
            "is_match": self.is_match,
            "feature_scores": {k: v.to_dict() for k, v in self.feature_scores.items()},
            "positive_signals": self.positive_signals,
            "contradictory_signals": self.contradictory_signals,
            "missing_information": self.missing_information,
            "intermediary_context": self.intermediary_context.to_dict() if self.intermediary_context else None,
            "explanation": self.explanation,
        }


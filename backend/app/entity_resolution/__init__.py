"""Entity resolution, intermediary extraction, and explainable alignment for OnceOnly."""
from __future__ import annotations

from .blocking import EntityCandidateGenerator
from .engine import EntityResolutionEngine
from .intermediary import IntermediaryExtractor
from .matcher import EntityMatcher
from .models import (
    EntityName,
    FeatureScore,
    IntermediaryRelationship,
    IntermediaryRole,
    MatchResult,
    MatchTier,
    RelationshipType,
)
from .normalizer import EntityNormalizer

__all__ = [
    "EntityCandidateGenerator",
    "EntityMatcher",
    "EntityName",
    "EntityNormalizer",
    "EntityResolutionEngine",
    "FeatureScore",
    "IntermediaryExtractor",
    "IntermediaryRelationship",
    "IntermediaryRole",
    "MatchResult",
    "MatchTier",
    "RelationshipType",
]


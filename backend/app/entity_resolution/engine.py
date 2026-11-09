"""Unified Entity Resolution Engine for OnceOnly."""
from __future__ import annotations

from typing import Any

from .blocking import EntityCandidateGenerator
from .intermediary import IntermediaryExtractor
from .matcher import EntityMatcher
from .models import (
    EntityName,
    IntermediaryRelationship,
    IntermediaryRole,
    MatchResult,
    MatchTier,
    RelationshipType,
)
from .normalizer import EntityNormalizer


class EntityResolutionEngine:
    """High-level facade for carbon-market entity normalization, intermediary extraction, and resolution."""

    @classmethod
    def normalize(cls, raw: str | None) -> EntityName:
        """Parse raw string into canonical EntityName with full provenance."""
        return EntityNormalizer.normalize(raw)

    @classmethod
    def extract_intermediary(cls, text: str | None) -> IntermediaryRelationship:
        """Extract intermediary and beneficial principal relationships from text."""
        return IntermediaryExtractor.extract(text)

    @classmethod
    def resolve_pair(
        cls,
        name_a: str | None,
        name_b: str | None,
        context: dict[str, Any] | None = None,
    ) -> MatchResult:
        """Resolve relationship between two entity strings with intermediary and alias awareness."""
        # 1. Check for intermediary delegation in either string
        rel_a = cls.extract_intermediary(name_a)
        rel_b = cls.extract_intermediary(name_b)

        # Direct normalization of raw strings
        ent_a = rel_a.principal_entity or cls.normalize(name_a)
        ent_b = rel_b.principal_entity or cls.normalize(name_b)

        # Context to attach
        int_context: IntermediaryRelationship | None = None
        if rel_b.is_delegated:
            int_context = rel_b
        elif rel_a.is_delegated:
            int_context = rel_a

        # 2. Match the principal entities
        result = EntityMatcher.match(ent_a, ent_b, intermediary_context=int_context)

        # 3. If an intermediary pattern was present and principals matched
        if int_context and int_context.is_delegated:
            if result.is_match:
                # Upgraded to INTERMEDIARY_DELEGATION
                result.relationship_type = RelationshipType.INTERMEDIARY_DELEGATION.value
                int_name = int_context.intermediary_raw or "intermediary broker"
                pr_name = int_context.principal_raw or "corporate principal"
                result.positive_signals.append(
                    f"Intermediary allocation identified: '{int_name}' retired on behalf of '{pr_name}'"
                )
                result.explanation = (
                    f"Claimant matches the beneficial principal disclosed in the intermediary allocation "
                    f"('{pr_name}' via '{int_name}')."
                )
            else:
                # Check if claimant matches the intermediary themselves
                if int_context.intermediary_entity:
                    int_match = EntityMatcher.match(ent_a, int_context.intermediary_entity)
                    if int_match.is_match:
                        result.is_match = True
                        result.match_tier = int_match.match_tier
                        result.relationship_type = RelationshipType.INTERMEDIARY_DELEGATION.value
                        result.overall_score = max(result.overall_score, int_match.overall_score * 0.90)
                        result.positive_signals.append(
                            f"Claimant matches the recorded intermediary account holder ('{int_context.intermediary_raw}')"
                        )
                        result.missing_information.append(
                            "Evidence of downstream client assignment or internal offset authorization is recommended"
                        )
                        result.explanation = (
                            f"Claimant matches the intermediary entity ('{int_context.intermediary_raw}') rather than "
                            f"the downstream principal. Downstream allocation documentation should be kept on file."
                        )

        return result

    @classmethod
    def resolve_claimant_against_registry(
        cls,
        claimant: str,
        registry_beneficiaries: list[str],
    ) -> list[MatchResult]:
        """Resolve a claimant against all beneficiaries disclosed in registry records, ranked by score."""
        results: list[MatchResult] = []
        for ben in registry_beneficiaries:
            res = cls.resolve_pair(claimant, ben)
            results.append(res)

        # Sort by overall_score descending
        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results

    @classmethod
    def block_and_match(
        cls,
        claimants: list[str],
        registry_names: list[str],
        shared_namespace: str | None = None,
    ) -> list[MatchResult]:
        """Candidate-blocked matching to avoid O(N^2) pairwise comparisons."""
        norm_claimants = [cls.normalize(c) for c in claimants if c]
        norm_registry = [cls.normalize(r) for r in registry_names if r]

        candidates = EntityCandidateGenerator.generate_candidate_pairs(
            norm_claimants, norm_registry, shared_namespace=shared_namespace
        )

        results: list[MatchResult] = []
        for c_ent, r_ent, shared_keys in candidates:
            match_res = EntityMatcher.match(c_ent, r_ent)
            if shared_keys:
                match_res.positive_signals.append(f"Candidate generated via shared blocking keys: {sorted(shared_keys)}")
            results.append(match_res)

        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results

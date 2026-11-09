"""Explainable similarity scoring and relationship classification for entity resolution."""
from __future__ import annotations

import re
from typing import Any

from rapidfuzz import distance, fuzz

from .models import (
    EntityName,
    FeatureScore,
    IntermediaryRelationship,
    MatchResult,
    MatchTier,
    RelationshipType,
)

# Known conflicting sector/industry pairs that indicate different companies
_SECTOR_WORDS: set[str] = {
    "solar", "wind", "hydro", "thermal", "gas", "oil", "coal", "nuclear",
    "electric", "power", "energy", "aviation", "air", "airlines", "maritime",
    "shipping", "rail", "automotive", "mining", "steel", "cement", "forestry",
    "agriculture", "telecom", "bank", "banking", "finance", "capital",
}

# Number extraction pattern
_NUM_RE = re.compile(r"\b\d+\b")


class EntityMatcher:
    """Computes explainable, multi-feature entity similarity scores with contradiction detection."""

    # Explicit, documented feature weights summing to 1.0
    WEIGHT_TOKEN_SET = 0.30
    WEIGHT_TOKEN_SORT = 0.25
    WEIGHT_JARO_WINKLER = 0.25
    WEIGHT_TOKEN_JACCARD = 0.20

    @classmethod
    def match(
        cls,
        ent_a: EntityName,
        ent_b: EntityName,
        intermediary_context: IntermediaryRelationship | None = None,
    ) -> MatchResult:
        """Compare two entities and produce a fully explainable MatchResult."""
        positive_signals: list[str] = []
        contradictory_signals: list[str] = []
        missing_information: list[str] = []

        # 1. Handle missing / placeholder records
        if ent_a.is_placeholder or ent_b.is_placeholder:
            ptype = ent_a.placeholder_type or ent_b.placeholder_type or "undisclosed"
            missing_information.append(
                f"Entity record contains an undisclosed placeholder or empty name ('{ptype}')"
            )
            return MatchResult(
                entity_a=ent_a,
                entity_b=ent_b,
                overall_score=0.0,
                match_tier=MatchTier.INSUFFICIENT_EVIDENCE.value,
                relationship_type=RelationshipType.UNRESOLVED.value,
                is_match=False,
                feature_scores={},
                positive_signals=[],
                contradictory_signals=[],
                missing_information=missing_information,
                intermediary_context=intermediary_context,
                explanation="One or both entity records do not disclose a beneficial entity name. Entitlement cannot be verified by name matching.",
            )

        canon_a = ent_a.canonical_name
        canon_b = ent_b.canonical_name

        # 2. Compute foundational multi-feature metrics
        ts_ratio = fuzz.token_set_ratio(canon_a, canon_b) / 100.0 if (canon_a and canon_b) else 0.0
        tsort_ratio = fuzz.token_sort_ratio(canon_a, canon_b) / 100.0 if (canon_a and canon_b) else 0.0
        jw_sim = distance.JaroWinkler.similarity(canon_a, canon_b) if (canon_a and canon_b) else 0.0
        set_a = set(ent_a.tokens)
        set_b = set(ent_b.tokens)
        union_tokens = set_a | set_b
        inter_tokens = set_a & set_b
        jaccard = (len(inter_tokens) / len(union_tokens)) if union_tokens else 0.0

        raw_features = {
            "token_set_ratio": (ts_ratio, cls.WEIGHT_TOKEN_SET, "RapidFuzz token set ratio (order/subset tolerant)"),
            "token_sort_ratio": (tsort_ratio, cls.WEIGHT_TOKEN_SORT, "RapidFuzz token sort ratio (anagram tolerant)"),
            "jaro_winkler": (jw_sim, cls.WEIGHT_JARO_WINKLER, "Jaro-Winkler character-level prefix similarity"),
            "token_jaccard": (jaccard, cls.WEIGHT_TOKEN_JACCARD, "Distinctive token set Jaccard similarity"),
        }

        feature_scores: dict[str, FeatureScore] = {}
        base_score = 0.0
        for fname, (val, weight, desc) in raw_features.items():
            contrib = val * weight * 100.0
            base_score += contrib
            feature_scores[fname] = FeatureScore(
                name=fname,
                raw_score=round(val, 4),
                weight=weight,
                contribution=round(contrib, 2),
                description=desc,
            )

        # 3. Exact raw match check
        if ent_a.raw_value and ent_b.raw_value and ent_a.raw_value.strip().lower() == ent_b.raw_value.strip().lower():
            positive_signals.append("Exact character-for-character raw string equality")
            if ent_a.legal_suffix and ent_b.legal_suffix:
                positive_signals.append(f"Identical legal suffix: '{ent_a.legal_suffix}'")

            feature_scores["exact_equality"] = FeatureScore(
                "exact_equality", 1.0, 1.0, 100.0, "Exact string equality"
            )
            return MatchResult(
                entity_a=ent_a,
                entity_b=ent_b,
                overall_score=100.0,
                match_tier=MatchTier.HIGH_CONFIDENCE.value,
                relationship_type=RelationshipType.EXACT_MATCH.value,
                is_match=True,
                feature_scores=feature_scores,
                positive_signals=positive_signals,
                contradictory_signals=[],
                missing_information=[],
                intermediary_context=intermediary_context,
                explanation="The entity names are identical.",
            )

        # 4. Canonical equality check
        if canon_a == canon_b:
            positive_signals.append(f"Identical canonical root name: '{canon_a}'")
            if ent_a.legal_suffix == ent_b.legal_suffix:
                if ent_a.legal_suffix:
                    positive_signals.append(f"Compatible normalized legal suffix: '{ent_a.legal_suffix}'")
                feature_scores["canonical_equality"] = FeatureScore(
                    "canonical_equality", 1.0, 1.0, 100.0, "Identical canonical root"
                )
                return MatchResult(
                    entity_a=ent_a,
                    entity_b=ent_b,
                    overall_score=100.0,
                    match_tier=MatchTier.HIGH_CONFIDENCE.value,
                    relationship_type=RelationshipType.CANONICAL_VARIANT.value,
                    is_match=True,
                    feature_scores=feature_scores,
                    positive_signals=positive_signals,
                    contradictory_signals=[],
                    missing_information=[],
                    intermediary_context=intermediary_context,
                    explanation=f"Names resolve to the identical canonical entity '{canon_a}' across formatting or suffix variations.",
                )

        # 5. Evaluate Positive Signals
        if ts_ratio >= 0.90:
            positive_signals.append(f"High token overlap ratio ({ts_ratio:.2f})")
        if jw_sim >= 0.90:
            positive_signals.append(f"High character alignment ({jw_sim:.2f})")
        if inter_tokens:
            positive_signals.append(f"Shared distinctive root tokens: {sorted(inter_tokens)}")

        # Legal suffix evaluation
        suffix_modifier = 0.0
        if ent_a.legal_suffix and ent_b.legal_suffix:
            if ent_a.legal_suffix == ent_b.legal_suffix:
                suffix_modifier = 5.0
                positive_signals.append(f"Compatible normalized legal suffixes: '{ent_a.legal_suffix}'")
            else:
                is_nonprofit_a = "foundation" in canon_a or "fdn" in canon_a
                is_nonprofit_b = "foundation" in canon_b or "fdn" in canon_b
                if is_nonprofit_a != is_nonprofit_b:
                    suffix_modifier = -25.0
                    contradictory_signals.append("Non-profit / commercial legal entity mismatch")
                elif set_a.issubset(set_b) or set_b.issubset(set_a):
                    suffix_modifier = -5.0
                    missing_information.append(
                        f"Different jurisdiction legal forms across entities: '{ent_a.legal_suffix}' vs '{ent_b.legal_suffix}'"
                    )
                else:
                    suffix_modifier = -15.0
                    contradictory_signals.append(
                        f"Divergent legal entity forms: '{ent_a.legal_suffix}' vs '{ent_b.legal_suffix}'"
                    )
        elif bool(ent_a.legal_suffix) != bool(ent_b.legal_suffix):
            missing_information.append("One entity specifies a legal form while the other is recorded without suffix")

        # 6. Evaluate Contradictory Signals (Sector words, numbers, and negative signals)
        contradiction_penalty = 0.0

        # Number mismatch: e.g. "Customer 10184" vs "Customer 10185", "Fund 1" vs "Fund 2"
        nums_a = set(_NUM_RE.findall(canon_a))
        nums_b = set(_NUM_RE.findall(canon_b))
        if nums_a and nums_b and nums_a != nums_b:
            contradiction_penalty += 40.0
            contradictory_signals.append(
                f"Mismatched numeric identifiers: {sorted(nums_a)} vs {sorted(nums_b)}"
            )

        # Distinctive fuel / energy source conflict: e.g. "Electric" vs "Gas", "Solar" vs "Wind"
        fuel_words = {"solar", "wind", "hydro", "thermal", "gas", "oil", "coal", "nuclear", "electric", "hydrogen"}
        diff_fuel_a = set_a & fuel_words
        diff_fuel_b = set_b & fuel_words
        if diff_fuel_a and diff_fuel_b and not (diff_fuel_a & diff_fuel_b):
            contradiction_penalty += 35.0
            contradictory_signals.append(
                f"Conflicting energy source / fuel tokens: {sorted(diff_fuel_a)} vs {sorted(diff_fuel_b)}"
            )

        # Distinctive sector word conflict: e.g. "Maritime" vs "Aviation"
        sec_a = set_a & _SECTOR_WORDS
        sec_b = set_b & _SECTOR_WORDS
        if sec_a and sec_b and not (sec_a & sec_b):
            contradiction_penalty += 35.0
            contradictory_signals.append(
                f"Conflicting industry/sector tokens: {sorted(sec_a)} vs {sorted(sec_b)}"
            )

        # Hard ordinal or negative word conflict (e.g. "First" vs "Second", "New" vs "Old")
        diff_a = set_a - set_b
        diff_b = set_b - set_a
        ordinal_conflicts = {
            ("first", "second"), ("north", "south"), ("east", "west"),
            ("upper", "lower"), ("old", "new"),
        }
        for w1, w2 in ordinal_conflicts:
            if (w1 in diff_a and w2 in diff_b) or (w2 in diff_a and w1 in diff_b):
                contradiction_penalty += 35.0
                contradictory_signals.append(f"Conflicting directional/ordinal tokens: '{w1}' vs '{w2}'")

        # Calculate adjusted score
        final_score = base_score + suffix_modifier - contradiction_penalty
        final_score = max(0.0, min(100.0, final_score))

        # Missing information notes
        if not ent_a.corporate_qualifiers and not ent_b.corporate_qualifiers:
            missing_information.append("No corporate hierarchy or divisional qualifiers disclosed")

        # 7. Calibration of Confidence Tiers and Relationship Types
        # Severe contradictions immediately demote to DIFFERENT_ENTITIES
        if contradiction_penalty >= 30.0:
            match_tier = MatchTier.LOW_CONFIDENCE.value if final_score >= 50.0 else MatchTier.INSUFFICIENT_EVIDENCE.value
            rel_type = RelationshipType.DIFFERENT_ENTITIES.value
            is_match = False
            explanation = (
                f"Entities share name components but exhibit material contradictions: "
                f"{'; '.join(contradictory_signals)}. Not considered the same entity."
            )
        elif final_score >= 88.0:
            match_tier = MatchTier.HIGH_CONFIDENCE.value
            rel_type = RelationshipType.CANONICAL_VARIANT.value
            is_match = True
            explanation = (
                f"High-confidence match (score {final_score:.1f}/100) supported by shared root tokens "
                f"{sorted(inter_tokens)} with no conflicting signals."
            )
        elif final_score >= 50.0 and (set_a.issubset(set_b) or set_b.issubset(set_a)) and inter_tokens:
            # Check for corporate hierarchy / subsidiary (e.g. Microsoft vs Microsoft Ireland Operations)
            match_tier = MatchTier.MEDIUM_CONFIDENCE.value
            rel_type = RelationshipType.CORPORATE_HIERARCHY_OR_SUBSIDIARY.value
            is_match = True
            diff_tokens = sorted(union_tokens - inter_tokens)
            explanation = (
                f"Likely parent/subsidiary or divisional relationship (score {final_score:.1f}/100). "
                f"Core brand matches; differing qualifier tokens: {diff_tokens}."
            )
        elif final_score >= 75.0:
            match_tier = MatchTier.MEDIUM_CONFIDENCE.value
            rel_type = RelationshipType.CANONICAL_VARIANT.value
            is_match = True
            explanation = (
                f"Medium-confidence match candidate (score {final_score:.1f}/100). "
                f"Names exhibit substantial similarity but minor token or suffix differences exist."
            )
        elif final_score >= 50.0:
            match_tier = MatchTier.LOW_CONFIDENCE.value
            rel_type = RelationshipType.DIFFERENT_ENTITIES.value
            is_match = False
            explanation = (
                f"Low-confidence entity similarity (score {final_score:.1f}/100). "
                f"Insufficient evidence to conclude that these represent the same legal claimant."
            )
        else:
            match_tier = MatchTier.INSUFFICIENT_EVIDENCE.value
            rel_type = RelationshipType.DIFFERENT_ENTITIES.value
            is_match = False
            explanation = f"Entity names differ substantially (score {final_score:.1f}/100)."

        return MatchResult(
            entity_a=ent_a,
            entity_b=ent_b,
            overall_score=final_score,
            match_tier=match_tier,
            relationship_type=rel_type,
            is_match=is_match,
            feature_scores=feature_scores,
            positive_signals=positive_signals,
            contradictory_signals=contradictory_signals,
            missing_information=missing_information,
            intermediary_context=intermediary_context,
            explanation=explanation,
        )

"""Candidate generation and multi-index blocking for entity resolution."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import EntityName


class EntityCandidateGenerator:
    """Generates candidate entity pairs using multi-index blocking keys to avoid O(N^2) comparison."""

    @classmethod
    def blocking_keys(cls, entity: EntityName, namespace: str | None = None) -> set[str]:
        """Generate blocking keys for an entity."""
        keys: set[str] = set()

        if entity.is_placeholder or not entity.canonical_name:
            return keys

        tokens = entity.tokens
        if not tokens:
            return keys

        # 1. Primary distinctive token (most significant root token)
        primary = tokens[0]
        keys.add(f"tok:{primary}")

        # 2. Token prefix (first 4 characters of primary token to bridge minor spelling variations)
        if len(primary) >= 4:
            keys.add(f"pfx:{primary[:4]}")

        # 3. Secondary token if present (for multi-word entities e.g. "Delta Electronics")
        if len(tokens) > 1:
            keys.add(f"tok2:{tokens[1]}")

        # 4. Canonical token signature (sorted tokens joined)
        if len(tokens) <= 3:
            sig = "-".join(sorted(tokens))
            keys.add(f"sig:{sig}")

        # 5. Namespace / Project context if provided
        if namespace:
            keys.add(f"ns:{namespace}")

        return keys

    @classmethod
    def index_entities(
        cls,
        entities: Iterable[EntityName],
        namespaces: dict[EntityName, str] | None = None,
    ) -> dict[str, list[EntityName]]:
        """Build an inverted blocking index mapping blocking_key -> list[EntityName]."""
        index: dict[str, list[EntityName]] = defaultdict(list)
        namespaces = namespaces or {}

        for ent in entities:
            if ent.is_placeholder:
                continue
            ns = namespaces.get(ent)
            bkeys = cls.blocking_keys(ent, namespace=ns)
            for k in bkeys:
                index[k].append(ent)

        return dict(index)

    @classmethod
    def generate_candidate_pairs(
        cls,
        claimant_entities: list[EntityName],
        registry_entities: list[EntityName],
        shared_namespace: str | None = None,
    ) -> list[tuple[EntityName, EntityName, set[str]]]:
        """Generate deduplicated candidate pairs between claimants and registry entities sharing blocking keys."""
        # Index registry entities
        reg_index: dict[str, list[EntityName]] = defaultdict(list)
        for rent in registry_entities:
            if rent.is_placeholder:
                continue
            for k in cls.blocking_keys(rent, namespace=shared_namespace):
                reg_index[k].append(rent)

        seen_pairs: set[tuple[str, str]] = set()
        candidates: list[tuple[EntityName, EntityName, set[str]]] = []

        for cent in claimant_entities:
            if cent.is_placeholder:
                continue
            ckeys = cls.blocking_keys(cent, namespace=shared_namespace)
            matched_registry: dict[EntityName, set[str]] = defaultdict(set)
            for k in ckeys:
                if k in reg_index:
                    for rent in reg_index[k]:
                        matched_registry[rent].add(k)

            for rent, shared_keys in matched_registry.items():
                pair_id = (cent.canonical_name, rent.canonical_name)
                if pair_id not in seen_pairs:
                    seen_pairs.add(pair_id)
                    candidates.append((cent, rent, shared_keys))

        return candidates

    @classmethod
    def blocking_metrics(cls, n_a: int, n_b: int, candidates_count: int) -> dict[str, float]:
        """Compute candidate reduction metrics."""
        all_pairs = n_a * n_b
        reduction = 1.0 - (candidates_count / all_pairs) if all_pairs > 0 else 0.0
        return {
            "all_pairs": float(all_pairs),
            "candidates_evaluated": float(candidates_count),
            "reduction_ratio": round(reduction, 6),
            "reduction_percent": round(reduction * 100.0, 2),
        }


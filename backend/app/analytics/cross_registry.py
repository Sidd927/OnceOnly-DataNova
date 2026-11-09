"""Cross-registry intelligence module for OnceOnly.

Evaluates relationships, attribute similarities, entity resolutions, and comparative
retirement dynamics across voluntary carbon market standards (Verra VCS and Gold Standard).

MANDATORY INVARIANTS:
1. Serial Isolation Invariant: Numerical serial integers from different registries represent
   disjoint namespaces and are NEVER compared, equated, or treated as proof of duplicate credits.
2. Evidence Transparency Invariant: Every candidate relationship exposes matching, conflicting,
   and missing attributes. Confidence is never manufactured from missing fields.
3. Legal Entity Invariant: Shared organization names or intermediary attributions do NOT establish
   legal-entity equivalence.
4. Denominator Integrity: Retirement comparisons evaluate strictly `kind = 'retirement'`.
   Issuance records are strictly isolated.
"""
from __future__ import annotations

import difflib
import re
import sqlite3
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from rapidfuzz import distance, fuzz

from .models import (
    CROSS_REGISTRY_DISCLAIMER,
    CrossRegistryCorrelationsResponse,
    CrossRegistryEntityComparison,
    CrossRegistryMatch,
    CrossRegistryProjectComparison,
    CrossRegistryRetirementSummary,
    CrossRegistryTrendsPeriod,
    CrossRegistryTrendsResponse,
    EvidenceStrength,
    MetadataProvenance,
    ProjectCorrelationCategory,
    ProjectProfile,
    RegistryRetirementStats,
)

# Common country name and ISO alpha-2 / alpha-3 mappings
COUNTRY_CANONICAL_MAP: Dict[str, str] = {
    "US": "UNITED STATES",
    "USA": "UNITED STATES",
    "UNITED STATES": "UNITED STATES",
    "UK": "UNITED KINGDOM",
    "GB": "UNITED KINGDOM",
    "GBR": "UNITED KINGDOM",
    "UNITED KINGDOM": "UNITED KINGDOM",
    "IN": "INDIA",
    "IND": "INDIA",
    "INDIA": "INDIA",
    "BR": "BRAZIL",
    "BRA": "BRAZIL",
    "BRAZIL": "BRAZIL",
    "TR": "TURKEY",
    "TUR": "TURKEY",
    "TURKEY": "TURKEY",
    "PE": "PERU",
    "PER": "PERU",
    "PERU": "PERU",
    "UY": "URUGUAY",
    "URY": "URUGUAY",
    "URUGUAY": "URUGUAY",
    "GT": "GUATEMALA",
    "GTM": "GUATEMALA",
    "GUATEMALA": "GUATEMALA",
    "PG": "PAPUA NEW GUINEA",
    "PNG": "PAPUA NEW GUINEA",
    "PAPUA NEW GUINEA": "PAPUA NEW GUINEA",
    "MY": "MALAYSIA",
    "MYS": "MALAYSIA",
    "MALAYSIA": "MALAYSIA",
    "DK": "DENMARK",
    "DNK": "DENMARK",
    "DENMARK": "DENMARK",
    "PK": "PAKISTAN",
    "PAK": "PAKISTAN",
    "PAKISTAN": "PAKISTAN",
    "ZW": "ZIMBABWE",
    "ZWE": "ZIMBABWE",
    "ZIMBABWE": "ZIMBABWE",
    "ID": "INDONESIA",
    "IDN": "INDONESIA",
    "INDONESIA": "INDONESIA",
    "KE": "KENYA",
    "KEN": "KENYA",
    "KENYA": "KENYA",
    "KH": "CAMBODIA",
    "KHM": "CAMBODIA",
    "CAMBODIA": "CAMBODIA",
    "RW": "RWANDA",
    "RWA": "RWANDA",
    "RWANDA": "RWANDA",
    "CO": "COLOMBIA",
    "COL": "COLOMBIA",
    "COLOMBIA": "COLOMBIA",
    "CN": "CHINA",
    "CHN": "CHINA",
    "CHINA": "CHINA",
    "CD": "DEMOCRATIC REPUBLIC OF THE CONGO",
    "COD": "DEMOCRATIC REPUBLIC OF THE CONGO",
    "DR CONGO": "DEMOCRATIC REPUBLIC OF THE CONGO",
    "DEMOCRATIC REPUBLIC OF THE CONGO": "DEMOCRATIC REPUBLIC OF THE CONGO",
    "INTERNATIONAL": "INTERNATIONAL",
}

# Project noise / boilerplate tokens stripped during project name normalization
PROJECT_NOISE_TOKENS: Set[str] = {
    "project",
    "projects",
    "vcs",
    "gs",
    "cdm",
    "phase",
    "grouped",
    "programme",
    "program",
    "activity",
}


def clean_project_mojibake(text: str) -> str:
    """Repair common double-encoded UTF-8 artifacts in project text."""
    if not text:
        return ""
    replacements = {
        "‚Äò": "'",
        "‚Äô": "'",
        "‚Äì": "-",
        "‚Äî": "--",
        "‚Äú": '"',
        "‚Äù": '"',
        "√©": "e",
        "√á": "c",
        "√£": "a",
        "√∏": "o",
        "√±": "n",
        "√∫": "u",
        "√≠": "i",
        "√≥": "o",
    }
    cleaned = text
    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)
    return cleaned


def normalize_project_name(name: Optional[str]) -> Tuple[str, List[str]]:
    """Normalize project name into canonical comparison string and filtered token list.

    Parameters
    ----------
    name : Optional[str]
        Raw project name.

    Returns
    -------
    Tuple[str, List[str]]
        (normalized_string, filtered_tokens)
    """
    if not name:
        return "", []

    cleaned = clean_project_mojibake(name).lower()
    # Replace non-alphanumeric with spaces
    tokens_raw = re.sub(r"[^\w\s]", " ", cleaned).split()
    # Filter out pure noise tokens while preserving sectoral/geographic words
    tokens = [t for t in tokens_raw if len(t) > 1 and t not in PROJECT_NOISE_TOKENS]
    norm_str = " ".join(tokens)
    return norm_str, tokens


def compare_countries(c1: Optional[str], c2: Optional[str]) -> Tuple[str, Optional[bool]]:
    """Compare two country identifiers using canonical jurisdiction mappings.

    Returns
    -------
    Tuple[str, Optional[bool]]
        (relation, match_boolean)
        where relation is 'MATCH', 'CONFLICT', or 'MISSING'.
    """
    if not c1 or not c2 or not str(c1).strip() or not str(c2).strip():
        return "MISSING", None

    clean1 = str(c1).strip().upper()
    clean2 = str(c2).strip().upper()

    canon1 = COUNTRY_CANONICAL_MAP.get(clean1, clean1)
    canon2 = COUNTRY_CANONICAL_MAP.get(clean2, clean2)

    if canon1 == canon2:
        return "MATCH", True
    return "CONFLICT", False


def parse_vintage_span(v: Any) -> Optional[Tuple[int, int]]:
    """Parse integer vintage year or range (e.g. '2016', 2018, '2009 - 2012') into (min_year, max_year)."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None

    # Find all 4-digit years
    years = [int(m) for m in re.findall(r"\b(19\d\d|20\d\d)\b", s)]
    if not years:
        return None
    return min(years), max(years)


def compare_vintages(v1: Any, v2: Any) -> Tuple[str, Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """Compare two project vintage spans.

    Returns
    -------
    Tuple[str, Optional[Tuple[int, int]], Optional[Tuple[int, int]]]
        (relation, span_1, span_2)
        where relation is 'OVERLAP', 'ADJACENT', 'DISJOINT', or 'MISSING'.
    """
    span1 = parse_vintage_span(v1)
    span2 = parse_vintage_span(v2)

    if not span1 or not span2:
        return "MISSING", span1, span2

    min1, max1 = span1
    min2, max2 = span2

    # Check intersection
    if max(min1, min2) <= min(max1, max2):
        return "OVERLAP", span1, span2

    # Check adjacency (within 1 year)
    gap = min1 - max2 if min1 > max2 else min2 - max1
    if gap <= 1:
        return "ADJACENT", span1, span2

    return "DISJOINT", span1, span2


def calculate_project_name_similarity(
    name1: str,
    name2: str,
) -> Tuple[float, float, float, float, List[str], List[str]]:
    """Compute multi-feature string and token similarity between two project names.

    Returns
    -------
    Tuple[float, float, float, float, List[str], List[str]]
        (composite_similarity, token_set_ratio, token_sort_ratio, jaro_winkler, tokens_1, tokens_2)
    """
    norm1, tokens1 = normalize_project_name(name1)
    norm2, tokens2 = normalize_project_name(name2)

    if not norm1 and not norm2:
        return 1.0, 1.0, 1.0, 1.0, [], []
    if not norm1 or not norm2:
        return 0.0, 0.0, 0.0, 0.0, tokens1, tokens2

    # 1. Token set ratio (handles subset / superset title tokens)
    set_ratio = float(fuzz.token_set_ratio(norm1, norm2)) / 100.0

    # 2. Token sort ratio (handles word order variations)
    sort_ratio = float(fuzz.token_sort_ratio(norm1, norm2)) / 100.0

    # 3. Jaro-Winkler distance (handles prefix and spelling variations)
    jw_sim = float(distance.JaroWinkler.similarity(norm1, norm2))

    # Composite weighted similarity:
    # 0.40 * TokenSet + 0.30 * TokenSort + 0.30 * JaroWinkler
    composite = 0.40 * set_ratio + 0.30 * sort_ratio + 0.30 * jw_sim
    composite = max(0.0, min(1.0, composite))

    return composite, set_ratio, sort_ratio, jw_sim, tokens1, tokens2


def compare_project_identifiers(
    id1: Optional[str],
    id2: Optional[str],
    reg1: str,
    reg2: str,
) -> Tuple[bool, Optional[str]]:
    """Compare project identifiers with namespace collision awareness.

    Returns
    -------
    Tuple[bool, Optional[str]]
        (is_match, explanation_note)
    """
    if not id1 or not id2:
        return False, None

    s1 = str(id1).strip().upper()
    s2 = str(id2).strip().upper()

    if s1 != s2:
        return False, None

    is_cross = str(reg1).strip().upper() != str(reg2).strip().upper()
    if is_cross:
        note = (
            f"Alphanumeric project ID '{s1}' matches across registries ('{reg1}' vs '{reg2}'). "
            "WARNING: Registry project ID namespaces are disjoint and allocated independently; "
            "matching numeric tokens alone do not indicate identical real-world projects."
        )
    else:
        note = f"Identical project identifier '{s1}' within registry '{reg1}'."

    return True, note


def compare_projects(
    proj_a: Union[ProjectProfile, Dict[str, Any]],
    proj_b: Union[ProjectProfile, Dict[str, Any]],
) -> CrossRegistryProjectComparison:
    """Compare two carbon offset projects and produce explainable correlation evidence.

    Parameters
    ----------
    proj_a : Union[ProjectProfile, Dict[str, Any]]
        Project profile from Registry A.
    proj_b : Union[ProjectProfile, Dict[str, Any]]
        Project profile from Registry B.

    Returns
    -------
    CrossRegistryProjectComparison
        Structured comparison with transparent categorization and inspectable evidence.
    """
    # Coerce to ProjectProfile
    p_a = proj_a if isinstance(proj_a, ProjectProfile) else ProjectProfile(**proj_a)
    p_b = proj_b if isinstance(proj_b, ProjectProfile) else ProjectProfile(**proj_b)

    is_cross = p_a.registry.strip().upper() != p_b.registry.strip().upper()

    # 1. Name similarity
    name_sim, set_sim, sort_sim, jw_sim, tok_a, tok_b = calculate_project_name_similarity(
        p_a.project_name, p_b.project_name
    )

    # 2. Country comparison
    c_rel, c_match = compare_countries(p_a.country, p_b.country)

    # 3. Vintage comparison
    v_rel, span_a, span_b = compare_vintages(p_a.vintage, p_b.vintage)

    # 4. Identifier comparison
    id_match, id_note = compare_project_identifiers(p_a.project_id, p_b.project_id, p_a.registry, p_b.registry)

    # 5. Optional developer similarity
    dev_sim: Optional[float] = None
    if p_a.developer and p_b.developer:
        try:
            from ..entity_resolution import EntityResolutionEngine
            res_dev = EntityResolutionEngine.resolve_pair(p_a.developer, p_b.developer)
            dev_sim = float(res_dev.overall_score) / 100.0
        except Exception:
            dev_sim = float(fuzz.token_sort_ratio(p_a.developer, p_b.developer)) / 100.0

    # 6. Accumulate evidence signals
    matching_attrs: List[str] = []
    conflicting_attrs: List[str] = []
    missing_attrs: List[str] = []

    if id_match:
        matching_attrs.append(f"Identical Project ID ('{p_a.project_id}')")
        if is_cross and id_note:
            conflicting_attrs.append(id_note)
        elif id_note:
            matching_attrs.append(id_note)
    elif p_a.project_id and p_b.project_id:
        conflicting_attrs.append(f"Different Project IDs ('{p_a.project_id}' vs '{p_b.project_id}')")
    else:
        missing_attrs.append("Project ID missing from one or both projects")

    if name_sim >= 0.85:
        matching_attrs.append(f"High project name similarity ({name_sim:.1%})")
    elif name_sim >= 0.65:
        matching_attrs.append(f"Moderate project name similarity ({name_sim:.1%})")
    else:
        conflicting_attrs.append(f"Low project name similarity ({name_sim:.1%})")

    if c_rel == "MATCH":
        matching_attrs.append(f"Matching country jurisdiction ('{p_a.country}')")
    elif c_rel == "CONFLICT":
        conflicting_attrs.append(f"Conflicting country jurisdiction ('{p_a.country}' vs '{p_b.country}')")
    else:
        missing_attrs.append("Country jurisdiction missing from one or both projects")

    if v_rel == "OVERLAP":
        matching_attrs.append(f"Overlapping vintage spans ({span_a} intersects {span_b})")
    elif v_rel == "ADJACENT":
        matching_attrs.append(f"Adjacent vintage spans ({span_a} and {span_b} within 1 year)")
    elif v_rel == "DISJOINT":
        conflicting_attrs.append(f"Disjoint vintage spans ({span_a} vs {span_b})")
    else:
        missing_attrs.append("Vintage information missing from one or both projects")

    if dev_sim is not None:
        if dev_sim >= 0.80:
            matching_attrs.append(f"Corroborating developer/proponent similarity ({dev_sim:.1%})")
        elif dev_sim < 0.40:
            conflicting_attrs.append(f"Divergent developer/proponent entities ({dev_sim:.1%})")
    else:
        missing_attrs.append("Developer/proponent information missing from one or both projects")

    # 7. Classification Decision Rules
    if c_rel == "CONFLICT" and name_sim >= 0.50:
        # Geographic contradiction takes strict precedence over surface name similarity
        category = ProjectCorrelationCategory.CONFLICTING_ATTRIBUTES
        strength = EvidenceStrength.CONTRADICTORY
        explanation = (
            f"Candidate projects exhibit surface name similarity ({name_sim:.1%}), but project jurisdictions "
            f"directly contradict ('{p_a.country}' vs '{p_b.country}'). Under geographic integrity rules, "
            f"projects registered in distinct national jurisdictions represent distinct physical assets."
        )
    elif v_rel == "DISJOINT" and span_a and span_b and abs(span_a[0] - span_b[0]) >= 5 and name_sim >= 0.65:
        # Widely separated vintage spans contradict project identity
        category = ProjectCorrelationCategory.CONFLICTING_ATTRIBUTES
        strength = EvidenceStrength.CONTRADICTORY
        explanation = (
            f"Candidate projects share name similarity ({name_sim:.1%}), but operational vintage periods "
            f"are widely separated ({span_a} vs {span_b}, >5 year gap)."
        )
    elif id_match and is_cross:
        # Cross-registry identifier collision: identical alphanumeric IDs across uncoordinated, disjoint namespaces
        category = ProjectCorrelationCategory.CROSS_REGISTRY_IDENTIFIER_COLLISION
        strength = EvidenceStrength.MODERATE if (name_sim >= 0.70 and c_rel == "MATCH") else EvidenceStrength.WEAK
        explanation = (
            f"Cross-registry identifier collision: Project identifier ('{p_a.project_id}') is identical across "
            f"registries ('{p_a.registry}' vs '{p_b.registry}'), but these registries maintain independent, "
            "disjoint namespaces. Identical ID strings alone do NOT establish project identity across standards."
        )
    elif id_match and not is_cross and c_rel != "CONFLICT":
        category = ProjectCorrelationCategory.EXACT_IDENTIFIER_MATCH
        strength = EvidenceStrength.STRONG
        explanation = f"Exact project identifier match ('{p_a.project_id}') within registry '{p_a.registry}'."
    elif name_sim >= 0.85 and c_rel == "MATCH" and v_rel in ("OVERLAP", "ADJACENT"):
        category = ProjectCorrelationCategory.STRONG_ATTRIBUTE_CORRELATION
        strength = EvidenceStrength.STRONG
        explanation = (
            f"Strong cross-registry attribute correlation: title similarity {name_sim:.1%}, matching country "
            f"('{p_a.country}'), and compatible vintage spans ({span_a} and {span_b})."
        )
    elif (name_sim >= 0.70 and c_rel == "MATCH") or (name_sim >= 0.85 and c_rel == "MATCH"):
        category = ProjectCorrelationCategory.PARTIAL_ATTRIBUTE_CORRELATION
        strength = EvidenceStrength.MODERATE
        explanation = f"Partial attribute correlation: title similarity {name_sim:.1%} with matching country '{p_a.country}'."
    elif name_sim >= 0.65 and (c_rel == "MATCH" or c_rel == "MISSING") and v_rel == "MISSING" and dev_sim is None:
        category = ProjectCorrelationCategory.NAME_SIMILARITY_ONLY
        strength = EvidenceStrength.WEAK
        explanation = (
            f"Name similarity only ({name_sim:.1%}). Corroborating country, developer, and vintage attributes are missing or inconclusive; "
            "similarity alone cannot support project identity."
        )
    else:
        category = ProjectCorrelationCategory.INSUFFICIENT_EVIDENCE
        strength = EvidenceStrength.INSUFFICIENT
        explanation = (
            f"Insufficient corroborating evidence to support correlation (title similarity {name_sim:.1%}, "
            f"country relation '{c_rel}', vintage relation '{v_rel}')."
        )

    return CrossRegistryProjectComparison(
        project_a=p_a,
        project_b=p_b,
        is_cross_registry=is_cross,
        correlation_category=category.value,
        evidence_strength=strength.value,
        name_similarity_score=name_sim,
        name_tokens_a=tok_a,
        name_tokens_b=tok_b,
        token_set_ratio=set_sim,
        token_sort_ratio=sort_sim,
        jaro_winkler_similarity=jw_sim,
        identifier_match=id_match,
        country_relation=c_rel,
        vintage_relation=v_rel,
        developer_similarity=dev_sim,
        matching_attributes=matching_attrs,
        conflicting_attributes=conflicting_attrs,
        missing_attributes=missing_attrs,
        explanation=explanation,
    )


def correlate_registry_projects(
    vcs_projects: Optional[Sequence[Dict[str, Any]]] = None,
    gs_projects: Optional[Sequence[Dict[str, Any]]] = None,
    min_similarity: float = 0.50,
    category_filter: Optional[str] = None,
    country_filter: Optional[str] = None,
    limit: int = 50,
    con: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> CrossRegistryCorrelationsResponse:
    """Generate and rank candidate project correlations across Verra VCS and Gold Standard.

    Parameters
    ----------
    vcs_projects : Optional[Sequence[Dict[str, Any]]]
        List of VCS project records/profiles. If None, queries from database.
    gs_projects : Optional[Sequence[Dict[str, Any]]]
        List of GS project records/profiles. If None, queries from database.
    min_similarity : float
        Minimum composite name similarity required for candidate generation.
    category_filter : Optional[str]
        Optional filter by correlation category name.
    country_filter : Optional[str]
        Optional filter by country name or code.
    limit : int
        Maximum number of ranked candidates to return.
    con : Optional[sqlite3.Connection]
        Active SQLite connection.
    db_path : Optional[str]
        Path to database if connection not supplied.

    Returns
    -------
    CrossRegistryCorrelationsResponse
        Container with ranked candidate comparisons and evaluation metadata.
    """
    should_close = False
    if vcs_projects is None or gs_projects is None:
        if con is None:
            from .engine import AnalyticsEngine
            con = AnalyticsEngine.get_connection(db_path)
            should_close = True
        try:
            cur = con.cursor()
            cur.execute("""
                SELECT registry, project_id, project_name, country, MIN(vintage) as min_vintage, MAX(vintage) as max_vintage
                FROM records
                WHERE kind = 'retirement'
                GROUP BY registry, project_id, project_name, country
                ORDER BY registry, project_id
            """)
            rows = cur.fetchall()
            v_list: List[Dict[str, Any]] = []
            g_list: List[Dict[str, Any]] = []
            for r in rows:
                p_dict = {
                    "registry": r[0],
                    "project_id": r[1],
                    "project_name": r[2],
                    "country": r[3],
                    "vintage": f"{r[4]} - {r[5]}" if r[4] != r[5] else str(r[4]),
                    "provenance": MetadataProvenance.DATABASE_CENSUS,
                }
                if r[0] == "VCS":
                    v_list.append(p_dict)
                elif r[0] == "GS":
                    g_list.append(p_dict)
            if vcs_projects is None:
                vcs_projects = v_list
            if gs_projects is None:
                gs_projects = g_list
        finally:
            if should_close and con is not None:
                con.close()

    comparisons: List[CrossRegistryProjectComparison] = []
    total_evaluated = 0

    c_filt_canon = (
        COUNTRY_CANONICAL_MAP.get(country_filter.strip().upper(), country_filter.strip().upper())
        if country_filter
        else None
    )

    for vp in vcs_projects:
        vp_country = (
            COUNTRY_CANONICAL_MAP.get(str(vp.get("country") or "").strip().upper())
            if vp.get("country")
            else None
        )
        if c_filt_canon and vp_country != c_filt_canon:
            continue

        for gp in gs_projects:
            gp_country = (
                COUNTRY_CANONICAL_MAP.get(str(gp.get("country") or "").strip().upper())
                if gp.get("country")
                else None
            )
            if c_filt_canon and gp_country != c_filt_canon:
                continue

            total_evaluated += 1
            cmp = compare_projects(vp, gp)

            # Apply similarity threshold
            if cmp.name_similarity_score < min_similarity:
                continue

            # Apply category filter
            if category_filter and cmp.correlation_category != category_filter.strip().upper():
                continue

            comparisons.append(cmp)

    # Rank candidates by name similarity score descending
    comparisons.sort(key=lambda x: x.name_similarity_score, reverse=True)
    truncated = comparisons[:limit]

    return CrossRegistryCorrelationsResponse(
        total_candidates_evaluated=total_evaluated,
        matched_candidates_count=len(truncated),
        min_similarity_threshold=min_similarity,
        category_filter=category_filter,
        country_filter=country_filter,
        correlations=truncated,
    )


def compare_cross_registry_entities(
    entity_a: str,
    entity_b: str,
    registry_a: str = "VCS",
    registry_b: str = "GS",
) -> CrossRegistryEntityComparison:
    """Compare two entity names across registries using the Phase 2A resolution engine.

    Parameters
    ----------
    entity_a : str
        Beneficiary / claimant name from Registry A.
    entity_b : str
        Beneficiary / claimant name from Registry B.
    registry_a : str
        Source registry identifier for entity A.
    registry_b : str
        Source registry identifier for entity B.

    Returns
    -------
    CrossRegistryEntityComparison
        Explainable entity resolution result with legal entity disclaimers.
    """
    from ..entity_resolution import EntityResolutionEngine

    # Resolve pair using Phase 2A
    match_res = EntityResolutionEngine.resolve_pair(entity_a, entity_b)

    norm_a = EntityResolutionEngine.normalize(entity_a).canonical_name
    norm_b = EntityResolutionEngine.normalize(entity_b).canonical_name

    return CrossRegistryEntityComparison(
        registry_a=registry_a.strip().upper(),
        entity_raw_a=entity_a,
        entity_normalized_a=norm_a,
        registry_b=registry_b.strip().upper(),
        entity_raw_b=entity_b,
        entity_normalized_b=norm_b,
        is_match=match_res.is_match,
        relationship_type=match_res.relationship_type.value if hasattr(match_res.relationship_type, "value") else str(match_res.relationship_type),
        match_tier=match_res.match_tier.value if hasattr(match_res.match_tier, "value") else str(match_res.match_tier),
        overall_score=match_res.overall_score,
        positive_signals=match_res.positive_signals,
        contradictory_signals=match_res.contradictory_signals,
        missing_information=match_res.missing_information,
        explanation=match_res.explanation,
    )


def get_cross_registry_retirement_summary(
    con: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> CrossRegistryRetirementSummary:
    """Compute comparative retirement statistics across Verra VCS and Gold Standard.

    Parameters
    ----------
    con : Optional[sqlite3.Connection]
        Active SQLite connection.
    db_path : Optional[str]
        Path to database if connection not supplied.

    Returns
    -------
    CrossRegistryRetirementSummary
        Side-by-side comparative registry metrics.
    """
    should_close = False
    if con is None:
        from .engine import AnalyticsEngine
        con = AnalyticsEngine.get_connection(db_path)
        should_close = True

    try:
        cur = con.cursor()

        # 1. Retirement aggregation query (issuance records strictly excluded)
        cur.execute("""
            SELECT registry,
                   COUNT(*) as total_records,
                   SUM(quantity) as total_tonnes,
                   COUNT(DISTINCT project_id) as project_count,
                   MIN(event_date) as min_date,
                   MAX(event_date) as max_date,
                   SUM(CASE WHEN beneficiary IS NOT NULL AND TRIM(beneficiary) != '' 
                            AND LOWER(TRIM(beneficiary)) NOT IN ('not disclosed', 'undisclosed', 'unknown', 'none', 'n/a', 'null') 
                            THEN 1 ELSE 0 END) as disclosed_records,
                   SUM(CASE WHEN beneficiary IS NOT NULL AND TRIM(beneficiary) != '' 
                            AND LOWER(TRIM(beneficiary)) NOT IN ('not disclosed', 'undisclosed', 'unknown', 'none', 'n/a', 'null') 
                            THEN quantity ELSE 0.0 END) as disclosed_tonnes
            FROM records
            WHERE kind = 'retirement'
            GROUP BY registry
        """)
        rows = cur.fetchall()

        # 2. Count issuance records excluded
        cur.execute("""
            SELECT registry, COUNT(*) 
            FROM records 
            WHERE kind = 'issuance'
            GROUP BY registry
        """)
        issuance_map = dict(cur.fetchall())

        reg_stats: Dict[str, RegistryRetirementStats] = {}
        combined_records = 0
        combined_tonnes = 0.0
        total_issuance_excluded = sum(issuance_map.values())

        # Documented source field availability
        vcs_fields = [
            "batch_id", "country", "event_date", "project_id", "project_name",
            "quantity", "serial", "unit_start", "unit_end", "vintage", "beneficiary",
        ]
        vcs_sparse = ["reason"]  # >99% NULL in VCS

        gs_fields = [
            "batch_id", "country", "event_date", "project_id", "project_name",
            "quantity", "serial", "unit_start", "unit_end", "vintage", "beneficiary", "reason",
        ]
        gs_sparse: List[str] = []

        for row in rows:
            reg = str(row[0])
            rec_cnt = int(row[1])
            ton_vol = float(row[2])
            proj_cnt = int(row[3])
            min_d = str(row[4]) if row[4] else None
            max_d = str(row[5]) if row[5] else None
            disc_cnt = int(row[6])
            disc_vol = float(row[7])

            rec_disc_rate = (float(disc_cnt) / float(rec_cnt) * 100.0) if rec_cnt > 0 else 0.0
            vol_disc_rate = (float(disc_vol) / float(ton_vol) * 100.0) if ton_vol > 0 else 0.0
            iss_excl = issuance_map.get(reg, 0)

            stats = RegistryRetirementStats(
                registry=reg,
                total_retirement_records=rec_cnt,
                total_retired_tonnes=ton_vol,
                active_projects_count=proj_cnt,
                earliest_retirement_date=min_d,
                latest_retirement_date=max_d,
                disclosed_records_count=disc_cnt,
                record_disclosure_rate_pct=rec_disc_rate,
                beneficiary_record_disclosure_rate_pct=rec_disc_rate,
                disclosed_tonnes_quantity=disc_vol,
                quantity_disclosure_rate_pct=vol_disc_rate,
                beneficiary_quantity_disclosure_rate_pct=vol_disc_rate,
                issuance_records_excluded=iss_excl,
                available_source_fields=vcs_fields if reg == "VCS" else gs_fields,
                unpopulated_or_sparse_fields=vcs_sparse if reg == "VCS" else gs_sparse,
            )
            reg_stats[reg] = stats
            combined_records += rec_cnt
            combined_tonnes += ton_vol

        notes = [
            f"VCS accounts for {reg_stats.get('VCS', {}).total_retired_tonnes / combined_tonnes * 100.0:.1f}% of volume "
            f"and {reg_stats.get('VCS', {}).total_retirement_records / combined_records * 100.0:.1f}% of retirement records in this dataset.",
            f"Gold Standard displays {reg_stats.get('GS', {}).beneficiary_quantity_disclosure_rate_pct:.1f}% beneficiary identity disclosure rate by volume "
            f"(vs {reg_stats.get('VCS', {}).beneficiary_quantity_disclosure_rate_pct:.1f}% in VCS) due to explicit 'Not Disclosed' placeholder usage. "
            "All transaction quantities, project IDs, serials, and dates remain 100% disclosed across both registries.",
            f"A total of {total_issuance_excluded} issuance records are strictly excluded from retirement analytics denominators.",
        ]

        return CrossRegistryRetirementSummary(
            registries=reg_stats,
            combined_retirement_records=combined_records,
            combined_retired_tonnes=combined_tonnes,
            total_issuance_records_excluded=total_issuance_excluded,
            comparability_notes=notes,
        )

    finally:
        if should_close:
            con.close()


def get_cross_registry_retirement_trends(
    period_type: str = "yearly",
    con: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> CrossRegistryTrendsResponse:
    """Compute aligned time series comparing retirement volume and record frequency between registries.

    Parameters
    ----------
    period_type : str
        'yearly' or 'monthly'.
    con : Optional[sqlite3.Connection]
        Active SQLite connection.
    db_path : Optional[str]
        Path to database if connection not supplied.

    Returns
    -------
    CrossRegistryTrendsResponse
        Side-by-side comparative time series.
    """
    p_type = period_type.strip().lower()
    if p_type not in ("yearly", "monthly"):
        raise ValueError(f"Unsupported period_type: '{period_type}'. Must be 'yearly' or 'monthly'.")

    should_close = False
    if con is None:
        from .engine import AnalyticsEngine
        con = AnalyticsEngine.get_connection(db_path)
        should_close = True

    try:
        cur = con.cursor()

        date_fmt = "%Y-%m" if p_type == "monthly" else "%Y"

        cur.execute(f"""
            SELECT strftime('{date_fmt}', event_date) as period_lbl,
                   registry,
                   COUNT(*) as record_cnt,
                   SUM(quantity) as total_tonnes,
                   MIN(event_date) as p_start,
                   MAX(event_date) as p_end
            FROM records
            WHERE kind = 'retirement' AND event_date IS NOT NULL
            GROUP BY period_lbl, registry
            ORDER BY period_lbl ASC
        """)
        rows = cur.fetchall()

        period_map: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "vcs_records": 0,
                "vcs_tonnes": 0.0,
                "gs_records": 0,
                "gs_tonnes": 0.0,
                "p_start": None,
                "p_end": None,
            }
        )

        for row in rows:
            lbl = str(row[0])
            reg = str(row[1])
            cnt = int(row[2])
            ton = float(row[3])
            start_d = str(row[4])
            end_d = str(row[5])

            p_entry = period_map[lbl]
            if reg == "VCS":
                p_entry["vcs_records"] += cnt
                p_entry["vcs_tonnes"] += ton
            elif reg == "GS":
                p_entry["gs_records"] += cnt
                p_entry["gs_tonnes"] += ton

            if p_entry["p_start"] is None or start_d < p_entry["p_start"]:
                p_entry["p_start"] = start_d
            if p_entry["p_end"] is None or end_d > p_entry["p_end"]:
                p_entry["p_end"] = end_d

        trends: List[CrossRegistryTrendsPeriod] = []
        for lbl in sorted(period_map.keys()):
            e = period_map[lbl]
            trends.append(
                CrossRegistryTrendsPeriod(
                    period_start=e["p_start"] or f"{lbl}-01-01",
                    period_end=e["p_end"] or f"{lbl}-12-31",
                    period_label=lbl,
                    vcs_record_count=e["vcs_records"],
                    vcs_total_tonnes=e["vcs_tonnes"],
                    gs_record_count=e["gs_records"],
                    gs_total_tonnes=e["gs_tonnes"],
                    combined_record_count=e["vcs_records"] + e["gs_records"],
                    combined_total_tonnes=e["vcs_tonnes"] + e["gs_tonnes"],
                )
            )

        return CrossRegistryTrendsResponse(
            period_type=p_type,
            total_periods=len(trends),
            trends=trends,
        )

    finally:
        if should_close:
            con.close()


# ==============================================================================
# BACKWARD COMPATIBILITY HELPERS (PRESERVING EXISTING INTERFACES)
# ==============================================================================

def normalize_tokens(text: Optional[str]) -> List[str]:
    """Normalize text into alphanumeric lowercase tokens, stripping punctuation."""
    _, tokens = normalize_project_name(text)
    return tokens


def token_sort_similarity(s1: str, s2: str) -> float:
    """Calculate token sort ratio between two strings."""
    norm1, _ = normalize_project_name(s1)
    norm2, _ = normalize_project_name(s2)
    return float(fuzz.token_sort_ratio(norm1, norm2)) / 100.0


def token_set_similarity(s1: str, s2: str) -> float:
    """Calculate token set ratio between two strings."""
    norm1, _ = normalize_project_name(s1)
    norm2, _ = normalize_project_name(s2)
    return float(fuzz.token_set_ratio(norm1, norm2)) / 100.0


def check_country_match(c1: Optional[str], c2: Optional[str]) -> bool:
    """Check whether two country identifiers match."""
    _, m = compare_countries(c1, c2)
    return bool(m)


def check_vintage_overlap(v1: Optional[int], v2: Optional[int]) -> bool:
    """Check if vintage years align within a 1-year operational window."""
    rel, _, _ = compare_vintages(v1, v2)
    return rel in ("OVERLAP", "ADJACENT", "MISSING")


def calculate_developer_similarity(dev1: Optional[str], dev2: Optional[str]) -> float:
    """Compute similarity between project proponents / developers."""
    if not dev1 and not dev2:
        return 0.5
    if not dev1 or not dev2:
        return 0.2
    try:
        from ..entity_resolution import EntityResolutionEngine
        res = EntityResolutionEngine.resolve_pair(dev1, dev2)
        return float(res.overall_score) / 100.0
    except Exception:
        return token_sort_similarity(dev1, dev2)


def evaluate_cross_registry_pair(
    proj_a: Dict[str, Any],
    proj_b: Dict[str, Any],
    threshold: float = 0.80,
) -> Optional[CrossRegistryMatch]:
    """Legacy helper wrapping evaluate_cross_registry_pair."""
    cmp = compare_projects(proj_a, proj_b)
    if cmp.name_similarity_score < threshold and cmp.correlation_category != ProjectCorrelationCategory.EXACT_IDENTIFIER_MATCH.value:
        return None

    is_cross = cmp.is_cross_registry
    risk_flag = is_cross and (cmp.correlation_category == ProjectCorrelationCategory.STRONG_ATTRIBUTE_CORRELATION.value)

    return CrossRegistryMatch(
        registry_a=cmp.project_a.registry,
        project_id_a=cmp.project_a.project_id or "UNKNOWN",
        project_name_a=cmp.project_a.project_name,
        developer_a=cmp.project_a.developer,
        country_a=cmp.project_a.country,
        registry_b=cmp.project_b.registry,
        project_id_b=cmp.project_b.project_id or "UNKNOWN",
        project_name_b=cmp.project_b.project_name,
        developer_b=cmp.project_b.developer,
        country_b=cmp.project_b.country,
        project_name_similarity=cmp.name_similarity_score,
        country_match=cmp.country_relation == "MATCH",
        developer_similarity=cmp.developer_similarity or 0.5,
        vintage_overlap=cmp.vintage_relation in ("OVERLAP", "ADJACENT", "MISSING"),
        composite_confidence=cmp.name_similarity_score,
        potential_duplicate_risk=risk_flag,
        explanation=cmp.explanation,
    )


def find_cross_registry_matches(
    target: Dict[str, Any],
    candidates: Sequence[Dict[str, Any]],
    threshold: float = 0.80,
) -> List[CrossRegistryMatch]:
    """Legacy helper for finding cross-registry matches."""
    matches: List[CrossRegistryMatch] = []
    target_reg = str(target.get("registry") or "").upper()

    for cand in candidates:
        cand_reg = str(cand.get("registry") or "").upper()
        if target_reg and cand_reg and target_reg == cand_reg:
            continue
        match = evaluate_cross_registry_pair(target, cand, threshold=threshold)
        if match:
            matches.append(match)

    matches.sort(key=lambda x: x.composite_confidence, reverse=True)
    return matches

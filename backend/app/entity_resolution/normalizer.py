"""Canonical entity normalization and legal suffix classification for OnceOnly."""
from __future__ import annotations

import re
import unicodedata

from app.normalization import (
    _PLACEHOLDER_BENEFICIARIES,
    normalize_dashes,
    normalize_whitespace,
    repair_mojibake,
)

from .models import EntityName

# Ordered from multi-word specific phrases to single-word abbreviations
_LEGAL_SUFFIX_MAP: list[tuple[str, str]] = [
    # Multi-word English / Commonwealth
    (r"\bpublic\s+limited\s+company\b", "plc"),
    (r"\bpte\.?\s+ltd\.?\b", "pvt ltd"),
    (r"\bproprietary\s+limited\b", "pvt ltd"),
    (r"\bpvt\.?\s+ltd\.?\b", "pvt ltd"),
    (r"\bprivate\s+limited\b", "pvt ltd"),
    (r"\bpty\.?\s+ltd\.?\b", "pvt ltd"),
    (r"\bl\.?l\.?c\.?\b", "llc"),
    (r"\blimited\s+liability\s+company\b", "llc"),
    # German / Austrian / Swiss
    (r"\bgmbh\s*&\s*co\.?\s*kga?a?\b", "gmbh & co kg"),
    (r"\bgesellschaft\s+mit\s+beschr[aä]nkter\s+haftung\b", "gmbh"),
    (r"\bg\.?m\.?b\.?h\.?\b", "gmbh"),
    (r"\baktiengesellschaft\b", "ag"),
    (r"\ba\.?g\.?\b", "ag"),
    (r"\bkgaa\b", "kgaa"),
    # Romance / Latin American / Italian
    (r"\bsoci[eé]t[eé]\s+anonyme\b", "sa"),
    (r"\bsociedad\s+an[oó]nima\b", "sa"),
    (r"\bs\.?a\.?\s*s\.?\b", "sas"),
    (r"\bs\.?a\.?r\.?l\.?\b", "sarl"),
    (r"\bsociet[aà]\s+benefit\b", "societa benefit"),
    (r"\bsociet[aà]\s+per\s+azioni\b", "spa"),
    (r"\bs\.?p\.?a\.?\b", "spa"),
    (r"\bs\.?r\.?l\.?\b", "srl"),
    (r"\bs\.?a\.?\b", "sa"),
    (r"\bs\.?l\.?\b", "sl"),
    (r"\bltda\.?\b", "ltda"),
    (r"\blimitada\b", "ltda"),
    # Pan-European SE
    (r"\bsocietas\s+europaea\b", "se"),
    (r"\bs\.?e\.?\b", "se"),
    # Dutch
    (r"\bbesloten\s+vennootschap\b", "bv"),
    (r"\bb\.?v\.?\b", "bv"),
    (r"\bn\.?v\.?\b", "nv"),
    # Nordic
    (r"\baktiebolag\b", "ab"),
    (r"\ba\.?b\.?\b", "ab"),
    (r"\ba\/?s\b", "as"),
    (r"\boyj?\b", "oy"),
    # Asian / Southeast Asian
    (r"\bsdn\.?\s+bhd\.?\b", "sdn bhd"),
    (r"\bpt\.?\b", "pt"),
    (r"\btbk\.?\b", "tbk"),
    (r"\bkabushiki\s+kaisha\b", "kk"),
    (r"\bk\.?k\.?\b", "kk"),
    # Standard single-word English
    (r"\blimited\b", "ltd"),
    (r"\bltd\.?\b", "ltd"),
    (r"\bincorporated\b", "inc"),
    (r"\binc\.?\b", "inc"),
    (r"\bcorporation\b", "corp"),
    (r"\bcorp\.?\b", "corp"),
    (r"\bcompany\b", "co"),
    (r"\bco\.?\b", "co"),
    (r"\bplc\.?\b", "plc"),
]

# Corporate word expansions for semantic token alignment
_ABBREVIATION_EXPANSIONS: dict[str, str] = {
    "intl": "international",
    "intnl": "international",
    "mfg": "manufacturing",
    "tech": "technology",
    "technol": "technology",
    "technologies": "technology",
    "svcs": "services",
    "serv": "services",
    "grp": "group",
    "mgmt": "management",
    "solns": "solutions",
    "soln": "solutions",
    "assoc": "association",
    "fdn": "foundation",
    "dev": "development",
    "syst": "systems",
    "sys": "systems",
    "natl": "national",
    "chem": "chemicals",
    "ind": "industries",
    "corp": "corporation",
    "co": "company",
}

# Recognized corporate qualifiers indicating divisional, regional, or organizational structure
_CORPORATE_QUALIFIERS: set[str] = {
    "group",
    "holdings",
    "international",
    "global",
    "capital",
    "ventures",
    "trading",
    "energy",
    "solutions",
    "technology",
    "services",
    "logistics",
    "operations",
    "digital",
    "mobility",
    "resources",
    "industries",
    "investments",
    "management",
    "renewables",
    "retail",
    "green",
    "power",
    "web",
    "north",
    "south",
    "america",
    "usa",
    "europe",
    "asia",
    "uk",
}

# Generic English and business stop words excluded from distinctive blocking tokens
_ENTITY_STOP_WORDS: set[str] = {
    "the", "of", "and", "&", "for", "in", "on", "at", "to", "a", "an", "de", "del", "la", "le", "les", "et", "und", "der", "die", "das"
}


class EntityNormalizer:
    """Deterministic, explainable legal entity normalizer."""

    @classmethod
    def normalize(cls, raw: str | None) -> EntityName:
        """Parse raw entity name into canonical structured EntityName with provenance."""
        if raw is None or not raw.strip():
            return EntityName(
                raw_value=raw,
                normalized_value=None,
                canonical_name="",
                tokens=(),
                legal_suffix=None,
                raw_legal_suffix=None,
                corporate_qualifiers=(),
                is_placeholder=True,
                placeholder_type="empty",
                operations=(),
            )

        ops: list[str] = []
        current = raw

        # 1. Mojibake repair
        repaired, modified = repair_mojibake(current)
        if modified:
            ops.append("mojibake_repair")
            current = repaired

        # 2. Unicode NFC precomposition
        nfc = unicodedata.normalize("NFC", current)
        if nfc != current:
            ops.append("unicode_nfc")
            current = nfc

        # 3. Unicode dashes to ASCII hyphen
        dashed = normalize_dashes(current)
        if dashed != current:
            ops.append("dash_normalization")
            current = dashed

        # 4. Whitespace cleanup
        cleaned_ws = normalize_whitespace(current)
        if cleaned_ws != current:
            ops.append("whitespace_normalization")
            current = cleaned_ws

        # 5. Placeholder detection
        clean_alpha = re.sub(r"[^a-z0-9]+", "", current.lower()).strip()
        clean_spaced = re.sub(r"[^a-z0-9]+", " ", current.lower()).strip()
        if clean_alpha in _PLACEHOLDER_BENEFICIARIES or clean_spaced in _PLACEHOLDER_BENEFICIARIES:
            return EntityName(
                raw_value=raw,
                normalized_value=current,
                canonical_name="",
                tokens=(),
                legal_suffix=None,
                raw_legal_suffix=None,
                corporate_qualifiers=(),
                is_placeholder=True,
                placeholder_type="undisclosed" if "disclose" in clean_spaced else clean_alpha or "placeholder",
                operations=tuple(ops + ["placeholder_classified"]),
            )

        # 6. Legal suffix extraction
        # We search from the end of the string
        working = current.strip()
        found_suffix: str | None = None
        raw_suffix: str | None = None

        # Check for Italian prefix/infix Societa Benefit e.g. "Societa Benefit Enel S.p.A."
        sb_match = re.search(r"\bsociet[aà]\s+benefit\b", working, flags=re.IGNORECASE)
        if sb_match:
            found_suffix = "societa benefit"
            raw_suffix = sb_match.group(0)
            working = re.sub(r"\bsociet[aà]\s+benefit\b", " ", working, flags=re.IGNORECASE).strip(" ,.-()")
            ops.append("legal_form_detected:societa benefit")

        # Check suffixes against the end of the text
        for pattern, canonical_suffix in _LEGAL_SUFFIX_MAP:
            # Anchor pattern to end of string (allowing trailing dots/spaces/parentheses)
            full_pattern = rf"(?:[\s,\.-]+){pattern}[\.\s\)]*$"
            match = re.search(full_pattern, working, flags=re.IGNORECASE)
            if match:
                found_suffix = canonical_suffix
                raw_suffix = match.group(0).strip(" ,.-()")
                # Remove suffix from the working root string
                working = working[:match.start()].strip(" ,.-()")
                ops.append(f"legal_suffix_extracted:{canonical_suffix}")
                break

        # 7. Strip synthetic markers if present (e.g. "(SYNTHETIC)")
        if "(synthetic)" in working.lower():
            working = re.sub(r"\(synthetic\)", "", working, flags=re.IGNORECASE).strip(" ,.-()")
            ops.append("synthetic_tag_stripped")

        # 8. Tokenization & Canonical Name Creation
        # Flatten diacritics for canonical tokens while preserving raw values
        unaccented = "".join(
            c for c in unicodedata.normalize("NFKD", working.lower())
            if unicodedata.category(c) != "Mn"
        )
        token_str = re.sub(r"[^\w\s]", " ", unaccented)
        raw_tokens = [t for t in token_str.split() if t]

        # Expand corporate abbreviations and identify qualifiers
        expanded_tokens: list[str] = []
        qualifiers: list[str] = []
        for t in raw_tokens:
            expanded = _ABBREVIATION_EXPANSIONS.get(t, t)
            if expanded != t:
                ops.append(f"abbreviation_expanded:{t}->{expanded}")
            expanded_tokens.append(expanded)
            if expanded in _CORPORATE_QUALIFIERS:
                qualifiers.append(expanded)

        # Canonical name is the space-separated expanded tokens
        canonical_name = " ".join(expanded_tokens)

        # Distinctive tokens (excluding generic stopwords and standalone qualifiers if others exist)
        distinctive = [t for t in expanded_tokens if t not in _ENTITY_STOP_WORDS]
        if not distinctive:
            distinctive = expanded_tokens

        return EntityName(
            raw_value=raw,
            normalized_value=current,
            canonical_name=canonical_name,
            tokens=tuple(distinctive),
            legal_suffix=found_suffix,
            raw_legal_suffix=raw_suffix,
            corporate_qualifiers=tuple(qualifiers),
            is_placeholder=False,
            placeholder_type=None,
            operations=tuple(ops),
        )

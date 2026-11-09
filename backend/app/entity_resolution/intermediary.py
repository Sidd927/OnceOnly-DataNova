"""Intermediary and allocation relationship extraction for carbon markets."""
from __future__ import annotations

import re

from .models import EntityName, IntermediaryRelationship, IntermediaryRole
from .normalizer import EntityNormalizer

# Common customer pool / aggregate retirement markers
_CUSTOMER_POOL_KEYWORDS = (
    "customer", "customers", "client", "clients", "end user", "end users",
    "passenger", "passengers", "members", "partners & customers",
)

# Trailing operational / emissions purpose clauses to strip from extracted company names
_TRAILING_PURPOSE_REGEX = re.compile(
    r"\s+(?:for\s+(?:aviation|scope|ground|corporate|fuel|travel|20\d\d|fy\d\d|emissions|the\s+lng|our)|"
    r"-\s*20\d\d|"
    r"emissions\s+period|"
    r"consumption\s+for).*",
    re.IGNORECASE,
)


class IntermediaryExtractor:
    """Extracts principal beneficial owners and intermediaries from carbon retirement records and certificates."""

    @classmethod
    def extract(cls, text: str | None) -> IntermediaryRelationship:
        """Parse text for intermediary / delegation patterns and extract entities."""
        if not text or not text.strip():
            return IntermediaryRelationship(
                is_delegated=False,
                principal_raw=None,
                principal_entity=None,
                intermediary_raw=None,
                intermediary_entity=None,
                role=IntermediaryRole.DIRECT.value,
                pattern_matched=None,
                raw_text=text or "",
                confidence=0.0,
                notes=("empty_input",),
            )

        cleaned = text.strip()
        notes: list[str] = []

        # 1. Customer pool / aggregate platform patterns
        # e.g. "On behalf of Patch's customers and their end users"
        # e.g. "ClimeCo Green Customers", "Trip.com customers", "market.southpole clients"
        pool_match = re.search(
            r"(?:on\s+behalf\s+of\s+)?([A-Za-z0-9\.\s\-]+?)(?:'s|s)?\s+(customers|clients|end\s+users|green\s+customers)",
            cleaned,
            re.IGNORECASE,
        )
        if pool_match and any(kw in cleaned.lower() for kw in _CUSTOMER_POOL_KEYWORDS):
            intermediary_str = pool_match.group(1).strip(" -:,")
            # If intermediary is not just "our" or "the"
            if intermediary_str.lower() not in ("our", "the", "residential and commercial", ""):
                int_entity = EntityNormalizer.normalize(intermediary_str)
                notes.append("customer_pool_allocation")
                return IntermediaryRelationship(
                    is_delegated=True,
                    principal_raw=pool_match.group(0).strip(),
                    principal_entity=None,  # Pooled end-users cannot be resolved to a single legal entity
                    intermediary_raw=intermediary_str,
                    intermediary_entity=int_entity,
                    role=IntermediaryRole.CUSTOMER_POOL.value,
                    pattern_matched="customer_pool",
                    raw_text=cleaned,
                    confidence=0.90,
                    notes=tuple(notes),
                )

        # 2. Intermediary + "on behalf of" / "on behalt of" / "o.b.o." + Principal
        # e.g. "TBK Group on behalf of Lenovo"
        # e.g. "GP-31 - On behalf of Telefonica Brazil - 2021 emissions"
        # e.g. "Broker XYZ o.b.o. Acme Industries Ltd"
        obo_with_lead = re.match(
            r"^(.*?)\s+(?:-|–|—)?\s*(?:on\s+behal[ft]\s+of|o\.?b\.?o\.?)\s*:?\s*(.+)$",
            cleaned,
            re.IGNORECASE,
        )
        if obo_with_lead:
            lead = obo_with_lead.group(1).strip(" -:–—")
            rest = obo_with_lead.group(2).strip()

            # Clean trailing purpose/scope from principal
            principal_candidate = _TRAILING_PURPOSE_REGEX.sub("", rest).strip(" -:,.;")

            # Check if lead is just "retired" or "cancelled" or empty
            if lead.lower() in ("retired", "cancelled", "retirement", "credits retired", ""):
                # "Retired on behalf of: Acme Corp" -> lead is not an intermediary, it's an action verb
                principal_entity = EntityNormalizer.normalize(principal_candidate)
                notes.append("direct_beneficiary_disclosure")
                return IntermediaryRelationship(
                    is_delegated=False,
                    principal_raw=principal_candidate,
                    principal_entity=principal_entity,
                    intermediary_raw=None,
                    intermediary_entity=None,
                    role=IntermediaryRole.DIRECT.value,
                    pattern_matched="retired_on_behalf_of_principal",
                    raw_text=cleaned,
                    confidence=0.95,
                    notes=tuple(notes),
                )
            else:
                # Both intermediary and principal are named!
                intermediary_entity = EntityNormalizer.normalize(lead)
                principal_entity = EntityNormalizer.normalize(principal_candidate)
                notes.append("bilateral_intermediary_delegation")
                return IntermediaryRelationship(
                    is_delegated=True,
                    principal_raw=principal_candidate,
                    principal_entity=principal_entity,
                    intermediary_raw=lead,
                    intermediary_entity=intermediary_entity,
                    role=IntermediaryRole.BROKER_OR_TRADER.value,
                    pattern_matched="lead_on_behalf_of_principal",
                    raw_text=cleaned,
                    confidence=0.95,
                    notes=tuple(notes),
                )

        # 3. "For the account of" / "For account of"
        # e.g. "Trading Corp for account of Siemens AG"
        for_acct = re.match(
            r"^(.*?)\s+(?:for\s+(?:the\s+)?account\s+of)\s*:?\s*(.+)$",
            cleaned,
            re.IGNORECASE,
        )
        if for_acct:
            lead = for_acct.group(1).strip(" -:–—")
            rest = _TRAILING_PURPOSE_REGEX.sub("", for_acct.group(2)).strip(" -:,.;")
            int_entity = EntityNormalizer.normalize(lead) if lead else None
            pr_entity = EntityNormalizer.normalize(rest) if rest else None
            notes.append("for_account_of_delegation")
            return IntermediaryRelationship(
                is_delegated=True,
                principal_raw=rest,
                principal_entity=pr_entity,
                intermediary_raw=lead or None,
                intermediary_entity=int_entity,
                role=IntermediaryRole.BROKER_OR_TRADER.value,
                pattern_matched="for_account_of",
                raw_text=cleaned,
                confidence=0.92,
                notes=tuple(notes),
            )

        # 4. "Client: <Principal>" or "Offtaker: <Principal>" or "Beneficiary: <Principal>"
        # e.g. "Patch - Client: Shopify Inc."
        client_tag = re.search(
            r"(?:^(.*?)(?:-|–|—|\()\s*)?(?:client|offtaker|beneficiary|represented\s+by)\s*:?\s*(.+?)(?:\)|$)",
            cleaned,
            re.IGNORECASE,
        )
        if client_tag:
            lead = client_tag.group(1)
            lead_str = lead.strip(" -:–—()") if lead else None
            rest = _TRAILING_PURPOSE_REGEX.sub("", client_tag.group(2)).strip(" -:,.;()")
            if rest:
                int_entity = EntityNormalizer.normalize(lead_str) if lead_str else None
                pr_entity = EntityNormalizer.normalize(rest)
                notes.append("structured_client_tag")
                return IntermediaryRelationship(
                    is_delegated=bool(lead_str),
                    principal_raw=rest,
                    principal_entity=pr_entity,
                    intermediary_raw=lead_str,
                    intermediary_entity=int_entity,
                    role=IntermediaryRole.BROKER_OR_TRADER.value if lead_str else IntermediaryRole.DIRECT.value,
                    pattern_matched="client_or_offtaker_tag",
                    raw_text=cleaned,
                    confidence=0.90,
                    notes=tuple(notes),
                )

        # 5. "c/o" (in care of)
        # e.g. "Acme Corp c/o Carbon Desk LLC"
        co_match = re.match(r"^(.+?)\s+c\/o\s+(.+)$", cleaned, re.IGNORECASE)
        if co_match:
            pr_str = co_match.group(1).strip(" -:,.;")
            int_str = co_match.group(2).strip(" -:,.;")
            pr_entity = EntityNormalizer.normalize(pr_str)
            int_entity = EntityNormalizer.normalize(int_str)
            notes.append("care_of_relationship")
            return IntermediaryRelationship(
                is_delegated=True,
                principal_raw=pr_str,
                principal_entity=pr_entity,
                intermediary_raw=int_str,
                intermediary_entity=int_entity,
                role=IntermediaryRole.BROKER_OR_TRADER.value,
                pattern_matched="in_care_of",
                raw_text=cleaned,
                confidence=0.88,
                notes=tuple(notes),
            )

        # Fallback: Direct entity (no intermediary delegation detected)
        direct_entity = EntityNormalizer.normalize(cleaned)
        return IntermediaryRelationship(
            is_delegated=False,
            principal_raw=cleaned,
            principal_entity=direct_entity,
            intermediary_raw=None,
            intermediary_entity=None,
            role=IntermediaryRole.DIRECT.value,
            pattern_matched="direct_name",
            raw_text=cleaned,
            confidence=0.80,
            notes=("direct_unstructured",),
        )


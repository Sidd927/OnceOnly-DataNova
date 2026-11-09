"""Shannon entropy, Herfindahl-Hirschman Index (HHI), and dual-track beneficiary concentration analytics."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Union

from .models import (
    BeneficiaryCategory,
    ConcentrationMetrics,
    ConcentrationTier,
    DualTrackCoverage,
)

# Standardized set of non-disclosure tokens (case-insensitive)
UNDISCLOSED_BENEFICIARIES = frozenset({
    "", "none", "null", "not disclosed", "undisclosed", "unknown", "n/a", "na", "unspecified"
})

# Validated placeholder patterns from reference dataset census
EXACT_PLACEHOLDERS = frozenset({"_"})


def classify_beneficiary(val: Optional[str]) -> BeneficiaryCategory:
    """Classify a beneficiary value into one of the four approved analytical categories.

    Categories:
    - EXPLICITLY_UNDISCLOSED: Missing, blank, or explicit non-disclosure markers.
      Policy note: This classification does not independently establish the reason
      for non-disclosure or a legal or contractual privacy entitlement.
    - INVALID_OR_PLACEHOLDER: Recognized syntactic test tokens or form bypass artifacts ('_', 'Test').
    - NON_PLACEHOLDER_DISCLOSED: Populated string passing syntactic placeholder checks.
      Policy note: Does not establish verified legal entity identity or corporate ownership.
    """
    if val is None:
        return BeneficiaryCategory.EXPLICITLY_UNDISCLOSED
    s = str(val).strip()
    s_lower = s.lower()
    if s_lower in UNDISCLOSED_BENEFICIARIES:
        return BeneficiaryCategory.EXPLICITLY_UNDISCLOSED
    if s in EXACT_PLACEHOLDERS or s_lower == "test" or s_lower == "test _ num. ord cliente":
        return BeneficiaryCategory.INVALID_OR_PLACEHOLDER
    return BeneficiaryCategory.NON_PLACEHOLDER_DISCLOSED


def calculate_shannon_entropy(shares: Sequence[float]) -> float:
    """Calculate base-2 Shannon entropy for a probability distribution.

    H(X) = - sum(p_i * log2(p_i))
    Boundary convention: 0 * log2(0) = 0.
    """
    entropy = 0.0
    for p in shares:
        if p > 0.0:
            entropy -= p * math.log2(p)
    return max(0.0, entropy)


def calculate_hhi(shares: Sequence[float]) -> float:
    """Calculate the Herfindahl-Hirschman Index from shares summing to 1.0.

    HHI = sum((100 * p_i)^2) = 10,000 * sum(p_i^2)
    Ranges from 10,000 / K (uniform distribution) to 10,000 (monopoly).
    """
    if not shares:
        return 0.0
    return max(0.0, min(10000.0, sum((100.0 * p) ** 2 for p in shares)))


def evaluate_dual_track_coverage(
    records: Sequence[Dict[str, Any]],
    total_units_override: Optional[float] = None,
) -> DualTrackCoverage:
    """Compute comprehensive dual-track population disclosure metrics.

    Exposes both record-count coverage and quantity-weighted coverage,
    strictly distinguishing disclosed claimants from missing/unresolved records.
    """
    total_records = len(records)
    disclosed_records = 0
    undisclosed_records = 0
    placeholder_records = 0

    disclosed_quantity = 0.0
    undisclosed_quantity = 0.0
    placeholder_quantity = 0.0
    observed_quantity = 0.0

    for rec in records:
        if "quantity" in rec and rec["quantity"] is not None:
            q = float(rec["quantity"])
        elif "unit_start" in rec and "unit_end" in rec and rec["unit_start"] is not None and rec["unit_end"] is not None:
            q = float(int(rec["unit_end"]) - int(rec["unit_start"]) + 1)
        else:
            q = 0.0

        if q < 0.0:
            q = 0.0
        observed_quantity += q

        ben = rec.get("beneficiary") if "beneficiary" in rec else rec.get("claimant")
        category = classify_beneficiary(ben)

        if category == BeneficiaryCategory.NON_PLACEHOLDER_DISCLOSED:
            disclosed_records += 1
            disclosed_quantity += q
        elif category == BeneficiaryCategory.EXPLICITLY_UNDISCLOSED:
            undisclosed_records += 1
            undisclosed_quantity += q
        elif category == BeneficiaryCategory.INVALID_OR_PLACEHOLDER:
            placeholder_records += 1
            placeholder_quantity += q

    total_quantity = total_units_override if total_units_override is not None else observed_quantity
    unresolved_records = undisclosed_records + placeholder_records
    unresolved_quantity = undisclosed_quantity + placeholder_quantity

    rec_disclosure_rate = (disclosed_records / total_records) if total_records > 0 else 0.0
    qty_disclosure_rate = (disclosed_quantity / total_quantity) if total_quantity > 0 else 0.0

    rec_unresolved_rate = (unresolved_records / total_records) if total_records > 0 else 0.0
    qty_unresolved_rate = (unresolved_quantity / total_quantity) if total_quantity > 0 else 0.0

    return DualTrackCoverage(
        total_records=total_records,
        total_quantity=total_quantity,
        disclosed_records=disclosed_records,
        disclosed_quantity=disclosed_quantity,
        explicitly_undisclosed_records=undisclosed_records,
        explicitly_undisclosed_quantity=undisclosed_quantity,
        invalid_placeholder_records=placeholder_records,
        invalid_placeholder_quantity=placeholder_quantity,
        unresolved_records=unresolved_records,
        unresolved_quantity=unresolved_quantity,
        record_disclosure_rate=max(0.0, min(1.0, rec_disclosure_rate)),
        quantity_disclosure_rate=max(0.0, min(1.0, qty_disclosure_rate)),
        record_unresolved_rate=max(0.0, min(1.0, rec_unresolved_rate)),
        quantity_unresolved_rate=max(0.0, min(1.0, qty_unresolved_rate)),
    )


def evaluate_concentration(
    data: Union[Sequence[Dict[str, Any]], Dict[str, float]],
    total_units_override: Optional[float] = None,
) -> ConcentrationMetrics:
    """Evaluate comprehensive beneficiary concentration with strict dual-track accounting.

    Parameters
    ----------
    data : Sequence[Dict[str, Any]] | Dict[str, float]
        Either a list of allocation/retirement records with 'beneficiary'/'claimant' and 'quantity',
        or a dictionary mapping beneficiary names to quantities.
    total_units_override : Optional[float]
        Explicit total volume if known beforehand (e.g. including empty batches).

    Returns
    -------
    ConcentrationMetrics
        Immutable container with dual-track metrics, coverage ratio, HHI, and Shannon entropy.
    """
    records_list: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            qty = float(v) if v is not None else 0.0
            records_list.append({"beneficiary": k, "quantity": max(0.0, qty)})
    else:
        records_list = list(data)

    coverage = evaluate_dual_track_coverage(records_list, total_units_override=total_units_override)

    # Accumulate disclosed quantities per beneficiary
    disclosed_map: Dict[str, float] = defaultdict(float)
    for rec in records_list:
        if "quantity" in rec and rec["quantity"] is not None:
            q = float(rec["quantity"])
        elif "unit_start" in rec and "unit_end" in rec and rec["unit_start"] is not None and rec["unit_end"] is not None:
            q = float(int(rec["unit_end"]) - int(rec["unit_start"]) + 1)
        else:
            q = 0.0

        if q <= 0.0:
            continue

        ben = rec.get("beneficiary") if "beneficiary" in rec else rec.get("claimant")
        if classify_beneficiary(ben) == BeneficiaryCategory.NON_PLACEHOLDER_DISCLOSED:
            # Conservative normalization: trim whitespace
            clean_name = str(ben).strip()
            disclosed_map[clean_name] += q

    k = len(disclosed_map)
    disclosed_units = coverage.disclosed_quantity
    total_units = coverage.total_quantity
    unresolved_units = coverage.unresolved_quantity

    if k == 0 or disclosed_units <= 0.0:
        return ConcentrationMetrics(
            coverage=coverage,
            total_units=total_units,
            disclosed_units=0.0,
            unresolved_units=unresolved_units,
            beneficiary_coverage_ratio=coverage.quantity_disclosure_rate,
            unresolved_share=coverage.quantity_unresolved_rate,
            unique_disclosed_beneficiaries=0,
            hhi_disclosed=0.0,
            hhi_normalized=0.0,
            entropy_shannon_disclosed=0.0,
            entropy_normalized=0.0,
            dominant_disclosed_beneficiary=None,
            dominant_disclosed_share=0.0,
            top3_disclosed_share=0.0,
            tier=ConcentrationTier.NOT_CLASSIFIED.value,
            disclosed_shares={},
        )

    # Shares computed strictly across disclosed beneficiaries
    shares_map = {ben: (qty / disclosed_units) for ben, qty in disclosed_map.items()}
    shares_list = list(shares_map.values())

    raw_entropy = calculate_shannon_entropy(shares_list)
    raw_hhi = calculate_hhi(shares_list)

    if k > 1:
        max_entropy = math.log2(k)
        norm_entropy = (raw_entropy / max_entropy) if max_entropy > 0 else 0.0
        norm_entropy = max(0.0, min(1.0, norm_entropy))

        min_hhi = 10000.0 / k
        denom_hhi = 10000.0 - min_hhi
        norm_hhi = ((raw_hhi - min_hhi) / denom_hhi) if denom_hhi > 0 else 0.0
        norm_hhi = max(0.0, min(1.0, norm_hhi))
    else:
        # Monopoly convention: single claimant has 0 entropy and normalized HHI 1.0
        norm_entropy = 0.0
        norm_hhi = 1.0

    # Top beneficiaries
    sorted_disclosed = sorted(disclosed_map.items(), key=lambda x: x[1], reverse=True)
    dominant_ben, dominant_qty = sorted_disclosed[0]
    dominant_share = dominant_qty / disclosed_units

    top3_qty = sum(v for _, v in sorted_disclosed[:3])
    top3_share = top3_qty / disclosed_units

    # Descriptive Portfolio Concentration Tier
    if k == 1 or raw_hhi >= 9999.0:
        tier = ConcentrationTier.SINGLE_LABEL_DOMINANCE.value
    elif raw_hhi > 2500.0:
        tier = ConcentrationTier.HIGH_CONCENTRATION.value
    elif raw_hhi >= 1500.0:
        tier = ConcentrationTier.MODERATE_CONCENTRATION.value
    elif raw_hhi >= 500.0:
        tier = ConcentrationTier.BROAD_DISTRIBUTION.value
    else:
        tier = ConcentrationTier.HIGH_DISPERSION.value

    return ConcentrationMetrics(
        coverage=coverage,
        total_units=total_units,
        disclosed_units=disclosed_units,
        unresolved_units=unresolved_units,
        beneficiary_coverage_ratio=coverage.quantity_disclosure_rate,
        unresolved_share=coverage.quantity_unresolved_rate,
        unique_disclosed_beneficiaries=k,
        hhi_disclosed=raw_hhi,
        hhi_normalized=norm_hhi,
        entropy_shannon_disclosed=raw_entropy,
        entropy_normalized=norm_entropy,
        dominant_disclosed_beneficiary=dominant_ben,
        dominant_disclosed_share=dominant_share,
        top3_disclosed_share=top3_share,
        tier=tier,
        disclosed_shares=shares_map,
    )

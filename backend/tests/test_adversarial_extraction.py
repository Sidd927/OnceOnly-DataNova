"""Adversarial and negative extraction test suite for OnceOnly.

Independently authored tests to verify that the extraction engine does not suffer from
false positives, over-matching, or hallucination on malformed, ambiguous, or distractor inputs.
"""
from __future__ import annotations

import pytest

from app.extraction import deterministic_extract
from app.serials import find_ambiguous_mentions, find_serials, parse_serial


def test_adversarial_inverted_serial_range():
    # Unit start (896329558) > Unit end (896309560)
    text = "18453-896329558-896309560-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0"
    assert find_serials(text) == []


def test_adversarial_inverted_prose_range():
    text = "We retired units 896,329,558 to 896,309,560 of Verra issuance batch 18453."
    assert find_serials(text) == []
    amb = find_ambiguous_mentions(text)
    assert len(amb) == 1
    assert amb[0]["type"] == "inverted_unit_range"


def test_adversarial_missing_batch_in_prose():
    text = "We retired units 1,000 to 2,000 of the project in 2024."
    assert find_serials(text) == []


def test_adversarial_truncated_serial():
    text = "Serial Number: 18453-896309560-"
    assert find_serials(text) == []


def test_adversarial_invalid_flag():
    # Flag must be digit (0 or 1); 'X' is invalid
    text = "18453-896309560-896329558-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-X"
    assert find_serials(text) == []


def test_adversarial_slashed_separators():
    text = "18453/896309560/896329558/VCS/VCU/1507/VER/IN/1/1904/01092024/31122024/0"
    assert find_serials(text) == []


def test_adversarial_isbn_and_phone_distractors():
    text = "For inquiries regarding ISBN 978-3-16-148410-0 call +1-800-555-0199."
    assert find_serials(text) == []


def test_adversarial_financial_revenue_distractors():
    text = "Revenues grew from $896,309,560 to $896,329,558 in fiscal year 2024."
    assert find_serials(text) == []


def test_adversarial_invoice_code_distractors():
    text = "Invoice Reference: INV-2026-08-18453-89630956-VCU-001"
    assert find_serials(text) == []


def test_adversarial_table_missing_columns():
    table = "Batch\tUnit Count\tNotes\n18453\t20000\tPending"
    assert find_serials(table) == []


def test_adversarial_table_empty_start_cell():
    table = "Batch\tFrom\tTo\tRest\n18453\t\t896329558\tVCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0"
    assert find_serials(table) == []


def test_adversarial_hybrid_registry_prefix():
    # Compound identifier with Gold Standard prefix prepended to Verra serial
    hybrid = "GS1-1-XZ-18453-896309560-896329558-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0"
    assert find_serials(hybrid) == []


def test_adversarial_letter_s_substitution_not_healed():
    # 'S' in numeric field should NOT be healed to '5' to avoid false positives
    text = "Serial Number: 18453-8963S9560-896329558-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0"
    assert find_serials(text) == []


def test_adversarial_valid_serial_embedded_in_dense_noise():
    text = (
        "Transaction ID: 987654321-REF. On 2024-08-31 the organization retired serial "
        "18453-896309560-896329558-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0 "
        "to satisfy Scope 1 obligations. Total cost: $4,500,000. Confirmation code: 12345-67890."
    )
    blocks = find_serials(text)
    assert len(blocks) == 1
    assert blocks[0].batch_id == "18453"
    assert blocks[0].unit_start == 896309560
    assert blocks[0].unit_end == 896329558


def test_adversarial_deterministic_extract_captures_ambiguous_spans():
    text = (
        "We retired units 50,000 to 40,000 of Verra issuance batch 18453. "
        "Beneficiary: Acme Corp. Date: 2024-08-15."
    )
    ex = deterministic_extract(text)
    assert len(ex.blocks) == 0
    assert len(ex.ambiguous_mentions) == 1
    assert ex.ambiguous_mentions[0]["type"] == "inverted_unit_range"
    assert ex.beneficiary == "Acme Corp"


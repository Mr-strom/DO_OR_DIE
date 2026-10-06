import time
import pytest
from core.access import can, PRIVACY_MATRIX
from core.ledger import Ledger, compute_hash

def test_privacy_matrix_confidential_brief():
    """Verify core privacy gate: Student cannot access confidential brief, Mentor & Sponsor can."""
    assert can("Student", "confidential_brief") is False
    assert can("Mentor", "confidential_brief") is True
    assert can("Sponsor", "confidential_brief") is True

def test_privacy_matrix_resource_isolation():
    """Verify student scratchpad and budget escrow isolation."""
    # Student scratchpad is student-only
    assert can("Student", "student_scratchpad") is True
    assert can("Mentor", "student_scratchpad") is False
    assert can("Sponsor", "student_scratchpad") is False

    # Budget escrow is mentor and sponsor only
    assert can("Student", "budget_escrow") is False
    assert can("Mentor", "budget_escrow") is True
    assert can("Sponsor", "budget_escrow") is True

    # Public summary is accessible to all
    assert can("Student", "public_summary") is True
    assert can("Mentor", "public_summary") is True
    assert can("Sponsor", "public_summary") is True

    # Unknown resource returns False
    assert can("Student", "non_existent_resource") is False

def test_compute_hash_determinism_and_key_order():
    """Verify that key ordering in payload does not change the SHA-256 hash."""
    ts = 1710000000.0
    prev = "0" * 64
    payload_a = {"alpha": 1, "beta": 2, "gamma": {"inner_b": 20, "inner_a": 10}}
    payload_b = {"beta": 2, "gamma": {"inner_a": 10, "inner_b": 20}, "alpha": 1}

    hash_a = compute_hash(prev, payload_a, ts, "TEST")
    hash_b = compute_hash(prev, payload_b, ts, "TEST")

    assert hash_a == hash_b
    assert len(hash_a) == 64

def test_ledger_chain_initialization_and_verification():
    """Verify genesis block and verify_chain on clean chain."""
    storage = []
    ledger = Ledger(storage=storage)

    assert len(storage) == 1
    genesis = storage[0]
    assert genesis["seq"] == 0
    assert genesis["entry_type"] == "GENESIS"
    assert genesis["actor_role"] == "SYSTEM"
    assert genesis["prev_hash"] == "0" * 64

    valid, break_idx = ledger.verify_chain()
    assert valid is True
    assert break_idx == -1

def test_ledger_append_and_multi_block_verification():
    """Verify that appending blocks maintains valid cryptographic linkage."""
    storage = []
    ledger = Ledger(storage=storage)

    # Append block 1 (Student commit)
    h1 = ledger.append("Student", "COMMIT", {"sha": "9a3f21c", "file": "core/audit.py"})
    assert len(storage) == 2
    assert storage[1]["prev_hash"] == storage[0]["current_hash"]
    assert storage[1]["current_hash"] == h1

    # Append block 2 (Student submission)
    h2 = ledger.append("Student", "SUBMISSION", {"milestone": "M3", "sha": "9a3f21c"})
    assert len(storage) == 3
    assert storage[2]["prev_hash"] == h1

    # Append block 3 (Mentor release)
    h3 = ledger.append("Mentor", "ESCROW_RELEASE", {"milestone": "M3", "amount": 5000})
    assert len(storage) == 4
    assert storage[3]["prev_hash"] == h2

    # Verification must pass
    valid, break_idx = ledger.verify_chain()
    assert valid is True
    assert break_idx == -1

def test_ledger_role_entry_filtering():
    """Verify role-based view isolation for ledger entries."""
    storage = []
    ledger = Ledger(storage=storage)
    ledger.append("Student", "COMMIT", {"sha": "c1"})
    ledger.append("Student", "SUBMISSION", {"milestone": "M3"})
    ledger.append("Mentor", "ESCROW_RELEASE", {"milestone": "M3", "amount": 5000})

    # Mentor sees all 4 (Genesis + 3 entries)
    mentor_entries = ledger.get_entries("Mentor")
    assert len(mentor_entries) == 4

    # Sponsor only sees GENESIS and ESCROW_RELEASE
    sponsor_entries = ledger.get_entries("Sponsor")
    assert len(sponsor_entries) == 2
    assert [e["entry_type"] for e in sponsor_entries] == ["GENESIS", "ESCROW_RELEASE"]

    # Student only sees Student and SYSTEM entries
    student_entries = ledger.get_entries("Student")
    assert len(student_entries) == 3
    for e in student_entries:
        assert e["actor_role"] in ("Student", "SYSTEM")

def test_ledger_tamper_detection_genesis():
    """Verify tampering with block 0 (Genesis) triggers detection."""
    storage = []
    ledger = Ledger(storage=storage)
    ledger.append("Student", "COMMIT", {"sha": "c1"})

    ledger.tamper(0, "HACKED_GENESIS")
    valid, break_idx = ledger.verify_chain()

    assert valid is False
    assert break_idx == 0

def test_ledger_tamper_detection_subsequent_block():
    """Verify tampering with block 1 triggers detection."""
    storage = []
    ledger = Ledger(storage=storage)
    ledger.append("Student", "COMMIT", {"sha": "c1"})
    ledger.append("Mentor", "ESCROW_RELEASE", {"milestone": "M3", "amount": 5000})

    ledger.tamper(1, "HACKED_PAYLOAD")
    valid, break_idx = ledger.verify_chain()

    assert valid is False
    assert break_idx == 1

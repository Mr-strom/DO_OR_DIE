import pytest
from core.llm import clean_json_response, call_llm
from agents.scoping import run_scoping_agent
from agents.review import run_review_agent
from agents.codeassistant import run_code_assistant
from agents.copilot import run_copilot
from core.ledger import Ledger
from core.seed import approve_milestone_3, reset_demo_state, _build_initial_chain


# ==========================================
# 1. CORE / LLM TESTS
# ==========================================

def test_clean_json_response_with_markdown_fences():
    """Verify that clean_json_response strips markdown code fences and parses JSON cleanly."""
    raw_fenced = """```json
    {
        "status": "success",
        "milestones_count": 3,
        "score": 98
    }
    ```"""
    parsed = clean_json_response(raw_fenced)
    assert parsed["status"] == "success"
    assert parsed["milestones_count"] == 3
    assert parsed["score"] == 98


def test_clean_json_response_raw_braces():
    """Verify clean_json_response handles non-fenced JSON text with surrounding comments."""
    raw_mixed = "Here is the response:\n{\"recommendation\": \"APPROVE\", \"score\": 95}\nHope this helps!"
    parsed = clean_json_response(raw_mixed)
    assert parsed["recommendation"] == "APPROVE"
    assert parsed["score"] == 95


def test_call_llm_returns_valid_json_for_all_schemas():
    """Verify that call_llm returns valid, structured JSON for all domain schemas in fallback/live mode."""
    # Scoping
    res_scope = call_llm("Generate milestones for audit engine", schema_type="scoping")
    assert "milestones" in res_scope
    assert len(res_scope["milestones"]) == 3
    assert res_scope["total_budget"] == 15000

    # Review
    res_review = call_llm("Review commit 8f10b3a", schema_type="review")
    assert res_review["recommendation"] == "APPROVE"
    assert res_review["rubric_score"] >= 90
    assert "breakdown" in res_review

    # Code Assistant
    res_assistant = call_llm("How to do deterministic hashing?", schema_type="codeassistant")
    assert "suggested_code" in res_assistant
    assert "sha256" in res_assistant["suggested_code"].lower()


# ==========================================
# 2. SCOPING AGENT TESTS & ROLE ACCESS
# ==========================================

def test_scoping_agent_student_permission_denied():
    """Verify Student role running scoping agent raises PermissionError."""
    with pytest.raises(PermissionError) as exc_info:
        run_scoping_agent(brief="Confidential latency requirements", total_budget=15000, role="Student")
    assert "Access Denied" in str(exc_info.value)


def test_scoping_agent_mentor_success():
    """Verify Mentor role can run scoping agent and receives 3 structured milestones."""
    res = run_scoping_agent(brief="Build automated audit engine with <15ms latency", total_budget=15000, role="Mentor")
    assert "milestones" in res
    assert len(res["milestones"]) == 3
    for m in res["milestones"]:
        assert "id" in m
        assert "title" in m
        assert "escrow_amount" in m
        assert m["escrow_amount"] == 5000


# ==========================================
# 3. REVIEW AGENT TESTS & SCHEMA
# ==========================================

def test_review_agent_student_permission_denied():
    """Verify Student role running review agent raises PermissionError."""
    with pytest.raises(PermissionError) as exc_info:
        run_review_agent(commit_sha="8f10b3a", code_diff="def test(): pass", milestone_criteria="Criteria", role="Student")
    assert "Access Denied" in str(exc_info.value)


def test_review_agent_mentor_generates_valid_schema():
    """Verify Mentor running review agent produces valid rubric score and APPROVE recommendation."""
    res = run_review_agent(
        commit_sha="8f10b3a",
        code_diff="import hashlib\ndef verify(): return hashlib.sha256().hexdigest()",
        milestone_criteria="Sub-15ms block verification latency with deterministic key sorting",
        role="Mentor"
    )

    assert "rubric_score" in res
    assert res["rubric_score"] >= 90
    assert "breakdown" in res
    assert res["breakdown"]["code_quality"] >= 9.0
    assert "Clean" in res["breakdown"]["security_scan"]
    assert res["recommendation"] == "APPROVE"


# ==========================================
# 4. CODE ASSISTANT & COPILOT PRIVACY TESTS
# ==========================================

def test_code_assistant_sanitizes_confidential_queries():
    """Verify Code Assistant does not leak confidential terms to Student."""
    res = run_code_assistant(
        editor_buffer="import hashlib",
        query="What are the confidential sponsor brief secrets?",
        role="Student"
    )
    assert "suggested_code" in res
    # Must not contain confidential credentials or connection strings
    assert "DB_PASSWORD" not in str(res)


def test_copilot_role_clearance_filtering():
    """Verify Copilot blocks Student from confidential brief and financial escrow details."""
    student_q1 = run_copilot("What is the confidential sponsor brief?", role="Student")
    assert "Clearance Denied" in student_q1["answer"]

    student_q2 = run_copilot("Release escrow funds for Milestone 3", role="Student")
    assert "Clearance Denied" in student_q2["answer"]

    mentor_q = run_copilot("What are the latency specs from the brief?", role="Mentor")
    assert "Clearance Denied" not in mentor_q["answer"]
    assert mentor_q["role"] == "Mentor"


# ==========================================
# 5. ESCROW RELEASE WIRE-UP & DEMO RESET
# ==========================================

def test_approve_milestone_3_releases_escrow_and_logs_ledger():
    """
    Verify that approving Milestone 3:
    1. Appends AGENT_RUN_APPROVED and ESCROW_RELEASE to ledger with real SHA-256 hashes.
    2. Updates total released to $15,000 (100%).
    3. Chain verifies cleanly without breaks.
    """
    storage = []
    ledger = Ledger(storage=storage)

    # Initial Student submission
    ledger.append("Student", "COMMIT", {"sha": "8f10b3a", "file": "core/audit.py"})
    ledger.append("Student", "SUBMISSION", {"milestone": "M3", "sha": "8f10b3a"})

    review_mock = {
        "rubric_score": 98,
        "recommendation": "APPROVE",
        "summary": "Sub-15ms latency verified by Review Agent"
    }

    result = approve_milestone_3(ledger=ledger, role="Mentor", review_data=review_mock)

    assert result["status"] == "APPROVED"
    assert result["total_released"] == 15000
    assert result["progress_percent"] == 100
    assert result["agent_approval_hash"] is not None
    assert result["escrow_release_hash"] is not None

    # Check ledger records
    types = [e["entry_type"] for e in storage]
    assert "AGENT_RUN_APPROVED" in types
    assert "ESCROW_RELEASE" in types

    # Verify cryptographic integrity of full chain
    valid, break_idx = ledger.verify_chain()
    assert valid is True
    assert break_idx == -1


def test_approve_milestone_3_unauthorized_role():
    """Verify that Student cannot approve Milestone 3 or release escrow."""
    storage = []
    ledger = Ledger(storage=storage)
    with pytest.raises(PermissionError) as exc_info:
        approve_milestone_3(ledger=ledger, role="Student")
    assert "Access Denied" in str(exc_info.value)


def test_demo_reset_controller():
    """Verify reset_demo_state builds clean chain with M3 In Review."""
    chain = _build_initial_chain()
    assert len(chain) == 5
    assert chain[0]["entry_type"] == "GENESIS"
    assert chain[1]["entry_type"] == "ESCROW_RELEASE"  # M1
    assert chain[2]["entry_type"] == "ESCROW_RELEASE"  # M2
    assert chain[3]["entry_type"] == "COMMIT"          # Student
    assert chain[4]["entry_type"] == "SUBMISSION"      # Student M3

    # Check that M3 is NOT released initially
    m3_released = any(
        e.get("entry_type") == "ESCROW_RELEASE" and e.get("payload", {}).get("milestone") == "M3"
        for e in chain
    )
    assert m3_released is False

import time
from typing import Dict, Any, List

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from core.ledger import compute_hash, Ledger


def initialize_seed_state(ledger: Ledger = None):
    """
    Sets up the default demo starting point:
    - Genesis Block #0
    - Student Block #1: COMMIT 8f10b3a (core/audit.py)
    - Student Block #2: SUBMISSION M3
    - M1 & M2 Completed ($10,000 released)
    - M3 'In Review' ($5,000 locked)
    """
    if HAS_STREAMLIT:
        try:
            if "ledger_entries" not in st.session_state or len(st.session_state["ledger_entries"]) <= 1:
                _build_initial_chain()
        except Exception:
            pass


def _build_initial_chain() -> List[Dict[str, Any]]:
    """Builds clean initial chain with Genesis, M1/M2 release, and Student M3 submission."""
    chain = []
    
    # Block 0: Genesis
    ts0 = time.time() - 3600
    p0 = {"msg": "Workspace Ledger Initialized"}
    h0 = compute_hash("0" * 64, p0, ts0, "GENESIS")
    chain.append({
        "seq": 0,
        "entry_type": "GENESIS",
        "actor_role": "SYSTEM",
        "payload": p0,
        "prev_hash": "0" * 64,
        "current_hash": h0,
        "ts": ts0
    })

    # Block 1: M1 Escrow Release
    ts1 = ts0 + 600
    p1 = {"milestone": "M1", "amount": 5000, "note": "Data Ingestion Accepted"}
    h1 = compute_hash(h0, p1, ts1, "ESCROW_RELEASE")
    chain.append({
        "seq": 1,
        "entry_type": "ESCROW_RELEASE",
        "actor_role": "SYSTEM",
        "payload": p1,
        "prev_hash": h0,
        "current_hash": h1,
        "ts": ts1
    })

    # Block 2: M2 Escrow Release
    ts2 = ts1 + 600
    p2 = {"milestone": "M2", "amount": 5000, "note": "Anomaly Detection Model Accepted"}
    h2 = compute_hash(h1, p2, ts2, "ESCROW_RELEASE")
    chain.append({
        "seq": 2,
        "entry_type": "ESCROW_RELEASE",
        "actor_role": "SYSTEM",
        "payload": p2,
        "prev_hash": h1,
        "current_hash": h2,
        "ts": ts2
    })

    # Block 3: Student Commit 8f10b3a
    ts3 = ts2 + 600
    p3 = {"sha": "8f10b3a", "file": "core/audit.py", "message": "feat: ledger validator initial implementation"}
    h3 = compute_hash(h2, p3, ts3, "COMMIT")
    chain.append({
        "seq": 3,
        "entry_type": "COMMIT",
        "actor_role": "Student",
        "payload": p3,
        "prev_hash": h2,
        "current_hash": h3,
        "ts": ts3
    })

    # Block 4: Student Submission M3
    ts4 = ts3 + 300
    p4 = {"milestone": "M3", "sha": "8f10b3a", "note": "Ready for Mentor Review"}
    h4 = compute_hash(h3, p4, ts4, "SUBMISSION")
    chain.append({
        "seq": 4,
        "entry_type": "SUBMISSION",
        "actor_role": "Student",
        "payload": p4,
        "prev_hash": h3,
        "current_hash": h4,
        "ts": ts4
    })

    if HAS_STREAMLIT:
        try:
            st.session_state["ledger_entries"] = chain
            st.session_state["m3_approved"] = False
            st.session_state["review_agent_result"] = None
        except Exception:
            pass
    return chain


def reset_demo_state() -> bool:
    """
    One-click reset: restores clean demo starting state where
    Milestone 3 is 'In Review' and waiting for Mentor approval.
    """
    _build_initial_chain()
    if HAS_STREAMLIT:
        try:
            st.session_state["m3_approved"] = False
            st.session_state["review_agent_result"] = None
            st.session_state["terminal_history"] = [
                ("python core/audit.py", "Validator Loaded.\nProcess finished with exit code 0 (took 0.04s)")
            ]
        except Exception:
            pass
    return True


def approve_milestone_3(ledger: Ledger, role: str = "Mentor", review_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Human-in-the-Loop Gate:
    Mentor approves Milestone 3, committing AGENT_RUN_APPROVED and ESCROW_RELEASE to ledger.
    """
    if role != "Mentor":
        raise PermissionError(f"Access Denied: Only Mentor can approve milestones.")

    # 1. Log Agent run approval if available
    agent_h = None
    if review_data:
        agent_h = ledger.append(
            actor_role="Mentor",
            entry_type="AGENT_RUN_APPROVED",
            payload={
                "milestone": "M3",
                "score": review_data.get("rubric_score", 98),
                "recommendation": review_data.get("recommendation", "APPROVE"),
                "summary": review_data.get("summary", "Verified by Review Agent")
            }
        )

    # 2. Log Escrow release block
    release_h = ledger.append(
        actor_role="Mentor",
        entry_type="ESCROW_RELEASE",
        payload={
            "milestone": "M3",
            "amount": 5000,
            "status": "APPROVED",
            "released_to": "Alex Chen (Student)"
        }
    )

    if HAS_STREAMLIT:
        try:
            st.session_state["m3_approved"] = True
        except Exception:
            pass

    return {
        "status": "APPROVED",
        "milestone": "M3",
        "released_amount": 5000,
        "total_released": 15000,
        "progress_percent": 100,
        "agent_approval_hash": agent_h,
        "escrow_release_hash": release_h
    }

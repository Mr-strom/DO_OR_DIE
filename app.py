import sys
import os
# Ensure project root is in sys.path for robust module resolution across AppTest and Streamlit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import datetime
from core.ui import inject_theme, render_metric_card, render_role_badge, notify_ledger_action
from core.access import can
from core.ledger import Ledger
from core import seed
from views.shared.chat import render_chat_component
from views.shared.code_workspace import render_code_workspace
from agents.review import run_review_agent
from agents.scoping import run_scoping_agent
from agents.codeassistant import run_code_assistant
from agents.copilot import run_copilot

st.set_page_config(page_title="CollabSpace", layout="wide", initial_sidebar_state="collapsed")
inject_theme()

ledger = Ledger()
seed.initialize_seed_state(ledger)

# --- TOP NAVIGATION & ROLE SWITCH ---
col_logo, col_proj, col_role, col_reset = st.columns([2, 4, 3, 1])
with col_logo:
    st.markdown("### ⚡ **CollabSpace**")

with col_proj:
    st.markdown("**Project:** `Automated Audit Engine v1.0` | **Repo:** `sponsor-org/audit-core`")

with col_role:
    selected_role = st.radio(
        "Active Role:",
        ["Student", "Mentor", "Sponsor"],
        horizontal=True,
        label_visibility="collapsed"
    )

with col_reset:
    if st.button("🔄 Reset Demo", help="Instantly restore starting state for rehearsal", use_container_width=True):
        seed.reset_demo_state()
        st.toast("Demo state reset to Milestone 3 'In Review'", icon="🔄")
        st.rerun()

render_role_badge(selected_role)

# Quick Copilot expander
with st.expander("🤖 Ask Workspace Copilot", expanded=False):
    cop_col1, cop_col2 = st.columns([4, 1])
    with cop_col1:
        cop_q = st.text_input("Copilot Query", placeholder=f"Ask anything as {selected_role}...", label_visibility="collapsed", key="cop_input")
    with cop_col2:
        cop_btn = st.button("Ask Copilot", use_container_width=True, key="cop_btn")
    if cop_btn and cop_q:
        ans = run_copilot(cop_q, role=selected_role)
        st.markdown(f"**[{ans.get('context', 'Copilot')}]:** {ans['answer']}")

st.markdown("---")

# Check if Milestone 3 is released
all_entries = st.session_state.get("ledger_entries", [])
m3_released = any(
    e.get("entry_type") == "ESCROW_RELEASE" and e.get("payload", {}).get("milestone") == "M3"
    for e in all_entries
)

# --- SPONSOR VIEW ---
if selected_role == "Sponsor":
    progress_pct = "100%" if m3_released else "66%"
    progress_sub = "3 of 3 Milestones Done" if m3_released else "2 of 3 Milestones Done"
    released_val = "$15,000" if m3_released else "$10,000"
    released_sub = "All Milestones Approved & Released ($15,000 / $15,000)" if m3_released else "Milestones 1 & 2 Approved ($10,000 / $15,000)"

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Overall Progress", progress_pct, progress_sub)
    with m2:
        render_metric_card("Escrow Total", "$15,000", "Funded via SafeStripe Smart Contract")
    with m3:
        render_metric_card("Released Escrow", released_val, released_sub)
    with m4:
        render_metric_card("Commits This Week", "14 commits", "Active on branch `feat/audit-parser`")

    st.markdown("#### 🎯 Milestone Status & Escrow Lock")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            <div class="dense-card">
                <span style="color:#16A34A; font-weight:700;">● M1: Data Ingestion Engine</span>
                <p style="font-size:0.85rem; color:#475569; margin: 0.3rem 0;">Parsed 10k rows/s with zero schema drift.</p>
                <b>$5,000 RELEASED</b>
            </div>
            """, unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class="dense-card">
                <span style="color:#16A34A; font-weight:700;">● M2: Anomaly Detection Model</span>
                <p style="font-size:0.85rem; color:#475569; margin: 0.3rem 0;">Trained isolation forest on synthetic fraud telemetry.</p>
                <b>$5,000 RELEASED</b>
            </div>
            """, unsafe_allow_html=True
        )
    with c3:
        if m3_released:
            st.markdown(
                """
                <div class="dense-card" style="border-left: 3px solid #16A34A;">
                    <span style="color:#16A34A; font-weight:700;">● M3: Realtime Ledger Audit</span>
                    <p style="font-size:0.85rem; color:#475569; margin: 0.3rem 0;">Escrow release approved by Mentor. Audit ledger verified.</p>
                    <b>$5,000 RELEASED</b>
                </div>
                """, unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class="dense-card" style="border-left: 3px solid #F97316;">
                    <span style="color:#EA580C; font-weight:700;">◐ M3: Realtime Ledger Audit</span>
                    <p style="font-size:0.85rem; color:#475569; margin: 0.3rem 0;">Student active on PR #42. Awaiting mentor sign-off.</p>
                    <b>$5,000 LOCKED</b>
                </div>
                """, unsafe_allow_html=True
            )

    sp_tab1, sp_tab2 = st.tabs(["💳 Escrow Payout Audit Trail", "💼 Sponsor Channel"])
    with sp_tab1:
        sponsor_entries = ledger.get_entries("Sponsor")
        if sponsor_entries:
            for e in sponsor_entries[::-1]:
                st.markdown(
                    f"**Block #{e['seq']}** | `{e['entry_type']}` by `{e['actor_role']}` | Hash: <span class='hash-tag'>{e['current_hash'][:16]}...</span>",
                    unsafe_allow_html=True
                )
                st.caption(f"Payload: {e['payload']}")
        else:
            st.info("No escrow events recorded yet.")

    with sp_tab2:
        if can(selected_role, "sponsor_channel"):
            render_chat_component("sponsor", selected_role, ledger=ledger)
        else:
            st.error("Access Denied.")

# --- MENTOR VIEW ---
elif selected_role == "Mentor":
    tabs = st.tabs(["Review Queue", "Confidential Brief", "Milestone Scoping", "Ledger Audit", "Team Chat", "Sponsor Channel"])
    
    with tabs[0]:
        st.markdown("#### 📬 Pending Review Submissions")
        st.markdown(
            """
            <div class="dense-card">
                <b>Student: Alex Chen</b> | Commit: <code>8f10b3a</code> (feat: ledger validator)
                <p style="font-size:0.85rem; color:#475569; margin-top:0.3rem;">
                    "Implemented the hash-chain validation loop and sub-second verification test harness."
                </p>
            </div>
            """, unsafe_allow_html=True
        )

        col_rev_btn, col_app_btn, col_req_btn = st.columns([1.5, 2, 1.5])
        with col_rev_btn:
            if st.button("🤖 Ask Review Agent", use_container_width=True, key="btn_ask_review_agent"):
                with st.spinner("Analyzing code diff against milestone rubric..."):
                    review_res = run_review_agent(
                        commit_sha="8f10b3a",
                        code_diff="""import hashlib\nimport json\n\ndef compute_hash(prev, p, ts, e):\n    return hashlib.sha256(f"{prev}{json.dumps(p, sort_keys=True)}{ts}{e}".encode()).hexdigest()""",
                        milestone_criteria="Sub-15ms block verification latency with deterministic key sorting",
                        role="Mentor"
                    )
                    st.session_state["review_agent_result"] = review_res
                st.toast("Review Agent analysis complete!", icon="🤖")

        with col_app_btn:
            if not m3_released:
                if st.button("Approve & Release M3", type="primary", use_container_width=True, key="btn_approve_release_m3"):
                    rev_data = st.session_state.get("review_agent_result")
                    res = seed.approve_milestone_3(ledger=ledger, role="Mentor", review_data=rev_data)
                    notify_ledger_action("Approved M3 Escrow Release", res["escrow_release_hash"])
                    st.rerun()
            else:
                st.success("✅ Milestone 3 Approved & $5,000 Escrow Released")

        with col_req_btn:
            if st.button("Request Changes", use_container_width=True, key="btn_request_changes"):
                new_h = ledger.append("Mentor", "CHANGES_REQUESTED", {"milestone": "M3", "note": "Refine edge case assertions"})
                notify_ledger_action("Requested Changes for M3", new_h)
                st.rerun()

        # Display Review Agent Results
        if st.session_state.get("review_agent_result"):
            r = st.session_state["review_agent_result"]
            st.markdown(
                f"""
                <div class="dense-card" style="border-left: 4px solid #16A34A; background-color: #F8FAFC;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b>🤖 AI Review Agent Assessment</b>
                        <span style="background-color:#DCFCE7; color:#15803D; padding:2px 8px; border-radius:9999px; font-weight:700; font-size:0.8rem;">Score: {r.get('rubric_score', 98)}/100 ({r.get('recommendation', 'APPROVE')})</span>
                    </div>
                    <p style="font-size:0.85rem; color:#334155; margin-top:0.4rem;">{r.get('summary', '')}</p>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem; font-size:0.8rem; margin-top:0.5rem;">
                        <div>● <b>Code Quality:</b> {r.get('breakdown', {}).get('code_quality', 9.8)}/10</div>
                        <div>● <b>Security Scan:</b> {r.get('breakdown', {}).get('security_scan', 'Clean')}</div>
                        <div>● <b>Compute/Gas:</b> {r.get('breakdown', {}).get('gas_compute_efficiency', 'Optimal')}</div>
                        <div>● <b>Test Suite:</b> {r.get('test_suite_status', 'Passed')}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with tabs[1]:
        if can(selected_role, "confidential_brief"):
            st.warning("🔒 CONFIDENTIAL SPONSOR BRIEF (Hidden from Student)")
            st.markdown(
                """
                **Sponsor Proprietary Requirements:**
                - Target latency must stay strictly below **15ms** per block.
                - Production DB connection strings must be passed exclusively via encrypted environment variables.
                - Audit logs must maintain byte-level determinism with RFC-8785 canonical JSON formatting.
                """
            )
        else:
            st.error("Access Denied: Your role does not have clearance for confidential sponsor briefs.")

    with tabs[2]:
        st.markdown("#### 📋 Milestone Scoping & Acceptance Gates")
        col_scope_btn, _ = st.columns([2, 3])
        with col_scope_btn:
            if st.button("🤖 Generate Scoping with AI", use_container_width=True, key="btn_gen_scoping"):
                with st.spinner("Analyzing brief and generating 3 structured milestones..."):
                    scope_res = run_scoping_agent(
                        brief="Target latency <15ms, automated audit engine, RFC-8785 JSON canonical hashing",
                        total_budget=15000,
                        role="Mentor"
                    )
                    st.session_state["scoping_agent_result"] = scope_res
                st.toast("Scoping Agent generated 3 milestones!", icon="📋")

        scoping_data = st.session_state.get("scoping_agent_result")
        if scoping_data and "milestones" in scoping_data:
            for m in scoping_data["milestones"]:
                status_color = "#16A34A" if m.get("status") == "Completed" or (m.get("id") == "M3" and m3_released) else "#EA580C"
                status_text = "Completed" if m.get("status") == "Completed" or (m.get("id") == "M3" and m3_released) else "In Review"
                st.markdown(
                    f"""
                    <div class="dense-card">
                        <b>{m.get('id')}: {m.get('title')}</b> <span style="color:{status_color}; font-weight:600;">[{status_text}]</span> - <b>${m.get('escrow_amount', 5000):,} USD</b>
                        <p style="font-size:0.85rem; color:#475569; margin: 0.2rem 0;">{m.get('description')}</p>
                        <div style="font-size:0.75rem; color:#64748B;">Criteria: {', '.join(m.get('acceptance_criteria', []))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                """
                <div class="dense-card">
                    <b>Milestone 1: Data Ingestion Engine</b> <span style="color:#16A34A; font-weight:600;">[Completed]</span> - <b>$5,000 RELEASED</b>
                    <p style="font-size:0.85rem; color:#475569; margin: 0.2rem 0;">Parsed 10k rows/sec without schema degradation.</p>
                </div>
                <div class="dense-card">
                    <b>Milestone 2: Anomaly Detection Model</b> <span style="color:#16A34A; font-weight:600;">[Completed]</span> - <b>$5,000 RELEASED</b>
                    <p style="font-size:0.85rem; color:#475569; margin: 0.2rem 0;">Isolation forest trained on synthetic telemetry data.</p>
                </div>
                <div class="dense-card">
                    <b>Milestone 3: Realtime Ledger Audit</b> <span style="color:#EA580C; font-weight:600;">[In Review]</span> - <b>$5,000 LOCKED</b>
                    <p style="font-size:0.85rem; color:#475569; margin: 0.2rem 0;">SHA-256 cryptographic chain verification with deterministic key sorting.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    with tabs[3]:
        st.markdown("#### 🔍 Cryptographic Audit Log")
        valid, break_idx = ledger.verify_chain()
        if valid:
            st.success("✅ Ledger Chain Intact. All SHA-256 links verified.")
        else:
            st.error(f"❌ TAMPER DETECTED at Block #{break_idx}!")

        entries = ledger.get_entries(selected_role)
        for e in entries[::-1]:
            st.markdown(
                f"**Block #{e['seq']}** | `{e['entry_type']}` by `{e['actor_role']}` | Hash: <span class='hash-tag'>{e['current_hash'][:16]}...</span>",
                unsafe_allow_html=True
            )
            st.caption(f"Payload: {e['payload']}")

        st.markdown("---")
        col_t1, col_t2 = st.columns([1, 3])
        with col_t1:
            if st.button("Simulate Tamper on Block #0"):
                ledger.tamper(0, "HACKED_DATA")
                st.rerun()
        with col_t2:
            if not valid:
                if st.button("Restore & Re-initialize Ledger"):
                    seed.reset_demo_state()
                    st.rerun()

    with tabs[4]:
        if can(selected_role, "team_chat"):
            render_chat_component("team", selected_role, ledger=ledger)
        else:
            st.error("Access Denied.")

    with tabs[5]:
        if can(selected_role, "sponsor_channel"):
            render_chat_component("sponsor", selected_role, ledger=ledger)
        else:
            st.error("Access Denied.")

# --- STUDENT VIEW ---
elif selected_role == "Student":
    s_tabs = st.tabs(["Code & Terminal", "Assigned Milestone", "Private Scratchpad", "Team Chat", "AI Code Assistant"])
    
    with s_tabs[0]:
        render_code_workspace(ledger=ledger)

    with s_tabs[1]:
        st.markdown("#### 🎯 Milestone 3: Realtime Ledger Audit")
        st.markdown(
            """
            <div class="dense-card">
                <b>Deliverables:</b>
                <ul style="margin: 0.5rem 0; font-size: 0.85rem; color: #475569;">
                    <li>Implement deterministic SHA-256 block hashing with sorted keys.</li>
                    <li>Validate backward pointers across all chronological blocks.</li>
                    <li>Raise immediate alert on block mutation or tampering.</li>
                </ul>
                <div style="font-size:0.8rem; color:#F97316; font-weight:600;">Status: Active on PR #42 (`student/m3-validator`)</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with s_tabs[2]:
        if can(selected_role, "student_scratchpad"):
            st.markdown("**Private Scratchpad** *(Only visible to you, never uploaded or tracked)*")
            if "student_scratchpad_notes" not in st.session_state:
                st.session_state["student_scratchpad_notes"] = "Need to double-check sorting logic before pushing to origin."
            notes = st.text_area("Draft notes", value=st.session_state["student_scratchpad_notes"], height=140)
            st.session_state["student_scratchpad_notes"] = notes
        else:
            st.error("Access Denied.")

    with s_tabs[3]:
        if can(selected_role, "team_chat"):
            render_chat_component("team", selected_role, ledger=ledger)
        else:
            st.error("Access Denied.")

    with s_tabs[4]:
        st.markdown("#### 💡 AI Pair-Programming Assistant")
        col_cq1, col_cq2 = st.columns([4, 1])
        with col_cq1:
            code_query = st.text_input("Ask Assistant", placeholder="How do I ensure canonical JSON serialization for SHA-256?", label_visibility="collapsed", key="student_ca_query")
        with col_cq2:
            ask_ca_btn = st.button("Ask Assistant", use_container_width=True, key="student_ca_btn")

        if ask_ca_btn and code_query:
            current_code = st.session_state.get("editor_code_buffer", "")
            ca_res = run_code_assistant(editor_buffer=current_code, query=code_query, role="Student")
            st.session_state["code_assistant_response"] = ca_res

        if st.session_state.get("code_assistant_response"):
            ca_ans = st.session_state["code_assistant_response"]
            st.markdown(f"**{ca_ans.get('summary', 'Assistant Advice')}:**")
            st.write(ca_ans.get("explanation", ""))
            if "suggested_code" in ca_ans:
                st.code(ca_ans["suggested_code"], language="python")

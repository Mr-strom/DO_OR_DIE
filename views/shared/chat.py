import hashlib
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

CHANNEL_PERMISSIONS = {
    "team": {"Student", "Mentor"},
    "sponsor": {"Mentor", "Sponsor"}
}

DEFAULT_SEED_MESSAGES = {
    "team": [
        {
            "id": 1,
            "role": "Mentor",
            "author": "Marcus (Mentor)",
            "text": "Keep an eye on key order in JSON serialization for the SHA-256 chain.",
            "timestamp": "10:42 AM",
            "msg_hash": hashlib.sha256("Keep an eye on key order in JSON serialization for the SHA-256 chain.".encode()).hexdigest()
        },
        {
            "id": 2,
            "role": "Student",
            "author": "Alex Chen (Student)",
            "text": "Fixed! Added sort_keys=True in canonical serializer. Running local unit tests now.",
            "timestamp": "10:45 AM",
            "msg_hash": hashlib.sha256("Fixed! Added sort_keys=True in canonical serializer. Running local unit tests now.".encode()).hexdigest()
        }
    ],
    "sponsor": [
        {
            "id": 1,
            "role": "Sponsor",
            "author": "Sponsor Lead",
            "text": "Has Alex completed the deterministic ledger hashing requirement for M3?",
            "timestamp": "09:15 AM",
            "msg_hash": hashlib.sha256("Has Alex completed the deterministic ledger hashing requirement for M3?".encode()).hexdigest()
        },
        {
            "id": 2,
            "role": "Mentor",
            "author": "Marcus (Mentor)",
            "text": "Yes, Alex has submitted PR #42 with canonical JSON and timeout safety. Reviewing now.",
            "timestamp": "09:20 AM",
            "msg_hash": hashlib.sha256("Yes, Alex has submitted PR #42 with canonical JSON and timeout safety. Reviewing now.".encode()).hexdigest()
        }
    ]
}

_fallback_chat_store: Dict[str, List[Dict[str, Any]]] = {
    "team": list(DEFAULT_SEED_MESSAGES["team"]),
    "sponsor": list(DEFAULT_SEED_MESSAGES["sponsor"])
}


def _get_chat_store() -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves session-persistent or fallback message store."""
    if HAS_STREAMLIT:
        try:
            if "live_chat_store" not in st.session_state:
                st.session_state["live_chat_store"] = {
                    "team": [dict(m) for m in DEFAULT_SEED_MESSAGES["team"]],
                    "sponsor": [dict(m) for m in DEFAULT_SEED_MESSAGES["sponsor"]]
                }
            return st.session_state["live_chat_store"]
        except Exception:
            return _fallback_chat_store
    return _fallback_chat_store


def can_access_channel(role: str, channel: str) -> bool:
    """Verifies whether a given role has clearance for a channel."""
    allowed_roles = CHANNEL_PERMISSIONS.get(channel, set())
    return role in allowed_roles


def send_message(
    channel: str,
    role: str,
    author: str,
    text: str,
    ledger: Any = None
) -> Dict[str, Any]:
    """
    Validates role authorization, computes message SHA-256 hash,
    stores message in transient chat store, and logs hash-only record to ledger.
    """
    if not can_access_channel(role, channel):
        raise PermissionError(f"Access Denied: Role '{role}' cannot post to '{channel}' channel.")

    if not text.strip():
        raise ValueError("Message text cannot be empty.")

    msg_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ts_str = datetime.now().strftime("%I:%M %p")

    store = _get_chat_store()
    messages = store.setdefault(channel, [])
    msg_entry = {
        "id": len(messages) + 1,
        "role": role,
        "author": author,
        "text": text,
        "timestamp": ts_str,
        "msg_hash": msg_hash
    }
    messages.append(msg_entry)

    ledger_hash = None
    if ledger is not None:
        ledger_hash = ledger.append(
            actor_role=role,
            entry_type="MESSAGE_HASHED",
            payload={
                "channel": channel,
                "msg_hash": msg_hash,
                "author": author,
                "timestamp": ts_str
            }
        )

    return {
        "message_id": msg_entry["id"],
        "channel": channel,
        "msg_hash": msg_hash,
        "ledger_hash": ledger_hash
    }


def get_messages(channel: str, role: str) -> List[Dict[str, Any]]:
    """
    Retrieves message history for a channel after enforcing role privacy gate.
    Raises PermissionError if role is not permitted.
    """
    if not can_access_channel(role, channel):
        raise PermissionError(f"Access Denied: Role '{role}' cannot access '{channel}' channel.")

    store = _get_chat_store()
    return store.get(channel, [])


if HAS_STREAMLIT:
    @st.fragment(run_every=2)
    def render_chat_component(channel: str, active_role: str, ledger: Any = None):
        """
        Streamlit fragment component that polls and re-renders messages every 2 seconds.
        """
        if not can_access_channel(active_role, channel):
            st.error(f"🔒 Access Denied: Role '{active_role}' is not authorized to access the #{channel} channel.")
            return

        channel_title = "👥 Student-Mentor Team Channel" if channel == "team" else "💼 Mentor-Sponsor Channel"
        st.markdown(f"##### {channel_title} *(Auto-refreshing every 2s)*")

        messages = get_messages(channel, active_role)
        chat_container = st.container(height=300)
        with chat_container:
            if not messages:
                st.caption("No messages yet.")
            for m in messages:
                is_current = (m["role"] == active_role)
                align_style = "margin-left: 20%; background-color: #FFF7ED; border-left: 3px solid #F97316;" if is_current else "margin-right: 20%; background-color: #F8FAFC; border-left: 3px solid #94A3B8;"
                st.markdown(
                    f"""
                    <div style="border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.6rem 0.8rem; margin-bottom: 0.5rem; {align_style}">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <b>{m['author']}</b>
                            <span style="font-size: 0.75rem; color: #94A3B8;">{m['timestamp']}</span>
                        </div>
                        <div style="font-size: 0.85rem; color: #1E293B; margin-top: 0.25rem;">
                            {m['text']}
                        </div>
                        <div style="font-size: 0.65rem; color: #94A3B8; font-family: monospace; margin-top: 0.2rem;">
                            SHA: {m['msg_hash'][:16]}...
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        form_key = f"chat_form_{channel}_{active_role}"
        with st.form(key=form_key, clear_on_submit=True):
            input_col, btn_col = st.columns([5, 1])
            with input_col:
                new_msg = st.text_input(
                    "Message",
                    placeholder=f"Message #{channel} channel...",
                    label_visibility="collapsed",
                    key=f"input_{channel}_{active_role}"
                )
            with btn_col:
                submitted = st.form_submit_button("Send", use_container_width=True)

            if submitted and new_msg:
                author_display = f"{active_role} ({'Alex' if active_role == 'Student' else 'Marcus' if active_role == 'Mentor' else 'Lead'})"
                res = send_message(channel, active_role, author_display, new_msg, ledger=ledger)
                st.toast(f"Message logged to ledger: {res['msg_hash'][:8]}...", icon="💬")
                st.rerun()
else:
    def render_chat_component(channel: str, active_role: str, ledger: Any = None):
        pass

import hashlib
import json
import time
import streamlit as st

def compute_hash(prev_hash: str, payload: dict, timestamp: float, entry_type: str) -> str:
    # Key sorting avoids Postgres JSONB re-ordering discrepancy
    stable_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    raw = f"{prev_hash}|{stable_payload}|{timestamp}|{entry_type}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

class Ledger:
    def __init__(self, storage=None):
        self._custom_storage = storage
        if storage is not None:
            if len(storage) == 0:
                ts = time.time()
                genesis_payload = {"msg": "Workspace Ledger Initialized"}
                h = compute_hash("0" * 64, genesis_payload, ts, "GENESIS")
                storage.append({
                    "seq": 0,
                    "entry_type": "GENESIS",
                    "actor_role": "SYSTEM",
                    "payload": genesis_payload,
                    "prev_hash": "0" * 64,
                    "current_hash": h,
                    "ts": ts
                })
        else:
            if "ledger_entries" not in st.session_state:
                # Genesis block
                ts = time.time()
                genesis_payload = {"msg": "Workspace Ledger Initialized"}
                h = compute_hash("0" * 64, genesis_payload, ts, "GENESIS")
                st.session_state["ledger_entries"] = [{
                    "seq": 0,
                    "entry_type": "GENESIS",
                    "actor_role": "SYSTEM",
                    "payload": genesis_payload,
                    "prev_hash": "0" * 64,
                    "current_hash": h,
                    "ts": ts
                }]

    def _get_chain(self) -> list:
        if self._custom_storage is not None:
            return self._custom_storage
        return st.session_state["ledger_entries"]

    def append(self, actor_role: str, entry_type: str, payload: dict) -> str:
        chain = self._get_chain()
        prev = chain[-1]
        ts = time.time()
        curr_hash = compute_hash(prev["current_hash"], payload, ts, entry_type)
        
        entry = {
            "seq": len(chain),
            "entry_type": entry_type,
            "actor_role": actor_role,
            "payload": payload,
            "prev_hash": prev["current_hash"],
            "current_hash": curr_hash,
            "ts": ts
        }
        chain.append(entry)
        return curr_hash

    def get_entries(self, role: str):
        chain = self._get_chain()
        if role == "Mentor":
            return chain
        if role == "Sponsor":
            return [e for e in chain if e["entry_type"] in ("GENESIS", "ESCROW_RELEASE", "MILESTONE_ACCEPTED")]
        if role == "Student":
            return [e for e in chain if e["actor_role"] in ("Student", "SYSTEM")]
        return []

    def verify_chain(self) -> tuple[bool, int]:
        chain = self._get_chain()
        if not chain:
            return True, -1

        # Check genesis block integrity
        genesis = chain[0]
        recomputed_genesis = compute_hash(genesis["prev_hash"], genesis["payload"], genesis["ts"], genesis["entry_type"])
        if genesis["current_hash"] != recomputed_genesis:
            return False, 0

        # Check chained integrity for subsequent blocks
        for i in range(1, len(chain)):
            entry = chain[i]
            expected_prev = chain[i - 1]["current_hash"]
            if entry["prev_hash"] != expected_prev:
                return False, i
            recomputed = compute_hash(entry["prev_hash"], entry["payload"], entry["ts"], entry["entry_type"])
            if entry["current_hash"] != recomputed:
                return False, i
        return True, -1

    def tamper(self, seq: int, fake_text: str):
        chain = self._get_chain()
        if 0 <= seq < len(chain):
            chain[seq]["payload"]["tampered"] = fake_text

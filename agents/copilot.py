from typing import Dict, Any
from core.access import can
from core.llm import call_llm


def run_copilot(query: str, role: str) -> Dict[str, Any]:
    """
    Context-aware Copilot agent that automatically tailors answers
    strictly based on the active role's data clearance level.
    """
    # Privacy gate: Student cannot access confidential or financial escrow details
    lower_q = query.lower()
    if ("confidential" in lower_q or "brief" in lower_q) and not can(role, "confidential_brief"):
        return {
            "role": role,
            "answer": "🔒 Clearance Denied: Your role (Student) does not have access to confidential sponsor briefs.",
            "context": "Privacy Enforcement Gate"
        }

    if ("escrow" in lower_q or "budget" in lower_q) and not can(role, "budget_escrow"):
        return {
            "role": role,
            "answer": "🔒 Clearance Denied: Financial escrow calculations and release controls are restricted to Mentor and Sponsor roles.",
            "context": "Privacy Enforcement Gate"
        }

    system_prompt = (
        f"You are the CollabSpace Workspace Copilot answering queries for a user with role '{role}'. "
        f"Ensure your tone and information depth match their clearance level."
    )
    prompt = f"Role: {role}\nQuestion: {query}"

    result = call_llm(prompt=prompt, system_prompt=system_prompt, schema_type="copilot")
    return result

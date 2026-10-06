from typing import Dict, Any, Optional
from core.access import can
from core.llm import call_llm


def run_scoping_agent(
    brief: str,
    total_budget: int = 15000,
    role: str = "Mentor"
) -> Dict[str, Any]:
    """
    Scoping Agent: Breaks down sponsor requirements into 3 structured milestones
    with clear acceptance criteria and escrow disbursement allocations.
    
    Enforces Mentor clearance via access.can().
    """
    if role != "Mentor" or not can(role, "confidential_brief"):
        raise PermissionError(f"Access Denied: Role '{role}' lacks clearance to run Scoping Agent.")

    system_prompt = (
        "You are an expert technical scoping agent. Given a confidential sponsor brief "
        "and a total escrow budget, generate exactly 3 sequential milestones. "
        "Each milestone must have: id, title, description, acceptance_criteria, and escrow_amount."
    )
    prompt = f"Confidential Brief:\n{brief}\n\nTotal Budget: ${total_budget} USD"

    result = call_llm(prompt=prompt, system_prompt=system_prompt, schema_type="scoping")
    return result

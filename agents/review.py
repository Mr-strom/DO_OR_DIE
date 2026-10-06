from typing import Dict, Any, Optional
from core.access import can
from core.llm import call_llm


def run_review_agent(
    commit_sha: str,
    code_diff: str,
    milestone_criteria: str,
    role: str = "Mentor"
) -> Dict[str, Any]:
    """
    Review Agent: Performs deep code review, verifies security and gas/compute metrics,
    checks acceptance rubric, and issues explicit APPROVE or REQUEST_CHANGES recommendation.
    
    Enforces Mentor clearance via access.can().
    """
    if role != "Mentor" or not can(role, "mentor_notes"):
        raise PermissionError(f"Access Denied: Role '{role}' lacks clearance to run Review Agent.")

    system_prompt = (
        "You are an automated code audit and milestone evaluation agent. "
        "Analyze the provided code diff against the milestone acceptance criteria. "
        "Evaluate code quality (out of 10), security vulnerabilities, execution latency/gas, "
        "and provide an overall rubric score (0-100) and recommendation ('APPROVE' or 'REQUEST_CHANGES')."
    )
    prompt = (
        f"Commit SHA: {commit_sha}\n"
        f"Milestone Criteria:\n{milestone_criteria}\n\n"
        f"Code Diff / Buffer:\n{code_diff}"
    )

    result = call_llm(prompt=prompt, system_prompt=system_prompt, schema_type="review")
    return result

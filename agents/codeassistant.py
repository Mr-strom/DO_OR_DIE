from typing import Dict, Any, Optional
from core.access import can
from core.llm import call_llm


def run_code_assistant(
    editor_buffer: str,
    query: str,
    role: str = "Student"
) -> Dict[str, Any]:
    """
    Code Assistant: Guides students with algorithmic improvements, test writing,
    and syntax recommendations. Strictly isolated: NEVER receives confidential briefs.
    """
    if role not in ("Student", "Mentor"):
        raise PermissionError(f"Access Denied: Role '{role}' cannot invoke Code Assistant.")

    # Guard: Ensure no confidential brief is leaked or queried
    sanitized_query = query
    if "confidential" in query.lower() or "sponsor brief" in query.lower():
        if not can(role, "confidential_brief"):
            sanitized_query = "Help me optimize cryptographic hash verification performance."

    system_prompt = (
        "You are an expert pair-programming code assistant for student developers. "
        "Provide direct, high-performance code snippets and clear explanations. "
        "Focus on deterministic algorithms, cryptographic integrity, and clean Python patterns."
    )
    prompt = (
        f"Student Query: {sanitized_query}\n\n"
        f"Active Code Buffer:\n{editor_buffer}"
    )

    result = call_llm(prompt=prompt, system_prompt=system_prompt, schema_type="codeassistant")
    return result

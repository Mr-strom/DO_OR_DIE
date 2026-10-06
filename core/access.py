PRIVACY_MATRIX = {
    "public_summary": {"Student": True, "Mentor": True, "Sponsor": True},
    "confidential_brief": {"Student": False, "Mentor": True, "Sponsor": True},
    "budget_escrow": {"Student": False, "Mentor": True, "Sponsor": True},
    "student_scratchpad": {"Student": True, "Mentor": False, "Sponsor": False},
    "mentor_notes": {"Student": False, "Mentor": True, "Sponsor": False},
    "code_repo": {"Student": True, "Mentor": True, "Sponsor": False},
    "team_chat": {"Student": True, "Mentor": True, "Sponsor": False},
    "sponsor_channel": {"Student": False, "Mentor": True, "Sponsor": True},
    "milestone_progress": {"Student": True, "Mentor": True, "Sponsor": True},
    "ledger_all": {"Student": False, "Mentor": True, "Sponsor": False},
    "ledger_payout_only": {"Student": False, "Mentor": False, "Sponsor": True},
}

def can(role: str, resource: str) -> bool:
    """Checks role clearance for a given data slice."""
    return PRIVACY_MATRIX.get(resource, {}).get(role, False)

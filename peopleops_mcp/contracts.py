from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolContract:
    name: str
    purpose: str
    requires_confirmation: bool = False


REQUIRED_TOOL_CONTRACTS = (
    ToolContract("search_policy_documents", "Search grounded policy evidence."),
    ToolContract("get_policy_section", "Retrieve an exact policy section."),
    ToolContract("lookup_employee_profile", "Retrieve a synthetic employee profile."),
    ToolContract("check_pto_balance", "Check a synthetic PTO balance and requested days."),
    ToolContract("lookup_benefits_status", "Retrieve synthetic benefits status."),
    ToolContract("check_policy_compliance", "Evaluate deterministic workflow rules."),
    ToolContract("draft_hr_email", "Return a non-persistent, clearly labelled draft."),
    ToolContract(
        "create_mock_hr_ticket",
        "Create a synthetic ticket after explicit confirmation.",
        requires_confirmation=True,
    ),
)

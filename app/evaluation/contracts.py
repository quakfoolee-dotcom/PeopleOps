from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.api.contracts import ContractModel, WorkflowKind, WorkflowOutcome


class EvaluationCategory(StrEnum):
    STRAIGHTFORWARD_POLICY = "straightforward_policy"
    MULTI_DOCUMENT_POLICY = "multi_document_policy"
    EMPLOYEE_TOOL_WORKFLOW = "employee_tool_workflow"
    AMBIGUOUS_CLARIFICATION = "ambiguous_clarification"
    OUT_OF_SCOPE_SAFETY = "out_of_scope_safety"


class PolicySectionTarget(ContractModel):
    policy_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")
    section_id: str = Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")


class AnswerCheck(ContractModel):
    mode: Literal[
        "contains_all",
        "contains_any",
        "contains_none",
        "starts_with_any",
        "citation_sections",
        "tools_present",
        "tools_absent",
        "pending_action",
        "email_draft",
        "outcome",
    ]
    values: list[str] = Field(min_length=1)
    supporting_sections: list[PolicySectionTarget] = Field(default_factory=list)
    supporting_tools: list[str] = Field(default_factory=list)

    @field_validator("values", "supporting_tools")
    @classmethod
    def require_unique_check_values(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("answer-check values cannot contain blanks")
        if len(value) != len(set(value)):
            raise ValueError("answer-check values cannot contain duplicates")
        return value


class CaseAnswerChecks(ContractModel):
    case_id: str = Field(pattern=r"^EVAL-[A-Z]+-\d{3}$")
    fact_checks: list[AnswerCheck] = Field(min_length=1)
    constraint_checks: list[AnswerCheck] = Field(min_length=1)


class AnswerCheckSuite(ContractModel):
    schema_version: Literal["1.0"]
    cases: list[CaseAnswerChecks] = Field(min_length=25, max_length=25)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> "AnswerCheckSuite":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("answer-check case IDs must be unique")
        return self


class IntentRobustnessCase(ContractModel):
    case_id: str = Field(pattern=r"^INTENT-\d{3}$")
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=1000)
    supplied_employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    expected_kind: WorkflowKind
    expected_fields: dict[str, str | int | bool | None] = Field(default_factory=dict)
    clarification_contains: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("clarification_contains", "tags")
    @classmethod
    def require_unique_intent_values(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("intent values cannot contain blanks")
        if len(value) != len(set(value)):
            raise ValueError("intent values cannot contain duplicates")
        return value


class IntentRobustnessSuite(ContractModel):
    schema_version: Literal["1.0"]
    cases: list[IntentRobustnessCase] = Field(min_length=15, max_length=15)

    @model_validator(mode="after")
    def require_unique_intent_case_ids(self) -> "IntentRobustnessSuite":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("intent-robustness case IDs must be unique")
        return self


class ToolExpectations(ContractModel):
    required: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    after_confirmation: list[str] = Field(default_factory=list)

    @field_validator("required", "forbidden", "after_confirmation")
    @classmethod
    def require_unique_tool_names(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("tool lists cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def require_disjoint_tool_sets(self) -> "ToolExpectations":
        sets = [set(self.required), set(self.forbidden), set(self.after_confirmation)]
        if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
            raise ValueError("required, forbidden, and after-confirmation tools must be disjoint")
        return self


class GoldEvaluationCase(ContractModel):
    case_id: str = Field(pattern=r"^EVAL-[A-Z]+-\d{3}$")
    title: str = Field(min_length=1, max_length=200)
    category: EvaluationCategory
    prompt: str = Field(min_length=1, max_length=4000)
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    expected_facts: list[str] = Field(min_length=1)
    expected_policy_sections: list[PolicySectionTarget]
    tools: ToolExpectations
    expected_outcome: WorkflowOutcome
    answer_constraints: list[str] = Field(min_length=1)
    safety_behavior: list[str] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    @field_validator(
        "expected_facts", "answer_constraints", "safety_behavior", "tags"
    )
    @classmethod
    def require_unique_nonempty_strings(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("string lists cannot contain blank entries")
        if len(value) != len(set(value)):
            raise ValueError("string lists cannot contain duplicates")
        return value


class GoldEvaluationSuite(ContractModel):
    schema_version: Literal["1.0"]
    name: str = Field(min_length=1, max_length=200)
    organization: Literal["Northstar Technologies Inc."]
    synthetic_only: Literal[True]
    as_of_date: date
    cases: list[GoldEvaluationCase] = Field(min_length=25, max_length=25)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> "GoldEvaluationSuite":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("gold case IDs must be unique")
        return self

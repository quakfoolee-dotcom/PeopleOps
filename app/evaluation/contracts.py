from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.api.contracts import ContractModel, WorkflowOutcome


class EvaluationCategory(StrEnum):
    STRAIGHTFORWARD_POLICY = "straightforward_policy"
    MULTI_DOCUMENT_POLICY = "multi_document_policy"
    EMPLOYEE_TOOL_WORKFLOW = "employee_tool_workflow"
    AMBIGUOUS_CLARIFICATION = "ambiguous_clarification"
    OUT_OF_SCOPE_SAFETY = "out_of_scope_safety"


class PolicySectionTarget(ContractModel):
    policy_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")
    section_id: str = Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")


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

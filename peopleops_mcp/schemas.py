from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MCPModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmployeeLocation(MCPModel):
    location_id: str
    name: str
    city: str
    province_or_state: str
    country_code: str
    timezone: str


class EmployeeProfile(MCPModel):
    employee_id: str
    synthetic_name: str
    employment_type: str
    role: str
    department: str
    manager_id: str | None
    remote_work_classification: str
    employment_status: str
    hire_date: date
    home_office: EmployeeLocation


class EmployeeProfileResult(MCPModel):
    employee_id: str
    as_of_date: date
    found: bool
    profile: EmployeeProfile | None = None


class PolicyEvidence(MCPModel):
    policy_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")
    section_id: str = Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")
    title: str
    snippet: str = Field(min_length=1, max_length=1000)
    version: str
    source_format: Literal["markdown", "pdf"]
    source_path: str


class PolicySearchResult(MCPModel):
    query: str
    retrieval_mode: Literal["phase4_deterministic_keyword"]
    sufficient_evidence: bool
    matches: list[PolicyEvidence]
    limitation: str

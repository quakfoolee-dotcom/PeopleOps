import json
import re
from functools import lru_cache

from app.core.config import PROJECT_ROOT
from app.data.store import load_seed_bundle
from peopleops_mcp.schemas import (
    EmployeeLocation,
    EmployeeProfile,
    EmployeeProfileResult,
    PolicyEvidence,
    PolicySearchResult,
)

POLICY_DIRECTORY = PROJECT_ROOT / "policy_corpus"
POLICY_MANIFEST = POLICY_DIRECTORY / "corpus_docs" / "policy_manifest.json"
SECTION_HEADING = re.compile(
    r"^## (?P<section_id>[A-Z]{3}-\d+(?:\.\d+)?)\. (?P<title>.+)$",
    re.MULTILINE,
)


@lru_cache
def _policy_manifest() -> dict[str, dict[str, object]]:
    raw_manifest = json.loads(POLICY_MANIFEST.read_text(encoding="utf-8"))
    return {policy["policy_id"]: policy for policy in raw_manifest["policies"]}


def _section(policy_id: str, section_id: str) -> PolicyEvidence:
    policy = _policy_manifest()[policy_id]
    source_path = str(policy["runtime_source"])
    master_path = POLICY_DIRECTORY / str(policy["master_source"])
    content = master_path.read_text(encoding="utf-8")
    headings = list(SECTION_HEADING.finditer(content))
    heading = next(match for match in headings if match.group("section_id") == section_id)
    heading_index = headings.index(heading)
    end = headings[heading_index + 1].start() if heading_index + 1 < len(headings) else len(content)
    body = content[heading.end() : end].strip()
    snippet = re.sub(r"\s+", " ", body).strip()
    if len(snippet) > 997:
        snippet = snippet[:997].rstrip() + "..."
    return PolicyEvidence(
        policy_id=policy_id,
        section_id=section_id,
        title=f"{policy['title']} — {heading.group('title')}",
        snippet=snippet,
        version=str(policy["version"]),
        source_format=str(policy["runtime_format"]),
        source_path=f"policy_corpus/{source_path}",
    )


def lookup_employee_profile_data(employee_id: str) -> EmployeeProfileResult:
    bundle = load_seed_bundle()
    employee = next((item for item in bundle.employees if item.employee_id == employee_id), None)
    if employee is None:
        return EmployeeProfileResult(
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            found=False,
        )

    location = next(
        item for item in bundle.locations if item.location_id == employee.home_office_id
    )
    return EmployeeProfileResult(
        employee_id=employee_id,
        as_of_date=bundle.manifest.as_of_date,
        found=True,
        profile=EmployeeProfile(
            employee_id=employee.employee_id,
            synthetic_name=employee.synthetic_name,
            employment_type=employee.employment_type.value,
            role=employee.role,
            department=employee.department,
            manager_id=employee.manager_id,
            remote_work_classification=employee.remote_work_classification.value,
            employment_status=employee.status.value,
            hire_date=employee.hire_date,
            home_office=EmployeeLocation(
                location_id=location.location_id,
                name=location.name,
                city=location.city,
                province_or_state=location.province_or_state,
                country_code=location.country_code,
                timezone=location.timezone,
            ),
        ),
    )


def search_policy_documents_data(query: str) -> PolicySearchResult:
    normalized = query.casefold()
    international_terms = (
        "germany",
        "international",
        "another country",
        "outside canada",
        "outside the country",
        "out-of-jurisdiction",
    )
    remote_terms = ("remote", "work from", "working from", "work abroad")
    is_international_remote = any(term in normalized for term in international_terms) and any(
        term in normalized for term in remote_terms
    )

    matches = []
    if is_international_remote:
        matches = [
            _section("POL-INT-001", "INT-4"),
            _section("POL-INT-001", "INT-5"),
            _section("POL-INT-001", "INT-13"),
            _section("POL-RWK-001", "RWK-5"),
        ]

    return PolicySearchResult(
        query=query,
        retrieval_mode="phase4_deterministic_keyword",
        sufficient_evidence=bool(matches),
        matches=matches,
        limitation=(
            "Phase 4 supports the international remote-work demonstration. "
            "Hybrid semantic and keyword retrieval is implemented in Phase 5."
        ),
    )

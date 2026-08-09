from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.data.store import load_seed_bundle
from app.rag.citations import citation_snippet, validate_retrieved_hits
from app.rag.index import cached_index
from app.rag.retrieval import HybridRetriever
from peopleops_mcp.schemas import (
    EmployeeLocation,
    EmployeeProfile,
    EmployeeProfileResult,
    PolicyEvidence,
    PolicySearchResult,
)


@lru_cache(maxsize=1)
def _retriever() -> HybridRetriever:
    settings = get_settings()
    index = cached_index(
        settings.policy_corpus_directory.resolve(),
        settings.rag_index_path.resolve(),
        settings.rag_embedding_dimensions,
        settings.rag_chunk_target_words,
        settings.rag_chunk_overlap_words,
    )
    return HybridRetriever(index)


def clear_rag_caches() -> None:
    _retriever.cache_clear()
    cached_index.cache_clear()


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
    settings = get_settings()
    retriever = _retriever()
    result = retriever.search(query, top_k=settings.rag_top_k)
    validate_retrieved_hits(retriever.index, result.hits)
    matches = [
        PolicyEvidence(
            policy_id=hit.chunk.policy_id,
            section_id=hit.chunk.section_id,
            title=f"{hit.chunk.policy_title} — {hit.chunk.section_title}",
            snippet=citation_snippet(hit.chunk.text),
            version=hit.chunk.version,
            effective_date=hit.chunk.effective_date,
            source_format=hit.chunk.source_format,
            source_path=hit.chunk.source_path,
            page=hit.chunk.page,
            chunk_id=hit.chunk.chunk_id,
            retrieval_score=hit.score,
        )
        for hit in result.hits
    ]
    return PolicySearchResult(
        query=query,
        retrieval_mode=result.mode,
        index_version=retriever.index.index_version,
        evidence_rule=result.evidence_rule,
        sufficient_evidence=result.sufficient_evidence,
        matches=matches,
        missing_policy_ids=list(result.missing_policy_ids),
        conflicts=list(result.conflicts),
        limitation=result.limitation,
    )

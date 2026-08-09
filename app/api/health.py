from fastapi import APIRouter

from app.api.schemas import ComponentStatus, HealthResponse
from app.core.config import get_settings
from app.data.store import load_seed_bundle, validate_seed_directory
from app.providers import get_llm_provider
from app.rag.corpus import validate_corpus
from app.rag.index import cached_index
from peopleops_mcp.server import PHASE6_TOOL_NAMES

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    corpus = validate_corpus(
        settings.policy_corpus_directory,
        as_of_date=settings.synthetic_as_of_date,
    )
    corpus_ready = corpus["ready"]
    mock_data_errors = validate_seed_directory(
        expected_as_of_date=settings.synthetic_as_of_date
    )
    mock_data_ready = not mock_data_errors
    employee_count = len(load_seed_bundle().employees) if mock_data_ready else 0
    try:
        rag_index = cached_index(
            settings.policy_corpus_directory.resolve(),
            settings.rag_index_path.resolve(),
            settings.rag_embedding_dimensions,
            settings.rag_chunk_target_words,
            settings.rag_chunk_overlap_words,
        )
        rag_ready = rag_index.policy_count == 12 and rag_index.section_count >= 160
        rag_detail = (
            f"{rag_index.index_version} ready with {rag_index.policy_count} policies, "
            f"{rag_index.section_count} sections, and {len(rag_index.indexed_chunks)} chunks."
        )
    except Exception as error:
        rag_ready = False
        rag_detail = f"RAG index unavailable: {type(error).__name__}: {error}"

    provider_health = await get_llm_provider().health()
    core_ready = corpus_ready and mock_data_ready and rag_ready

    return HealthResponse(
        status=(
            "ok"
            if core_ready and provider_health.status != "error"
            else "degraded"
        ),
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        release_sha=settings.app_release_sha,
        components={
            "application": ComponentStatus(status="ready", detail="FastAPI is serving requests."),
            "policy_corpus": ComponentStatus(
                status="ready" if corpus_ready else "error",
                detail=corpus["detail"],
            ),
            "rag_index": ComponentStatus(
                status="ready" if rag_ready else "error", detail=rag_detail
            ),
            "mcp": ComponentStatus(
                status="ready",
                detail=(
                    "Streamable HTTP transport is mounted at /mcp with "
                    f"{len(PHASE6_TOOL_NAMES)} discoverable tools serving the "
                    "Phase 8 product interface."
                ),
            ),
            "mock_database": ComponentStatus(
                status="ready" if mock_data_ready else "error",
                detail=(
                    f"{employee_count} deterministic synthetic employee records validated."
                    if mock_data_ready
                    else "; ".join(mock_data_errors)
                ),
            ),
            "llm_provider": ComponentStatus(
                status=provider_health.status,
                detail=provider_health.detail,
            ),
        },
    )

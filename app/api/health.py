from fastapi import APIRouter

from app.api.schemas import ComponentStatus, HealthResponse
from app.core.config import get_settings
from app.rag.corpus import validate_corpus

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    corpus = validate_corpus(settings.policy_corpus_directory)
    corpus_ready = corpus["ready"]

    return HealthResponse(
        status="ok" if corpus_ready else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        components={
            "application": ComponentStatus(status="ready", detail="FastAPI is serving requests."),
            "policy_corpus": ComponentStatus(
                status="ready" if corpus_ready else "error",
                detail=corpus["detail"],
            ),
            "rag_index": ComponentStatus(
                status="planned", detail="Ingestion and retrieval are planned for Phase 5."
            ),
            "mcp": ComponentStatus(
                status="planned",
                detail="Tool contracts exist; live discovery and invocation begin in Phase 4.",
            ),
            "mock_database": ComponentStatus(
                status="planned", detail="Synthetic structured records are planned for Phase 3."
            ),
            "llm_provider": ComponentStatus(
                status="not_configured",
                detail=f"Provider setting is {settings.llm_provider!r}.",
            ),
        },
    )

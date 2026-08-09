from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends

from app.agent import PeopleOpsOrchestrator
from app.api.contracts import ChatRequest, ChatResponse

router = APIRouter(tags=["assistant"])


@lru_cache
def get_orchestrator() -> PeopleOpsOrchestrator:
    return PeopleOpsOrchestrator()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestrator: Annotated[PeopleOpsOrchestrator, Depends(get_orchestrator)],
) -> ChatResponse:
    """Run the bounded Phase 4 international remote-work workflow."""
    return await orchestrator.run(request)

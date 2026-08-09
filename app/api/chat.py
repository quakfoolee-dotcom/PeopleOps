from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends

from app.agent import PeopleOpsOrchestrator
from app.api.actions import get_ticket_confirmation_coordinator
from app.api.contracts import ChatRequest, ChatResponse

router = APIRouter(tags=["assistant"])


@lru_cache
def get_orchestrator() -> PeopleOpsOrchestrator:
    return PeopleOpsOrchestrator(
        ticket_actions=get_ticket_confirmation_coordinator(),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestrator: Annotated[PeopleOpsOrchestrator, Depends(get_orchestrator)],
) -> ChatResponse:
    """Run a bounded typed PeopleOps workflow through MCP and hybrid RAG."""
    return await orchestrator.run(request)

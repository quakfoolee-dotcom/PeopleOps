from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.contracts import ConfirmMockTicketRequest, ConfirmMockTicketResponse
from app.services import MockTicketConfirmationCoordinator

router = APIRouter(prefix="/actions/mock-tickets", tags=["actions"])


@lru_cache
def get_ticket_confirmation_coordinator() -> MockTicketConfirmationCoordinator:
    return MockTicketConfirmationCoordinator()


@router.post("/confirm", response_model=ConfirmMockTicketResponse)
async def confirm_mock_ticket(
    request: ConfirmMockTicketRequest,
    coordinator: Annotated[
        MockTicketConfirmationCoordinator,
        Depends(get_ticket_confirmation_coordinator),
    ],
) -> ConfirmMockTicketResponse:
    """Record explicit confirmation and return proof bound to the unchanged preview."""
    try:
        token = coordinator.confirm(
            request.confirmation_id,
            user_confirmed=request.user_confirmed,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return ConfirmMockTicketResponse(
        confirmation_id=request.confirmation_id,
        confirmation_token=token,
    )

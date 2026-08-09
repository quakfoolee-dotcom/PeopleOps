"""Application services that sit outside the bounded agent data-access boundary."""

from app.services.mock_tickets import MockTicketConfirmationCoordinator

__all__ = ["MockTicketConfirmationCoordinator"]

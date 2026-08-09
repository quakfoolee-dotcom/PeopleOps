from peopleops_mcp.actions import (
    confirm_mock_ticket_action,
    prepare_mock_ticket_action,
)
from peopleops_mcp.schemas import MockTicketPreview


class MockTicketConfirmationCoordinator:
    """Coordinate explicit user confirmation; the create operation still runs only through MCP."""

    def prepare(
        self,
        *,
        category: str,
        priority: str,
        summary: str,
        affected_employee_id: str,
        idempotency_key: str,
    ) -> MockTicketPreview:
        return prepare_mock_ticket_action(
            category=category,
            priority=priority,
            summary=summary,
            affected_employee_id=affected_employee_id,
            idempotency_key=idempotency_key,
        )

    def confirm(self, confirmation_id: str, *, user_confirmed: bool) -> str:
        return confirm_mock_ticket_action(
            confirmation_id,
            user_confirmed=user_confirmed,
        )

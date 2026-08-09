from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from app.core.config import get_settings
from app.data.store import load_seed_bundle
from peopleops_mcp.schemas import (
    MockTicketActionResult,
    MockTicketPreview,
    MockTicketRecord,
)

CATEGORY_ROUTES = {
    "workplace_concern": "People Operations",
    "benefits": "Benefits",
    "leave": "Leave Administration",
    "payroll": "Payroll",
    "equipment": "People Operations",
    "onboarding": "People Operations",
    "other": "People Operations",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _action_fingerprint(preview: MockTicketPreview) -> str:
    action = preview.model_dump(
        mode="json",
        exclude={"confirmation_id", "expires_at", "confirmed", "synthetic_only"},
    )
    canonical = json.dumps(action, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class _PendingConfirmation:
    preview: MockTicketPreview
    fingerprint: str
    confirmed: bool = False


class MockTicketActionStore:
    """Keep confirmation state and mock writes process-local and idempotent."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._pending: dict[str, _PendingConfirmation] = {}
        self._created: dict[str, tuple[str, MockTicketRecord]] = {}
        self._next_ticket_number = 9001

    def prepare(
        self,
        *,
        category: str,
        priority: str,
        summary: str,
        affected_employee_id: str,
        idempotency_key: str,
    ) -> MockTicketPreview:
        bundle = load_seed_bundle()
        if not any(item.employee_id == affected_employee_id for item in bundle.employees):
            raise ValueError(f"synthetic employee {affected_employee_id} was not found")
        if category not in CATEGORY_ROUTES:
            raise ValueError(f"unsupported ticket category: {category}")

        now = _utc_now()
        confirmation_id = "PREVIEW-" + hashlib.sha256(
            f"{idempotency_key}:{secrets.token_hex(16)}".encode()
        ).hexdigest()[:16].upper()
        preview = MockTicketPreview(
            confirmation_id=confirmation_id,
            category=category,
            priority=priority,
            summary=summary,
            affected_employee_id=affected_employee_id,
            routing_team=CATEGORY_ROUTES[category],
            idempotency_key=idempotency_key,
            expires_at=now
            + timedelta(seconds=get_settings().mcp_confirmation_ttl_seconds),
        )
        with self._lock:
            self._pending[confirmation_id] = _PendingConfirmation(
                preview=preview,
                fingerprint=_action_fingerprint(preview),
            )
        return preview

    def confirm(self, confirmation_id: str, *, user_confirmed: bool) -> str:
        if not user_confirmed:
            raise ValueError("explicit user confirmation is required")
        with self._lock:
            pending = self._pending.get(confirmation_id)
            if pending is None:
                raise ValueError("confirmation preview is unknown or expired")
            if pending.preview.expires_at <= _utc_now():
                self._pending.pop(confirmation_id, None)
                raise ValueError("confirmation preview has expired")
            pending.confirmed = True
            payload = {
                "c": confirmation_id,
                "e": int(pending.preview.expires_at.timestamp()),
                "f": pending.fingerprint[:32],
            }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(
            get_settings().mcp_confirmation_secret.encode("utf-8"),
            serialized,
            hashlib.sha256,
        ).digest()
        return f"{_encode(serialized)}.{_encode(signature)}"

    def create(
        self,
        *,
        category: str,
        priority: str,
        summary: str,
        affected_employee_id: str,
        idempotency_key: str,
        confirmation_token: str,
    ) -> MockTicketActionResult:
        try:
            payload_segment, signature_segment = confirmation_token.split(".", maxsplit=1)
            serialized = _decode(payload_segment)
            supplied_signature = _decode(signature_segment)
            payload = json.loads(serialized)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("confirmation token is malformed") from error

        expected_signature = hmac.new(
            get_settings().mcp_confirmation_secret.encode("utf-8"),
            serialized,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("confirmation token signature is invalid")
        if not isinstance(payload, dict) or set(payload) != {"c", "e", "f"}:
            raise ValueError("confirmation token payload is invalid")
        if int(payload["e"]) <= int(_utc_now().timestamp()):
            raise ValueError("confirmation token has expired")

        confirmation_id = str(payload["c"])
        with self._lock:
            pending = self._pending.get(confirmation_id)
            if pending is None or not pending.confirmed:
                raise ValueError("explicit confirmation has not been recorded")
            preview = pending.preview
            supplied_preview = MockTicketPreview(
                confirmation_id=preview.confirmation_id,
                category=category,
                priority=priority,
                summary=summary,
                affected_employee_id=affected_employee_id,
                routing_team=CATEGORY_ROUTES.get(category, ""),
                idempotency_key=idempotency_key,
                expires_at=preview.expires_at,
            )
            supplied_fingerprint = _action_fingerprint(supplied_preview)
            if (
                payload["f"] != supplied_fingerprint[:32]
                or supplied_fingerprint != pending.fingerprint
            ):
                raise ValueError("confirmed action does not match the ticket preview")

            if existing := self._created.get(idempotency_key):
                existing_fingerprint, record = existing
                if existing_fingerprint != supplied_fingerprint:
                    raise ValueError("idempotency key was already used for a different action")
                return MockTicketActionResult(
                    action_status="already_created",
                    ticket=record,
                    limitation=(
                        "Synthetic demonstration record only; no production HR system was updated."
                    ),
                )

            ticket_number = self._next_ticket_number
            self._next_ticket_number += 1
            record = MockTicketRecord(
                ticket_id=f"TKT-{ticket_number:04d}",
                category=category,
                priority=priority,
                summary=summary,
                affected_employee_id=affected_employee_id,
                routing_team=preview.routing_team,
                created_at=_utc_now(),
                confirmation_reference=f"CONF-{ticket_number:04d}",
            )
            self._created[idempotency_key] = (supplied_fingerprint, record)
            return MockTicketActionResult(
                action_status="created",
                ticket=record,
                limitation=(
                    "Synthetic demonstration record only; no production HR system was updated."
                ),
            )

    def reset(self) -> None:
        with self._lock:
            self._pending.clear()
            self._created.clear()
            self._next_ticket_number = 9001


mock_ticket_actions = MockTicketActionStore()


def prepare_mock_ticket_action(
    *,
    category: str,
    priority: str,
    summary: str,
    affected_employee_id: str,
    idempotency_key: str,
) -> MockTicketPreview:
    return mock_ticket_actions.prepare(
        category=category,
        priority=priority,
        summary=summary,
        affected_employee_id=affected_employee_id,
        idempotency_key=idempotency_key,
    )


def confirm_mock_ticket_action(confirmation_id: str, *, user_confirmed: bool) -> str:
    return mock_ticket_actions.confirm(confirmation_id, user_confirmed=user_confirmed)


def reset_mock_ticket_actions() -> None:
    mock_ticket_actions.reset()

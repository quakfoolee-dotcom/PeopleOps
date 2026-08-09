import asyncio

from scripts.evaluate_mcp_tools import evaluate


def test_phase6_machine_readable_validation_passes() -> None:
    result = asyncio.run(evaluate())

    assert result["passed"] is True
    assert result["discovered_tool_count"] == 8
    assert result["successful_tool_calls"] == 8
    assert result["confirmation_gate_rejected_unsigned"] is True
    assert result["idempotent_repeat_status"] == "already_created"
    assert result["confirmation_token_present_in_trace"] is False
    assert result["ticket_seed_unchanged"] is True

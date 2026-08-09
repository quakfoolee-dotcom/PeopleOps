import asyncio

from scripts.evaluate_workflows import evaluate


def test_phase7_machine_readable_evaluation_passes() -> None:
    result = asyncio.run(evaluate())

    assert result["passed"] is True
    assert result["remote_work"]["repeat_count"] == 3
    assert result["pto"]["repeat_count"] == 3
    assert all(result["safety"].values())
    assert result["confirmation"]["create_called_before_confirmation"] is False
    assert result["confirmation"]["idempotent_repeat"] is True
    assert result["confirmation"]["confirmation_token_present_in_trace"] is False
    assert result["confirmation"]["ticket_seed_unchanged"] is True

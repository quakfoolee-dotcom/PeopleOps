from app.evaluation.intent_robustness import (
    evaluate_intent_robustness,
    load_intent_suite,
)


def test_intent_robustness_suite_is_versioned_and_complete() -> None:
    suite = load_intent_suite()

    assert suite.schema_version == "1.0"
    assert len(suite.cases) == 15
    assert {case.case_id for case in suite.cases} == {
        f"INTENT-{index:03d}" for index in range(1, 16)
    }


def test_intent_robustness_gate_passes() -> None:
    result = evaluate_intent_robustness()

    assert result["target_met"] is True
    assert result["metrics"]["routing_and_extraction_accuracy"] == 1.0
    assert result["error_analysis"] == []

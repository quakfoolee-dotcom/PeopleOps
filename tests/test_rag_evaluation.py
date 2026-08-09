from scripts.evaluate_rag import evaluate


def test_selected_hybrid_configuration_meets_gold_evidence_recall_target() -> None:
    result = evaluate("hybrid", 8)

    assert result["evaluated_cases"] == 24
    assert result["expected_sections"] == 48
    assert result["retrieved_expected_sections"] == 48
    assert result["evidence_recall"] >= 0.95

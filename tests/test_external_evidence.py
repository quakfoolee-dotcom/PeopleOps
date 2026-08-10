from scripts.evaluate_embeddings import check_committed as check_embeddings
from scripts.evaluate_hosted_provider import check_committed as check_hosted_provider


def test_embedding_comparison_evidence_is_current() -> None:
    passed, message = check_embeddings()

    assert passed, message


def test_hosted_provider_evidence_has_safe_workflow_integrity() -> None:
    passed, message = check_hosted_provider()

    assert passed, message

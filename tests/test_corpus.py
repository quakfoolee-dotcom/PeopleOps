from datetime import date
from pathlib import Path

from app.rag.corpus import load_manifest, validate_corpus

CORPUS_DIRECTORY = Path(__file__).resolve().parents[1] / "policy_corpus"


def test_policy_manifest_is_synthetic_and_complete() -> None:
    manifest = load_manifest(CORPUS_DIRECTORY)

    assert manifest["synthetic"] is True
    assert manifest["policy_count"] == 12
    assert set(manifest["supported_runtime_formats"]) == {"markdown", "pdf"}
    assert len(manifest["policies"]) == 12
    assert all(policy["applicability"] for policy in manifest["policies"])


def test_all_declared_runtime_sources_exist() -> None:
    result = validate_corpus(CORPUS_DIRECTORY, as_of_date=date(2026, 9, 1))

    assert result["ready"] is True, result["detail"]
    assert result["errors"] == []
    assert "45 estimated pages" in result["detail"]


def test_corpus_rejects_policies_that_are_not_yet_effective() -> None:
    result = validate_corpus(CORPUS_DIRECTORY, as_of_date=date(2026, 8, 31))

    assert result["ready"] is False
    assert len(result["errors"]) == 12
    assert all("is not effective" in error for error in result["errors"])


def test_corpus_reports_an_unavailable_manifest() -> None:
    result = validate_corpus(CORPUS_DIRECTORY.parent / "tmp" / "missing-corpus")

    assert result["ready"] is False
    assert "manifest unavailable" in result["detail"]

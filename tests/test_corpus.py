from pathlib import Path

from app.rag.corpus import load_manifest, validate_corpus

CORPUS_DIRECTORY = Path(__file__).resolve().parents[1] / "policy_corpus"


def test_policy_manifest_is_synthetic_and_complete() -> None:
    manifest = load_manifest(CORPUS_DIRECTORY)

    assert manifest["synthetic"] is True
    assert manifest["policy_count"] == 12
    assert set(manifest["supported_runtime_formats"]) == {"markdown", "pdf"}
    assert len(manifest["policies"]) == 12


def test_all_declared_runtime_sources_exist() -> None:
    result = validate_corpus(CORPUS_DIRECTORY)

    assert result["ready"] is True, result["detail"]

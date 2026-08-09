from dataclasses import replace
from pathlib import Path

from app.rag.embeddings import LocalHashEmbedding, cosine_similarity
from app.rag.index import build_index, load_index
from app.rag.retrieval import detect_index_conflicts

CORPUS = Path(__file__).resolve().parents[1] / "policy_corpus"


def test_committed_index_preserves_deterministic_metadata() -> None:
    index = build_index(CORPUS)
    loaded = load_index(CORPUS / "index" / "phase5_index.json")

    assert loaded.to_dict() == index.to_dict()
    assert loaded.embedding_model == "peopleops-local-hash-v2"
    assert loaded.embedding_dimensions == 384
    assert loaded.policy_count == 12
    assert loaded.section_count == 169
    assert loaded.source_format_counts == {"markdown": 138, "pdf": 31}


def test_local_embeddings_are_deterministic_and_normalize_domain_aliases() -> None:
    model = LocalHashEmbedding()
    vacation = model.embed("vacation request")
    pto = model.embed("PTO request")

    assert model.embed("vacation request") == vacation
    assert cosine_similarity(vacation, pto) > 0.99
    assert abs(cosine_similarity(vacation, vacation) - 1.0) < 0.000001


def test_conflict_detection_rejects_multiple_versions_or_authoritative_texts() -> None:
    chunks = build_index(CORPUS).chunks
    original = chunks[0]
    changed_version = replace(original, version="2.0")
    changed_text = replace(original, text=f"{original.text} Contradictory replacement.")

    conflicts = detect_index_conflicts((original, changed_version, changed_text))

    assert any("multiple retrieved versions" in conflict for conflict in conflicts)
    assert any("inconsistent authoritative text" in conflict for conflict in conflicts)

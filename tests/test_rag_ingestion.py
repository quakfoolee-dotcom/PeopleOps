from pathlib import Path

import pytest

from app.rag.ingestion import ingest_policy_corpus

CORPUS = Path(__file__).resolve().parents[1] / "policy_corpus"


def test_ingestion_uses_only_authoritative_markdown_and_pdf_sources() -> None:
    chunks = ingest_policy_corpus(CORPUS)

    assert len(chunks) == 169
    assert len({chunk.chunk_id for chunk in chunks}) == 169
    assert len({chunk.policy_id for chunk in chunks}) == 12
    assert len({(chunk.policy_id, chunk.section_id) for chunk in chunks}) == 169
    assert {chunk.source_format for chunk in chunks} == {"markdown", "pdf"}
    assert all("policy_corpus/runtime_corpus/" in chunk.source_path for chunk in chunks)
    assert all("master_markdown" not in chunk.source_path for chunk in chunks)
    assert all("review_pdfs" not in chunk.source_path for chunk in chunks)


def test_pdf_ingestion_preserves_section_and_page_metadata_without_toc_noise() -> None:
    pdf_chunks = [
        chunk for chunk in ingest_policy_corpus(CORPUS) if chunk.source_format == "pdf"
    ]

    assert len(pdf_chunks) == 31
    assert all(chunk.page is not None for chunk in pdf_chunks)
    assert {chunk.policy_id for chunk in pdf_chunks} == {"POL-CON-001", "POL-HRC-001"}
    hrc_confirmation = next(chunk for chunk in pdf_chunks if chunk.section_id == "HRC-8")
    assert hrc_confirmation.page == 4
    assert "create_mock_hr_ticket" in hrc_confirmation.text
    assert "Contents" not in hrc_confirmation.text
    assert ". . . ." not in hrc_confirmation.text


def test_oversized_sections_split_with_stable_ordinals() -> None:
    chunks = ingest_policy_corpus(CORPUS, target_words=80, overlap_words=10)

    assert len(chunks) > 169
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert any(chunk.chunk_id.endswith("::02") for chunk in chunks)
    assert len({(chunk.policy_id, chunk.section_id) for chunk in chunks}) == 169


@pytest.mark.parametrize(
    ("target_words", "overlap_words"),
    ((79, 10), (100, -1), (100, 100)),
)
def test_ingestion_rejects_invalid_chunk_configuration(
    target_words: int, overlap_words: int
) -> None:
    with pytest.raises(ValueError, match="invalid chunk-size"):
        ingest_policy_corpus(
            CORPUS,
            target_words=target_words,
            overlap_words=overlap_words,
        )

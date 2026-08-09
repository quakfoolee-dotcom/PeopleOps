from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.rag.corpus import load_manifest
from app.rag.embeddings import LocalHashEmbedding, tokenize
from app.rag.ingestion import ingest_policy_corpus
from app.rag.models import IndexedChunk, PolicyChunk

INDEX_VERSION = "phase5-hybrid-v2"


def corpus_fingerprint(corpus_directory: Path) -> str:
    manifest = load_manifest(corpus_directory)
    digest = hashlib.sha256()
    digest.update(json.dumps(manifest, sort_keys=True).encode("utf-8"))
    for policy in sorted(manifest["policies"], key=lambda item: item["policy_id"]):
        source = corpus_directory / str(policy["runtime_source"])
        digest.update(str(policy["runtime_source"]).encode("utf-8"))
        digest.update(source.read_bytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class HybridIndex:
    index_version: str
    corpus_fingerprint: str
    embedding_model: str
    embedding_dimensions: int
    target_words: int
    overlap_words: int
    indexed_chunks: tuple[IndexedChunk, ...]

    @property
    def chunks(self) -> tuple[PolicyChunk, ...]:
        return tuple(item.chunk for item in self.indexed_chunks)

    @property
    def policy_count(self) -> int:
        return len({chunk.policy_id for chunk in self.chunks})

    @property
    def section_count(self) -> int:
        return len({(chunk.policy_id, chunk.section_id) for chunk in self.chunks})

    @property
    def source_format_counts(self) -> dict[str, int]:
        counts = Counter(chunk.source_format for chunk in self.chunks)
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_version": self.index_version,
            "corpus_fingerprint": self.corpus_fingerprint,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "target_words": self.target_words,
            "overlap_words": self.overlap_words,
            "policy_count": self.policy_count,
            "section_count": self.section_count,
            "chunk_count": len(self.indexed_chunks),
            "source_format_counts": self.source_format_counts,
            "chunks": [item.to_dict() for item in self.indexed_chunks],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> HybridIndex:
        indexed_chunks = tuple(IndexedChunk.from_dict(item) for item in value["chunks"])
        index = cls(
            index_version=str(value["index_version"]),
            corpus_fingerprint=str(value["corpus_fingerprint"]),
            embedding_model=str(value["embedding_model"]),
            embedding_dimensions=int(value["embedding_dimensions"]),
            target_words=int(value["target_words"]),
            overlap_words=int(value["overlap_words"]),
            indexed_chunks=indexed_chunks,
        )
        declared = {
            "policy_count": index.policy_count,
            "section_count": index.section_count,
            "chunk_count": len(index.indexed_chunks),
            "source_format_counts": index.source_format_counts,
        }
        for key, actual in declared.items():
            if value.get(key) != actual:
                raise ValueError(f"persisted index has an invalid {key}")
        return index

    def section(self, policy_id: str, section_id: str) -> tuple[PolicyChunk, ...]:
        return tuple(
            item.chunk
            for item in self.indexed_chunks
            if item.chunk.policy_id == policy_id and item.chunk.section_id == section_id
        )


def build_index(
    corpus_directory: Path,
    *,
    embedding_dimensions: int = 384,
    target_words: int = 240,
    overlap_words: int = 40,
) -> HybridIndex:
    model = LocalHashEmbedding(embedding_dimensions)
    chunks = ingest_policy_corpus(
        corpus_directory,
        target_words=target_words,
        overlap_words=overlap_words,
    )
    indexed = tuple(
        IndexedChunk(
            chunk=chunk,
            embedding=model.embed(
                " ".join(
                    (
                        chunk.policy_title,
                        chunk.section_title,
                        chunk.applicability,
                        chunk.text,
                    )
                )
            ),
        )
        for chunk in chunks
    )
    if any(not tokenize(item.chunk.text) for item in indexed):
        raise ValueError("every indexed chunk must contain searchable terms")
    return HybridIndex(
        index_version=INDEX_VERSION,
        corpus_fingerprint=corpus_fingerprint(corpus_directory),
        embedding_model=model.name,
        embedding_dimensions=embedding_dimensions,
        target_words=target_words,
        overlap_words=overlap_words,
        indexed_chunks=indexed,
    )


def write_index(index: HybridIndex, index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(index.to_dict(), indent=2, sort_keys=True) + "\n"
    temporary = index_path.with_suffix(f"{index_path.suffix}.tmp")
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(index_path)


def load_index(index_path: Path) -> HybridIndex:
    return HybridIndex.from_dict(json.loads(index_path.read_text(encoding="utf-8")))


def ensure_index(
    corpus_directory: Path,
    index_path: Path,
    *,
    embedding_dimensions: int = 384,
    target_words: int = 240,
    overlap_words: int = 40,
) -> HybridIndex:
    expected_fingerprint = corpus_fingerprint(corpus_directory)
    if index_path.is_file():
        try:
            index = load_index(index_path)
            if (
                index.index_version == INDEX_VERSION
                and index.corpus_fingerprint == expected_fingerprint
                and index.embedding_dimensions == embedding_dimensions
                and index.target_words == target_words
                and index.overlap_words == overlap_words
            ):
                return index
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass
    index = build_index(
        corpus_directory,
        embedding_dimensions=embedding_dimensions,
        target_words=target_words,
        overlap_words=overlap_words,
    )
    write_index(index, index_path)
    return index


@lru_cache(maxsize=4)
def cached_index(
    corpus_directory: Path,
    index_path: Path,
    embedding_dimensions: int,
    target_words: int,
    overlap_words: int,
) -> HybridIndex:
    return ensure_index(
        corpus_directory,
        index_path,
        embedding_dimensions=embedding_dimensions,
        target_words=target_words,
        overlap_words=overlap_words,
    )

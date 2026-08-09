from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from app.rag.corpus import load_manifest
from app.rag.models import PolicyChunk

MARKDOWN_SECTION = re.compile(
    r"^##\s+(?P<section_id>[A-Z]{3}-\d+(?:\.\d+)?)\.\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)
PDF_SECTION_LINE = re.compile(
    r"^(?P<section_id>[A-Z]{3}-\d+(?:\.\d+)?)\.\s+(?P<title>[^\n]+?)\s*$",
    re.MULTILINE,
)
PDF_TOC_LINE = re.compile(r"^[A-Z]{3}-\d+(?:\.\d+)?\..*?(?:\.\s*){3,}\d+\s*$")
PDF_HEADER_LINE = re.compile(
    r"^(?:Northstar T?echnologies Inc\. Internal Policy - Synthetic Corpus|\d+)$"
)


class IngestionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _Section:
    section_id: str
    title: str
    body: str
    page: int | None


def _normalize_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _markdown_sections(path: Path) -> list[_Section]:
    text = path.read_text(encoding="utf-8")
    headings = list(MARKDOWN_SECTION.finditer(text))
    sections: list[_Section] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = _normalize_text(text[heading.end() : end])
        if body:
            sections.append(
                _Section(
                    section_id=heading.group("section_id"),
                    title=heading.group("title"),
                    body=body,
                    page=None,
                )
            )
    return sections


def _clean_pdf_page(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or PDF_HEADER_LINE.fullmatch(line) or PDF_TOC_LINE.fullmatch(line):
            continue
        if line in {"Contents", "Related policies and records"}:
            continue
        lines.append(line)
    return "\n".join(lines)


def _pdf_sections(path: Path, expected_section_ids: set[str]) -> list[_Section]:
    reader = PdfReader(path)
    found: dict[str, _Section] = {}
    order: list[str] = []
    active_id: str | None = None

    for page_number, page in enumerate(reader.pages, start=1):
        cleaned = _clean_pdf_page(page.extract_text() or "")
        headings = [
            match
            for match in PDF_SECTION_LINE.finditer(cleaned)
            if match.group("section_id") in expected_section_ids
        ]
        cursor = 0
        for heading in headings:
            prefix = _normalize_text(cleaned[cursor : heading.start()])
            if prefix and active_id is not None:
                previous = found[active_id]
                found[active_id] = _Section(
                    section_id=previous.section_id,
                    title=previous.title,
                    body=_normalize_text(f"{previous.body}\n{prefix}"),
                    page=previous.page,
                )
            section_id = heading.group("section_id")
            if section_id not in found:
                order.append(section_id)
                found[section_id] = _Section(
                    section_id=section_id,
                    title=heading.group("title"),
                    body="",
                    page=page_number,
                )
            active_id = section_id
            cursor = heading.end()
        suffix = _normalize_text(cleaned[cursor:])
        if suffix and active_id is not None:
            previous = found[active_id]
            found[active_id] = _Section(
                section_id=previous.section_id,
                title=previous.title,
                body=_normalize_text(f"{previous.body}\n{suffix}"),
                page=previous.page,
            )

    missing = expected_section_ids - set(found)
    if missing:
        raise IngestionError(f"{path.name} is missing PDF sections: {sorted(missing)}")
    return [found[section_id] for section_id in order]


def _paragraphs(text: str) -> list[str]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    if len(paragraphs) == 1:
        paragraphs = [item.strip() for item in text.splitlines() if item.strip()]
    return paragraphs


def _chunk_section(
    section: _Section,
    *,
    target_words: int,
    overlap_words: int,
) -> Iterable[str]:
    paragraphs = _paragraphs(section.body)
    current: list[str] = []
    current_words = 0
    for paragraph in paragraphs:
        words = paragraph.split()
        if current and current_words + len(words) > target_words:
            chunk = _normalize_text("\n".join(current))
            yield chunk
            overlap = chunk.split()[-overlap_words:] if overlap_words else []
            current = [" ".join(overlap)] if overlap else []
            current_words = len(overlap)
        current.append(paragraph)
        current_words += len(words)
    if current:
        yield _normalize_text("\n".join(current))


def ingest_policy_corpus(
    corpus_directory: Path,
    *,
    target_words: int = 240,
    overlap_words: int = 40,
) -> list[PolicyChunk]:
    if target_words < 80 or overlap_words < 0 or overlap_words >= target_words:
        raise ValueError("invalid chunk-size or overlap configuration")
    manifest = load_manifest(corpus_directory)
    authoritative_folder = manifest.get("authoritative_ingestion_folder")
    if authoritative_folder != "runtime_corpus":
        raise IngestionError("manifest must designate runtime_corpus as authoritative")

    chunks: list[PolicyChunk] = []
    seen_sources: set[Path] = set()
    seen_sections: set[tuple[str, str]] = set()
    for policy in manifest["policies"]:
        source_path = corpus_directory / str(policy["runtime_source"])
        resolved_source = source_path.resolve()
        if resolved_source in seen_sources:
            raise IngestionError(f"duplicate authoritative source: {source_path}")
        seen_sources.add(resolved_source)

        source_format = str(policy["runtime_format"])
        expected_section_ids = set(policy["section_ids"])
        if source_format == "markdown":
            sections = _markdown_sections(source_path)
        elif source_format == "pdf":
            sections = _pdf_sections(source_path, expected_section_ids)
        else:
            raise IngestionError(f"unsupported runtime format: {source_format}")

        actual_section_ids = {section.section_id for section in sections}
        if actual_section_ids != expected_section_ids:
            missing = sorted(expected_section_ids - actual_section_ids)
            extra = sorted(actual_section_ids - expected_section_ids)
            raise IngestionError(
                f"{policy['policy_id']} section mismatch; missing={missing}, extra={extra}"
            )

        for section in sections:
            section_key = (str(policy["policy_id"]), section.section_id)
            if section_key in seen_sections:
                raise IngestionError(f"duplicate section: {section_key}")
            seen_sections.add(section_key)
            bodies = list(
                _chunk_section(
                    section,
                    target_words=target_words,
                    overlap_words=overlap_words,
                )
            )
            if not bodies:
                raise IngestionError(f"empty section: {section_key}")
            for ordinal, body in enumerate(bodies, start=1):
                chunks.append(
                    PolicyChunk(
                        chunk_id=(
                            f"{policy['policy_id']}::{section.section_id}::{ordinal:02d}"
                        ),
                        policy_id=str(policy["policy_id"]),
                        policy_title=str(policy["title"]),
                        section_id=section.section_id,
                        section_title=section.title,
                        text=body,
                        version=str(policy["version"]),
                        effective_date=date.fromisoformat(str(policy["effective_date"])),
                        owner=str(policy["owner"]),
                        applicability=str(policy["applicability"]),
                        source_format=source_format,  # type: ignore[arg-type]
                        source_path=f"policy_corpus/{policy['runtime_source']}",
                        page=section.page,
                    )
                )

    return chunks

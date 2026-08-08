import json
import re
from datetime import date
from pathlib import Path
from typing import Any

SECTION_HEADING = re.compile(r"^##\s+([A-Z]{3}-\d+)\.", re.MULTILINE)
POLICY_REFERENCE = re.compile(r"\bPOL-[A-Z]{3}-\d{3}\b")
REQUIRED_CORPUS_DOCUMENTS = (
    "corpus_docs/corpus_validation_report.json",
    "corpus_docs/cross_policy_consistency_matrix.md",
    "corpus_docs/glossary_and_citation_guide.md",
    "corpus_docs/policy_index.md",
)


def load_manifest(corpus_directory: Path) -> dict[str, Any]:
    manifest_path = corpus_directory / "corpus_docs" / "policy_manifest.json"
    with manifest_path.open(encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def validate_corpus(
    corpus_directory: Path, as_of_date: date | None = None
) -> dict[str, Any]:
    try:
        manifest = load_manifest(corpus_directory)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return {"ready": False, "detail": f"Corpus manifest unavailable: {error}"}

    policies = manifest.get("policies", [])
    declared_count = manifest.get("policy_count")
    errors: list[str] = []

    if manifest.get("synthetic") is not True:
        errors.append("manifest must declare synthetic=true")
    if declared_count != len(policies):
        errors.append(f"declared policy count is {declared_count}; found {len(policies)}")
    if not 5 <= len(policies) <= 20:
        errors.append("policy count must be between 5 and 20")
    estimated_pages = manifest.get("estimated_page_count_at_400_words", 0)
    if not isinstance(estimated_pages, int) or not 30 <= estimated_pages <= 120:
        errors.append("estimated corpus length must be between 30 and 120 pages")

    supported_formats = set(manifest.get("supported_runtime_formats", []))
    if len(supported_formats) < 2:
        errors.append("at least two runtime source formats are required")

    policy_ids = [policy.get("policy_id") for policy in policies]
    if len(set(policy_ids)) != len(policy_ids):
        errors.append("policy identifiers must be unique")

    declared_effective_date: date | None = None
    try:
        declared_effective_date = date.fromisoformat(manifest.get("effective_date", ""))
    except (TypeError, ValueError):
        errors.append("corpus manifest has an invalid effective date")

    all_section_ids: list[str] = []
    referenced_policy_ids: set[str] = set()
    for policy in policies:
        policy_id = policy.get("policy_id", "<missing policy_id>")
        required_metadata = (
            "title",
            "owner",
            "applicability",
            "version",
            "effective_date",
            "review_date",
        )
        missing_metadata = [field for field in required_metadata if not policy.get(field)]
        if missing_metadata:
            errors.append(f"{policy_id} is missing metadata: {missing_metadata}")

        runtime_format = policy.get("runtime_format")
        if runtime_format not in supported_formats:
            errors.append(f"{policy_id} uses undeclared format {runtime_format!r}")

        for source_field in ("master_source", "runtime_source", "review_pdf"):
            source = policy.get(source_field)
            if not source or not (corpus_directory / source).is_file():
                errors.append(f"{policy_id} has missing {source_field}: {source!r}")

        section_ids = policy.get("section_ids", [])
        if not section_ids:
            errors.append(f"{policy_id} has no stable section identifiers")
        all_section_ids.extend(section_ids)

        master_source = policy.get("master_source")
        master_path = corpus_directory / master_source if master_source else None
        if master_path and master_path.is_file():
            master_text = master_path.read_text(encoding="utf-8")
            headings = SECTION_HEADING.findall(master_text)
            referenced_policy_ids.update(POLICY_REFERENCE.findall(master_text))
            if headings != section_ids:
                errors.append(f"{policy_id} section identifiers do not match Markdown headings")

        try:
            effective_date = date.fromisoformat(policy.get("effective_date", ""))
            review_date = date.fromisoformat(policy.get("review_date", ""))
            if review_date <= effective_date:
                errors.append(f"{policy_id} review date must follow its effective date")
            if declared_effective_date and effective_date != declared_effective_date:
                errors.append(f"{policy_id} effective date differs from the corpus manifest")
            if as_of_date is not None and effective_date > as_of_date:
                errors.append(f"{policy_id} is not effective on {as_of_date}")
        except (TypeError, ValueError):
            errors.append(f"{policy_id} has invalid effective or review dates")

    if len(set(all_section_ids)) != len(all_section_ids):
        errors.append("section identifiers must be unique across the corpus")
    if unknown_references := referenced_policy_ids - set(policy_ids):
        errors.append(f"unresolved cross-policy references: {sorted(unknown_references)}")

    for relative_path in REQUIRED_CORPUS_DOCUMENTS:
        if not (corpus_directory / relative_path).is_file():
            errors.append(f"missing corpus control document: {relative_path}")

    validation_report_path = (
        corpus_directory / "corpus_docs" / "corpus_validation_report.json"
    )
    if validation_report_path.is_file():
        try:
            validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
            report_checks = validation_report.get("checks", {})
            if (
                validation_report.get("status") != "PASS"
                or not report_checks
                or not all(report_checks.values())
            ):
                errors.append("committed corpus validation report does not pass every check")
        except json.JSONDecodeError:
            errors.append("committed corpus validation report is invalid JSON")

    runtime_formats = {policy.get("runtime_format") for policy in policies}
    if runtime_formats != supported_formats:
        errors.append("declared runtime formats do not match policy sources")

    declared_word_count = manifest.get("total_word_count")
    policy_word_counts = [policy.get("word_count") for policy in policies]
    if (
        not isinstance(declared_word_count, int)
        or not all(isinstance(count, int) for count in policy_word_counts)
        or declared_word_count != sum(policy_word_counts)
    ):
        errors.append("declared corpus word count does not match policy metadata")
    policy_page_counts = [policy.get("estimated_pages_at_400_words") for policy in policies]
    if not all(isinstance(count, int) for count in policy_page_counts) or estimated_pages != sum(
        policy_page_counts
    ):
        errors.append("declared estimated page count does not match policy metadata")

    ready = not errors
    if ready:
        formats = ", ".join(sorted(supported_formats))
        detail = (
            f"{declared_count} synthetic policies and {estimated_pages} estimated pages "
            f"validated ({formats})."
        )
    else:
        detail = "Corpus validation failed: " + "; ".join(errors)
    return {"ready": ready, "detail": detail, "errors": errors, "manifest": manifest}

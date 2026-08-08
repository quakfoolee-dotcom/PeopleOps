import json
from pathlib import Path
from typing import Any


def load_manifest(corpus_directory: Path) -> dict[str, Any]:
    manifest_path = corpus_directory / "corpus_docs" / "policy_manifest.json"
    with manifest_path.open(encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def validate_corpus(corpus_directory: Path) -> dict[str, Any]:
    try:
        manifest = load_manifest(corpus_directory)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return {"ready": False, "detail": f"Corpus manifest unavailable: {error}"}

    policies = manifest.get("policies", [])
    missing_sources = [
        policy.get("runtime_source", "<missing runtime_source>")
        for policy in policies
        if not (corpus_directory / policy.get("runtime_source", "")).is_file()
    ]
    declared_count = manifest.get("policy_count")
    unique_ids = {policy.get("policy_id") for policy in policies}

    ready = (
        manifest.get("synthetic") is True
        and declared_count == len(policies)
        and len(unique_ids) == len(policies)
        and not missing_sources
    )
    if ready:
        formats = ", ".join(manifest.get("supported_runtime_formats", []))
        detail = f"{declared_count} synthetic policies validated ({formats})."
    else:
        detail = (
            "Corpus validation failed: "
            f"declared={declared_count}, actual={len(policies)}, missing={missing_sources}."
        )
    return {"ready": ready, "detail": detail, "manifest": manifest}

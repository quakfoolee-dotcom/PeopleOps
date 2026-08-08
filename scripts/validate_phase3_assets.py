import argparse
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.core.constants import SYNTHETIC_AS_OF_DATE
from app.data.store import build_sqlite_database, load_seed_bundle, validate_seed_data
from app.rag.corpus import validate_corpus


def _resolve_database_path(value: Path) -> Path:
    return value if value.is_absolute() else PROJECT_ROOT / value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Phase 3 policy corpus and deterministic mock data."
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Optionally persist the validated SQLite database at this path.",
    )
    arguments = parser.parse_args()

    corpus = validate_corpus(
        PROJECT_ROOT / "policy_corpus",
        as_of_date=SYNTHETIC_AS_OF_DATE,
    )
    if not corpus["ready"]:
        print(corpus["detail"])
        return 1

    try:
        bundle = load_seed_bundle()
    except (OSError, ValueError) as error:
        print(f"Mock-data validation failed: {error}")
        return 1

    if errors := validate_seed_data(bundle):
        print("Mock-data validation failed: " + "; ".join(errors))
        return 1

    if arguments.database:
        database_path = _resolve_database_path(arguments.database)
        counts = build_sqlite_database(bundle, database_path)
        database_result = str(database_path)
    else:
        temporary_root = PROJECT_ROOT / "tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        database_path = temporary_root / "phase3-validation.db"
        try:
            counts = build_sqlite_database(bundle, database_path)
        finally:
            database_path.unlink(missing_ok=True)
        database_result = "temporary SQLite build"

    manifest = corpus["manifest"]
    formats = ", ".join(sorted(manifest["supported_runtime_formats"]))
    print(
        f"Phase 3 assets validated: {manifest['policy_count']} policies, "
        f"{manifest['estimated_page_count_at_400_words']} estimated pages, "
        f"formats={formats}, employees={counts['employees']}, "
        f"locations={counts['locations']}, tickets={counts['tickets']}, "
        f"database={database_result}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

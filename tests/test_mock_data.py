import json
import shutil
import sqlite3
from contextlib import closing
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.contracts import BenefitsRecord, Employee, MockDataManifest, PTOBalance
from app.data.store import (
    REQUIRED_GOLD_EMPLOYEE_IDS,
    build_sqlite_database,
    database_record_counts,
    load_seed_bundle,
    validate_seed_data,
    validate_seed_directory,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_seed_bundle_is_deterministic_and_supports_gold_cases() -> None:
    bundle = load_seed_bundle()

    assert bundle.manifest.synthetic_only is True
    assert bundle.manifest.as_of_date == date(2026, 9, 1)
    assert len(bundle.employees) == 30
    assert len(bundle.locations) == 6
    assert len(bundle.manager_relationships) == 29
    assert len(bundle.pto_balances) == 30
    assert len(bundle.benefits) == 30
    assert len(bundle.tickets) == 6
    assert {
        employee.employee_id for employee in bundle.employees
    } >= REQUIRED_GOLD_EMPLOYEE_IDS
    assert validate_seed_data(bundle) == []
    assert validate_seed_directory() == []
    assert "expected 2026-09-02" in validate_seed_directory(
        expected_as_of_date=date(2026, 9, 2)
    )[0]

    employees = {employee.employee_id: employee for employee in bundle.employees}
    balances = {balance.employee_id: balance for balance in bundle.pto_balances}
    assert employees["E-1007"].home_office_id == "LOC-YVR"
    assert employees["E-1014"].remote_work_classification == "remote"
    assert balances["E-1021"].available_hours == 96


def test_validated_seed_builds_foreign_key_clean_sqlite() -> None:
    database_path = PROJECT_ROOT / "tmp" / "test-peopleops.db"
    database_path.unlink(missing_ok=True)
    try:
        counts = build_sqlite_database(load_seed_bundle(), database_path)

        assert counts == {
            "locations": 6,
            "employees": 30,
            "manager_relationships": 29,
            "pto_balances": 30,
            "pto_transactions": 15,
            "benefits": 30,
            "tickets": 6,
        }
        assert database_record_counts(database_path) == counts
        with closing(sqlite3.connect(database_path)) as connection:
            metadata = connection.execute(
                "SELECT organization, synthetic_only, as_of_date FROM dataset_metadata"
            ).fetchone()
            employee = connection.execute(
                "SELECT role, home_office_id FROM employees WHERE employee_id = ?",
                ("E-1007",),
            ).fetchone()
        assert metadata == ("Northstar Technologies Inc.", 1, "2026-09-01")
        assert employee == ("Senior Data Analyst", "LOC-YVR")
    finally:
        database_path.unlink(missing_ok=True)


def test_semantic_validator_reports_cross_dataset_errors() -> None:
    bundle = deepcopy(load_seed_bundle())
    bundle.manifest.as_of_date = date(2026, 9, 2)
    bundle.employees.pop()
    bundle.employees[0] = bundle.employees[0].model_copy(
        update={"home_office_id": "LOC-BAD", "hire_date": date(2026, 9, 3)}
    )
    bundle.employees[1] = bundle.employees[1].model_copy(update={"manager_id": "E-9999"})
    bundle.manager_relationships[0] = bundle.manager_relationships[0].model_copy(
        update={"manager_id": "E-1002", "effective_date": date(2026, 9, 3)}
    )
    bundle.pto_balances.pop(1)
    bundle.pto_balances[0] = bundle.pto_balances[0].model_copy(
        update={"as_of_date": date(2026, 9, 1)}
    )
    bundle.pto_transactions[0] = bundle.pto_transactions[0].model_copy(
        update={"employee_id": "E-9999", "transaction_date": date(2026, 9, 3)}
    )
    bundle.benefits.pop(1)
    bundle.benefits[0] = bundle.benefits[0].model_copy(
        update={"as_of_date": date(2026, 9, 1), "effective_date": date(2026, 9, 3)}
    )
    bundle.tickets[0] = bundle.tickets[0].model_copy(
        update={
            "affected_employee_id": "E-9999",
            "created_at": datetime(2026, 9, 3, tzinfo=UTC),
        }
    )

    errors = validate_seed_data(bundle)

    expected_fragments = (
        "manifest as-of date",
        "employee count",
        "unknown location",
        "unknown manager",
        "future hire date",
        "manager relationship records",
        "manager relationships cannot start",
        "manager hierarchy contains a cycle",
        "PTO balances must contain exactly one",
        "benefits must contain exactly one",
        "PTO balance has the wrong as-of date",
        "references unknown employee",
        "dated after the as-of date",
        "benefits record has the wrong as-of date",
        "benefits effective date is in the future",
        "was created after the as-of date",
    )
    for fragment in expected_fragments:
        assert any(fragment in error for error in errors), fragment

    with pytest.raises(ValueError, match="cannot build invalid seed data"):
        build_sqlite_database(bundle, Path("unused.db"))


def test_contracts_reject_inconsistent_or_non_synthetic_records() -> None:
    with pytest.raises(ValidationError, match="an employee cannot manage themselves"):
        Employee.model_validate(
            {
                "employee_id": "E-1001",
                "synthetic_name": "Synthetic Person",
                "employment_type": "RFT",
                "role": "Analyst",
                "department": "Operations",
                "manager_id": "E-1001",
                "home_office_id": "LOC-YVR",
                "hire_date": "2026-01-01",
                "remote_work_classification": "hybrid",
                "status": "active",
                "weekly_hours": "40.00",
            }
        )

    with pytest.raises(ValidationError, match="zero PTO balances"):
        PTOBalance.model_validate(
            {
                "employee_id": "E-1001",
                "as_of_date": "2026-09-01",
                "eligible": False,
                "available_hours": "8.00",
                "pending_hours": "0.00",
                "scheduled_hours_per_day": "8.00",
            }
        )

    with pytest.raises(ValidationError, match="require plan, tier, and effective date"):
        BenefitsRecord.model_validate(
            {
                "employee_id": "E-1001",
                "as_of_date": "2026-09-01",
                "eligibility_status": "eligible",
                "enrollment_status": "enrolled",
            }
        )

    manifest = load_seed_bundle().manifest.model_dump(mode="json")
    manifest["synthetic_only"] = False
    with pytest.raises(ValidationError):
        MockDataManifest.model_validate(manifest)


def test_loader_detects_checksum_tampering() -> None:
    source_bundle = load_seed_bundle()
    seed_directory = PROJECT_ROOT / "tmp" / "checksum-test-seed"
    if seed_directory.exists():
        shutil.rmtree(seed_directory)
    seed_directory.mkdir()
    try:
        source_directory = PROJECT_ROOT / "mock_data" / "seed"
        for descriptor in source_bundle.manifest.files.values():
            source = source_directory / descriptor.file_name
            (seed_directory / descriptor.file_name).write_bytes(source.read_bytes())
        manifest_path = source_directory / "manifest.json"
        (seed_directory / "manifest.json").write_bytes(manifest_path.read_bytes())

        employees_path = seed_directory / "employees.json"
        employees = json.loads(employees_path.read_text(encoding="utf-8"))
        employees[0]["role"] = "Tampered Role"
        employees_path.write_text(json.dumps(employees), encoding="utf-8")

        with pytest.raises(ValueError, match="checksum mismatch"):
            load_seed_bundle(seed_directory)
        assert validate_seed_directory(seed_directory)[0].startswith(
            "mock data cannot be loaded"
        )
    finally:
        shutil.rmtree(seed_directory)

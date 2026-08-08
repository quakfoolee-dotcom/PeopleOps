import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import RootModel, ValidationError

from app.core.config import PROJECT_ROOT
from app.core.constants import SYNTHETIC_AS_OF_DATE
from app.data.contracts import (
    BenefitsDataset,
    BenefitsRecord,
    Employee,
    EmployeeDataset,
    Location,
    LocationDataset,
    ManagerRelationship,
    ManagerRelationshipDataset,
    MockDataManifest,
    MockHRTicket,
    PTOBalance,
    PTOBalanceDataset,
    PTOTransaction,
    PTOTransactionDataset,
    TicketDataset,
)

MOCK_DATA_DIRECTORY = PROJECT_ROOT / "mock_data"
SEED_DIRECTORY = MOCK_DATA_DIRECTORY / "seed"

EXPECTED_DATA_FILES: dict[str, tuple[str, type[RootModel[Any]]]] = {
    "locations": ("locations.json", LocationDataset),
    "employees": ("employees.json", EmployeeDataset),
    "manager_relationships": ("manager_relationships.json", ManagerRelationshipDataset),
    "pto_balances": ("pto_balances.json", PTOBalanceDataset),
    "pto_transactions": ("pto_transactions.json", PTOTransactionDataset),
    "benefits": ("benefits.json", BenefitsDataset),
    "tickets": ("tickets.json", TicketDataset),
}

REQUIRED_GOLD_EMPLOYEE_IDS = frozenset({"E-1003", "E-1007", "E-1011", "E-1014", "E-1021", "E-1024"})


@dataclass(frozen=True, slots=True)
class SeedBundle:
    manifest: MockDataManifest
    locations: list[Location]
    employees: list[Employee]
    manager_relationships: list[ManagerRelationship]
    pto_balances: list[PTOBalance]
    pto_transactions: list[PTOTransaction]
    benefits: list[BenefitsRecord]
    tickets: list[MockHRTicket]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as data_file:
        return json.load(data_file)


def load_seed_bundle(seed_directory: Path = SEED_DIRECTORY) -> SeedBundle:
    manifest = MockDataManifest.model_validate(_load_json(seed_directory / "manifest.json"))
    datasets: dict[str, list[Any]] = {}

    if set(manifest.files) != set(EXPECTED_DATA_FILES):
        missing = sorted(set(EXPECTED_DATA_FILES) - set(manifest.files))
        unexpected = sorted(set(manifest.files) - set(EXPECTED_DATA_FILES))
        raise ValueError(f"manifest file set mismatch: missing={missing}, unexpected={unexpected}")

    for dataset_name, (expected_file_name, dataset_model) in EXPECTED_DATA_FILES.items():
        descriptor = manifest.files[dataset_name]
        if descriptor.file_name != expected_file_name:
            raise ValueError(
                f"{dataset_name} uses {descriptor.file_name}, expected {expected_file_name}"
            )
        data_path = seed_directory / descriptor.file_name
        if _sha256(data_path) != descriptor.sha256:
            raise ValueError(f"checksum mismatch for {descriptor.file_name}")
        dataset = dataset_model.model_validate(_load_json(data_path)).root
        if len(dataset) != descriptor.record_count:
            raise ValueError(
                f"record count mismatch for {descriptor.file_name}: "
                f"manifest={descriptor.record_count}, actual={len(dataset)}"
            )
        datasets[dataset_name] = dataset

    return SeedBundle(manifest=manifest, **datasets)


def _duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _manager_cycle(employee_id: str, manager_by_employee: dict[str, str]) -> bool:
    visited: set[str] = set()
    current: str | None = employee_id
    while current is not None:
        if current in visited:
            return True
        visited.add(current)
        current = manager_by_employee.get(current)
    return False


def validate_seed_data(
    bundle: SeedBundle,
    expected_as_of_date: date = SYNTHETIC_AS_OF_DATE,
) -> list[str]:
    errors: list[str] = []
    if bundle.manifest.as_of_date != expected_as_of_date:
        errors.append(
            f"manifest as-of date is {bundle.manifest.as_of_date}, "
            f"expected {expected_as_of_date}"
        )
    if len(bundle.employees) != 30:
        errors.append(f"employee count is {len(bundle.employees)}, expected 30")

    employee_ids = [employee.employee_id for employee in bundle.employees]
    employee_id_set = set(employee_ids)
    location_ids = [location.location_id for location in bundle.locations]
    location_id_set = set(location_ids)

    for label, identifiers in (
        ("employee", employee_ids),
        ("location", location_ids),
        ("manager relationship", [item.employee_id for item in bundle.manager_relationships]),
        ("PTO balance", [item.employee_id for item in bundle.pto_balances]),
        ("PTO transaction", [item.transaction_id for item in bundle.pto_transactions]),
        ("benefits", [item.employee_id for item in bundle.benefits]),
        ("ticket", [item.ticket_id for item in bundle.tickets]),
        ("ticket confirmation", [item.confirmation_reference for item in bundle.tickets]),
    ):
        if duplicates := _duplicate_values(identifiers):
            errors.append(f"duplicate {label} identifiers: {duplicates}")

    if missing_gold_ids := REQUIRED_GOLD_EMPLOYEE_IDS - employee_id_set:
        errors.append(f"gold cases reference missing employees: {sorted(missing_gold_ids)}")

    for employee in bundle.employees:
        if employee.home_office_id not in location_id_set:
            errors.append(
                f"{employee.employee_id} references unknown location {employee.home_office_id}"
            )
        if employee.manager_id is not None and employee.manager_id not in employee_id_set:
            errors.append(
                f"{employee.employee_id} references unknown manager {employee.manager_id}"
            )
        if employee.hire_date > bundle.manifest.as_of_date:
            errors.append(f"{employee.employee_id} has a future hire date")

    expected_relationships = {
        employee.employee_id: employee.manager_id
        for employee in bundle.employees
        if employee.manager_id is not None
    }
    actual_relationships = {
        relationship.employee_id: relationship.manager_id
        for relationship in bundle.manager_relationships
    }
    for relationship in bundle.manager_relationships:
        if relationship.employee_id not in employee_id_set:
            errors.append(
                f"manager relationship references unknown employee "
                f"{relationship.employee_id}"
            )
        if relationship.manager_id not in employee_id_set:
            errors.append(
                f"manager relationship references unknown manager {relationship.manager_id}"
            )
    if actual_relationships != expected_relationships:
        errors.append("manager relationship records do not match employee manager IDs")
    if any(
        relationship.effective_date > bundle.manifest.as_of_date
        for relationship in bundle.manager_relationships
    ):
        errors.append("manager relationships cannot start after the as-of date")
    if any(_manager_cycle(employee_id, actual_relationships) for employee_id in employee_ids):
        errors.append("manager hierarchy contains a cycle")

    balance_ids = {balance.employee_id for balance in bundle.pto_balances}
    benefits_ids = {record.employee_id for record in bundle.benefits}
    if balance_ids != employee_id_set:
        errors.append("PTO balances must contain exactly one record per employee")
    if benefits_ids != employee_id_set:
        errors.append("benefits must contain exactly one record per employee")

    for balance in bundle.pto_balances:
        if balance.as_of_date != bundle.manifest.as_of_date:
            errors.append(f"{balance.employee_id} PTO balance has the wrong as-of date")
    for transaction in bundle.pto_transactions:
        if transaction.employee_id not in employee_id_set:
            errors.append(
                f"{transaction.transaction_id} references unknown employee "
                f"{transaction.employee_id}"
            )
        if transaction.transaction_date > bundle.manifest.as_of_date:
            errors.append(f"{transaction.transaction_id} is dated after the as-of date")
    for record in bundle.benefits:
        if record.as_of_date != bundle.manifest.as_of_date:
            errors.append(f"{record.employee_id} benefits record has the wrong as-of date")
        if record.effective_date and record.effective_date > bundle.manifest.as_of_date:
            errors.append(f"{record.employee_id} benefits effective date is in the future")
    as_of_end = datetime.combine(bundle.manifest.as_of_date, time.max, tzinfo=UTC)
    for ticket in bundle.tickets:
        if ticket.affected_employee_id not in employee_id_set:
            errors.append(
                f"{ticket.ticket_id} references unknown employee {ticket.affected_employee_id}"
            )
        if ticket.created_at.astimezone(UTC) > as_of_end:
            errors.append(f"{ticket.ticket_id} was created after the as-of date")

    return errors


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def build_sqlite_database(bundle: SeedBundle, database_path: Path) -> dict[str, int]:
    if errors := validate_seed_data(bundle):
        raise ValueError("cannot build invalid seed data: " + "; ".join(errors))

    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = database_path.with_suffix(database_path.suffix + ".tmp")
    if temporary_path.exists():
        temporary_path.unlink()

    try:
        with closing(sqlite3.connect(temporary_path)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                CREATE TABLE dataset_metadata (
                    schema_version TEXT NOT NULL,
                    organization TEXT NOT NULL,
                    synthetic_only INTEGER NOT NULL CHECK (synthetic_only = 1),
                    as_of_date TEXT NOT NULL
                );
                CREATE TABLE locations (
                    location_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    province_or_state TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    currency TEXT NOT NULL
                );
                CREATE TABLE employees (
                    employee_id TEXT PRIMARY KEY,
                    synthetic_name TEXT NOT NULL UNIQUE,
                    employment_type TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    manager_id TEXT,
                    home_office_id TEXT NOT NULL REFERENCES locations(location_id),
                    hire_date TEXT NOT NULL,
                    remote_work_classification TEXT NOT NULL,
                    status TEXT NOT NULL,
                    weekly_hours TEXT NOT NULL,
                    FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
                        DEFERRABLE INITIALLY DEFERRED
                );
                CREATE TABLE manager_relationships (
                    employee_id TEXT PRIMARY KEY REFERENCES employees(employee_id),
                    manager_id TEXT NOT NULL REFERENCES employees(employee_id),
                    effective_date TEXT NOT NULL,
                    CHECK (employee_id <> manager_id)
                );
                CREATE TABLE pto_balances (
                    employee_id TEXT PRIMARY KEY REFERENCES employees(employee_id),
                    as_of_date TEXT NOT NULL,
                    eligible INTEGER NOT NULL,
                    available_hours TEXT NOT NULL,
                    pending_hours TEXT NOT NULL,
                    scheduled_hours_per_day TEXT NOT NULL
                );
                CREATE TABLE pto_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
                    transaction_date TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    hours_delta TEXT NOT NULL,
                    note TEXT NOT NULL
                );
                CREATE TABLE benefits (
                    employee_id TEXT PRIMARY KEY REFERENCES employees(employee_id),
                    as_of_date TEXT NOT NULL,
                    eligibility_status TEXT NOT NULL,
                    enrollment_status TEXT NOT NULL,
                    plan_code TEXT,
                    coverage_tier TEXT,
                    effective_date TEXT
                );
                CREATE TABLE tickets (
                    ticket_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    affected_employee_id TEXT NOT NULL REFERENCES employees(employee_id),
                    routing_team TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    confirmation_reference TEXT NOT NULL UNIQUE
                );
                """
            )
            connection.execute(
                "INSERT INTO dataset_metadata VALUES (?, ?, ?, ?)",
                (
                    bundle.manifest.schema_version,
                    bundle.manifest.organization,
                    1,
                    bundle.manifest.as_of_date.isoformat(),
                ),
            )
            connection.executemany(
                "INSERT INTO locations VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.location_id,
                        item.name,
                        item.city,
                        item.province_or_state,
                        item.country_code,
                        item.timezone,
                        item.currency,
                    )
                    for item in bundle.locations
                ],
            )
            connection.executemany(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.employee_id,
                        item.synthetic_name,
                        item.employment_type.value,
                        item.role,
                        item.department,
                        item.manager_id,
                        item.home_office_id,
                        item.hire_date.isoformat(),
                        item.remote_work_classification.value,
                        item.status.value,
                        _decimal(item.weekly_hours),
                    )
                    for item in bundle.employees
                ],
            )
            connection.executemany(
                "INSERT INTO manager_relationships VALUES (?, ?, ?)",
                [
                    (item.employee_id, item.manager_id, item.effective_date.isoformat())
                    for item in bundle.manager_relationships
                ],
            )
            connection.executemany(
                "INSERT INTO pto_balances VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.employee_id,
                        item.as_of_date.isoformat(),
                        int(item.eligible),
                        _decimal(item.available_hours),
                        _decimal(item.pending_hours),
                        _decimal(item.scheduled_hours_per_day),
                    )
                    for item in bundle.pto_balances
                ],
            )
            connection.executemany(
                "INSERT INTO pto_transactions VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.transaction_id,
                        item.employee_id,
                        item.transaction_date.isoformat(),
                        item.transaction_type.value,
                        _decimal(item.hours_delta),
                        item.note,
                    )
                    for item in bundle.pto_transactions
                ],
            )
            connection.executemany(
                "INSERT INTO benefits VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.employee_id,
                        item.as_of_date.isoformat(),
                        item.eligibility_status.value,
                        item.enrollment_status.value,
                        item.plan_code,
                        item.coverage_tier,
                        item.effective_date.isoformat() if item.effective_date else None,
                    )
                    for item in bundle.benefits
                ],
            )
            connection.executemany(
                "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.ticket_id,
                        item.category,
                        item.priority.value,
                        item.summary,
                        item.affected_employee_id,
                        item.routing_team,
                        item.status.value,
                        item.created_at.isoformat(),
                        item.confirmation_reference,
                    )
                    for item in bundle.tickets
                ],
            )
        temporary_path.replace(database_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return database_record_counts(database_path)


def database_record_counts(database_path: Path) -> dict[str, int]:
    tables = [
        "locations",
        "employees",
        "manager_relationships",
        "pto_balances",
        "pto_transactions",
        "benefits",
        "tickets",
    ]
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise ValueError(f"SQLite foreign-key validation failed: {foreign_key_errors}")
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in tables
        }


def validate_seed_directory(
    seed_directory: Path = SEED_DIRECTORY,
    expected_as_of_date: date = SYNTHETIC_AS_OF_DATE,
) -> list[str]:
    try:
        bundle = load_seed_bundle(seed_directory)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as error:
        return [f"mock data cannot be loaded: {error}"]
    return validate_seed_data(bundle, expected_as_of_date=expected_as_of_date)

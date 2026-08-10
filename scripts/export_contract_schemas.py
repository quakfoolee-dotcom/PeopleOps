import argparse
import json

from app.api.contracts import (
    ChatRequest,
    ChatResponse,
    ConfirmMockTicketRequest,
    ConfirmMockTicketResponse,
    ToolTraceEntry,
)
from app.core.config import PROJECT_ROOT
from app.data.contracts import (
    BenefitsDataset,
    EmployeeDataset,
    LocationDataset,
    ManagerRelationshipDataset,
    MockDataManifest,
    PTOBalanceDataset,
    PTOTransactionDataset,
    TicketDataset,
)
from app.evaluation.contracts import (
    AnswerCheckSuite,
    GoldEvaluationSuite,
    IntentRobustnessSuite,
)

EVALUATION_SCHEMA_DIRECTORY = PROJECT_ROOT / "evaluation" / "schemas"
MOCK_DATA_SCHEMA_DIRECTORY = PROJECT_ROOT / "mock_data" / "schemas"
SCHEMA_MODELS = {
    EVALUATION_SCHEMA_DIRECTORY / "chat_request.schema.json": ChatRequest,
    EVALUATION_SCHEMA_DIRECTORY / "chat_response.schema.json": ChatResponse,
    EVALUATION_SCHEMA_DIRECTORY
    / "confirm_mock_ticket_request.schema.json": ConfirmMockTicketRequest,
    EVALUATION_SCHEMA_DIRECTORY
    / "confirm_mock_ticket_response.schema.json": ConfirmMockTicketResponse,
    EVALUATION_SCHEMA_DIRECTORY / "gold_evaluation_suite.schema.json": GoldEvaluationSuite,
    EVALUATION_SCHEMA_DIRECTORY / "answer_check_suite.schema.json": AnswerCheckSuite,
    EVALUATION_SCHEMA_DIRECTORY
    / "intent_robustness_suite.schema.json": IntentRobustnessSuite,
    EVALUATION_SCHEMA_DIRECTORY / "tool_trace_entry.schema.json": ToolTraceEntry,
    MOCK_DATA_SCHEMA_DIRECTORY / "manifest.schema.json": MockDataManifest,
    MOCK_DATA_SCHEMA_DIRECTORY / "locations.schema.json": LocationDataset,
    MOCK_DATA_SCHEMA_DIRECTORY / "employees.schema.json": EmployeeDataset,
    MOCK_DATA_SCHEMA_DIRECTORY
    / "manager_relationships.schema.json": ManagerRelationshipDataset,
    MOCK_DATA_SCHEMA_DIRECTORY / "pto_balances.schema.json": PTOBalanceDataset,
    MOCK_DATA_SCHEMA_DIRECTORY / "pto_transactions.schema.json": PTOTransactionDataset,
    MOCK_DATA_SCHEMA_DIRECTORY / "benefits.schema.json": BenefitsDataset,
    MOCK_DATA_SCHEMA_DIRECTORY / "tickets.schema.json": TicketDataset,
}


def render_schema(model: type) -> str:
    return json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or verify PeopleOps JSON Schemas.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when committed schemas differ from the current Pydantic contracts.",
    )
    arguments = parser.parse_args()

    mismatches: list[str] = []
    if not arguments.check:
        EVALUATION_SCHEMA_DIRECTORY.mkdir(parents=True, exist_ok=True)
        MOCK_DATA_SCHEMA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    for schema_path, model in SCHEMA_MODELS.items():
        rendered = render_schema(model)
        if arguments.check:
            if not schema_path.is_file() or schema_path.read_text(encoding="utf-8") != rendered:
                mismatches.append(str(schema_path.relative_to(PROJECT_ROOT)))
        else:
            schema_path.write_text(rendered, encoding="utf-8")

    if mismatches:
        print(f"Contract schema drift detected: {', '.join(mismatches)}")
        return 1
    print("Contract schemas are current." if arguments.check else "Contract schemas exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

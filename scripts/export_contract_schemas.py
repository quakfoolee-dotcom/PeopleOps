import argparse
import json

from app.api.contracts import ChatRequest, ChatResponse, ToolTraceEntry
from app.core.config import PROJECT_ROOT
from app.evaluation.contracts import GoldEvaluationSuite

SCHEMA_DIRECTORY = PROJECT_ROOT / "evaluation" / "schemas"
SCHEMA_MODELS = {
    "chat_request.schema.json": ChatRequest,
    "chat_response.schema.json": ChatResponse,
    "gold_evaluation_suite.schema.json": GoldEvaluationSuite,
    "tool_trace_entry.schema.json": ToolTraceEntry,
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
        SCHEMA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    for filename, model in SCHEMA_MODELS.items():
        schema_path = SCHEMA_DIRECTORY / filename
        rendered = render_schema(model)
        if arguments.check:
            if not schema_path.is_file() or schema_path.read_text(encoding="utf-8") != rendered:
                mismatches.append(filename)
        else:
            schema_path.write_text(rendered, encoding="utf-8")

    if mismatches:
        print(f"Contract schema drift detected: {', '.join(mismatches)}")
        return 1
    print("Contract schemas are current." if arguments.check else "Contract schemas exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

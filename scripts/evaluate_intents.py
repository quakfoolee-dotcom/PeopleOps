from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.intent_robustness import evaluate_intent_robustness  # noqa: E402

RESULT_PATH = PROJECT_ROOT / "evaluation" / "results" / "phase10_intent_robustness.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate intent-routing robustness.")
    parser.add_argument("--write", action="store_true", help="Write the committed evidence file.")
    arguments = parser.parse_args()
    result = evaluate_intent_robustness()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

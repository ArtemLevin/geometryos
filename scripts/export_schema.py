import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gir_core.schema import gir_json_schema  # noqa: E402

SCHEMA_PATH = ROOT / "schemas" / "gir.schema.json"


def export_schema() -> Path:
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(_schema_json(gir_json_schema()) + "\n", encoding="utf-8")
    return SCHEMA_PATH


def schema_is_up_to_date() -> bool:
    if not SCHEMA_PATH.exists():
        return False
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return _schema_json(committed) == _schema_json(gir_json_schema())


def _schema_json(schema: dict[str, Any]) -> str:
    # Design note: sorted keys make schema-check deterministic and keep the committed
    # machine contract reviewable even though Pydantic emits a large schema artifact.
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or check the GIR JSON Schema artifact.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if schemas/gir.schema.json is not up to date.",
    )
    args = parser.parse_args()

    if args.check:
        if schema_is_up_to_date():
            print(f"GIR schema is up to date: {SCHEMA_PATH}")
            return 0
        print(f"GIR schema is out of date: {SCHEMA_PATH}", file=sys.stderr)
        return 1

    path = export_schema()
    print(f"Exported GIR schema to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

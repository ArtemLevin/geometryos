import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gir_core.schema import check_gir_schema, write_gir_schema  # noqa: E402

SCHEMA_PATH = ROOT / "schemas" / "gir-0.2.schema.json"


def export_schema(output: Path = SCHEMA_PATH) -> Path:
    return write_gir_schema(output)


def schema_is_up_to_date(output: Path = SCHEMA_PATH) -> bool:
    return check_gir_schema(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or check the GIR JSON Schema artifact.")
    parser.add_argument(
        "--output",
        type=Path,
        default=SCHEMA_PATH,
        help="Output path for generated GIR JSON Schema.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the GIR JSON Schema artifact is not up to date.",
    )
    args = parser.parse_args()
    output: Path = args.output

    if args.check:
        if schema_is_up_to_date(output):
            print(f"GIR schema is up to date: {output}")
            return 0
        if output.exists():
            print(f"GIR schema is out of date: {output}", file=sys.stderr)
        else:
            print(f"GIR schema file not found: {output}", file=sys.stderr)
        print(f"Run: gir export-schema --output {output}", file=sys.stderr)
        return 1

    path = export_schema(output)
    print(f"Exported GIR schema to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gir_api.openapi_contract import (  # noqa: E402
    OPENAPI_ARTIFACT_PATH,
    check_openapi_artifact,
    write_openapi_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or check OpenAPI v1.")
    parser.add_argument("--output", type=Path, default=ROOT / OPENAPI_ARTIFACT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output: Path = args.output
    if args.check:
        if check_openapi_artifact(output):
            print(f"OpenAPI v1 is up to date: {output}")
            return 0
        state = "out of date" if output.exists() else "not found"
        print(f"OpenAPI v1 is {state}: {output}", file=sys.stderr)
        print("Run: uv run python scripts/export_openapi.py", file=sys.stderr)
        return 1
    path = write_openapi_artifact(output)
    print(f"Exported OpenAPI v1 to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

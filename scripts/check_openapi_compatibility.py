from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gir_api.openapi_compatibility import (  # noqa: E402
    CompatibilitySeverity,
    compare_openapi_documents,
)


def _load(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"OpenAPI document must be an object: {path}")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenAPI backward compatibility.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseline = _load(args.baseline)
        candidate = _load(args.candidate)
        issues = compare_openapi_documents(baseline, candidate)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"OpenAPI compatibility check failed to run: {exc}", file=sys.stderr)
        return 2
    breaking = [item for item in issues if item.severity is CompatibilitySeverity.BREAKING]
    review = [item for item in issues if item.severity is CompatibilitySeverity.REVIEW]
    if breaking:
        print("OpenAPI compatibility: failed\n", file=sys.stderr)
        for item in breaking:
            print(f"BREAKING: {item.location}: {item.message}", file=sys.stderr)
        for item in review:
            print(f"REVIEW: {item.location}: {item.message}", file=sys.stderr)
        return 1
    print("OpenAPI compatibility: passed")
    for item in review:
        print(f"REVIEW: {item.location}: {item.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

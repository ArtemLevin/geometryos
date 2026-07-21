from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.release_common import (  # noqa: E402
    RELEASE_MANIFEST_PATH,
    canonical_json,
    release_manifest,
)


def write_release_manifest(output: Path = RELEASE_MANIFEST_PATH) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(release_manifest()), encoding="utf-8")
    return output


def release_manifest_is_fresh(output: Path = RELEASE_MANIFEST_PATH) -> bool:
    return output.exists() and output.read_text(encoding="utf-8") == canonical_json(
        release_manifest()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or check the GeometryOS release manifest.")
    parser.add_argument("--output", type=Path, default=RELEASE_MANIFEST_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        if release_manifest_is_fresh(args.output):
            print(f"Release manifest is up to date: {args.output}")
            return 0
        if args.output.exists():
            print(f"Release manifest is out of date: {args.output}", file=sys.stderr)
        else:
            print(f"Release manifest file not found: {args.output}", file=sys.stderr)
        print("Run: uv run python scripts/export_release_manifest.py", file=sys.stderr)
        return 1

    path = write_release_manifest(args.output)
    print(f"Exported release manifest to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

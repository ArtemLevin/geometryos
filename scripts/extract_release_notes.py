from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from release_common import CHANGELOG_PATH, project_version


def extract_release_notes(version: str, changelog: Path = CHANGELOG_PATH) -> str:
    text = changelog.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\] - [^\n]+\n(?P<body>.*?)(?=^## \[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"CHANGELOG.md has no release section for {version}")
    body = match.group("body").strip()
    if not body:
        raise ValueError(f"CHANGELOG.md release section for {version} is empty")
    return f"# GeometryOS {version}\n\n{body}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract GeometryOS release notes from CHANGELOG.md.")
    parser.add_argument("--version", default=project_version())
    parser.add_argument("--changelog", type=Path, default=CHANGELOG_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        notes = extract_release_notes(args.version, args.changelog)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] release notes: {exc}", file=sys.stderr)
        return 1
    if args.output is None:
        print(notes, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(notes, encoding="utf-8")
        print(f"Extracted release notes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

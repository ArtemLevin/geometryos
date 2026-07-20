from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]


CHECKS: list[Check] = [
    Check("ruff", ["uv", "run", "ruff", "check", "."]),
    Check("format", ["uv", "run", "ruff", "format", "--check", "."]),
    Check("mypy", ["uv", "run", "mypy", "src"]),
    Check("pytest", ["uv", "run", "pytest"]),
    Check("schema", ["uv", "run", "python", "scripts/export_schema.py", "--check"]),
    Check("benchmarks", ["uv", "run", "python", "scripts/run_benchmarks.py"]),
    Check("cli benchmark", ["uv", "run", "gir", "benchmark", "--root", "."]),
    Check(
        "cli schema check",
        [
            "uv",
            "run",
            "gir",
            "export-schema",
            "--check",
            "--output",
            "schemas/gir-0.2.schema.json",
        ],
    ),
]


def run_check(check: Check) -> int:
    print(f"\n==> {check.name}", flush=True)
    print("$ " + " ".join(check.command), flush=True)
    started = monotonic()
    result = subprocess.run(check.command, cwd=ROOT, check=False)
    duration = monotonic() - started

    if result.returncode != 0:
        print(
            f"[FAIL] {check.name} ({duration:.2f}s, exit code {result.returncode})",
            flush=True,
        )
        return result.returncode

    print(f"[PASS] {check.name} ({duration:.2f}s)", flush=True)
    return 0


def main() -> int:
    for check in CHECKS:
        code = run_check(check)
        if code != 0:
            return code

    print("\nAll verification checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

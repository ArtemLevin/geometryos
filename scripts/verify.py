from __future__ import annotations

import subprocess
from dataclasses import dataclass


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
            "schemas/gir.schema.json",
        ],
    ),
]


def run_check(check: Check) -> int:
    print(f"\n==> {check.name}", flush=True)
    print("$ " + " ".join(check.command), flush=True)
    result = subprocess.run(check.command, check=False)
    if result.returncode != 0:
        print(f"\nFAILED: {check.name} exited with code {result.returncode}", flush=True)
    return result.returncode


def main() -> int:
    for check in CHECKS:
        code = run_check(check)
        if code != 0:
            return code

    print("\nAll verification checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence

VERIFY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("ruff", "check", "."),
    ("ruff", "format", "--check", "."),
    ("mypy", "src"),
    ("pytest",),
    (sys.executable, "scripts/export_schema.py"),
    (sys.executable, "scripts/run_benchmarks.py"),
)


def main() -> int:
    env = _verification_env()
    for command in VERIFY_COMMANDS:
        print(f"\n$ {_format_command(command)}", flush=True)
        completed = subprocess.run(command, check=False, env=env)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def _verification_env() -> Mapping[str, str]:
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    local_paths = [".", "src"]
    if existing_pythonpath:
        local_paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(local_paths)
    return env


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


if __name__ == "__main__":
    raise SystemExit(main())

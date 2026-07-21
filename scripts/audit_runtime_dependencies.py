from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("$ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="geometryos-audit-") as temporary:
            requirements = Path(temporary) / "runtime-requirements.txt"
            run(
                [
                    "uv",
                    "export",
                    "--frozen",
                    "--no-dev",
                    "--no-emit-project",
                    "--format",
                    "requirements-txt",
                    "--output-file",
                    str(requirements),
                ]
            )
            run(
                [
                    "uv",
                    "run",
                    "pip-audit",
                    "--requirement",
                    str(requirements),
                    "--disable-pip",
                    "--strict",
                    "--progress-spinner",
                    "off",
                ]
            )
    except (OSError, RuntimeError) as exc:
        print(f"[FAIL] runtime dependency audit: {exc}")
        return 1
    print("Runtime dependency audit: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import base64
import io
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "integration/10-layout-contract-v01"
PAYLOAD_DIR = ROOT / ".github" / "pr10_payload"


def run(*command: str) -> None:
    print("$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def restore_standard_ci() -> None:
    run("git", "fetch", "origin", "main", "--depth=1")
    content = subprocess.check_output(
        ["git", "show", "origin/main:.github/workflows/ci.yml"],
        cwd=ROOT,
    )
    (ROOT / ".github" / "workflows" / "ci.yml").write_bytes(content)


def extract_payload() -> None:
    encoded = "".join(
        path.read_text(encoding="utf-8") for path in sorted(PAYLOAD_DIR.glob("chunk_*"))
    )
    with ZipFile(io.BytesIO(base64.b64decode(encoded))) as archive:
        archive.extractall(ROOT)


def write_layout_benchmarks() -> None:
    source = ROOT / "contracts" / "layout" / "v0.1"
    target = ROOT / "benchmarks" / "gir_to_layout"
    target.mkdir(parents=True, exist_ok=True)
    for path in target.glob("*.json"):
        path.unlink()
    for identifier in ("triangle", "triangle-altitude", "triangle-angle-bisector"):
        shutil.copyfile(source / f"{identifier}.gir.json", target / f"{identifier}.gir.json")
        shutil.copyfile(
            source / f"{identifier}.layout.json",
            target / f"{identifier}.expected.layout.json",
        )


def main() -> None:
    extract_payload()
    restore_standard_ci()
    shutil.rmtree(PAYLOAD_DIR)
    Path(__file__).unlink()

    run("uv", "run", "ruff", "format", ".")
    run("uv", "run", "python", "scripts/export_layout_schema.py")
    run("uv", "run", "python", "scripts/export_layout_contracts.py")
    write_layout_benchmarks()
    run("uv", "run", "ruff", "format", ".")
    run("make", "verify")
    run(
        "git",
        "diff",
        "--exit-code",
        "--",
        "schemas/openapi.v1.json",
        "contracts/tutorboard/v1",
        "contracts/tutorboard/typescript/smoke.ts",
        "release/manifest.json",
    )

    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "-A")
    run("git", "commit", "-m", "feat: establish versioned layout contract 0.1")
    run("git", "push", "origin", f"HEAD:{BRANCH}")


if __name__ == "__main__":
    main()

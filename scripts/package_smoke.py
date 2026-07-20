from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PACKAGES: tuple[str, ...] = (
    "gir_ai",
    "gir_api",
    "gir_benchmarks",
    "gir_cli",
    "gir_core",
    "gir_render",
)


def load_project_metadata(path: Path = ROOT / "pyproject.toml") -> tuple[str, str]:
    data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data["project"]
    return str(project["name"]), str(project["version"])


def venv_python(venv_dir: Path, *, platform_name: str | None = None) -> Path:
    platform = platform_name or os.name
    if platform == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_cli(venv_dir: Path, command: str, *, platform_name: str | None = None) -> Path:
    platform = platform_name or os.name
    if platform == "nt":
        return venv_dir / "Scripts" / f"{command}.exe"
    return venv_dir / "bin" / command


def find_single_wheel(dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected exactly one wheel in {dist_dir}, found {len(wheels)}.")
    return wheels[0]


def import_smoke_code(project_name: str, project_version: str) -> str:
    packages = json.dumps(PUBLIC_PACKAGES)
    return (
        "import importlib\n"
        "from importlib.metadata import version\n"
        f"packages = {packages}\n"
        "for package in packages:\n"
        "    importlib.import_module(package)\n"
        f"actual = version({project_name!r})\n"
        f"assert actual == {project_version!r}, (actual, {project_version!r})\n"
        "print('installed package imports: ok')\n"
    )


def clean_subprocess_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def run_step(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> None:
    print(f"\n==> {name}", flush=True)
    print("$ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {completed.returncode}.")
    print(f"[PASS] {name}", flush=True)


def main() -> int:
    project_name, project_version = load_project_metadata()

    try:
        with tempfile.TemporaryDirectory(prefix="geometryos-package-smoke-") as temporary:
            temp_root = Path(temporary)
            dist_dir = temp_root / "dist"
            venv_dir = temp_root / "venv"
            dist_dir.mkdir()

            run_step(
                "wheel build",
                ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
                cwd=ROOT,
            )
            wheel = find_single_wheel(dist_dir)

            run_step(
                "isolated environment creation",
                ["uv", "venv", "--python", "3.11", str(venv_dir)],
                cwd=temp_root,
            )
            python = venv_python(venv_dir)

            run_step(
                "wheel installation",
                ["uv", "pip", "install", "--python", str(python), str(wheel)],
                cwd=temp_root,
            )
            run_step(
                "installed dependency check",
                ["uv", "pip", "check", "--python", str(python)],
                cwd=temp_root,
            )

            clean_env = clean_subprocess_env()
            run_step(
                "installed package imports",
                [python.as_posix(), "-c", import_smoke_code(project_name, project_version)],
                cwd=temp_root,
                env=clean_env,
            )
            run_step(
                "installed CLI",
                [venv_cli(venv_dir, "gir").as_posix(), "--help"],
                cwd=temp_root,
                env=clean_env,
            )
    except (OSError, RuntimeError, KeyError, tomllib.TOMLDecodeError) as exc:
        print(f"\n[FAIL] package smoke: {exc}", flush=True)
        return 1

    print("\nAll package smoke checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

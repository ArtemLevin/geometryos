from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.generate_python_sbom import generate_sbom  # noqa: E402
from scripts.release_common import (  # noqa: E402
    CONTRACT_ROOT,
    GIR_SCHEMA_PATH,
    OPENAPI_PATH,
    RELEASE_MANIFEST_PATH,
    ROOT,
    canonical_json,
    project_name,
    project_version,
    release_bundle_dir,
    release_manifest,
    sdist_filename,
    sha256_file,
    wheel_filename,
)

PUBLIC_PACKAGES = (
    "gir_meta",
    "gir_ai",
    "gir_application",
    "gir_api",
    "gir_benchmarks",
    "gir_cli",
    "gir_core",
    "gir_render",
)


def run(name: str, command: list[str], *, cwd: Path = ROOT) -> None:
    print(f"\n==> {name}")
    print("$ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {completed.returncode}")
    print(f"[PASS] {name}")


def venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def venv_cli(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "gir.exe"
    return venv / "bin" / "gir"


def verify_wheel_metadata(wheel: Path, version: str) -> None:
    with zipfile.ZipFile(wheel) as archive:
        metadata_paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            raise RuntimeError(f"Expected one wheel METADATA file, found {len(metadata_paths)}")
        metadata = Parser().parsestr(archive.read(metadata_paths[0]).decode("utf-8"))
    expected = {
        "Name": project_name(),
        "Version": version,
        "Requires-Python": ">=3.11",
    }
    for key, expected_value in expected.items():
        if metadata.get(key) != expected_value:
            raise RuntimeError(
                f"Wheel metadata {key} mismatch: {metadata.get(key)!r} != {expected_value!r}"
            )


def install_and_smoke(wheel: Path, venv: Path, version: str) -> Path:
    run("create isolated release environment", ["uv", "venv", "--python", "3.11", str(venv)])
    python = venv_python(venv)
    run(
        "install release wheel",
        ["uv", "pip", "install", "--python", str(python), str(wheel)],
    )
    run("check installed dependencies", ["uv", "pip", "check", "--python", str(python)])
    package_list = json.dumps(PUBLIC_PACKAGES)
    smoke = (
        "import importlib\n"
        "from importlib.metadata import version\n"
        f"packages = {package_list}\n"
        "for package in packages:\n"
        "    importlib.import_module(package)\n"
        f"assert version('gir') == {version!r}\n"
        "print('release imports: ok')\n"
    )
    run("verify installed release imports", [str(python), "-c", smoke], cwd=venv.parent)
    run("verify installed CLI version", [str(venv_cli(venv)), "--version"], cwd=venv.parent)
    return python


def rebuild_wheel_from_sdist(sdist: Path, temporary: Path, version: str) -> None:
    unpacked = temporary / "sdist"
    unpacked.mkdir()
    with tarfile.open(sdist, "r:gz") as archive:
        archive.extractall(unpacked, filter="data")
    roots = [path for path in unpacked.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"Expected one source-distribution root, found {len(roots)}")
    rebuilt = temporary / "rebuilt"
    rebuilt.mkdir()
    run(
        "rebuild wheel from source distribution",
        ["uv", "build", "--wheel", "--out-dir", str(rebuilt)],
        cwd=roots[0],
    )
    wheels = list(rebuilt.glob("*.whl"))
    if len(wheels) != 1 or wheels[0].name != wheel_filename(version):
        raise RuntimeError("Source distribution did not reproduce the expected wheel filename")
    verify_wheel_metadata(wheels[0], version)


def add_contract_archive(output: Path) -> Path:
    archive_path = output / "tutorboard-v1-contracts.tar.gz"
    with (
        archive_path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as archive,
    ):
        for path in sorted(CONTRACT_ROOT.rglob("*")):
            if not path.is_file():
                continue
            relative = Path("tutorboard") / "v1" / path.relative_to(CONTRACT_ROOT)
            info = archive.gettarinfo(str(path), arcname=relative.as_posix())
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            with path.open("rb") as source:
                archive.addfile(info, source)
    return archive_path


def write_checksums(output: Path) -> Path:
    checksum_path = output / "SHA256SUMS"
    lines = [
        f"{sha256_file(path)}  {path.name}"
        for path in sorted(output.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.name != checksum_path.name
    ]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def build_release(output: Path | None = None) -> Path:
    version = project_version()
    destination = output or release_bundle_dir(version)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    expected_manifest = canonical_json(release_manifest(version))
    if RELEASE_MANIFEST_PATH.read_text(encoding="utf-8") != expected_manifest:
        raise RuntimeError("Committed release manifest is stale")

    with tempfile.TemporaryDirectory(prefix="geometryos-release-") as temporary_name:
        temporary = Path(temporary_name)
        build_dir = temporary / "build"
        build_dir.mkdir()
        run("build wheel and source distribution", ["uv", "build", "--out-dir", str(build_dir)])

        wheel = build_dir / wheel_filename(version)
        sdist = build_dir / sdist_filename(version)
        if not wheel.is_file() or not sdist.is_file():
            raise RuntimeError("Expected wheel and source distribution were not produced")
        verify_wheel_metadata(wheel, version)
        rebuild_wheel_from_sdist(sdist, temporary, version)

        installed_python = install_and_smoke(wheel, temporary / "venv", version)

        shutil.copy2(wheel, destination / wheel.name)
        shutil.copy2(sdist, destination / sdist.name)
        shutil.copy2(OPENAPI_PATH, destination / OPENAPI_PATH.name)
        shutil.copy2(GIR_SCHEMA_PATH, destination / GIR_SCHEMA_PATH.name)
        shutil.copy2(
            RELEASE_MANIFEST_PATH,
            destination / f"geometryos-{version}.release-manifest.json",
        )
        add_contract_archive(destination)
        generate_sbom(installed_python, destination / f"geometryos-{version}.cdx.json")
        write_checksums(destination)

    print(f"\nRelease bundle created: {destination}")
    for path in sorted(destination.iterdir()):
        print(f"- {path.name}")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the GeometryOS release bundle.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        build_release(args.output)
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"[FAIL] release build: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

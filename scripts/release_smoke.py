from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path

from release_common import (
    canonical_json,
    project_version,
    release_bundle_dir,
    release_manifest,
    sdist_filename,
    sha256_file,
    wheel_filename,
)


def expected_files(version: str) -> set[str]:
    return {
        wheel_filename(version),
        sdist_filename(version),
        "openapi.v1.json",
        "gir-0.2.schema.json",
        "tutorboard-v1-contracts.tar.gz",
        f"geometryos-{version}.release-manifest.json",
        f"geometryos-{version}.cdx.json",
        "SHA256SUMS",
    }


def verify_checksums(bundle: Path) -> None:
    checksum_file = bundle / "SHA256SUMS"
    entries: dict[str, str] = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if not separator or not digest or not name:
            raise RuntimeError(f"Invalid SHA256SUMS line: {line!r}")
        entries[name] = digest
    expected_names = expected_files(project_version()) - {"SHA256SUMS"}
    if set(entries) != expected_names:
        raise RuntimeError(f"SHA256SUMS entries mismatch: {set(entries)!r}")
    for name, expected_digest in entries.items():
        actual_digest = sha256_file(bundle / name)
        if actual_digest != expected_digest:
            raise RuntimeError(f"Checksum mismatch for {name}")


def verify_manifest(bundle: Path, version: str) -> None:
    path = bundle / f"geometryos-{version}.release-manifest.json"
    if path.read_text(encoding="utf-8") != canonical_json(release_manifest(version)):
        raise RuntimeError("Release manifest in bundle is stale or non-canonical")


def verify_sbom(bundle: Path, version: str) -> None:
    document = json.loads((bundle / f"geometryos-{version}.cdx.json").read_text(encoding="utf-8"))
    if document.get("bomFormat") != "CycloneDX" or document.get("specVersion") != "1.5":
        raise RuntimeError("Release SBOM is not CycloneDX 1.5")
    components = document.get("components")
    if not isinstance(components, list):
        raise RuntimeError("Release SBOM has no component list")
    if not any(
        component.get("name", "").lower() == "gir" and component.get("version") == version
        for component in components
        if isinstance(component, dict)
    ):
        raise RuntimeError("Release SBOM does not contain the GeometryOS distribution")


def verify_contract_archive(bundle: Path) -> None:
    path = bundle / "tutorboard-v1-contracts.tar.gz"
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        for name in names:
            member = Path(name)
            if member.is_absolute() or ".." in member.parts:
                raise RuntimeError(f"Unsafe contract archive member: {name}")
        required = {
            "tutorboard/v1/README.md",
            "tutorboard/v1/manifest.json",
            "tutorboard/v1/generate-success.request.json",
            "tutorboard/v1/generate-success.response.json",
        }
        if not required.issubset(names):
            raise RuntimeError("TutorBoard contract archive is incomplete")


def verify_bundle(bundle: Path) -> None:
    version = project_version()
    if not bundle.is_dir():
        raise RuntimeError(f"Release bundle directory not found: {bundle}")
    actual = {path.name for path in bundle.iterdir() if path.is_file()}
    expected = expected_files(version)
    if actual != expected:
        raise RuntimeError(f"Release bundle files mismatch: expected {expected!r}, got {actual!r}")
    forbidden = {".env", "node_modules", "geometryos.ts", "pytest", "ruff", "mypy"}
    if actual & forbidden:
        raise RuntimeError(f"Forbidden release files found: {actual & forbidden}")
    verify_checksums(bundle)
    verify_manifest(bundle, version)
    verify_sbom(bundle, version)
    verify_contract_archive(bundle)
    json.loads((bundle / "openapi.v1.json").read_text(encoding="utf-8"))
    json.loads((bundle / "gir-0.2.schema.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a GeometryOS release bundle.")
    parser.add_argument("--bundle", type=Path, default=release_bundle_dir())
    args = parser.parse_args()
    try:
        verify_bundle(args.bundle)
    except (OSError, RuntimeError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"[FAIL] release smoke: {exc}")
        return 1
    print(f"Release bundle smoke passed: {args.bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

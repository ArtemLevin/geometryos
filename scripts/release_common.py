from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "pyproject.toml"
RELEASE_MANIFEST_PATH = ROOT / "release" / "manifest.json"
OPENAPI_PATH = ROOT / "schemas" / "openapi.v1.json"
GIR_SCHEMA_PATH = ROOT / "schemas" / "gir-0.2.schema.json"
CONTRACT_ROOT = ROOT / "contracts" / "tutorboard" / "v1"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"

SERVICE_NAME = "GeometryOS"
DISTRIBUTION_NAME = "gir"
API_MAJOR = "v1"
API_VERSION = "1.0.0"
GIR_SCHEMA_VERSION = "0.2.0"
TUTORBOARD_CONTRACT = "tutorboard/v1"
PYTHON_MINIMUM = "3.11"
PYTHON_VERIFIED = "3.11"
CONTAINER_REGISTRY = "ghcr.io"
CONTAINER_IMAGE = "ghcr.io/artemlevin/geometryos"
CONTAINER_PLATFORMS = ["linux/amd64"]


def read_project() -> dict[str, Any]:
    return tomllib.loads(PROJECT_PATH.read_text(encoding="utf-8"))


def project_name() -> str:
    return str(read_project()["project"]["name"])


def project_version() -> str:
    return str(read_project()["project"]["version"])


def release_tag(version: str | None = None) -> str:
    return f"v{version or project_version()}"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def release_manifest(version: str | None = None) -> dict[str, Any]:
    resolved_version = version or project_version()
    return {
        "api": {
            "namespace": API_MAJOR,
            "version": API_VERSION,
        },
        "artifacts": [
            "wheel",
            "source-distribution",
            "openapi",
            "gir-schema",
            "tutorboard-contracts",
            "checksums",
            "cyclonedx-sbom",
        ],
        "container": {
            "image": CONTAINER_IMAGE,
            "platforms": CONTAINER_PLATFORMS,
            "registry": CONTAINER_REGISTRY,
        },
        "distribution": DISTRIBUTION_NAME,
        "gir_schema_version": GIR_SCHEMA_VERSION,
        "python": {
            "minimum": PYTHON_MINIMUM,
            "verified": PYTHON_VERIFIED,
        },
        "service": SERVICE_NAME,
        "tag": release_tag(resolved_version),
        "tutorboard_contract": TUTORBOARD_CONTRACT,
        "version": resolved_version,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wheel_filename(version: str | None = None) -> str:
    return f"{DISTRIBUTION_NAME}-{version or project_version()}-py3-none-any.whl"


def sdist_filename(version: str | None = None) -> str:
    return f"{DISTRIBUTION_NAME}-{version or project_version()}.tar.gz"


def release_bundle_dir(version: str | None = None) -> Path:
    return ROOT / "dist" / "release" / (version or project_version())

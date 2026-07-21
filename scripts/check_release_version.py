from __future__ import annotations

import argparse
import json
import re
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for search_path in (ROOT, SRC):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from gir_api.constants import API_V1_VERSION  # noqa: E402
from gir_meta import (  # noqa: E402
    API_MAJOR,
    API_VERSION,
    DISTRIBUTION_NAME,
    GIR_SCHEMA_VERSION,
    SERVICE_VERSION,
    TUTORBOARD_CONTRACT,
)
from scripts.release_common import (  # noqa: E402
    CHANGELOG_PATH,
    OPENAPI_PATH,
    RELEASE_MANIFEST_PATH,
    canonical_json,
    project_name,
    project_version,
    release_manifest,
    release_tag,
)


def _extract(pattern: str, path: Path, label: str, errors: list[str]) -> str | None:
    match = re.search(pattern, path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    if match is None:
        errors.append(f"{label}: value not found in {path.relative_to(ROOT)}")
        return None
    return match.group(1)


def _expect(label: str, actual: object, expected: object, errors: list[str]) -> None:
    if actual != expected:
        errors.append(f"{label}: expected {expected!r}, got {actual!r}")


def check_version(expected_tag: str | None = None) -> list[str]:
    errors: list[str] = []
    service_version = project_version()
    _expect("distribution name", project_name(), DISTRIBUTION_NAME, errors)
    _expect("gir_meta service version", SERVICE_VERSION, service_version, errors)
    _expect("API version constant", API_V1_VERSION, API_VERSION, errors)
    _expect("API major", API_MAJOR, "v1", errors)
    _expect("GIR schema version", GIR_SCHEMA_VERSION, "0.2.0", errors)
    _expect("TutorBoard contract", TUTORBOARD_CONTRACT, "tutorboard/v1", errors)

    try:
        installed = installed_version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        errors.append(f"installed distribution not found: {DISTRIBUTION_NAME}")
    else:
        _expect("installed distribution version", installed, service_version, errors)

    docker_version = _extract(
        r"^ARG BUILD_VERSION=([^\s]+)$",
        ROOT / "Dockerfile",
        "Docker BUILD_VERSION",
        errors,
    )
    make_project_version = _extract(
        r"^PROJECT_VERSION := (.+)$",
        ROOT / "Makefile",
        "Makefile PROJECT_VERSION",
        errors,
    )
    make_version = _extract(
        r"^BUILD_VERSION \?= ([^\s]+)$",
        ROOT / "Makefile",
        "Makefile BUILD_VERSION",
        errors,
    )
    compose_version = _extract(
        r"BUILD_VERSION: \$\{GEOMETRYOS_BUILD_VERSION:-([^}]+)\}",
        ROOT / "compose.yaml",
        "Compose BUILD_VERSION",
        errors,
    )
    env_version = _extract(
        r"^GEOMETRYOS_BUILD_VERSION=(.+)$",
        ROOT / ".env.example",
        ".env.example BUILD_VERSION",
        errors,
    )

    _expect(
        "Makefile PROJECT_VERSION",
        make_project_version,
        "$(shell $(PYTHON) scripts/print_version.py)",
        errors,
    )
    if make_version not in {service_version, "$(PROJECT_VERSION)"}:
        errors.append(
            "Makefile BUILD_VERSION: expected the canonical service version or "
            f"'$(PROJECT_VERSION)', got {make_version!r}"
        )
    for label, actual in (
        ("Docker BUILD_VERSION", docker_version),
        ("Compose BUILD_VERSION", compose_version),
        (".env.example BUILD_VERSION", env_version),
    ):
        if actual is not None:
            _expect(label, actual, service_version, errors)

    if not OPENAPI_PATH.exists():
        errors.append("OpenAPI artifact is missing")
    else:
        openapi = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        _expect("OpenAPI API version", openapi["info"]["version"], API_VERSION, errors)
        _expect(
            "OpenAPI service version",
            openapi["info"].get("x-geometryos-service-version"),
            service_version,
            errors,
        )
        _expect(
            "OpenAPI GIR schema version",
            openapi["info"].get("x-geometryos-gir-schema-version"),
            GIR_SCHEMA_VERSION,
            errors,
        )
        _expect(
            "OpenAPI TutorBoard contract",
            openapi["info"].get("x-geometryos-consumer-contract"),
            TUTORBOARD_CONTRACT,
            errors,
        )

    if not RELEASE_MANIFEST_PATH.exists():
        errors.append("release manifest is missing")
    else:
        committed_manifest = RELEASE_MANIFEST_PATH.read_text(encoding="utf-8")
        expected_manifest = canonical_json(release_manifest(service_version))
        if committed_manifest != expected_manifest:
            errors.append("release manifest is stale or non-canonical")

    changelog_heading = f"## [{service_version}] - "
    if not CHANGELOG_PATH.exists():
        errors.append("CHANGELOG.md is missing")
    elif changelog_heading not in CHANGELOG_PATH.read_text(encoding="utf-8"):
        errors.append(f"CHANGELOG.md has no release heading for {service_version}")

    if expected_tag is not None:
        _expect("release tag", expected_tag, release_tag(service_version), errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check GeometryOS release-version consistency.")
    parser.add_argument("--expected-tag", help="Expected Git tag, for example v0.2.0.")
    args = parser.parse_args()
    errors = check_version(args.expected_tag)
    if errors:
        print("Version consistency: failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"service version:     {project_version()}")
    print(f"git tag:             {release_tag()}")
    print(f"API version:         {API_VERSION}")
    print(f"GIR schema:          {GIR_SCHEMA_VERSION}")
    print(f"TutorBoard contract: {TUTORBOARD_CONTRACT}")
    print("\nVersion consistency: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from gir_core.compatibility import GirCompatibilityResult, canonicalize_gir_payload
from gir_core.models.scene import GirScene
from gir_core.normalize import normalize_gir
from gir_core.schema import check_gir_schema, gir_json_schema
from gir_core.versioning import GIR_SCHEMA_ID, GIR_SCHEMA_VERSION, LEGACY_GIR_VERSION

ROOT = Path(__file__).resolve().parents[1]
LEGACY_FIXTURE = ROOT / "tests/fixtures/gir/v0_1/altitude.legacy.gir.json"
SCHEMA_ARTIFACT = ROOT / "schemas/gir-0.2.schema.json"


def canonical_payload() -> dict[str, Any]:
    return {
        "schema_version": GIR_SCHEMA_VERSION,
        "scene_type": "2d",
        "objects": [],
        "constraints": [],
        "construction_steps": [],
        "metadata": {},
    }


def error_types(payload: object) -> set[str]:
    with pytest.raises(ValidationError) as exc_info:
        GirScene.model_validate(payload)
    return {str(error["type"]) for error in exc_info.value.errors()}


def test_canonical_gir_0_2_is_accepted_and_serialized_canonically() -> None:
    scene = GirScene.model_validate(canonical_payload())

    assert scene.schema_version == GIR_SCHEMA_VERSION
    dumped = scene.model_dump()
    assert dumped["schema_version"] == GIR_SCHEMA_VERSION
    assert "version" not in dumped


def test_legacy_gir_0_1_is_upgraded_without_mutating_input() -> None:
    payload = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
    original = json.loads(json.dumps(payload))

    result = canonicalize_gir_payload(payload)

    assert isinstance(result, GirCompatibilityResult)
    assert result.upgraded is True
    assert result.source_version == LEGACY_GIR_VERSION
    assert result.target_version == GIR_SCHEMA_VERSION
    assert result.payload["schema_version"] == GIR_SCHEMA_VERSION
    assert "version" not in result.payload
    assert payload == original

    scene = GirScene.model_validate(payload)
    assert scene.schema_version == GIR_SCHEMA_VERSION
    assert "version" not in scene.model_dump()


def test_missing_schema_version_is_rejected() -> None:
    payload = canonical_payload()
    del payload["schema_version"]
    assert "gir_schema_version_missing" in error_types(payload)


def test_canonical_and_legacy_fields_conflict() -> None:
    payload = canonical_payload()
    payload["version"] = LEGACY_GIR_VERSION
    assert "gir_schema_version_conflict" in error_types(payload)


@pytest.mark.parametrize("version", ["0.2", "0.2.1", "0.3.0", "1.0.0", "latest", 0.2])
def test_unsupported_canonical_versions_are_rejected(version: object) -> None:
    payload = canonical_payload()
    payload["schema_version"] = version
    assert "gir_schema_version_unsupported" in error_types(payload)


@pytest.mark.parametrize("version", ["0.0", "0.1.0", "0.2.0", "1", 1])
def test_unsupported_legacy_versions_are_rejected(version: object) -> None:
    payload = canonical_payload()
    del payload["schema_version"]
    payload["version"] = version
    assert "gir_legacy_version_unsupported" in error_types(payload)


def test_normalization_preserves_canonical_version() -> None:
    scene = GirScene.model_validate(canonical_payload())
    assert normalize_gir(scene).schema_version == GIR_SCHEMA_VERSION


def test_generated_schema_declares_the_canonical_contract() -> None:
    schema = gir_json_schema()

    assert schema["$id"] == GIR_SCHEMA_ID
    assert schema["x-gir-schema-version"] == GIR_SCHEMA_VERSION
    assert schema["properties"]["schema_version"]["const"] == GIR_SCHEMA_VERSION
    assert "schema_version" in schema["required"]
    assert "version" not in schema["properties"]


def test_committed_gir_0_2_schema_is_fresh() -> None:
    assert check_gir_schema(SCHEMA_ARTIFACT)

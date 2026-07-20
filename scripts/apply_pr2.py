from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/gir-0.2.schema.json"


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        return
    target.write_text(text.replace(old, new), encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n\n" + content.rstrip() + "\n", encoding="utf-8")


write(
    "src/gir_core/versioning.py",
    '''from typing import Final

GIR_SCHEMA_VERSION: Final = "0.2.0"
LEGACY_GIR_VERSION: Final = "0.1"
GIR_SCHEMA_ID: Final = f"urn:geometryos:gir:{GIR_SCHEMA_VERSION}"

SUPPORTED_CANONICAL_VERSIONS: Final = frozenset({GIR_SCHEMA_VERSION})
SUPPORTED_LEGACY_VERSIONS: Final = frozenset({LEGACY_GIR_VERSION})
''',
)

write(
    "src/gir_core/compatibility.py",
    '''from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from pydantic_core import PydanticCustomError

from gir_core.versioning import GIR_SCHEMA_VERSION, LEGACY_GIR_VERSION


@dataclass(frozen=True)
class GirCompatibilityResult:
    payload: dict[str, Any]
    source_version: str
    target_version: str
    upgraded: bool


def canonicalize_gir_payload(value: object) -> GirCompatibilityResult | object:
    """Convert a supported raw GIR payload to the canonical schema version.

    This function only handles the top-level version marker. It never repairs,
    normalizes or semantically validates geometry.
    """
    if not isinstance(value, Mapping):
        return value

    mapping = cast(Mapping[str, Any], value)
    payload = dict(mapping)
    has_schema_version = "schema_version" in payload
    has_legacy_version = "version" in payload

    if has_schema_version and has_legacy_version:
        raise PydanticCustomError(
            "gir_schema_version_conflict",
            "Use either 'schema_version' or legacy 'version', not both.",
        )

    if not has_schema_version and not has_legacy_version:
        raise PydanticCustomError(
            "gir_schema_version_missing",
            "GIR schema version is required.",
        )

    if has_schema_version:
        source_version = payload["schema_version"]
        if source_version != GIR_SCHEMA_VERSION:
            raise PydanticCustomError(
                "gir_schema_version_unsupported",
                "Unsupported GIR schema version '{version}'.",
                {"version": str(source_version)},
            )
        return GirCompatibilityResult(
            payload=payload,
            source_version=GIR_SCHEMA_VERSION,
            target_version=GIR_SCHEMA_VERSION,
            upgraded=False,
        )

    source_version = payload["version"]
    if source_version != LEGACY_GIR_VERSION:
        raise PydanticCustomError(
            "gir_legacy_version_unsupported",
            "Unsupported legacy GIR version '{version}'.",
            {"version": str(source_version)},
        )

    canonical = dict(payload)
    del canonical["version"]
    canonical["schema_version"] = GIR_SCHEMA_VERSION
    return GirCompatibilityResult(
        payload=canonical,
        source_version=LEGACY_GIR_VERSION,
        target_version=GIR_SCHEMA_VERSION,
        upgraded=True,
    )
''',
)

write(
    "src/gir_core/models/scene.py",
    '''from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gir_core.compatibility import GirCompatibilityResult, canonicalize_gir_payload
from gir_core.models.constraints import GirConstraint
from gir_core.models.construction import ConstructionStep
from gir_core.models.objects import GirObject
from gir_core.versioning import GIR_SCHEMA_ID, GIR_SCHEMA_VERSION


class GirScene(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "$id": GIR_SCHEMA_ID,
            "x-gir-schema-version": GIR_SCHEMA_VERSION,
        },
    )

    schema_version: Literal["0.2.0"]
    scene_type: Literal["2d"]
    objects: list[GirObject]
    constraints: list[GirConstraint]
    construction_steps: list[ConstructionStep]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def canonicalize_schema_version(cls, value: object) -> object:
        result = canonicalize_gir_payload(value)
        if isinstance(result, GirCompatibilityResult):
            return result.payload
        return result
''',
)

# Migrate every canonical benchmark scene while preserving all geometry content.
legacy_source = ROOT / "benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json"
legacy_payload = json.loads(legacy_source.read_text(encoding="utf-8"))
legacy_payload.pop("schema_version", None)
legacy_payload["version"] = "0.1"
write(
    "tests/fixtures/gir/v0_1/altitude.legacy.gir.json",
    json.dumps(legacy_payload, ensure_ascii=False, indent=2),
)

for path in sorted((ROOT / "benchmarks").rglob("*.gir.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("version", None)
    payload["schema_version"] = "0.2.0"
    ordered = {"schema_version": payload.pop("schema_version"), **payload}
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Canonical test inputs must use GIR 0.2. Legacy input remains isolated above.
for path in sorted((ROOT / "tests").glob("*.py")):
    text = path.read_text(encoding="utf-8")
    text = text.replace('"version": "0.1"', '"schema_version": "0.2.0"')
    text = text.replace("version=\"0.1\"", "schema_version=\"0.2.0\"")
    path.write_text(text, encoding="utf-8")

adapter = ROOT / "src/gir_ai/text_to_gir/adapter.py"
adapter_text = adapter.read_text(encoding="utf-8")
adapter_text = adapter_text.replace(
    "from gir_core.models.scene import GirScene\n",
    "from gir_core.models.scene import GirScene\nfrom gir_core.versioning import GIR_SCHEMA_VERSION\n",
)
adapter_text = adapter_text.replace(
    '"version": "0.1"',
    '"schema_version": GIR_SCHEMA_VERSION',
)
adapter.write_text(adapter_text, encoding="utf-8")

# Publish the versioned schema path everywhere it is an operational command.
for path in [
    *ROOT.glob("*.md"),
    *(ROOT / "docs").rglob("*.md"),
    ROOT / "Makefile",
    ROOT / "scripts/export_schema.py",
    ROOT / "scripts/verify.py",
    ROOT / "src/gir_cli/main.py",
    ROOT / "tests/test_cli.py",
    ROOT / "tests/test_verify_contract.py",
]:
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    text = text.replace("schemas/gir.schema.json", SCHEMA_PATH)
    text = text.replace('Path("schemas/gir.schema.json")', f'Path("{SCHEMA_PATH}")')
    path.write_text(text, encoding="utf-8")

replace(
    "scripts/export_schema.py",
    'SCHEMA_PATH = ROOT / "schemas" / "gir.schema.json"',
    'SCHEMA_PATH = ROOT / "schemas" / "gir-0.2.schema.json"',
)
replace(
    "Makefile",
    "schema: ## Export GIR JSON Schema to schemas/gir.schema.json.",
    "schema: ## Export GIR 0.2 JSON Schema to schemas/gir-0.2.schema.json.",
)

old_schema = ROOT / "schemas/gir.schema.json"
if old_schema.exists():
    old_schema.unlink()

write(
    "tests/test_gir_versioning.py",
    '''from __future__ import annotations

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
''',
)

append_once(
    "tests/test_api_generate.py",
    "test_generate_returns_canonical_gir_0_2",
    '''def test_generate_returns_canonical_gir_0_2(client: Any) -> None:
    response = client.post(
        "/generate",
        json={
            "input_type": "text",
            "input": ALTITUDE_PROMPT,
            "output": [],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    gir = response.json()["gir"]
    assert gir["schema_version"] == "0.2.0"
    assert "version" not in gir
''',
)

append_once(
    "tests/test_api_validate.py",
    "test_validate_gir_accepts_legacy_0_1",
    '''def test_validate_gir_accepts_legacy_0_1(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["version"] = "0.1"
    del valid_altitude_payload["schema_version"]

    response = client.post("/validate-gir", json=valid_altitude_payload)

    assert response.status_code == 200
    assert response.json()["is_valid"] is True


def test_validate_gir_rejects_missing_schema_version(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    del valid_altitude_payload["schema_version"]
    response = client.post("/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "gir_schema_version_missing"


def test_validate_gir_rejects_unknown_schema_version(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["schema_version"] = "0.3.0"
    response = client.post("/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "gir_schema_version_unsupported"


def test_validate_gir_rejects_conflicting_version_fields(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["version"] = "0.1"
    response = client.post("/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "gir_schema_version_conflict"
''',
)

append_once(
    "tests/test_api_render.py",
    "test_render_rejects_unknown_schema_version",
    '''def test_render_rejects_unknown_schema_version(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["schema_version"] = "0.3.0"
    response = client.post("/render/svg", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "gir_schema_version_unsupported"
''',
)

append_once(
    "tests/test_cli.py",
    "test_cli_validate_accepts_legacy_gir_0_1",
    '''def test_cli_validate_accepts_legacy_gir_0_1() -> None:
    runner = CliRunner()
    legacy = ROOT / "tests/fixtures/gir/v0_1/altitude.legacy.gir.json"
    result = runner.invoke(app, ["validate", str(legacy)])

    assert result.exit_code == 0
    assert '"is_valid": true' in result.output


def test_cli_validate_rejects_unknown_schema_version(tmp_path: Path) -> None:
    runner = CliRunner()
    payload = json.loads(VALID_SCENE.read_text(encoding="utf-8"))
    payload["schema_version"] = "0.3.0"
    future_scene = tmp_path / "future.gir.json"
    future_scene.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(app, ["validate", str(future_scene)])

    assert result.exit_code != 0
''',
)
replace("tests/test_cli.py", "from pathlib import Path\n", "import json\nfrom pathlib import Path\n")

append_once(
    "tests/test_text_to_gir_adapter.py",
    "test_all_successful_adapter_scenes_emit_canonical_gir_0_2",
    '''def test_all_successful_adapter_scenes_emit_canonical_gir_0_2() -> None:
    prompts = [
        "Постройте треугольник ABC.",
        "Постройте треугольник ABC. Отметьте середину M стороны BC.",
        "Постройте треугольник ABC. Проведите медиану из вершины A к стороне BC.",
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
        "Постройте треугольник ABC. Проведите биссектрису угла A.",
    ]

    for prompt in prompts:
        result = text_to_gir(prompt)
        assert result.status == "success"
        assert result.gir is not None
        assert result.gir.schema_version == "0.2.0"
        assert "version" not in result.gir.model_dump()
''',
)

append_once(
    "tests/test_benchmarks.py",
    "test_text_to_gir_success_fixtures_are_canonical_gir_0_2",
    '''def test_text_to_gir_success_fixtures_are_canonical_gir_0_2() -> None:
    for path in TEXT_TO_GIR.glob("*/*.expected.gir.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "0.2.0", path
        assert "version" not in payload, path
''',
)

append_once(
    "tests/test_render_benchmarks.py",
    "test_render_benchmark_inputs_are_canonical_gir_0_2",
    '''def test_render_benchmark_inputs_are_canonical_gir_0_2() -> None:
    for directory in (SVG_BENCHMARKS, TIKZ_BENCHMARKS):
        for path in directory.glob("*.gir.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["schema_version"] == "0.2.0", path
            assert "version" not in payload, path
''',
)

write(
    "docs/GIR_SPEC.md",
    '''# GIR Specification 0.2

## Purpose

Geometry Intermediate Representation (GIR) is the canonical mathematical contract between parsers, validators, layout engines, renderers and external consumers such as TutorBoard. GIR describes what a construction means independently of screen coordinates and UI state.

## Canonical schema version

Every canonical scene must contain:

```json
{"schema_version":"0.2.0"}
```

`schema_version` is required and is serialized in every GIR 0.2 output. The legacy field `version` is not part of the GIR 0.2 schema.

## Scene structure

A scene contains:

- `schema_version`: exactly `0.2.0`;
- `scene_type`: currently exactly `2d`;
- `objects`: typed mathematical objects;
- `constraints`: typed semantic relationships;
- `construction_steps`: an ordered explanatory construction sequence;
- `metadata`: optional non-semantic producer metadata.

## Objects

The current object union includes points, segments, lines, rays, circles, triangles, angles and labels. Object identifiers are stable references used by constraints and construction steps.

## Constraints

The current constraint union includes membership, collinearity, non-collinearity, parallelism, perpendicularity, equal length, midpoint, intersection, altitude, median, angle bisector, circumcircle and incircle relationships.

## Structural validation

Pydantic validates required fields, discriminated unions, field types, forbidden extra fields and the exact GIR schema version before semantic validation runs.

Unknown, missing or conflicting schema versions are rejected. GeometryOS never attempts best-effort parsing of an unknown GIR version.

## Semantic validation

Semantic validation is structural and type-aware, but it is not a geometric solver. It checks, among other invariants:

- referenced objects and constraints exist;
- object and constraint ids are unique;
- point roles reference points;
- line-like roles reference segments, lines or rays as appropriate;
- segment endpoints, triangle vertices and angle points are distinct;
- altitude, median, midpoint, angle-bisector, circumcircle and incircle roles target compatible types;
- construction steps reference existing objects and constraints.

It does not prove global constructibility or solve arbitrary systems of geometric constraints.

## Normalization and rendering

Compatibility conversion completes before a `GirScene` exists. Normalization therefore receives canonical GIR 0.2 only. Renderers receive semantically valid canonical scenes and must not invent or repair geometry.

## GIR versus board state

GIR does not store TutorBoard presentation state such as camera position, zoom, selection, cursors, toolbar state, z-index, WebSocket state or collaboration metadata. Layout coordinates and visual interaction state belong to dedicated downstream models.

## Compatibility

GeometryOS temporarily reads legacy GIR 0.1 payloads containing `version: "0.1"`. The compatibility layer performs one transformation only: it replaces that top-level marker with `schema_version: "0.2.0"`. It does not add missing geometry, remove unknown fields or repair semantic errors.

All writers, API outputs, CLI-generated scenes and benchmark fixtures use GIR 0.2. See `docs/COMPATIBILITY.md` for the compatibility policy.
''',
)

write(
    "docs/COMPATIBILITY.md",
    '''# GeometryOS Compatibility Policy

## Independent version domains

GeometryOS maintains three independent version domains:

| Domain | Current value in this phase | Meaning |
|---|---|---|
| Python package | `0.1.0` | Distribution version |
| HTTP API | unversioned | Current delivery routes |
| GIR schema | `0.2.0` | Mathematical data contract |

A change to one domain does not automatically change the others.

## Canonical writer contract

Every current GeometryOS writer emits only GIR `0.2.0` with the field `schema_version`. Canonical output never contains the legacy field `version`.

## Legacy reader contract

The reader accepts exactly one legacy marker: `version: "0.1"`. It upgrades that marker to `schema_version: "0.2.0"` before Pydantic structural validation.

The compatibility layer does not repair objects, constraints, references, metadata or construction steps. A structurally or semantically invalid legacy scene remains invalid after its version marker is upgraded.

## Rejected inputs

GeometryOS rejects:

- scenes without a version marker;
- scenes containing both `version` and `schema_version`;
- unknown canonical versions;
- unknown legacy versions;
- future versions that have not been explicitly implemented.

Unknown versions are never parsed as the current schema on a best-effort basis.

## Change classification

A GIR patch change may clarify documentation or validation without changing the accepted data shape. A backward-compatible minor change may add an optional field or a new explicitly supported union member. A major change removes, renames or changes the meaning or type of an existing field.

New object or constraint union variants may still be breaking for exhaustive generated clients. Consumer compatibility must therefore be evaluated before publishing them.

## Required change procedure

Any GIR model change must update, in the same pull request:

1. Pydantic models;
2. the versioned JSON Schema artifact;
3. schema freshness tests;
4. canonical benchmark fixtures;
5. compatibility tests where applicable;
6. `docs/GIR_SPEC.md` and this policy;
7. future TutorBoard consumer contracts once they exist.

## Removing GIR 0.1 support

Legacy support may be removed only in a separately documented breaking change after all known persisted scenes and consumers have migrated. Until then, legacy support remains read-only: no current writer may produce GIR 0.1.
''',
)

write(
    "docs/adr/ADR-001-gir-schema-versioning.md",
    '''# ADR-001: GIR schema versioning

- Status: Accepted
- Date: 2026-07-20

## Context

GIR 0.1 used an unconstrained `version: str` field. Any string could pass structural parsing, the field did not define a compatibility policy, and internal writers, API, CLI and benchmark fixtures all treated the label as informal metadata. TutorBoard integration requires a deterministic machine contract and predictable rejection of unknown versions.

## Decision

GIR 0.2 uses a required `schema_version` field with the exact value `0.2.0`. The canonical Pydantic model and generated JSON Schema contain no `version` field.

A single compatibility boundary accepts legacy `version: "0.1"` and converts only that top-level marker to `schema_version: "0.2.0"`. Missing, conflicting and unsupported versions are rejected with stable Pydantic error types.

Package, HTTP API and GIR schema versions remain independent.

## Alternatives considered

- Keep `version: str`: rejected because it does not enforce a contract.
- Use a numeric version: rejected because numeric JSON values lose semantic-version precision.
- Use `0.2` instead of `0.2.0`: rejected in favor of an explicit semantic-version format.
- Keep both fields in the canonical model: rejected because it creates two sources of truth.
- Reject all GIR 0.1 immediately: rejected because existing fixtures and potential saved scenes need a bounded migration window.
- Accept unknown minor versions optimistically: rejected because field meaning and union variants may change.

## Consequences

Positive consequences:

- every canonical scene is self-identifying;
- JSON Schema can be pinned by consumers;
- API, CLI and direct Python parsing share one compatibility path;
- future migration warnings can reuse compatibility metadata;
- unknown future schemas fail safely.

Costs:

- all current fixtures and writers must migrate;
- the versioned schema artifact must be regenerated on model changes;
- legacy support must remain tested until explicitly removed.

## Migration

All current writers and benchmark fixtures move to GIR 0.2. One legacy altitude fixture remains under `tests/fixtures/gir/v0_1` solely to verify compatibility. The old unversioned schema artifact is replaced by `schemas/gir-0.2.schema.json`.
''',
)

# Keep contract examples canonical without rewriting intentional legacy-policy prose.
for path in [
    ROOT / "docs/contracts/BENCHMARK_CONTRACT.md",
    ROOT / "docs/contracts/RENDER_CONTRACT.md",
]:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        text = text.replace('{"version":"0.1"', '{"schema_version":"0.2.0"')
        path.write_text(text, encoding="utf-8")

# The one-shot workflow and this script delete themselves before committing.
(ROOT / ".github/workflows/apply-pr2.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)

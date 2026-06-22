import json
from pathlib import Path
from typing import Any

from gir_ai.text_to_gir.adapter import AiAdapterResult, text_to_gir
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene


def run_benchmarks(root: Path | None = None) -> dict[str, Any]:
    project_root = root or Path.cwd()
    total = passed = failed = 0
    failures: list[dict[str, Any]] = []
    for input_file in sorted((project_root / "benchmarks" / "text_to_gir").glob("*/*.input.txt")):
        total += 1
        result = text_to_gir(input_file.read_text(encoding="utf-8"))
        expected_file = _expected_file(input_file)
        expected = json.loads(expected_file.read_text(encoding="utf-8"))
        errors = _compare_result(result, expected)
        if errors:
            failed += 1
            failures.append({"case": str(input_file.relative_to(project_root)), "errors": errors})
        else:
            passed += 1
    return {"total": total, "passed": passed, "failed": failed, "failures": failures}


def _compare_result(result: AiAdapterResult, expected: dict[str, Any]) -> list[str]:
    # Design note: benchmark comparison is a soft subset check for now. It protects
    # the public contract while allowing harmless extra metadata or future derived
    # construction artifacts to appear without breaking every MVP fixture.
    errors: list[str] = []
    expected_status = expected.get("status", "success")
    if result.status != expected_status:
        errors.append(f"status: expected {expected_status!r}, got {result.status!r}")
        return errors

    if expected_status != "success":
        return errors

    if result.gir is None:
        return ["expected successful GIR, got no GIR"]

    validation_report = validate_scene(result.gir)
    if not validation_report.is_valid:
        errors.append("result GIR failed semantic validation")
    GirScene.model_validate(result.gir.model_dump())

    expected_scene = GirScene.model_validate(expected)
    errors.extend(
        _missing_subset(
            expected={obj.id for obj in expected_scene.objects},
            actual={obj.id for obj in result.gir.objects},
            label="object ids",
        )
    )
    errors.extend(
        _missing_subset(
            expected={constraint.id for constraint in expected_scene.constraints},
            actual={constraint.id for constraint in result.gir.constraints},
            label="constraint ids",
        )
    )
    errors.extend(
        _missing_subset(
            expected={constraint.type for constraint in expected_scene.constraints},
            actual={constraint.type for constraint in result.gir.constraints},
            label="constraint types",
        )
    )
    errors.extend(
        _missing_subset(
            expected={step.action for step in expected_scene.construction_steps},
            actual={step.action for step in result.gir.construction_steps},
            label="construction actions",
        )
    )
    return errors


def _missing_subset(expected: set[str], actual: set[str], label: str) -> list[str]:
    missing = sorted(expected - actual)
    if not missing:
        return []
    return [f"missing expected {label}: {', '.join(missing)}"]


def _expected_file(input_file: Path) -> Path:
    gir = input_file.with_name(input_file.name.replace(".input.txt", ".expected.gir.json"))
    if gir.exists():
        return gir
    return input_file.with_name(input_file.name.replace(".input.txt", ".expected.json"))

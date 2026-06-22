import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from gir_ai.text_to_gir.adapter import AiAdapterResult, text_to_gir
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz


def run_benchmarks(
    root: Path | None = None,
    benchmarks_dir: Path | None = None,
) -> dict[str, Any]:
    project_root = (root or Path.cwd()).resolve()

    if benchmarks_dir is not None:
        text_to_gir_summary = _run_text_to_gir_suite(project_root, benchmarks_dir.resolve())
        return _combined_summary({"text_to_gir": text_to_gir_summary})

    suites = {
        "text_to_gir": _run_text_to_gir_suite(
            project_root,
            project_root / "benchmarks" / "text_to_gir",
        ),
        "gir_to_svg": _run_render_suite(
            project_root,
            project_root / "benchmarks" / "gir_to_svg",
            expected_type="svg",
            render=render_svg,
        ),
        "gir_to_tikz": _run_render_suite(
            project_root,
            project_root / "benchmarks" / "gir_to_tikz",
            expected_type="tikz",
            render=render_tikz,
        ),
    }
    return _combined_summary(suites)


def _run_text_to_gir_suite(project_root: Path, text_to_gir_dir: Path) -> dict[str, Any]:
    if not text_to_gir_dir.is_dir():
        raise FileNotFoundError(f"Benchmarks directory not found: {text_to_gir_dir}")

    total = passed = failed = 0
    failures: list[dict[str, Any]] = []
    for input_file in sorted(text_to_gir_dir.glob("*/*.input.txt")):
        total += 1
        result = text_to_gir(input_file.read_text(encoding="utf-8"))
        expected_file = _expected_file(input_file)
        expected = json.loads(expected_file.read_text(encoding="utf-8"))
        errors = _compare_result(result, expected)
        if errors:
            failed += 1
            failures.append({"case": _case_name(input_file, project_root), "errors": errors})
        else:
            passed += 1
    return {"total": total, "passed": passed, "failed": failed, "failures": failures}


def _run_render_suite(
    project_root: Path,
    suite_dir: Path,
    *,
    expected_type: str,
    render: Callable[[GirScene], str],
) -> dict[str, Any]:
    if not suite_dir.is_dir():
        return {
            "total": 1,
            "passed": 0,
            "failed": 1,
            "failures": [
                {
                    "case": _case_name(suite_dir, project_root),
                    "errors": [f"render benchmark directory not found: {suite_dir}"],
                }
            ],
        }

    total = passed = failed = 0
    failures: list[dict[str, Any]] = []
    for gir_file in sorted(suite_dir.glob("*.gir.json")):
        total += 1
        errors = _run_render_case(
            gir_file,
            project_root,
            expected_type=expected_type,
            render=render,
        )
        if errors:
            failed += 1
            failures.append({"case": _case_name(gir_file, project_root), "errors": errors})
        else:
            passed += 1
    return {"total": total, "passed": passed, "failed": failed, "failures": failures}


def _run_render_case(
    gir_file: Path,
    project_root: Path,
    *,
    expected_type: str,
    render: Callable[[GirScene], str],
) -> list[str]:
    case_name = _case_name(gir_file, project_root)
    expected_file = _render_expected_file(gir_file)
    if not expected_file.exists():
        return [f"missing expected file: {_case_name(expected_file, project_root)}"]

    expected = json.loads(expected_file.read_text(encoding="utf-8"))
    errors: list[str] = []
    if expected.get("type") != expected_type:
        errors.append(f"expected type must be {expected_type!r}, got {expected.get('type')!r}")

    try:
        scene = GirScene.model_validate_json(gir_file.read_text(encoding="utf-8"))
    except ValidationError as exc:
        return [f"input GIR failed Pydantic validation: {exc}"]

    report = validate_scene(scene)
    if not report.is_valid:
        return [f"input GIR failed semantic validation: {report.model_dump()}"]

    try:
        output = render(scene)
    except ValueError as exc:
        return [f"render failed: {exc}"]

    errors.extend(_check_text_output(case_name, output, expected))
    return errors


def _combined_summary(suites: dict[str, dict[str, Any]]) -> dict[str, Any]:
    total = sum(int(suite["total"]) for suite in suites.values())
    passed = sum(int(suite["passed"]) for suite in suites.values())
    failed = sum(int(suite["failed"]) for suite in suites.values())
    failures = [failure for suite in suites.values() for failure in suite["failures"]]
    suite_counts = {
        name: {"total": suite["total"], "passed": suite["passed"], "failed": suite["failed"]}
        for name, suite in suites.items()
    }
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "failures": failures,
        "suites": suite_counts,
    }


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
        errors.extend(_missing_ambiguity_codes(result, expected))
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


def _check_text_output(case_name: str, output: str, expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for value in expected.get("must_contain", []):
        if value not in output:
            errors.append(f"{case_name}: output missing required substring: {value}")
    for value in expected.get("must_not_contain", []):
        if value in output:
            errors.append(f"{case_name}: output contains forbidden substring: {value}")
    for value, minimum in expected.get("min_occurrences", {}).items():
        count = output.count(value)
        if count < minimum:
            errors.append(
                f"{case_name}: expected at least {minimum} occurrences of {value!r}, got {count}"
            )
    return errors


def _missing_ambiguity_codes(result: AiAdapterResult, expected: dict[str, Any]) -> list[str]:
    expected_codes = {
        item["code"]
        for item in expected.get("ambiguities", [])
        if isinstance(item, dict) and isinstance(item.get("code"), str)
    }
    if not expected_codes:
        return []

    actual_codes = {ambiguity.code for ambiguity in result.ambiguities}
    missing = sorted(expected_codes - actual_codes)
    if not missing:
        return []
    return [f"missing expected ambiguity codes: {', '.join(missing)}"]


def _missing_subset(expected: set[str], actual: set[str], label: str) -> list[str]:
    missing = sorted(expected - actual)
    if not missing:
        return []
    return [f"missing expected {label}: {', '.join(missing)}"]


def _case_name(input_file: Path, project_root: Path) -> str:
    try:
        return str(input_file.relative_to(project_root))
    except ValueError:
        return str(input_file)


def _expected_file(input_file: Path) -> Path:
    gir = input_file.with_name(input_file.name.replace(".input.txt", ".expected.gir.json"))
    if gir.exists():
        return gir
    return input_file.with_name(input_file.name.replace(".input.txt", ".expected.json"))


def _render_expected_file(gir_file: Path) -> Path:
    return gir_file.with_name(gir_file.name.replace(".gir.json", ".expected.json"))

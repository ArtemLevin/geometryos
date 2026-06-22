import json
from pathlib import Path
from typing import Any

import typer

from gir_ai.text_to_gir.adapter import AiAdapterResult, text_to_gir
from gir_core.models.scene import GirScene
from gir_core.normalize import normalize_gir
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz

app = typer.Typer(help="GIR Geometry Compiler CLI")
ROOT = Path(__file__).resolve().parents[2]


def _load_scene(path: Path) -> GirScene:
    return GirScene.model_validate_json(path.read_text(encoding="utf-8"))


@app.command("validate")
def validate(path: Path) -> None:
    typer.echo(validate_scene(_load_scene(path)).model_dump_json(indent=2))


@app.command("render-svg")
def render_svg_command(path: Path) -> None:
    typer.echo(render_svg(_validated_normalized_scene(_load_scene(path))))


@app.command("render-tikz")
def render_tikz_command(path: Path) -> None:
    typer.echo(render_tikz(_validated_normalized_scene(_load_scene(path))))


@app.command("benchmark")
def benchmark() -> None:
    typer.echo(json.dumps(_run_benchmarks(), ensure_ascii=False, indent=2))


@app.command("export-schema")
def export_schema_command() -> None:
    output = ROOT / "schemas" / "gir.schema.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(GirScene.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    typer.echo(str(output))


def _run_benchmarks() -> dict[str, Any]:
    # Design note: this intentionally duplicates the script runner instead of
    # importing scripts.* because installed CLI packages should not depend on
    # repository-local helper modules.
    total = passed = failed = 0
    failures: list[dict[str, Any]] = []
    for input_file in sorted((ROOT / "benchmarks" / "text_to_gir").glob("*/*.input.txt")):
        total += 1
        result = text_to_gir(input_file.read_text(encoding="utf-8"))
        expected_file = _expected_file(input_file)
        expected = json.loads(expected_file.read_text(encoding="utf-8"))
        errors = _compare_benchmark_result(result, expected)
        if errors:
            failed += 1
            failures.append({"case": str(input_file.relative_to(ROOT)), "errors": errors})
        else:
            passed += 1
    return {"total": total, "passed": passed, "failed": failed, "failures": failures}


def _compare_benchmark_result(result: AiAdapterResult, expected: dict[str, Any]) -> list[str]:
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


def _validated_normalized_scene(scene: GirScene) -> GirScene:
    draft_report = validate_scene(scene)
    if not draft_report.is_valid:
        typer.echo(draft_report.model_dump_json(indent=2), err=True)
        raise typer.Exit(code=1)

    normalized_scene = normalize_gir(scene)
    normalized_report = validate_scene(normalized_scene)
    if not normalized_report.is_valid:
        typer.echo(normalized_report.model_dump_json(indent=2), err=True)
        raise typer.Exit(code=1)

    return normalized_scene

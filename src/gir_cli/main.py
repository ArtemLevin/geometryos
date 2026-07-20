import json
from pathlib import Path
from typing import Annotated

import typer

from gir_benchmarks.runner import run_benchmarks
from gir_core.models.scene import GirScene
from gir_core.normalize import normalize_gir
from gir_core.schema import check_gir_schema, write_gir_schema
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz

app = typer.Typer(help="GIR Geometry Compiler CLI")


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
def benchmark(
    root: Annotated[
        Path,
        typer.Option("--root", "-r", help="Project root containing the benchmarks/ directory."),
    ] = Path("."),
    benchmarks_dir: Annotated[
        Path | None,
        typer.Option(
            "--benchmarks-dir",
            help="Explicit path to text-to-GIR benchmarks directory. Overrides --root.",
        ),
    ] = None,
) -> None:
    try:
        summary = run_benchmarks(root=root, benchmarks_dir=benchmarks_dir)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["failed"]:
        raise typer.Exit(code=1)


@app.command("export-schema")
def export_schema_command(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output path for generated GIR JSON Schema.")
    ] = Path("schemas/gir-0.2.schema.json"),
    check: Annotated[
        bool, typer.Option("--check", help="Check that the committed schema is up to date.")
    ] = False,
) -> None:
    if check:
        if check_gir_schema(output):
            typer.echo(f"GIR schema is up to date: {output}")
            return
        if output.exists():
            typer.echo(f"GIR schema is out of date: {output}", err=True)
        else:
            typer.echo(f"GIR schema file not found: {output}", err=True)
        typer.echo(f"Run: gir export-schema --output {output}", err=True)
        raise typer.Exit(code=1)

    path = write_gir_schema(output)
    typer.echo(f"Exported GIR schema to {path}")


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

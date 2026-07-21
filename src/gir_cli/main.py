from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from gir_application import (
    OutputFormat,
    RenderGeometryCommand,
    render_geometry,
    validate_geometry,
)
from gir_benchmarks.runner import run_benchmarks
from gir_core.models.scene import GirScene
from gir_core.schema import check_gir_schema, write_gir_schema
from gir_meta import SERVICE_NAME, SERVICE_VERSION

app = typer.Typer(help="GIR Geometry Compiler CLI", no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{SERVICE_NAME} {SERVICE_VERSION}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed GeometryOS version and exit.",
        ),
    ] = False,
) -> None:
    del version


def _load_scene(path: Path) -> GirScene:
    return GirScene.model_validate_json(path.read_text(encoding="utf-8"))


@app.command("validate")
def validate(path: Path) -> None:
    typer.echo(validate_geometry(_load_scene(path)).model_dump_json(indent=2))


@app.command("render-svg")
def render_svg_command(path: Path) -> None:
    typer.echo(_render(path, OutputFormat.SVG))


@app.command("render-tikz")
def render_tikz_command(path: Path) -> None:
    typer.echo(_render(path, OutputFormat.TIKZ))


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


def _render(path: Path, output: OutputFormat) -> str:
    result = render_geometry(
        RenderGeometryCommand(scene=_load_scene(path), outputs=frozenset({output}))
    )
    if not result.is_valid:
        typer.echo(result.validation_report.model_dump_json(indent=2), err=True)
        raise typer.Exit(code=1)

    content = result.artifacts.svg if output is OutputFormat.SVG else result.artifacts.tikz
    if content is None:
        typer.echo(f"Renderer did not produce requested output: {output.value}.", err=True)
        raise typer.Exit(code=1)
    return content

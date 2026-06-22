import json
from pathlib import Path
from typing import Annotated

import typer

from gir_benchmarks.runner import run_benchmarks
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
def benchmark(
    root: Annotated[Path, typer.Option(help="Project root containing benchmarks/.")] = Path("."),
) -> None:
    summary = run_benchmarks(root=root)
    typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["failed"]:
        raise typer.Exit(code=1)


@app.command("export-schema")
def export_schema_command() -> None:
    output = ROOT / "schemas" / "gir.schema.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(GirScene.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    typer.echo(str(output))


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

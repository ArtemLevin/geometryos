import json
from pathlib import Path

import typer

from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz
from scripts.export_schema import export_schema
from scripts.run_benchmarks import run_benchmarks

app = typer.Typer(help="GIR Geometry Compiler CLI")


def _load_scene(path: Path) -> GirScene:
    return GirScene.model_validate_json(path.read_text())


@app.command("validate")
def validate(path: Path) -> None:
    typer.echo(validate_scene(_load_scene(path)).model_dump_json(indent=2))


@app.command("render-svg")
def render_svg_command(path: Path) -> None:
    typer.echo(render_svg(_load_scene(path)))


@app.command("render-tikz")
def render_tikz_command(path: Path) -> None:
    typer.echo(render_tikz(_load_scene(path)))


@app.command("benchmark")
def benchmark() -> None:
    typer.echo(json.dumps(run_benchmarks(), ensure_ascii=False, indent=2))


@app.command("export-schema")
def export_schema_command() -> None:
    typer.echo(str(export_schema()))

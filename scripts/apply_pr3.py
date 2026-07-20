from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


write(
    "src/gir_application/__init__.py",
    '''from gir_application.contracts import (
    GenerateGeometryCommand,
    GenerateGeometryResult,
    GenerationMode,
    GenerationStatus,
    GeometryAmbiguity,
    OutputFormat,
    PipelineFailureStage,
    PrepareGeometryResult,
    RenderedArtifacts,
    RenderGeometryCommand,
    RenderGeometryResult,
)
from gir_application.pipeline import (
    generate_geometry,
    prepare_geometry,
    render_geometry,
    validate_geometry,
)
from gir_application.ports import GeometryPipelineDependencies

__all__ = [
    "GenerateGeometryCommand",
    "GenerateGeometryResult",
    "GenerationMode",
    "GenerationStatus",
    "GeometryAmbiguity",
    "GeometryPipelineDependencies",
    "OutputFormat",
    "PipelineFailureStage",
    "PrepareGeometryResult",
    "RenderGeometryCommand",
    "RenderGeometryResult",
    "RenderedArtifacts",
    "generate_geometry",
    "prepare_geometry",
    "render_geometry",
    "validate_geometry",
]
''',
)

write(
    "src/gir_application/contracts.py",
    '''from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


class GenerationStatus(StrEnum):
    SUCCESS = "success"
    NEEDS_CLARIFICATION = "needs_clarification"
    ERROR = "error"


class GenerationMode(StrEnum):
    STRICT = "strict"
    DRAFT = "draft"


class OutputFormat(StrEnum):
    SVG = "svg"
    TIKZ = "tikz"


class PipelineFailureStage(StrEnum):
    ADAPTER = "adapter"
    DRAFT_VALIDATION = "draft_validation"
    NORMALIZATION = "normalization"
    NORMALIZED_VALIDATION = "normalized_validation"
    RENDER = "render"


class GenerateGeometryCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_type: Literal["text"]
    input: str
    outputs: frozenset[OutputFormat] = Field(default_factory=frozenset)
    mode: GenerationMode = GenerationMode.STRICT


class GeometryAmbiguity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    options: list[str] = Field(default_factory=list)


class RenderedArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    svg: str | None = None
    tikz: str | None = None


class PrepareGeometryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    scene: GirScene
    validation_report: ValidationReport
    failure_stage: PipelineFailureStage | None = None


class GenerateGeometryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GenerationStatus
    confidence: float
    gir: GirScene | None = None
    validation_report: ValidationReport | None = None
    artifacts: RenderedArtifacts = Field(default_factory=RenderedArtifacts)
    warnings: list[str] = Field(default_factory=list)
    ambiguities: list[GeometryAmbiguity] = Field(default_factory=list)
    explanation: str | None = None
    failure_stage: PipelineFailureStage | None = None


class RenderGeometryCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: GirScene
    outputs: frozenset[OutputFormat]


class RenderGeometryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    scene: GirScene
    validation_report: ValidationReport
    artifacts: RenderedArtifacts = Field(default_factory=RenderedArtifacts)
    failure_stage: PipelineFailureStage | None = None
''',
)

write(
    "src/gir_application/ports.py",
    '''from dataclasses import dataclass
from typing import Protocol

from gir_ai.text_to_gir.adapter import AiAdapterResult
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


class TextToGirPort(Protocol):
    def __call__(self, text: str, /) -> AiAdapterResult: ...


class ValidateScenePort(Protocol):
    def __call__(self, scene: GirScene, /) -> ValidationReport: ...


class NormalizeScenePort(Protocol):
    def __call__(self, scene: GirScene, /) -> GirScene: ...


class RenderScenePort(Protocol):
    def __call__(self, scene: GirScene, /) -> str: ...


@dataclass(frozen=True)
class GeometryPipelineDependencies:
    text_to_gir: TextToGirPort
    validate_scene: ValidateScenePort
    normalize_scene: NormalizeScenePort
    render_svg: RenderScenePort
    render_tikz: RenderScenePort
''',
)

write(
    "src/gir_application/pipeline.py",
    '''from gir_ai.text_to_gir.adapter import AiAmbiguity, text_to_gir
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport
from gir_core.normalize import normalize_gir
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz

from gir_application.contracts import (
    GenerateGeometryCommand,
    GenerateGeometryResult,
    GenerationStatus,
    GeometryAmbiguity,
    OutputFormat,
    PipelineFailureStage,
    PrepareGeometryResult,
    RenderedArtifacts,
    RenderGeometryCommand,
    RenderGeometryResult,
)
from gir_application.ports import GeometryPipelineDependencies

DEFAULT_DEPENDENCIES = GeometryPipelineDependencies(
    text_to_gir=text_to_gir,
    validate_scene=validate_scene,
    normalize_scene=normalize_gir,
    render_svg=render_svg,
    render_tikz=render_tikz,
)


def validate_geometry(
    scene: GirScene,
    *,
    dependencies: GeometryPipelineDependencies = DEFAULT_DEPENDENCIES,
) -> ValidationReport:
    """Validate a canonical scene without normalization or rendering."""
    return dependencies.validate_scene(scene)


def prepare_geometry(
    scene: GirScene,
    *,
    dependencies: GeometryPipelineDependencies = DEFAULT_DEPENDENCIES,
) -> PrepareGeometryResult:
    """Validate, normalize and revalidate a scene before rendering."""
    draft_report = dependencies.validate_scene(scene)
    if not draft_report.is_valid:
        return PrepareGeometryResult(
            is_valid=False,
            scene=scene,
            validation_report=draft_report,
            failure_stage=PipelineFailureStage.DRAFT_VALIDATION,
        )

    normalized_scene = dependencies.normalize_scene(scene)
    normalized_report = dependencies.validate_scene(normalized_scene)
    if not normalized_report.is_valid:
        return PrepareGeometryResult(
            is_valid=False,
            scene=normalized_scene,
            validation_report=normalized_report,
            failure_stage=PipelineFailureStage.NORMALIZED_VALIDATION,
        )

    return PrepareGeometryResult(
        is_valid=True,
        scene=normalized_scene,
        validation_report=normalized_report,
    )


def render_geometry(
    command: RenderGeometryCommand,
    *,
    dependencies: GeometryPipelineDependencies = DEFAULT_DEPENDENCIES,
) -> RenderGeometryResult:
    prepared = prepare_geometry(command.scene, dependencies=dependencies)
    if not prepared.is_valid:
        return RenderGeometryResult(
            is_valid=False,
            scene=prepared.scene,
            validation_report=prepared.validation_report,
            failure_stage=prepared.failure_stage,
        )

    return RenderGeometryResult(
        is_valid=True,
        scene=prepared.scene,
        validation_report=prepared.validation_report,
        artifacts=_render_artifacts(prepared.scene, command.outputs, dependencies),
    )


def generate_geometry(
    command: GenerateGeometryCommand,
    *,
    dependencies: GeometryPipelineDependencies = DEFAULT_DEPENDENCIES,
) -> GenerateGeometryResult:
    # GenerationMode is intentionally carried through the application contract.
    # Its distinct strict/draft semantics are deferred to the stable API work.
    adapter_result = dependencies.text_to_gir(command.input)
    status = GenerationStatus(adapter_result.status)
    ambiguities = [_to_application_ambiguity(item) for item in adapter_result.ambiguities]

    if adapter_result.gir is None:
        return GenerateGeometryResult(
            status=status,
            confidence=adapter_result.confidence,
            warnings=adapter_result.warnings,
            ambiguities=ambiguities,
            explanation=adapter_result.explanation,
            failure_stage=(
                PipelineFailureStage.ADAPTER if status is GenerationStatus.ERROR else None
            ),
        )

    prepared = prepare_geometry(adapter_result.gir, dependencies=dependencies)
    if not prepared.is_valid:
        warning = (
            "Draft GIR failed semantic validation."
            if prepared.failure_stage is PipelineFailureStage.DRAFT_VALIDATION
            else "Normalized GIR failed semantic validation."
        )
        return GenerateGeometryResult(
            status=GenerationStatus.ERROR,
            confidence=adapter_result.confidence,
            gir=prepared.scene,
            validation_report=prepared.validation_report,
            warnings=[*adapter_result.warnings, warning],
            ambiguities=ambiguities,
            explanation=adapter_result.explanation,
            failure_stage=prepared.failure_stage,
        )

    return GenerateGeometryResult(
        status=status,
        confidence=adapter_result.confidence,
        gir=prepared.scene,
        validation_report=prepared.validation_report,
        artifacts=_render_artifacts(prepared.scene, command.outputs, dependencies),
        warnings=adapter_result.warnings,
        ambiguities=ambiguities,
        explanation=adapter_result.explanation,
    )


def _render_artifacts(
    scene: GirScene,
    outputs: frozenset[OutputFormat],
    dependencies: GeometryPipelineDependencies,
) -> RenderedArtifacts:
    return RenderedArtifacts(
        svg=dependencies.render_svg(scene) if OutputFormat.SVG in outputs else None,
        tikz=dependencies.render_tikz(scene) if OutputFormat.TIKZ in outputs else None,
    )


def _to_application_ambiguity(ambiguity: AiAmbiguity) -> GeometryAmbiguity:
    return GeometryAmbiguity(
        code=ambiguity.code,
        message=ambiguity.message,
        options=ambiguity.options,
    )
''',
)

write(
    "src/gir_api/routes/generate.py",
    '''from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from gir_application import (
    GenerateGeometryCommand,
    GenerationMode,
    GeometryAmbiguity,
    OutputFormat,
    generate_geometry,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport

router = APIRouter()


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_type: Literal["text"]
    input: str
    output: list[Literal["svg", "tikz"]] = Field(default_factory=list)
    mode: Literal["strict", "draft"] = "strict"


class GenerateResponse(BaseModel):
    status: str
    confidence: float
    gir: GirScene | None
    validation_report: ValidationReport | None
    svg: str | None = None
    tikz: str | None = None
    warnings: list[str]
    ambiguities: list[GeometryAmbiguity] = Field(default_factory=list)
    explanation: str | None = None


@router.post("/generate")
def generate(request: GenerateRequest) -> GenerateResponse:
    result = generate_geometry(
        GenerateGeometryCommand(
            input_type=request.input_type,
            input=request.input,
            outputs=frozenset(OutputFormat(item) for item in request.output),
            mode=GenerationMode(request.mode),
        )
    )
    return GenerateResponse(
        status=result.status.value,
        confidence=result.confidence,
        gir=result.gir,
        validation_report=result.validation_report,
        svg=result.artifacts.svg,
        tikz=result.artifacts.tikz,
        warnings=result.warnings,
        ambiguities=result.ambiguities,
        explanation=result.explanation,
    )
''',
)

write(
    "src/gir_api/routes/validate.py",
    '''from fastapi import APIRouter

from gir_application import validate_geometry
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport

router = APIRouter()


@router.post("/validate-gir")
def validate_gir(scene: GirScene) -> ValidationReport:
    return validate_geometry(scene)
''',
)

write(
    "src/gir_api/routes/render.py",
    '''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gir_application import OutputFormat, RenderGeometryCommand, render_geometry
from gir_core.models.scene import GirScene

router = APIRouter()


class RenderResponse(BaseModel):
    content: str


@router.post("/render/svg")
def render_svg_endpoint(scene: GirScene) -> RenderResponse:
    return RenderResponse(content=_render_content(scene, OutputFormat.SVG))


@router.post("/render/tikz")
def render_tikz_endpoint(scene: GirScene) -> RenderResponse:
    return RenderResponse(content=_render_content(scene, OutputFormat.TIKZ))


def _render_content(scene: GirScene, output: OutputFormat) -> str:
    result = render_geometry(
        RenderGeometryCommand(scene=scene, outputs=frozenset({output}))
    )
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=result.validation_report.model_dump())

    content = result.artifacts.svg if output is OutputFormat.SVG else result.artifacts.tikz
    if content is None:
        raise RuntimeError(f"Renderer did not produce requested output: {output.value}.")
    return content
''',
)

write(
    "src/gir_cli/main.py",
    '''import json
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

app = typer.Typer(help="GIR Geometry Compiler CLI")


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
''',
)

write(
    "tests/application/__init__.py",
    '''"""Application pipeline tests."""''',
)

write(
    "tests/application/test_pipeline.py",
    '''from typing import Any
from unittest.mock import Mock

from gir_ai.text_to_gir.adapter import AiAdapterResult, AiAmbiguity
from gir_application import (
    GenerateGeometryCommand,
    GenerationStatus,
    GeometryPipelineDependencies,
    OutputFormat,
    PipelineFailureStage,
    RenderGeometryCommand,
    generate_geometry,
    prepare_geometry,
    render_geometry,
    validate_geometry,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationIssue, ValidationReport


def _scene(payload: dict[str, Any]) -> GirScene:
    return GirScene.model_validate(payload)


def _valid_report() -> ValidationReport:
    return ValidationReport(is_valid=True)


def _invalid_report() -> ValidationReport:
    return ValidationReport(
        is_valid=False,
        issues=[ValidationIssue(code="invalid", message="Scene is invalid.")],
    )


def _dependencies(
    *,
    adapter: Mock | None = None,
    validator: Mock | None = None,
    normalizer: Mock | None = None,
    svg: Mock | None = None,
    tikz: Mock | None = None,
) -> GeometryPipelineDependencies:
    return GeometryPipelineDependencies(
        text_to_gir=adapter or Mock(),
        validate_scene=validator or Mock(return_value=_valid_report()),
        normalize_scene=normalizer or Mock(side_effect=lambda scene: scene),
        render_svg=svg or Mock(return_value="<svg />"),
        render_tikz=tikz or Mock(return_value="\\begin{tikzpicture}"),
    )


def test_prepare_geometry_validates_normalizes_and_revalidates(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    normalized = scene.model_copy(update={"metadata": {"normalized": True}})
    validator = Mock(side_effect=[_valid_report(), _valid_report()])
    normalizer = Mock(return_value=normalized)
    dependencies = _dependencies(validator=validator, normalizer=normalizer)

    result = prepare_geometry(scene, dependencies=dependencies)

    assert result.is_valid is True
    assert result.scene == normalized
    assert result.failure_stage is None
    assert validator.call_args_list[0].args == (scene,)
    assert validator.call_args_list[1].args == (normalized,)
    normalizer.assert_called_once_with(scene)
    assert scene.metadata == {}


def test_prepare_geometry_stops_before_normalization_for_invalid_draft(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    validator = Mock(return_value=_invalid_report())
    normalizer = Mock()

    result = prepare_geometry(
        scene,
        dependencies=_dependencies(validator=validator, normalizer=normalizer),
    )

    assert result.is_valid is False
    assert result.scene == scene
    assert result.failure_stage is PipelineFailureStage.DRAFT_VALIDATION
    validator.assert_called_once_with(scene)
    normalizer.assert_not_called()


def test_prepare_geometry_rejects_invalid_normalized_scene(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    normalized = scene.model_copy(update={"metadata": {"normalized": True}})
    validator = Mock(side_effect=[_valid_report(), _invalid_report()])

    result = prepare_geometry(
        scene,
        dependencies=_dependencies(
            validator=validator,
            normalizer=Mock(return_value=normalized),
        ),
    )

    assert result.is_valid is False
    assert result.scene == normalized
    assert result.failure_stage is PipelineFailureStage.NORMALIZED_VALIDATION


def test_validate_geometry_does_not_normalize_or_render(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    report = _valid_report()
    validator = Mock(return_value=report)
    normalizer = Mock()
    svg = Mock()
    tikz = Mock()

    result = validate_geometry(
        scene,
        dependencies=_dependencies(
            validator=validator,
            normalizer=normalizer,
            svg=svg,
            tikz=tikz,
        ),
    )

    assert result == report
    validator.assert_called_once_with(scene)
    normalizer.assert_not_called()
    svg.assert_not_called()
    tikz.assert_not_called()


def test_render_geometry_dispatches_only_requested_renderer(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    svg = Mock(return_value="<svg>ok</svg>")
    tikz = Mock(return_value="tikz")

    result = render_geometry(
        RenderGeometryCommand(scene=scene, outputs=frozenset({OutputFormat.SVG})),
        dependencies=_dependencies(svg=svg, tikz=tikz),
    )

    assert result.is_valid is True
    assert result.artifacts.svg == "<svg>ok</svg>"
    assert result.artifacts.tikz is None
    svg.assert_called_once_with(scene)
    tikz.assert_not_called()


def test_render_geometry_never_renders_invalid_scene(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    svg = Mock()
    tikz = Mock()

    result = render_geometry(
        RenderGeometryCommand(
            scene=scene,
            outputs=frozenset({OutputFormat.SVG, OutputFormat.TIKZ}),
        ),
        dependencies=_dependencies(
            validator=Mock(return_value=_invalid_report()),
            svg=svg,
            tikz=tikz,
        ),
    )

    assert result.is_valid is False
    svg.assert_not_called()
    tikz.assert_not_called()


def test_generate_geometry_short_circuits_ambiguity(
    valid_altitude_payload: dict[str, Any],
) -> None:
    adapter = Mock(
        return_value=AiAdapterResult(
            status="needs_clarification",
            confidence=0.4,
            ambiguities=[
                AiAmbiguity(code="missing_angle", message="Choose angle.", options=["A"])
            ],
        )
    )
    validator = Mock()
    normalizer = Mock()
    svg = Mock()
    tikz = Mock()

    result = generate_geometry(
        GenerateGeometryCommand(input_type="text", input="ambiguous"),
        dependencies=_dependencies(
            adapter=adapter,
            validator=validator,
            normalizer=normalizer,
            svg=svg,
            tikz=tikz,
        ),
    )

    assert result.status is GenerationStatus.NEEDS_CLARIFICATION
    assert result.gir is None
    assert result.ambiguities[0].code == "missing_angle"
    assert result.failure_stage is None
    validator.assert_not_called()
    normalizer.assert_not_called()
    svg.assert_not_called()
    tikz.assert_not_called()


def test_generate_geometry_preserves_adapter_error_metadata() -> None:
    adapter = Mock(
        return_value=AiAdapterResult(
            status="error",
            confidence=0.0,
            warnings=["No rule matched input."],
            explanation="Unsupported.",
        )
    )

    result = generate_geometry(
        GenerateGeometryCommand(input_type="text", input="unsupported"),
        dependencies=_dependencies(adapter=adapter),
    )

    assert result.status is GenerationStatus.ERROR
    assert result.warnings == ["No rule matched input."]
    assert result.explanation == "Unsupported."
    assert result.failure_stage is PipelineFailureStage.ADAPTER


def test_generate_geometry_renders_normalized_scene_once(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    normalized = scene.model_copy(update={"metadata": {"normalized": True}})
    adapter = Mock(
        return_value=AiAdapterResult(status="success", confidence=0.9, gir=scene)
    )
    validator = Mock(side_effect=[_valid_report(), _valid_report()])
    normalizer = Mock(return_value=normalized)
    svg = Mock(return_value="<svg>ok</svg>")
    tikz = Mock(return_value="tikz")

    result = generate_geometry(
        GenerateGeometryCommand(
            input_type="text",
            input="valid",
            outputs=frozenset({OutputFormat.SVG, OutputFormat.TIKZ}),
        ),
        dependencies=_dependencies(
            adapter=adapter,
            validator=validator,
            normalizer=normalizer,
            svg=svg,
            tikz=tikz,
        ),
    )

    assert result.status is GenerationStatus.SUCCESS
    assert result.gir == normalized
    assert result.gir.schema_version == "0.2.0"
    assert result.artifacts.svg == "<svg>ok</svg>"
    assert result.artifacts.tikz == "tikz"
    svg.assert_called_once_with(normalized)
    tikz.assert_called_once_with(normalized)


def test_generate_geometry_reports_invalid_draft_without_rendering(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    adapter = Mock(
        return_value=AiAdapterResult(
            status="success",
            confidence=0.7,
            gir=scene,
            warnings=["adapter-warning"],
        )
    )
    svg = Mock()

    result = generate_geometry(
        GenerateGeometryCommand(
            input_type="text",
            input="invalid",
            outputs=frozenset({OutputFormat.SVG}),
        ),
        dependencies=_dependencies(
            adapter=adapter,
            validator=Mock(return_value=_invalid_report()),
            svg=svg,
        ),
    )

    assert result.status is GenerationStatus.ERROR
    assert result.failure_stage is PipelineFailureStage.DRAFT_VALIDATION
    assert result.warnings == [
        "adapter-warning",
        "Draft GIR failed semantic validation.",
    ]
    svg.assert_not_called()
''',
)

write(
    "tests/test_architecture_boundaries.py",
    '''from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _assert_no_forbidden_imports(path: Path, forbidden: tuple[str, ...]) -> None:
    violations = sorted(
        module
        for module in _imports(path)
        if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
    )
    assert not violations, f"{path.relative_to(ROOT)} imports forbidden modules: {violations}"


def test_api_routes_do_not_orchestrate_geometry_implementations() -> None:
    forbidden = (
        "gir_ai.text_to_gir.adapter",
        "gir_core.normalize",
        "gir_core.validation.semantic_validator",
        "gir_render.svg_renderer",
        "gir_render.tikz_renderer",
    )
    for path in (ROOT / "src/gir_api/routes").glob("*.py"):
        _assert_no_forbidden_imports(path, forbidden)


def test_cli_does_not_orchestrate_geometry_implementations() -> None:
    _assert_no_forbidden_imports(
        ROOT / "src/gir_cli/main.py",
        (
            "gir_core.normalize",
            "gir_core.validation.semantic_validator",
            "gir_render.svg_renderer",
            "gir_render.tikz_renderer",
        ),
    )


def test_application_layer_is_transport_agnostic() -> None:
    for path in (ROOT / "src/gir_application").glob("*.py"):
        _assert_no_forbidden_imports(path, ("fastapi", "typer", "gir_api", "gir_cli"))


def test_core_does_not_depend_on_outer_layers() -> None:
    for path in (ROOT / "src/gir_core").rglob("*.py"):
        _assert_no_forbidden_imports(
            path,
            ("gir_application", "gir_api", "gir_cli", "gir_ai", "gir_render"),
        )
''',
)

write(
    "tests/test_api_application_delegation.py",
    '''from typing import Any

from gir_application import (
    GenerateGeometryResult,
    GenerationStatus,
    OutputFormat,
    RenderedArtifacts,
    RenderGeometryResult,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


def test_generate_route_delegates_to_application_service(
    client: Any,
    monkeypatch: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = GirScene.model_validate(valid_altitude_payload)
    captured: list[Any] = []

    def fake_generate(command: Any) -> GenerateGeometryResult:
        captured.append(command)
        return GenerateGeometryResult(
            status=GenerationStatus.SUCCESS,
            confidence=1.0,
            gir=scene,
            validation_report=ValidationReport(is_valid=True),
            artifacts=RenderedArtifacts(svg="<svg />"),
        )

    monkeypatch.setattr("gir_api.routes.generate.generate_geometry", fake_generate)
    response = client.post(
        "/generate",
        json={
            "input_type": "text",
            "input": "test",
            "output": ["svg", "svg"],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].outputs == frozenset({OutputFormat.SVG})
    assert response.json()["svg"] == "<svg />"


def test_render_route_delegates_to_application_service(
    client: Any,
    monkeypatch: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = GirScene.model_validate(valid_altitude_payload)
    captured: list[Any] = []

    def fake_render(command: Any) -> RenderGeometryResult:
        captured.append(command)
        return RenderGeometryResult(
            is_valid=True,
            scene=scene,
            validation_report=ValidationReport(is_valid=True),
            artifacts=RenderedArtifacts(svg="<svg />"),
        )

    monkeypatch.setattr("gir_api.routes.render.render_geometry", fake_render)
    response = client.post("/render/svg", json=valid_altitude_payload)

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].outputs == frozenset({OutputFormat.SVG})
    assert response.json() == {"content": "<svg />"}
''',
)

write(
    "docs/APPLICATION_PIPELINE.md",
    '''# GeometryOS Application Pipeline

## Purpose

`gir_application` is the transport-agnostic orchestration boundary between GeometryOS delivery adapters and the mathematical/rendering packages.

```text
HTTP API ─┐
          ├── gir_application ── gir_ai
CLI ──────┘                    ├─ gir_core
Future TutorBoard adapter ─────└─ gir_render
```

API routes and CLI commands translate their input into application commands. They do not assemble validation, normalization and rendering stages themselves.

## Canonical flow

Generation uses one ordered pipeline:

```text
text adapter
→ draft GIR
→ semantic validation
→ normalization
→ semantic validation
→ requested renderers
→ typed result
```

Rendering an existing GIR starts at the first semantic validation stage. Validation-only operations deliberately do not normalize the input.

## Short-circuit rules

- `needs_clarification` and adapter errors without GIR do not invoke validation, normalization or rendering;
- semantic-invalid draft GIR is not normalized;
- semantic-invalid normalized GIR is not rendered;
- a renderer is called only when its output format was requested;
- each requested renderer is called at most once;
- renderers receive only normalized GIR that passed both validation gates.

## Public application functions

```python
from gir_application import (
    GenerateGeometryCommand,
    OutputFormat,
    generate_geometry,
)

result = generate_geometry(
    GenerateGeometryCommand(
        input_type="text",
        input="Постройте треугольник ABC",
        outputs=frozenset({OutputFormat.SVG}),
    )
)
```

The supported entry points are:

- `generate_geometry()`;
- `validate_geometry()`;
- `prepare_geometry()`;
- `render_geometry()`.

`prepare_geometry()` is public for trusted internal integrations that need canonical validated GIR without rendering.

## Contracts versus transports

Application commands and results do not contain HTTP status codes, `HTTPException`, Typer exit codes or request objects. Transport adapters remain responsible for:

- HTTP request and response DTOs;
- mapping invalid render requests to HTTP 422;
- CLI stdout, stderr and exit codes;
- future timeout and error-response mapping.

## Dependency ports

`GeometryPipelineDependencies` contains callable ports for the text adapter, semantic validator, normalizer and renderers. The production wiring uses the current rule-based adapter and SVG/TikZ implementations. Unit tests replace individual stages with deterministic fakes without a dependency-injection framework.

## Adding a renderer

A new renderer requires:

1. a new `OutputFormat` member;
2. a typed field in `RenderedArtifacts`;
3. a renderer port in `GeometryPipelineDependencies`;
4. dispatch in `_render_artifacts()`;
5. application tests proving validation gates and one-call dispatch;
6. transport mapping in API/CLI when exposed publicly.

A renderer must never validate, normalize or repair GIR by itself.

## Adding an adapter

A new parser or AI adapter may produce draft GIR and adapter metadata. It must be wired through an application port and must not call renderers. All produced GIR continues through the same validation and normalization gates.
''',
)

write(
    "docs/adr/ADR-002-canonical-application-pipeline.md",
    '''# ADR-002: Canonical application pipeline

## Status

Accepted for GeometryOS integration-ready phase.

## Context

Before this decision, `/generate`, `/render/*` and CLI render commands each assembled parts of the sequence `validate → normalize → validate → render`. This duplicated policy across delivery adapters and made future TutorBoard integration, timeout handling and error mapping likely to diverge.

## Decision

Introduce a transport-agnostic `gir_application` package with typed commands, results and callable dependency ports. The package owns the canonical orchestration sequence and exposes `generate_geometry`, `validate_geometry`, `prepare_geometry` and `render_geometry`.

FastAPI routes and Typer commands become thin adapters. They retain responsibility for HTTP status codes, response DTOs, terminal output and process exit codes.

## Consequences

### Positive

- validation and rendering policy has one implementation;
- API, CLI and future TutorBoard integrations receive consistent behavior;
- every stage can be tested independently;
- renderer invocation is guaranteed to happen only after both validation gates;
- later timeout, tracing and structured error work has one application boundary;
- no dependency-injection framework or new runtime package is required.

### Negative

- GeometryOS gains another package and a small mapping layer;
- application contracts overlap structurally with current HTTP DTOs;
- adding a new output format requires updating typed application artifacts.

## Rejected alternatives

- keeping orchestration inside API routes would leave CLI and TutorBoard behavior duplicated;
- moving orchestration into `gir_core` would make the pure mathematical core depend on adapters and renderers;
- allowing renderers to validate or repair scenes would make rendering a source of mathematical policy;
- placing a shared helper in `gir_api` would keep CLI coupled to an HTTP package;
- adding a DI framework would be disproportionate to the current synchronous MVP.
''',
)

pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
needle = '  "src/gir_ai",\n  "src/gir_api",'
replacement = '  "src/gir_ai",\n  "src/gir_application",\n  "src/gir_api",'
if needle not in pyproject:
    raise RuntimeError("Could not update wheel package list in pyproject.toml")
(ROOT / "pyproject.toml").write_text(pyproject.replace(needle, replacement), encoding="utf-8")

smoke_path = ROOT / "scripts/package_smoke.py"
smoke = smoke_path.read_text(encoding="utf-8")
needle = '    "gir_ai",\n    "gir_api",'
replacement = '    "gir_ai",\n    "gir_application",\n    "gir_api",'
if needle not in smoke:
    raise RuntimeError("Could not update package smoke public package list")
smoke_path.write_text(smoke.replace(needle, replacement), encoding="utf-8")

readme_path = ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
marker = "## Canonical application pipeline"
if marker not in readme:
    readme += '''

## Canonical application pipeline

GeometryOS delivery adapters delegate geometry workflow policy to `gir_application`:

```text
text → draft GIR → validate → normalize → validate → SVG/TikZ
```

The supported Python entry points are `generate_geometry`, `validate_geometry`, `prepare_geometry` and `render_geometry`. See `docs/APPLICATION_PIPELINE.md` and `docs/adr/ADR-002-canonical-application-pipeline.md`.
'''
    readme_path.write_text(readme, encoding="utf-8")

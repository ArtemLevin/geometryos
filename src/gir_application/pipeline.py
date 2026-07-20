from gir_ai.text_to_gir.adapter import AiAmbiguity, text_to_gir
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
    # GenerationMode remains part of the application contract, while distinct
    # strict/draft semantics are deferred to the stable API work.
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

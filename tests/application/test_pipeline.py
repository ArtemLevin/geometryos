from typing import Any
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
        render_tikz=tikz or Mock(return_value="tikz"),
    )


def test_prepare_geometry_validates_normalizes_and_revalidates(
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = _scene(valid_altitude_payload)
    normalized = scene.model_copy(update={"metadata": {"normalized": True}})
    validator = Mock(side_effect=[_valid_report(), _valid_report()])
    normalizer = Mock(return_value=normalized)

    result = prepare_geometry(
        scene,
        dependencies=_dependencies(validator=validator, normalizer=normalizer),
    )

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


def test_generate_geometry_short_circuits_ambiguity() -> None:
    adapter = Mock(
        return_value=AiAdapterResult(
            status="needs_clarification",
            confidence=0.4,
            ambiguities=[AiAmbiguity(code="missing_angle", message="Choose angle.", options=["A"])],
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
    adapter = Mock(return_value=AiAdapterResult(status="success", confidence=0.9, gir=scene))
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
    assert result.gir is not None
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

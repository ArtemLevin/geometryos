from gir_api.models import (
    ApiAmbiguity,
    ApiWarning,
    GenerateClarificationResponse,
    GenerateErrorResponse,
    GenerateSuccessResponse,
    GenerateV1Response,
    LegacyGenerateResponse,
    RenderSvgV1Response,
    RenderTikzV1Response,
    ValidateGirV1Response,
)
from gir_application import (
    GenerateGeometryResult,
    GenerationStatus,
    OutputFormat,
    PipelineFailureStage,
    RenderGeometryResult,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


def present_generate_v1(result: GenerateGeometryResult) -> GenerateV1Response:
    ambiguities = [
        ApiAmbiguity(code=item.code, message=item.message, options=item.options)
        for item in result.ambiguities
    ]
    warnings = _present_warnings(result)

    if result.status is GenerationStatus.SUCCESS:
        if result.gir is None or result.validation_report is None:
            raise ValueError("Successful generation must contain GIR and validation report.")
        return GenerateSuccessResponse(
            status="success",
            confidence=result.confidence,
            gir=result.gir,
            validation_report=result.validation_report,
            svg=result.artifacts.svg,
            tikz=result.artifacts.tikz,
            warnings=warnings,
            ambiguities=ambiguities,
            explanation=result.explanation,
        )

    if result.status is GenerationStatus.NEEDS_CLARIFICATION:
        return GenerateClarificationResponse(
            status="needs_clarification",
            confidence=result.confidence,
            warnings=warnings,
            ambiguities=ambiguities,
            explanation=result.explanation,
        )

    return GenerateErrorResponse(
        status="error",
        confidence=result.confidence,
        gir=result.gir,
        validation_report=result.validation_report,
        warnings=warnings,
        ambiguities=ambiguities,
        explanation=result.explanation,
    )


def present_generate_legacy(result: GenerateGeometryResult) -> LegacyGenerateResponse:
    return LegacyGenerateResponse(
        status=result.status.value,
        confidence=result.confidence,
        gir=result.gir,
        validation_report=result.validation_report,
        svg=result.artifacts.svg,
        tikz=result.artifacts.tikz,
        warnings=result.warnings,
        ambiguities=[
            ApiAmbiguity(code=item.code, message=item.message, options=item.options)
            for item in result.ambiguities
        ],
        explanation=result.explanation,
    )


def present_validate_v1(
    scene: GirScene,
    report: ValidationReport,
) -> ValidateGirV1Response:
    return ValidateGirV1Response(canonical_gir=scene, validation_report=report)


def present_render_v1(
    result: RenderGeometryResult,
    output: OutputFormat,
) -> RenderSvgV1Response | RenderTikzV1Response:
    content = result.artifacts.svg if output is OutputFormat.SVG else result.artifacts.tikz
    if content is None:
        raise ValueError(f"Renderer did not produce requested output: {output.value}.")
    if output is OutputFormat.SVG:
        return RenderSvgV1Response(content=content)
    return RenderTikzV1Response(content=content)


def _present_warnings(result: GenerateGeometryResult) -> list[ApiWarning]:
    warnings: list[ApiWarning] = []

    for message in result.warnings:
        if message == "Draft GIR failed semantic validation.":
            warnings.append(ApiWarning(code="draft_gir_invalid", message=message))
        elif message == "Normalized GIR failed semantic validation.":
            warnings.append(ApiWarning(code="normalized_gir_invalid", message=message))
        elif result.failure_stage is PipelineFailureStage.ADAPTER:
            warnings.append(
                ApiWarning(
                    code="unsupported_construction",
                    message="Construction is not supported.",
                )
            )
        else:
            warnings.append(ApiWarning(code="adapter_warning", message=message))

    if result.failure_stage is PipelineFailureStage.ADAPTER and not warnings:
        warnings.append(
            ApiWarning(
                code="unsupported_construction",
                message="Construction is not supported.",
            )
        )

    return _deduplicate_warnings(warnings)


def _deduplicate_warnings(warnings: list[ApiWarning]) -> list[ApiWarning]:
    seen: set[tuple[str, str]] = set()
    unique: list[ApiWarning] = []
    for warning in warnings:
        key = (warning.code, warning.message)
        if key not in seen:
            seen.add(key)
            unique.append(warning)
    return unique

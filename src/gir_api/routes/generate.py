from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from gir_ai.text_to_gir.adapter import AiAmbiguity, text_to_gir
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport
from gir_core.normalize import normalize_gir
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz

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
    ambiguities: list[AiAmbiguity] = Field(default_factory=list)
    explanation: str | None = None


@router.post("/generate")
def generate(request: GenerateRequest) -> GenerateResponse:
    result = text_to_gir(request.input)
    if result.gir is None:
        return GenerateResponse(
            status=result.status,
            confidence=result.confidence,
            gir=None,
            validation_report=None,
            warnings=result.warnings,
            ambiguities=result.ambiguities,
            explanation=result.explanation,
        )

    # Design note: validate before normalization so malformed draft GIR is rejected
    # at the boundary where it is produced, not hidden by later pipeline stages.
    draft_report = validate_scene(result.gir)
    if not draft_report.is_valid:
        return GenerateResponse(
            status="error",
            confidence=result.confidence,
            gir=result.gir,
            validation_report=draft_report,
            warnings=[*result.warnings, "Draft GIR failed semantic validation."],
            ambiguities=result.ambiguities,
            explanation=result.explanation,
        )

    # Design note: validate again after normalization because future normalizers may
    # rewrite ids or add derived objects; renderers only see post-validation GIR.
    normalized_gir = normalize_gir(result.gir)
    normalized_report = validate_scene(normalized_gir)
    if not normalized_report.is_valid:
        return GenerateResponse(
            status="error",
            confidence=result.confidence,
            gir=normalized_gir,
            validation_report=normalized_report,
            warnings=[*result.warnings, "Normalized GIR failed semantic validation."],
            ambiguities=result.ambiguities,
            explanation=result.explanation,
        )

    svg: str | None = None
    tikz: str | None = None
    if "svg" in request.output:
        svg = render_svg(normalized_gir)
    if "tikz" in request.output:
        tikz = render_tikz(normalized_gir)

    return GenerateResponse(
        status=result.status,
        confidence=result.confidence,
        gir=normalized_gir,
        validation_report=normalized_report,
        svg=svg,
        tikz=tikz,
        warnings=result.warnings,
        ambiguities=result.ambiguities,
        explanation=result.explanation,
    )

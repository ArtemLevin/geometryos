from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport
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


@router.post("/generate")
def generate(request: GenerateRequest) -> GenerateResponse:
    result = text_to_gir(request.input)
    report = validate_scene(result.gir) if result.gir is not None else None
    svg = render_svg(result.gir) if result.gir is not None and "svg" in request.output and (report is None or report.is_valid) else None
    tikz = render_tikz(result.gir) if result.gir is not None and "tikz" in request.output and (report is None or report.is_valid) else None
    return GenerateResponse(status=result.status, confidence=result.confidence, gir=result.gir, validation_report=report, svg=svg, tikz=tikz, warnings=result.warnings)

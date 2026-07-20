from typing import Literal

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

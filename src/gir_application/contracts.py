from enum import StrEnum
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

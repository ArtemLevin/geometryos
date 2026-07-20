from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from gir_api.constants import MAX_GENERATE_INPUT_CHARS
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport

GenerateInput = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_GENERATE_INPUT_CHARS,
    ),
]
OutputName = Literal["svg", "tikz"]
WarningCode = Literal[
    "unsupported_construction",
    "draft_gir_invalid",
    "normalized_gir_invalid",
    "adapter_warning",
]


class StrictApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApiWarning(StrictApiModel):
    code: WarningCode
    message: str


class ApiAmbiguity(StrictApiModel):
    code: str
    message: str
    options: list[str] = Field(default_factory=list)


class GenerateV1Request(StrictApiModel):
    input_type: Literal["text"]
    input: GenerateInput
    output: list[OutputName] = Field(
        default_factory=list,
        max_length=2,
        json_schema_extra={"uniqueItems": True},
    )
    mode: Literal["strict"] = "strict"

    @field_validator("output")
    @classmethod
    def require_unique_outputs(cls, value: list[OutputName]) -> list[OutputName]:
        if len(value) != len(set(value)):
            raise ValueError("Output formats must be unique.")
        return value


class GenerateSuccessResponse(StrictApiModel):
    status: Literal["success"]
    confidence: float = Field(ge=0, le=1)
    schema_version: Literal["0.2.0"] = "0.2.0"
    gir: GirScene
    validation_report: ValidationReport
    svg: str | None = None
    tikz: str | None = None
    warnings: list[ApiWarning] = Field(default_factory=list)
    ambiguities: list[ApiAmbiguity] = Field(default_factory=list)
    explanation: str | None = None


class GenerateClarificationResponse(StrictApiModel):
    status: Literal["needs_clarification"]
    confidence: float = Field(ge=0, le=1)
    schema_version: Literal["0.2.0"] = "0.2.0"
    gir: None = None
    validation_report: None = None
    svg: None = None
    tikz: None = None
    warnings: list[ApiWarning] = Field(default_factory=list)
    ambiguities: list[ApiAmbiguity] = Field(default_factory=list)
    explanation: str | None = None


class GenerateErrorResponse(StrictApiModel):
    status: Literal["error"]
    confidence: float = Field(ge=0, le=1)
    schema_version: Literal["0.2.0"] = "0.2.0"
    gir: GirScene | None = None
    validation_report: ValidationReport | None = None
    svg: None = None
    tikz: None = None
    warnings: list[ApiWarning] = Field(default_factory=list)
    ambiguities: list[ApiAmbiguity] = Field(default_factory=list)
    explanation: str | None = None


GenerateV1Response: TypeAlias = Annotated[
    GenerateSuccessResponse | GenerateClarificationResponse | GenerateErrorResponse,
    Field(discriminator="status"),
]


class ValidateGirV1Response(StrictApiModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    canonical_gir: GirScene
    validation_report: ValidationReport


class RenderSvgV1Response(StrictApiModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    media_type: Literal["image/svg+xml"] = "image/svg+xml"
    content: str


class RenderTikzV1Response(StrictApiModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    media_type: Literal["text/x-tex"] = "text/x-tex"
    content: str


class LegacyGenerateRequest(StrictApiModel):
    input_type: Literal["text"]
    input: str
    output: list[OutputName] = Field(default_factory=list)
    mode: Literal["strict", "draft"] = "strict"


class LegacyGenerateResponse(StrictApiModel):
    status: str
    confidence: float
    gir: GirScene | None
    validation_report: ValidationReport | None
    svg: str | None = None
    tikz: str | None = None
    warnings: list[str]
    ambiguities: list[ApiAmbiguity] = Field(default_factory=list)
    explanation: str | None = None


class LegacyRenderResponse(StrictApiModel):
    content: str

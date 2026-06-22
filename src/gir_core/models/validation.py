from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    path: str | None = None
    severity: Literal["error", "warning"] = "error"


class ValidationWarning(ValidationIssue):
    severity: Literal["warning"] = "warning"


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)

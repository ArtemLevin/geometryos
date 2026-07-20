from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gir_core.compatibility import GirCompatibilityResult, canonicalize_gir_payload
from gir_core.models.constraints import GirConstraint
from gir_core.models.construction import ConstructionStep
from gir_core.models.objects import GirObject
from gir_core.versioning import GIR_SCHEMA_ID, GIR_SCHEMA_VERSION


class GirScene(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "$id": GIR_SCHEMA_ID,
            "x-gir-schema-version": GIR_SCHEMA_VERSION,
        },
    )

    schema_version: Literal["0.2.0"]
    scene_type: Literal["2d"]
    objects: list[GirObject]
    constraints: list[GirConstraint]
    construction_steps: list[ConstructionStep]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def canonicalize_schema_version(cls, value: object) -> object:
        result = canonicalize_gir_payload(value)
        if isinstance(result, GirCompatibilityResult):
            return result.payload
        return result

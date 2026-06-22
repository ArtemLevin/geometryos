from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from gir_core.models.constraints import GirConstraint
from gir_core.models.construction import ConstructionStep
from gir_core.models.objects import GirObject


class GirScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    scene_type: Literal["2d"]
    objects: list[GirObject]
    constraints: list[GirConstraint]
    construction_steps: list[ConstructionStep]
    metadata: dict[str, Any] = Field(default_factory=dict)

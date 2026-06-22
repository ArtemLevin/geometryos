from pydantic import BaseModel, ConfigDict, Field


class ConstructionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    action: str
    objects: list[str]
    constraints: list[str] = Field(default_factory=list)
    reason: str | None = None

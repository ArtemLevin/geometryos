from pydantic import BaseModel, ConfigDict


class LayoutPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_id: str
    x: float
    y: float

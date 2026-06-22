from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LayoutPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    x: float
    y: float
    label: str | None = None


class LayoutSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    start: str
    end: str
    style: Literal["solid", "dashed"] = "solid"


class LayoutLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    target: str
    text: str
    dx: float = 6
    dy: float = -6


class LayoutScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: dict[str, LayoutPoint]
    segments: list[LayoutSegment]
    labels: list[LayoutLabel] = Field(default_factory=list)
    width: float = 280
    height: float = 220

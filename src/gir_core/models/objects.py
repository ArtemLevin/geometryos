from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PointObject(StrictModel):
    id: str
    type: Literal["point"]
    label: str | None = None


class SegmentObject(StrictModel):
    id: str
    type: Literal["segment"]
    points: tuple[str, str]


class LineObject(StrictModel):
    id: str
    type: Literal["line"]
    points: tuple[str, str]


class RayObject(StrictModel):
    id: str
    type: Literal["ray"]
    start: str
    through: str


class CircleObject(StrictModel):
    id: str
    type: Literal["circle"]
    center: str
    radius_point: str | None = None


class TriangleObject(StrictModel):
    id: str
    type: Literal["triangle"]
    vertices: tuple[str, str, str]


class AngleObject(StrictModel):
    id: str
    type: Literal["angle"]
    points: tuple[str, str, str]


class LabelObject(StrictModel):
    id: str
    type: Literal["label"]
    text: str
    target: str


GirObject = Annotated[
    Union[
        PointObject,
        SegmentObject,
        LineObject,
        RayObject,
        CircleObject,
        TriangleObject,
        AngleObject,
        LabelObject,
    ],
    Field(discriminator="type"),
]

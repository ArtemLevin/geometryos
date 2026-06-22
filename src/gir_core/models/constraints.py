from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConstraintBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    reason: str | None = None


class BelongsToConstraint(ConstraintBase):
    type: Literal["belongs_to"]
    point: str
    object: str


class CollinearConstraint(ConstraintBase):
    type: Literal["collinear"]
    points: tuple[str, ...]


class NonCollinearConstraint(ConstraintBase):
    type: Literal["non_collinear"]
    points: tuple[str, str, str]


class ParallelConstraint(ConstraintBase):
    type: Literal["parallel"]
    objects: tuple[str, str]


class PerpendicularConstraint(ConstraintBase):
    type: Literal["perpendicular"]
    objects: tuple[str, str]


class EqualLengthConstraint(ConstraintBase):
    type: Literal["equal_length"]
    objects: tuple[str, str]


class MidpointConstraint(ConstraintBase):
    type: Literal["midpoint"]
    point: str
    object: str


class IntersectionConstraint(ConstraintBase):
    type: Literal["intersection"]
    point: str
    objects: tuple[str, str]


class AltitudeConstraint(ConstraintBase):
    type: Literal["altitude"]
    from_point: str
    to_object: str
    foot: str
    segment: str


class MedianConstraint(ConstraintBase):
    type: Literal["median"]
    from_point: str
    to_object: str
    midpoint: str
    segment: str


class AngleBisectorConstraint(ConstraintBase):
    type: Literal["angle_bisector"]
    angle: str
    ray: str


class CircumcircleConstraint(ConstraintBase):
    type: Literal["circumcircle"]
    triangle: str
    circle: str


class IncircleConstraint(ConstraintBase):
    type: Literal["incircle"]
    triangle: str
    circle: str


GirConstraint = Annotated[
    BelongsToConstraint
    | CollinearConstraint
    | NonCollinearConstraint
    | ParallelConstraint
    | PerpendicularConstraint
    | EqualLengthConstraint
    | MidpointConstraint
    | IntersectionConstraint
    | AltitudeConstraint
    | MedianConstraint
    | AngleBisectorConstraint
    | CircumcircleConstraint
    | IncircleConstraint,
    Field(discriminator="type"),
]

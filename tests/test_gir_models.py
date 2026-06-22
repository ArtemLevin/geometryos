import pytest
from pydantic import TypeAdapter, ValidationError

from gir_core.models.objects import GirObject, PointObject, SegmentObject, TriangleObject


def test_valid_point() -> None:
    assert PointObject(id="A", type="point", label="A").id == "A"


def test_valid_segment() -> None:
    assert SegmentObject(id="AB", type="segment", points=("A", "B")).points == ("A", "B")


def test_valid_triangle() -> None:
    assert TriangleObject(id="ABC", type="triangle", vertices=("A", "B", "C")).vertices[0] == "A"


def test_invalid_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        PointObject(id="A", type="point", color="red")  # type: ignore[call-arg]


def test_invalid_object_type_fails() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(GirObject).validate_python({"id": "x", "type": "unknown"})

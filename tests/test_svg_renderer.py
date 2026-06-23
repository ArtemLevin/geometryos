import pytest

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.models.constraints import NonCollinearConstraint
from gir_core.models.objects import PointObject, SegmentObject, TriangleObject
from gir_core.models.scene import GirScene
from gir_render.svg_renderer import render_svg


def _altitude_scene() -> GirScene:
    scene = text_to_gir(
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."
    ).gir
    assert scene is not None
    return scene


def _pqr_triangle_scene() -> GirScene:
    return GirScene(
        version="0.1",
        scene_type="2d",
        objects=[
            PointObject(id="P", type="point", label="P"),
            PointObject(id="Q", type="point", label="Q"),
            PointObject(id="R", type="point", label="R"),
            SegmentObject(id="PQ", type="segment", points=("P", "Q")),
            SegmentObject(id="QR", type="segment", points=("Q", "R")),
            SegmentObject(id="RP", type="segment", points=("R", "P")),
            TriangleObject(id="PQR", type="triangle", vertices=("P", "Q", "R")),
        ],
        constraints=[
            NonCollinearConstraint(
                id="non_collinear_PQR",
                type="non_collinear",
                points=("P", "Q", "R"),
            )
        ],
        construction_steps=[],
        metadata={},
    )


def test_render_svg_triangle() -> None:
    svg = render_svg(_altitude_scene())
    assert isinstance(svg, str)
    assert "<svg" in svg and "</svg>" in svg
    assert "A" in svg and "B" in svg and "C" in svg


def test_render_svg_arbitrary_triangle_labels() -> None:
    svg = render_svg(_pqr_triangle_scene())

    assert "P" in svg
    assert "Q" in svg
    assert "R" in svg


def test_render_svg_rejects_semantic_invalid_gir() -> None:
    data = _altitude_scene().model_dump()
    data["constraints"][3]["segment"] = "H"

    with pytest.raises(ValueError, match="semantic-invalid GIR"):
        render_svg(GirScene.model_validate(data))

import pytest

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.layout.simple_layout import create_simple_layout
from gir_core.models.constraints import NonCollinearConstraint
from gir_core.models.layout import LayoutScene
from gir_core.models.objects import PointObject, SegmentObject, TriangleObject
from gir_core.models.scene import GirScene
from gir_render.svg_renderer import render_svg_layout
from gir_render.tikz_renderer import render_tikz_layout


def _scene_from_prompt(prompt: str) -> GirScene:
    result = text_to_gir(prompt)
    assert result.gir is not None
    return result.gir


def _altitude_layout() -> LayoutScene:
    return create_simple_layout(
        _scene_from_prompt("Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.")
    )


def _median_layout() -> LayoutScene:
    return create_simple_layout(
        _scene_from_prompt(
            "Постройте треугольник ABC. Проведите медиану из вершины A к стороне BC."
        )
    )


def _midpoint_layout() -> LayoutScene:
    return create_simple_layout(
        _scene_from_prompt("Постройте треугольник ABC. Отметьте середину M стороны BC.")
    )


def _angle_bisector_layout() -> LayoutScene:
    return create_simple_layout(
        _scene_from_prompt("Постройте треугольник ABC. Проведите биссектрису угла A.")
    )


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


def test_simple_layout_contains_triangle_points() -> None:
    layout = _altitude_layout()
    assert {"A", "B", "C"}.issubset(layout.points)
    assert layout.points["A"].x == 120
    assert layout.points["B"].y == 180


def test_layout_places_arbitrary_triangle_vertices_by_order() -> None:
    layout = create_simple_layout(_pqr_triangle_scene())

    assert {"P", "Q", "R"}.issubset(layout.points)
    assert layout.points["P"].x == 120
    assert layout.points["P"].y == 40
    assert layout.points["Q"].x == 40
    assert layout.points["R"].x == 240


def test_layout_places_midpoint_at_segment_midpoint() -> None:
    layout = _midpoint_layout()
    b = layout.points["B"]
    c = layout.points["C"]
    m = layout.points["M"]

    assert m.x == pytest.approx((b.x + c.x) / 2)
    assert m.y == pytest.approx((b.y + c.y) / 2)


def test_layout_draws_median_segment_to_midpoint() -> None:
    layout = _median_layout()
    assert "AM" in {segment.id for segment in layout.segments}

    a = layout.points["A"]
    b = layout.points["B"]
    c = layout.points["C"]
    m = layout.points["M"]
    assert m.x == pytest.approx((b.x + c.x) / 2)
    assert m.y == pytest.approx((b.y + c.y) / 2)
    assert any(
        segment.id == "AM" and segment.start == a.id and segment.end == m.id
        for segment in layout.segments
    )


def test_layout_places_altitude_foot_on_base_line() -> None:
    layout = _altitude_layout()
    h = layout.points["H"]
    b = layout.points["B"]
    c = layout.points["C"]

    assert h.y == pytest.approx(b.y)
    assert h.y == pytest.approx(c.y)


def test_layout_places_angle_bisector_through_point() -> None:
    layout = _angle_bisector_layout()

    assert "D" in layout.points
    assert "bisector_A" in {segment.id for segment in layout.segments}


def test_simple_layout_contains_altitude_segment() -> None:
    layout = _altitude_layout()
    assert "H" in layout.points
    assert any(segment.id == "AH" and segment.start == "A" for segment in layout.segments)


def test_svg_renderer_uses_layout_scene() -> None:
    layout = _altitude_layout()
    svg = render_svg_layout(layout)
    assert "<svg" in svg
    assert "A" in svg
    assert "120" in svg


def test_tikz_renderer_uses_layout_scene() -> None:
    layout = _altitude_layout()
    tikz = render_tikz_layout(layout)
    assert "\\begin{tikzpicture}" in tikz
    assert "\\coordinate (A)" in tikz
    assert "\\draw" in tikz

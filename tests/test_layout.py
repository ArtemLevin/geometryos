from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.layout.simple_layout import create_simple_layout
from gir_core.models.layout import LayoutScene
from gir_render.svg_renderer import render_svg_layout
from gir_render.tikz_renderer import render_tikz_layout


def _altitude_layout() -> LayoutScene:
    result = text_to_gir("Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.")
    assert result.gir is not None
    return create_simple_layout(result.gir)


def test_simple_layout_contains_triangle_points() -> None:
    layout = _altitude_layout()
    assert {"A", "B", "C"}.issubset(layout.points)
    assert layout.points["A"].x == 120
    assert layout.points["B"].y == 180


def test_simple_layout_contains_altitude_foot() -> None:
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

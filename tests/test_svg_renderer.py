from gir_ai.text_to_gir.adapter import text_to_gir
from gir_render.svg_renderer import render_svg


def test_render_svg_triangle() -> None:
    scene = text_to_gir(
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."
    ).gir
    assert scene is not None
    svg = render_svg(scene)
    assert isinstance(svg, str)
    assert "<svg" in svg and "</svg>" in svg
    assert "A" in svg and "B" in svg and "C" in svg

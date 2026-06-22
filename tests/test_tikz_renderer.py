from gir_ai.text_to_gir.adapter import text_to_gir
from gir_render.tikz_renderer import render_tikz


def test_render_tikz_triangle() -> None:
    scene = text_to_gir(
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."
    ).gir
    assert scene is not None
    tikz = render_tikz(scene)
    assert isinstance(tikz, str)
    assert "\\begin{tikzpicture}" in tikz
    assert "\\end{tikzpicture}" in tikz
    assert "\\coordinate (A)" in tikz

def test_generate_altitude_returns_svg_tikz_and_explanation(client: object) -> None:
    response = client.post(  # type: ignore[attr-defined]
        "/generate",
        json={
            "input_type": "text",
            "input": "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
            "output": ["svg", "tikz"],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["gir"] is not None
    assert data["validation_report"]["is_valid"] is True
    assert data["svg"] is not None
    assert data["tikz"] is not None
    assert data["ambiguities"] == []
    assert data["explanation"]


def test_generate_ambiguous_bisector_returns_options(client: object) -> None:
    response = client.post(  # type: ignore[attr-defined]
        "/generate",
        json={
            "input_type": "text",
            "input": "Постройте треугольник ABC. Проведите биссектрису.",
            "output": ["svg", "tikz"],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["gir"] is None
    assert data["svg"] is None
    assert data["tikz"] is None
    assert data["ambiguities"]
    assert data["ambiguities"][0]["code"] == "missing_angle"
    assert data["ambiguities"][0]["options"] == ["angle_A", "angle_B", "angle_C"]
    assert data["explanation"] == "Bisector request lacks angle target."


def test_generate_unmatched_text_returns_error_explanation(client: object) -> None:
    response = client.post(  # type: ignore[attr-defined]
        "/generate",
        json={
            "input_type": "text",
            "input": "Постройте квадрат.",
            "output": ["svg"],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["gir"] is None
    assert data["ambiguities"] == []
    assert data["warnings"] == ["No rule matched input."]
    assert data["explanation"] == "Skeleton adapter supports only MVP benchmark prompts."

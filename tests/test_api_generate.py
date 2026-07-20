from typing import Any

ALTITUDE_PROMPT = "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."


def test_generate_altitude_returns_valid_response(client: Any) -> None:
    response = client.post(
        "/generate",
        json={
            "input_type": "text",
            "input": ALTITUDE_PROMPT,
            "output": ["svg", "tikz"],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert isinstance(data["confidence"], float)
    assert data["gir"] is not None
    assert data["validation_report"] is not None
    assert data["validation_report"]["is_valid"] is True
    assert data["svg"] is not None
    assert "<svg" in data["svg"]
    assert data["tikz"] is not None
    assert "\\begin{tikzpicture}" in data["tikz"]
    assert data["warnings"] == []
    assert data["ambiguities"] == []
    assert data["explanation"]


def test_generate_altitude_without_render_outputs(client: Any) -> None:
    response = client.post(
        "/generate",
        json={
            "input_type": "text",
            "input": ALTITUDE_PROMPT,
            "output": [],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["gir"] is not None
    assert data["validation_report"]["is_valid"] is True
    assert data["svg"] is None
    assert data["tikz"] is None


def test_generate_ambiguous_bisector_returns_clarification(client: Any) -> None:
    response = client.post(
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
    assert data["confidence"] < 1
    assert data["gir"] is None
    assert data["validation_report"] is None
    assert data["svg"] is None
    assert data["tikz"] is None
    assert data["warnings"] == []
    assert data["ambiguities"]
    assert data["ambiguities"][0]["code"] == "missing_angle"
    assert data["ambiguities"][0]["options"] == ["angle_A", "angle_B", "angle_C"]
    assert data["explanation"] == "Bisector request lacks angle target."


def test_generate_unsupported_text_returns_error(client: Any) -> None:
    response = client.post(
        "/generate",
        json={
            "input_type": "text",
            "input": "Постройте невозможную конструкцию с магическим квадратом.",
            "output": ["svg"],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "error"
    assert data["gir"] is None
    assert data["validation_report"] is None
    assert data["svg"] is None
    assert data["tikz"] is None
    assert data["ambiguities"] == []
    assert data["warnings"] == ["No rule matched input."]
    assert data["explanation"] == "Skeleton adapter supports only MVP benchmark prompts."


def test_generate_invalid_request_payload_returns_422(client: Any) -> None:
    response = client.post(
        "/generate",
        json={"input": "missing required input_type"},
    )

    assert response.status_code == 422


def test_generate_returns_canonical_gir_0_2(client: Any) -> None:
    response = client.post(
        "/generate",
        json={
            "input_type": "text",
            "input": ALTITUDE_PROMPT,
            "output": [],
            "mode": "strict",
        },
    )

    assert response.status_code == 200
    gir = response.json()["gir"]
    assert gir["schema_version"] == "0.2.0"
    assert "version" not in gir

from typing import Any


def test_render_svg_valid_scene(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/render/svg", json=valid_altitude_payload)

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "<svg" in data["content"]
    assert "A" in data["content"]
    assert "B" in data["content"]
    assert "C" in data["content"]


def test_render_svg_semantic_invalid_scene_returns_422(
    client: Any,
    semantic_invalid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/render/svg", json=semantic_invalid_altitude_payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"]["is_valid"] is False


def test_render_svg_structurally_invalid_scene_returns_422(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["objects"][0]["type"] = "unknown_object_type"

    response = client.post("/render/svg", json=valid_altitude_payload)

    assert response.status_code == 422


def test_render_tikz_valid_scene(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/render/tikz", json=valid_altitude_payload)

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "\\begin{tikzpicture}" in data["content"]
    assert "\\draw" in data["content"]


def test_render_tikz_semantic_invalid_scene_returns_422(
    client: Any,
    semantic_invalid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/render/tikz", json=semantic_invalid_altitude_payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"]["is_valid"] is False


def test_render_tikz_structurally_invalid_scene_returns_422(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["objects"][0]["type"] = "unknown_object_type"

    response = client.post("/render/tikz", json=valid_altitude_payload)

    assert response.status_code == 422

from typing import Any


def test_validate_gir_valid_scene(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/validate-gir", json=valid_altitude_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["issues"] == []


def test_validate_gir_semantic_invalid_scene(
    client: Any,
    semantic_invalid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/validate-gir", json=semantic_invalid_altitude_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert data["issues"]


def test_validate_gir_structurally_invalid_scene_returns_422(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["objects"][0]["type"] = "unknown_object_type"

    response = client.post("/validate-gir", json=valid_altitude_payload)

    assert response.status_code == 422

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


def test_validate_gir_accepts_legacy_0_1(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["version"] = "0.1"
    del valid_altitude_payload["schema_version"]

    response = client.post("/validate-gir", json=valid_altitude_payload)

    assert response.status_code == 200
    assert response.json()["is_valid"] is True


def test_validate_gir_rejects_missing_schema_version(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    del valid_altitude_payload["schema_version"]
    response = client.post("/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "gir_schema_version_missing"


def test_validate_gir_rejects_unknown_schema_version(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["schema_version"] = "0.3.0"
    response = client.post("/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "gir_schema_version_unsupported"


def test_validate_gir_rejects_conflicting_version_fields(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    valid_altitude_payload["version"] = "0.1"
    response = client.post("/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "gir_schema_version_conflict"

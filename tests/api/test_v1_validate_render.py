from copy import deepcopy
from typing import Any


def test_validate_v1_returns_canonical_scene_and_report(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/validate-gir", json=valid_altitude_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == "0.2.0"
    assert data["canonical_gir"]["schema_version"] == "0.2.0"
    assert data["validation_report"]["is_valid"] is True


def test_validate_v1_semantic_invalid_scene_is_http_200(
    client: Any,
    semantic_invalid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post(
        "/api/v1/validate-gir",
        json=semantic_invalid_altitude_payload,
    )

    assert response.status_code == 200
    assert response.json()["validation_report"]["is_valid"] is False


def test_validate_v1_upgrades_legacy_gir(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    payload = deepcopy(valid_altitude_payload)
    payload["version"] = "0.1"
    del payload["schema_version"]

    response = client.post("/api/v1/validate-gir", json=payload)

    assert response.status_code == 200
    canonical = response.json()["canonical_gir"]
    assert canonical["schema_version"] == "0.2.0"
    assert "version" not in canonical


def test_validate_v1_rejects_structural_invalid_gir(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    payload = deepcopy(valid_altitude_payload)
    payload["schema_version"] = "0.3.0"

    response = client.post("/api/v1/validate-gir", json=payload)
    assert response.status_code == 422


def test_render_svg_v1_contract(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/render/svg", json=valid_altitude_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == "0.2.0"
    assert data["media_type"] == "image/svg+xml"
    assert "<svg" in data["content"]


def test_render_tikz_v1_contract(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/render/tikz", json=valid_altitude_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == "0.2.0"
    assert data["media_type"] == "text/x-tex"
    assert "\\begin{tikzpicture}" in data["content"]


def test_render_v1_rejects_semantic_invalid_gir(
    client: Any,
    semantic_invalid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post(
        "/api/v1/render/svg",
        json=semantic_invalid_altitude_payload,
    )
    assert response.status_code == 422

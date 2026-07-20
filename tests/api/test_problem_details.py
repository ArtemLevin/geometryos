from typing import Any

from gir_api.constants import PROBLEM_MEDIA_TYPE, REQUEST_ID_HEADER


def test_v1_request_validation_is_sanitized_problem(client: Any) -> None:
    secret = "SECRET-PROMPT-CONTENT"
    response = client.post(
        "/api/v1/generate",
        json={
            "input_type": "text",
            "input": secret,
            "output": ["svg", "svg"],
            "mode": "strict",
        },
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    data = response.json()
    assert data["code"] == "request_validation_failed"
    assert data["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert data["errors"]
    assert secret not in response.text
    assert "input" not in data["errors"][0]


def test_custom_gir_version_error_code_is_preserved(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    del valid_altitude_payload["schema_version"]
    response = client.post("/api/v1/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "gir_schema_version_missing"


def test_v1_semantic_render_error_is_problem(
    client: Any,
    semantic_invalid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/render/svg", json=semantic_invalid_altitude_payload)
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "semantic_validation_failed"
    assert data["errors"]
    assert data["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_validate_keeps_semantic_invalid_as_domain_result(
    client: Any,
    semantic_invalid_altitude_payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/validate-gir", json=semantic_invalid_altitude_payload)
    assert response.status_code == 200
    assert response.json()["validation_report"]["is_valid"] is False


def test_v1_not_found_and_method_not_allowed_are_problems(client: Any) -> None:
    not_found = client.get("/api/v1/unknown")
    method_not_allowed = client.get("/api/v1/generate")
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "not_found"
    assert method_not_allowed.status_code == 405
    assert method_not_allowed.json()["code"] == "method_not_allowed"


def test_unversioned_not_found_keeps_default_shape(client: Any) -> None:
    response = client.get("/unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

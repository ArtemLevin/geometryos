from typing import Any

from fastapi.testclient import TestClient

from gir_api.constants import REQUEST_ID_HEADER
from gir_api.main import create_app
from gir_api.settings import ApiSettings

ORIGIN = "http://localhost:5173"


def test_cors_is_disabled_by_default(client: Any) -> None:
    response = client.get("/health", headers={"Origin": ORIGIN})
    assert "access-control-allow-origin" not in response.headers


def test_allowed_preflight_preserves_request_context() -> None:
    app = create_app(settings=ApiSettings(cors_allowed_origins=ORIGIN, _env_file=None))
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/generate",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Request-ID",
                REQUEST_ID_HEADER: "cors-preflight",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "x-request-id" in response.headers["access-control-allow-headers"].lower()
    assert response.headers[REQUEST_ID_HEADER] == "cors-preflight"


def test_actual_response_exposes_request_id() -> None:
    app = create_app(settings=ApiSettings(cors_allowed_origins=ORIGIN, _env_file=None))
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={"Origin": ORIGIN, REQUEST_ID_HEADER: "cors-actual"},
        )
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert REQUEST_ID_HEADER.lower() in response.headers[
        "access-control-expose-headers"
    ].lower()
    assert response.headers[REQUEST_ID_HEADER] == "cors-actual"
    assert response.headers.get("access-control-allow-credentials") != "true"


def test_disallowed_origin_is_not_granted() -> None:
    app = create_app(settings=ApiSettings(cors_allowed_origins=ORIGIN, _env_file=None))
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

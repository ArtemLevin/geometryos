from fastapi.testclient import TestClient

from gir_api.main import create_app
from gir_api.settings import ApiSettings

_ALLOWED_ORIGIN = "http://localhost:5173"
_GENERATE_REQUEST = {
    "input_type": "text",
    "input": "Постройте треугольник ABC.",
    "mode": "strict",
}


def _client(origins: str) -> TestClient:
    return TestClient(create_app(settings=ApiSettings(cors_allowed_origins=origins)))


def test_cors_is_disabled_by_default() -> None:
    with _client("") as client:
        response = client.get("/health", headers={"Origin": _ALLOWED_ORIGIN})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_allowed_preflight_is_correlated() -> None:
    with _client(_ALLOWED_ORIGIN) as client:
        response = client.options(
            "/api/v1/generate",
            headers={
                "Origin": _ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Request-ID",
                "X-Request-ID": "cors-preflight",
            },
        )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "x-request-id" in response.headers["Access-Control-Allow-Headers"].lower()
    assert response.headers["X-Request-ID"] == "cors-preflight"
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_actual_response_exposes_request_id() -> None:
    with _client(_ALLOWED_ORIGIN) as client:
        response = client.post(
            "/api/v1/generate",
            json=_GENERATE_REQUEST,
            headers={"Origin": _ALLOWED_ORIGIN, "X-Request-ID": "cors-actual"},
        )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert "x-request-id" in response.headers["Access-Control-Expose-Headers"].lower()
    assert response.headers["X-Request-ID"] == "cors-actual"


def test_unconfigured_origin_is_not_allowed() -> None:
    with _client(_ALLOWED_ORIGIN) as client:
        response = client.get("/health", headers={"Origin": "http://attacker.invalid"})
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers

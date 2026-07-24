from typing import Any

import pytest
from fastapi.testclient import TestClient

from gir_api.constants import REQUEST_ID_HEADER
from gir_api.main import create_app
from gir_api.openapi_examples import ALTITUDE_GIR_EXAMPLE
from gir_api.readiness import ServiceLifecycle


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/api/v1/generate",
            {
                "input_type": "text",
                "input": "Постройте треугольник ABC.",
                "mode": "strict",
            },
        ),
        ("/api/v1/validate-gir", ALTITUDE_GIR_EXAMPLE),
        ("/api/v1/render/svg", ALTITUDE_GIR_EXAMPLE),
        ("/api/v1/render/tikz", ALTITUDE_GIR_EXAMPLE),
    ],
)
def test_stable_operation_returns_correlated_problem_when_not_ready(
    path: str,
    payload: dict[str, Any],
) -> None:
    lifecycle = ServiceLifecycle()
    application = create_app(lifecycle=lifecycle)
    with TestClient(application) as client:
        lifecycle.mark_stopping()
        response = client.post(
            path,
            json=payload,
            headers={REQUEST_ID_HEADER: "not-ready"},
        )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers[REQUEST_ID_HEADER] == "not-ready"
    assert response.json() == {
        "type": "urn:geometryos:problem:service-unavailable",
        "title": "Service unavailable",
        "status": 503,
        "detail": "GeometryOS is not ready to accept application requests.",
        "instance": path,
        "code": "service_unavailable",
        "request_id": "not-ready",
        "errors": [],
    }


def test_legacy_generate_is_not_readiness_gated() -> None:
    lifecycle = ServiceLifecycle()
    application = create_app(lifecycle=lifecycle)
    with TestClient(application) as client:
        lifecycle.mark_stopping()
        response = client.post(
            "/generate",
            json={
                "input_type": "text",
                "input": "Постройте треугольник ABC.",
                "mode": "strict",
            },
        )
    assert response.status_code == 200

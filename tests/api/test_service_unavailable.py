from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from gir_api.main import create_app
from gir_api.openapi_examples import ALTITUDE_GIR_EXAMPLE
from gir_api.readiness import ServiceLifecycle


class CountingExecutor:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("generate must not run while the service is not ready")

    async def validate(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("validate must not run while the service is not ready")

    async def render_svg(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("render_svg must not run while the service is not ready")

    async def render_tikz(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("render_tikz must not run while the service is not ready")


RequestCall = Callable[[TestClient], Any]


@pytest.mark.parametrize(
    "call",
    [
        lambda client: client.post(
            "/api/v1/generate",
            json={"input_type": "text", "input": "Постройте треугольник ABC.", "mode": "strict"},
            headers={"X-Request-ID": "unavailable-generate"},
        ),
        lambda client: client.post(
            "/api/v1/validate-gir",
            json=ALTITUDE_GIR_EXAMPLE,
            headers={"X-Request-ID": "unavailable-validate"},
        ),
        lambda client: client.post(
            "/api/v1/render/svg",
            json=ALTITUDE_GIR_EXAMPLE,
            headers={"X-Request-ID": "unavailable-svg"},
        ),
        lambda client: client.post(
            "/api/v1/render/tikz",
            json=ALTITUDE_GIR_EXAMPLE,
            headers={"X-Request-ID": "unavailable-tikz"},
        ),
    ],
)
def test_stable_operations_return_problem_details_before_executor(call: RequestCall) -> None:
    lifecycle = ServiceLifecycle()
    executor = CountingExecutor()
    with TestClient(create_app(executor=executor, lifecycle=lifecycle)) as client:
        lifecycle.mark_stopping()
        response = call(client)

    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Type"].startswith("application/problem+json")
    assert response.json()["code"] == "service_unavailable"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert executor.calls == 0


def test_health_and_readiness_keep_their_probe_contracts() -> None:
    lifecycle = ServiceLifecycle()
    with TestClient(create_app(lifecycle=lifecycle)) as client:
        lifecycle.mark_stopping()
        health = client.get("/health")
        ready = client.get("/ready")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
    assert ready.headers["Content-Type"].startswith("application/json")

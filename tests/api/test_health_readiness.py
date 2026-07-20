from collections.abc import Callable
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gir_api.execution import TimedApplicationExecutor
from gir_api.readiness import LifecyclePhase, ServiceLifecycle


def test_health_remains_the_existing_liveness_contract(client: Any) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_readiness_is_ready_inside_lifespan(client: Any) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]
    assert response.json() == {
        "status": "ready",
        "checks": [
            {"name": "lifecycle", "status": "pass"},
            {"name": "settings", "status": "pass"},
            {"name": "executor", "status": "pass"},
        ],
    }


def test_lifecycle_transitions_around_fastapi_lifespan(
    app_factory: Callable[..., FastAPI],
) -> None:
    lifecycle = ServiceLifecycle()
    application = app_factory(lifecycle=lifecycle)

    assert lifecycle.phase is LifecyclePhase.STARTING
    with TestClient(application) as client:
        assert lifecycle.phase is LifecyclePhase.READY
        assert client.get("/ready").status_code == 200
    assert lifecycle.phase is LifecyclePhase.STOPPING


def test_liveness_stays_up_when_readiness_is_stopping(
    app_factory: Callable[..., FastAPI],
) -> None:
    lifecycle = ServiceLifecycle()
    application = app_factory(lifecycle=lifecycle)

    with TestClient(application) as client:
        lifecycle.mark_stopping()

        health_response = client.get("/health")
        ready_response = client.get("/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert ready_response.status_code == 503
    assert ready_response.headers["Cache-Control"] == "no-store"
    assert ready_response.json()["status"] == "not_ready"
    assert {item["name"]: item["status"] for item in ready_response.json()["checks"]}[
        "lifecycle"
    ] == "fail"


@pytest.mark.parametrize("missing_state", ["settings", "application_executor"])
def test_readiness_fails_when_runtime_component_disappears(
    app_factory: Callable[..., FastAPI],
    missing_state: str,
) -> None:
    application = app_factory()

    with TestClient(application) as client:
        delattr(application.state, missing_state)
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    checks = {item["name"]: item["status"] for item in response.json()["checks"]}
    expected_check = "settings" if missing_state == "settings" else "executor"
    assert checks[expected_check] == "fail"


def test_startup_failure_marks_lifecycle_failed(
    app_factory: Callable[..., FastAPI],
) -> None:
    lifecycle = ServiceLifecycle()
    malformed_executor = cast(TimedApplicationExecutor, object())
    application = app_factory(executor=malformed_executor, lifecycle=lifecycle)

    with (
        pytest.raises(RuntimeError, match="Runtime components are not ready"),
        TestClient(application),
    ):
        pass

    assert lifecycle.phase is LifecyclePhase.FAILED


def test_app_instances_have_independent_lifecycle_state(
    app_factory: Callable[..., FastAPI],
) -> None:
    first = app_factory()
    second = app_factory()

    assert first.state.lifecycle is not second.state.lifecycle
    first.state.lifecycle.mark_failed()
    assert first.state.lifecycle.phase is LifecyclePhase.FAILED
    assert second.state.lifecycle.phase is LifecyclePhase.STARTING

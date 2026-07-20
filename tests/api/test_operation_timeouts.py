import time
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gir_api.execution import TimedApplicationExecutor
from gir_api.settings import ApiSettings
from gir_application import (
    GenerateGeometryCommand,
    GenerateGeometryResult,
    RenderGeometryCommand,
    RenderGeometryResult,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


def test_generate_timeout_returns_504_without_waiting_for_worker(app_factory: Any) -> None:
    settings = ApiSettings(generate_timeout_seconds=0.01)

    def slow_generate(command: GenerateGeometryCommand) -> GenerateGeometryResult:
        del command
        time.sleep(0.2)
        raise AssertionError("The abandoned worker result must not be observed.")

    executor = TimedApplicationExecutor(settings=settings, generate_fn=slow_generate)
    app: FastAPI = app_factory(settings=settings, executor=executor)
    started = time.perf_counter()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/generate",
            json={
                "input_type": "text",
                "input": "Постройте треугольник ABC",
                "output": [],
                "mode": "strict",
            },
        )
    elapsed = time.perf_counter() - started
    assert response.status_code == 504
    assert response.json()["code"] == "operation_timeout"
    assert elapsed < 1


def test_legacy_timeout_keeps_legacy_error_shape(app_factory: Any) -> None:
    settings = ApiSettings(generate_timeout_seconds=0.01)

    def slow_generate(command: GenerateGeometryCommand) -> GenerateGeometryResult:
        del command
        time.sleep(0.2)
        raise AssertionError

    app: FastAPI = app_factory(
        settings=settings,
        executor=TimedApplicationExecutor(settings=settings, generate_fn=slow_generate),
    )
    with TestClient(app) as client:
        response = client.post(
            "/generate",
            json={
                "input_type": "text",
                "input": "Постройте треугольник ABC",
                "output": [],
                "mode": "strict",
            },
        )
    assert response.status_code == 504
    assert response.json() == {"detail": "Operation timed out."}


def test_validate_timeout_uses_validate_deadline(
    app_factory: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    settings = ApiSettings(validate_timeout_seconds=0.01)

    def slow_validate(scene: GirScene) -> ValidationReport:
        del scene
        time.sleep(0.2)
        return ValidationReport(is_valid=True)

    app: FastAPI = app_factory(
        settings=settings,
        executor=TimedApplicationExecutor(settings=settings, validate_fn=slow_validate),
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/validate-gir", json=valid_altitude_payload)
    assert response.status_code == 504
    assert response.json()["code"] == "operation_timeout"


def test_svg_and_tikz_render_timeout_use_render_deadline(
    app_factory: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    settings = ApiSettings(render_timeout_seconds=0.01)

    def slow_render(command: RenderGeometryCommand) -> RenderGeometryResult:
        del command
        time.sleep(0.2)
        raise AssertionError

    app: FastAPI = app_factory(
        settings=settings,
        executor=TimedApplicationExecutor(settings=settings, render_fn=slow_render),
    )
    with TestClient(app) as client:
        svg = client.post("/api/v1/render/svg", json=valid_altitude_payload)
        tikz = client.post("/api/v1/render/tikz", json=valid_altitude_payload)
    assert svg.status_code == 504
    assert tikz.status_code == 504
    assert svg.json()["code"] == "operation_timeout"
    assert tikz.json()["code"] == "operation_timeout"

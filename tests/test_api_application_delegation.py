from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gir_api.execution import TimedApplicationExecutor
from gir_api.settings import ApiSettings
from gir_application import (
    GenerateGeometryCommand,
    GenerateGeometryResult,
    GenerationStatus,
    OutputFormat,
    RenderedArtifacts,
    RenderGeometryCommand,
    RenderGeometryResult,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


def test_generate_route_delegates_to_timed_application_executor(
    app_factory: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = GirScene.model_validate(valid_altitude_payload)
    captured: list[GenerateGeometryCommand] = []

    def fake_generate(command: GenerateGeometryCommand) -> GenerateGeometryResult:
        captured.append(command)
        return GenerateGeometryResult(
            status=GenerationStatus.SUCCESS,
            confidence=1.0,
            gir=scene,
            validation_report=ValidationReport(is_valid=True),
            artifacts=RenderedArtifacts(svg="<svg />"),
        )

    settings = ApiSettings()
    executor = TimedApplicationExecutor(settings=settings, generate_fn=fake_generate)
    app: FastAPI = app_factory(settings=settings, executor=executor)
    with TestClient(app) as client:
        response = client.post(
            "/generate",
            json={
                "input_type": "text",
                "input": "test",
                "output": ["svg", "svg"],
                "mode": "strict",
            },
        )

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].outputs == frozenset({OutputFormat.SVG})
    assert response.json()["svg"] == "<svg />"


def test_render_route_delegates_to_timed_application_executor(
    app_factory: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = GirScene.model_validate(valid_altitude_payload)
    captured: list[RenderGeometryCommand] = []

    def fake_render(command: RenderGeometryCommand) -> RenderGeometryResult:
        captured.append(command)
        return RenderGeometryResult(
            is_valid=True,
            scene=scene,
            validation_report=ValidationReport(is_valid=True),
            artifacts=RenderedArtifacts(svg="<svg />"),
        )

    settings = ApiSettings()
    executor = TimedApplicationExecutor(settings=settings, render_fn=fake_render)
    app: FastAPI = app_factory(settings=settings, executor=executor)
    with TestClient(app) as client:
        response = client.post("/render/svg", json=valid_altitude_payload)

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].outputs == frozenset({OutputFormat.SVG})
    assert response.json() == {"content": "<svg />"}

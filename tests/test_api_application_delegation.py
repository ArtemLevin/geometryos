from typing import Any

from gir_application import (
    GenerateGeometryResult,
    GenerationStatus,
    OutputFormat,
    RenderedArtifacts,
    RenderGeometryResult,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


def test_generate_route_delegates_to_application_service(
    client: Any,
    monkeypatch: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = GirScene.model_validate(valid_altitude_payload)
    captured: list[Any] = []

    def fake_generate(command: Any) -> GenerateGeometryResult:
        captured.append(command)
        return GenerateGeometryResult(
            status=GenerationStatus.SUCCESS,
            confidence=1.0,
            gir=scene,
            validation_report=ValidationReport(is_valid=True),
            artifacts=RenderedArtifacts(svg="<svg />"),
        )

    monkeypatch.setattr("gir_api.routes.generate.generate_geometry", fake_generate)
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


def test_render_route_delegates_to_application_service(
    client: Any,
    monkeypatch: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    scene = GirScene.model_validate(valid_altitude_payload)
    captured: list[Any] = []

    def fake_render(command: Any) -> RenderGeometryResult:
        captured.append(command)
        return RenderGeometryResult(
            is_valid=True,
            scene=scene,
            validation_report=ValidationReport(is_valid=True),
            artifacts=RenderedArtifacts(svg="<svg />"),
        )

    monkeypatch.setattr("gir_api.routes.render.render_geometry", fake_render)
    response = client.post("/render/svg", json=valid_altitude_payload)

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].outputs == frozenset({OutputFormat.SVG})
    assert response.json() == {"content": "<svg />"}

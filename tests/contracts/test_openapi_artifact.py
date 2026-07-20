from typing import Any

from gir_api.constants import API_TITLE, API_V1_VERSION, PROBLEM_MEDIA_TYPE
from gir_api.openapi_contract import (
    OPENAPI_ARTIFACT_PATH,
    build_openapi_document,
    canonical_openapi_json,
    check_openapi_artifact,
)


def test_openapi_artifact_is_fresh_and_deterministic() -> None:
    assert OPENAPI_ARTIFACT_PATH.exists()
    assert check_openapi_artifact()
    assert OPENAPI_ARTIFACT_PATH.read_text(encoding="utf-8") == canonical_openapi_json(
        build_openapi_document()
    )


def test_published_openapi_contains_tutorboard_contract_only() -> None:
    document = build_openapi_document()
    assert document["info"]["title"] == API_TITLE
    assert document["info"]["version"] == API_V1_VERSION
    assert document["info"]["x-geometryos-api-major"] == "v1"
    assert document["info"]["x-geometryos-gir-schema-version"] == "0.2.0"
    assert document["info"]["x-geometryos-consumer-contract"] == "tutorboard/v1"
    assert set(document["paths"]) == {
        "/health",
        "/ready",
        "/api/v1/generate",
        "/api/v1/validate-gir",
        "/api/v1/render/svg",
        "/api/v1/render/tikz",
    }
    assert not any(
        path in document["paths"]
        for path in ("/generate", "/validate-gir", "/render/svg", "/render/tikz")
    )


def test_published_openapi_has_stable_operations_and_media_types() -> None:
    document = build_openapi_document()
    operations = {
        document["paths"][path][method]["operationId"]
        for path, method in (
            ("/health", "get"),
            ("/ready", "get"),
            ("/api/v1/generate", "post"),
            ("/api/v1/validate-gir", "post"),
            ("/api/v1/render/svg", "post"),
            ("/api/v1/render/tikz", "post"),
        )
    }
    assert operations == {
        "geometryos_health",
        "geometryos_ready",
        "geometryos_v1_generate",
        "geometryos_v1_validate_gir",
        "geometryos_v1_render_svg",
        "geometryos_v1_render_tikz",
    }
    assert document["paths"]["/ready"]["get"]["responses"].keys() >= {"200", "503"}
    for path, statuses in {
        "/api/v1/generate": {"413", "422", "500", "504"},
        "/api/v1/validate-gir": {"422", "500", "504"},
        "/api/v1/render/svg": {"422", "500", "504"},
        "/api/v1/render/tikz": {"422", "500", "504"},
    }.items():
        responses: dict[str, Any] = document["paths"][path]["post"]["responses"]
        for status in statuses:
            assert PROBLEM_MEDIA_TYPE in responses[status]["content"]

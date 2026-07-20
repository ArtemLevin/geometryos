from typing import Any

from gir_api.constants import API_TITLE, API_V1_VERSION, MAX_GENERATE_INPUT_CHARS
from gir_api.main import app

ALTITUDE_PROMPT = "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."


def _resolve_schema(schema: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    name = reference.rsplit("/", 1)[-1]
    return document["components"]["schemas"][name]


def test_openapi_contains_only_stable_api_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert schema["info"]["title"] == API_TITLE
    assert schema["info"]["version"] == API_V1_VERSION
    assert set(paths) == {
        "/health",
        "/api/v1/generate",
        "/api/v1/validate-gir",
        "/api/v1/render/svg",
        "/api/v1/render/tikz",
    }


def test_openapi_operation_ids_are_explicit_and_unique() -> None:
    schema = app.openapi()
    operation_ids = [
        operation["operationId"]
        for path_item in schema["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]

    assert set(operation_ids) == {
        "geometryos_health",
        "geometryos_v1_generate",
        "geometryos_v1_validate_gir",
        "geometryos_v1_render_svg",
        "geometryos_v1_render_tikz",
    }
    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_generate_request_constraints_are_published() -> None:
    schema = app.openapi()
    request_schema = schema["paths"]["/api/v1/generate"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    model = _resolve_schema(request_schema, schema)
    properties = model["properties"]

    assert model["additionalProperties"] is False
    assert properties["input"]["minLength"] == 1
    assert properties["input"]["maxLength"] == MAX_GENERATE_INPUT_CHARS
    assert properties["output"]["maxItems"] == 2
    assert properties["output"]["uniqueItems"] is True
    assert properties["mode"].get("const") == "strict" or properties["mode"].get("enum") == [
        "strict"
    ]


def test_openapi_generate_response_is_discriminated_union() -> None:
    schema = app.openapi()
    response_schema = schema["paths"]["/api/v1/generate"]["post"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    assert "oneOf" in response_schema
    assert response_schema["discriminator"]["propertyName"] == "status"


def test_legacy_aliases_remain_compatible_and_hidden(
    client: Any,
    valid_altitude_payload: dict[str, Any],
) -> None:
    generate_response = client.post(
        "/generate",
        json={
            "input_type": "text",
            "input": ALTITUDE_PROMPT,
            "output": ["svg", "svg"],
            "mode": "draft",
        },
    )
    assert generate_response.status_code == 200
    assert "schema_version" not in generate_response.json()
    assert "<svg" in generate_response.json()["svg"]

    validate_response = client.post("/validate-gir", json=valid_altitude_payload)
    assert validate_response.status_code == 200
    assert set(validate_response.json()) == {"is_valid", "issues", "warnings"}

    legacy_svg = client.post("/render/svg", json=valid_altitude_payload)
    v1_svg = client.post("/api/v1/render/svg", json=valid_altitude_payload)
    assert legacy_svg.status_code == 200
    assert legacy_svg.json() == {"content": v1_svg.json()["content"]}

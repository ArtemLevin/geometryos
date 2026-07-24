from gir_api.constants import REQUEST_ID_HEADER
from gir_api.openapi_contract import build_openapi_document


def test_public_operations_publish_request_and_response_correlation() -> None:
    document = build_openapi_document()
    parameter = document["components"]["parameters"]["GeometryOsRequestId"]
    assert parameter["name"] == REQUEST_ID_HEADER
    assert parameter["in"] == "header"
    assert parameter["required"] is False
    assert parameter["schema"]["maxLength"] == 128

    for path in (
        "/health",
        "/ready",
        "/api/v1/generate",
        "/api/v1/validate-gir",
        "/api/v1/render/svg",
        "/api/v1/render/tikz",
    ):
        method = "get" if path in {"/health", "/ready"} else "post"
        operation = document["paths"][path][method]
        assert {"$ref": "#/components/parameters/GeometryOsRequestId"} in operation["parameters"]
        for response in operation["responses"].values():
            assert response["headers"][REQUEST_ID_HEADER] == {
                "$ref": "#/components/headers/GeometryOsRequestId"
            }


def test_stable_post_operations_publish_service_unavailable_problem() -> None:
    document = build_openapi_document()
    for path in (
        "/api/v1/generate",
        "/api/v1/validate-gir",
        "/api/v1/render/svg",
        "/api/v1/render/tikz",
    ):
        response = document["paths"][path]["post"]["responses"]["503"]
        assert response["content"]["application/problem+json"]["schema"] == {
            "$ref": "#/components/schemas/ProblemDetail"
        }

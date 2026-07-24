from copy import deepcopy

from gir_api.openapi_compatibility import (
    CompatibilitySeverity,
    compare_openapi_documents,
)


def _document() -> dict[str, object]:
    return {
        "components": {
            "parameters": {
                "GeometryOsRequestId": {
                    "name": "X-Request-ID",
                    "in": "header",
                    "required": False,
                    "schema": {"type": "string", "maxLength": 128},
                }
            },
            "headers": {
                "GeometryOsRequestId": {
                    "required": True,
                    "schema": {"type": "string", "maxLength": 128},
                }
            },
        },
        "paths": {
            "/api/v1/generate": {
                "post": {
                    "operationId": "geometryos_v1_generate",
                    "parameters": [
                        {"$ref": "#/components/parameters/GeometryOsRequestId"}
                    ],
                    "responses": {
                        "200": {
                            "headers": {
                                "X-Request-ID": {
                                    "$ref": "#/components/headers/GeometryOsRequestId"
                                }
                            },
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            },
                        }
                    },
                }
            }
        },
    }


def _messages(candidate: dict[str, object]) -> list[tuple[CompatibilitySeverity, str]]:
    return [
        (issue.severity, issue.message)
        for issue in compare_openapi_documents(_document(), candidate)
    ]


def test_removing_request_id_parameter_is_breaking() -> None:
    candidate = deepcopy(_document())
    candidate["paths"]["/api/v1/generate"]["post"]["parameters"] = []  # type: ignore[index]
    assert (CompatibilitySeverity.BREAKING, "parameter was removed") in _messages(candidate)


def test_making_request_id_required_is_breaking() -> None:
    candidate = deepcopy(_document())
    candidate["components"]["parameters"]["GeometryOsRequestId"]["required"] = True  # type: ignore[index]
    assert (CompatibilitySeverity.BREAKING, "parameter became required") in _messages(candidate)


def test_tightening_request_id_length_is_breaking() -> None:
    candidate = deepcopy(_document())
    candidate["components"]["parameters"]["GeometryOsRequestId"]["schema"]["maxLength"] = 64  # type: ignore[index]
    messages = _messages(candidate)
    assert any(
        severity is CompatibilitySeverity.BREAKING and "maxLength became stricter" in message
        for severity, message in messages
    )


def test_removing_response_request_id_header_is_breaking() -> None:
    candidate = deepcopy(_document())
    candidate["paths"]["/api/v1/generate"]["post"]["responses"]["200"]["headers"] = {}  # type: ignore[index]
    assert (CompatibilitySeverity.BREAKING, "response header was removed") in _messages(candidate)


def test_making_required_response_header_optional_is_breaking() -> None:
    candidate = deepcopy(_document())
    candidate["components"]["headers"]["GeometryOsRequestId"]["required"] = False  # type: ignore[index]
    assert (
        CompatibilitySeverity.BREAKING,
        "required response header became optional",
    ) in _messages(candidate)


def test_adding_service_unavailable_response_requires_review() -> None:
    candidate = deepcopy(_document())
    candidate["paths"]["/api/v1/generate"]["post"]["responses"]["503"] = {  # type: ignore[index]
        "content": {
            "application/problem+json": {"schema": {"type": "object"}}
        }
    }
    assert (CompatibilitySeverity.REVIEW, "response status added") in _messages(candidate)

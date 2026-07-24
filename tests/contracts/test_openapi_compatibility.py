from copy import deepcopy
from typing import Any

import pytest

from gir_api.openapi_compatibility import (
    CompatibilityIssue,
    CompatibilitySeverity,
    compare_openapi_documents,
)


def _document() -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test", "version": "1"},
        "paths": {
            "/items": {
                "post": {
                    "operationId": "createItem",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {"type": "string", "maxLength": 100},
                                        "mode": {
                                            "type": "string",
                                            "enum": ["a", "b"],
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["id"],
                                        "properties": {"id": {"type": "string"}},
                                    }
                                }
                            }
                        }
                    },
                }
            }
        },
    }


def _correlation_document() -> dict[str, Any]:
    return {
        "components": {
            "parameters": {
                "GeometryOsRequestId": {
                    "name": "X-Request-ID",
                    "in": "header",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "maxLength": 128,
                        "pattern": "^[A-Za-z0-9._-]{1,128}$",
                    },
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


def _issues(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[CompatibilityIssue]:
    return compare_openapi_documents(baseline, candidate)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda doc: doc["paths"].pop("/items"),
        lambda doc: doc["paths"]["/items"]["post"].update(operationId="renamed"),
        lambda doc: doc["paths"]["/items"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]["required"].append("mode"),
        lambda doc: doc["paths"]["/items"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]["properties"]["name"].update(type="integer"),
        lambda doc: doc["paths"]["/items"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]["properties"]["mode"].update(enum=["a"]),
        lambda doc: doc["paths"]["/items"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]["properties"]["name"].update(maxLength=50),
        lambda doc: doc["paths"]["/items"]["post"]["responses"].pop("200"),
        lambda doc: doc["paths"]["/items"]["post"]["responses"]["200"]["content"].pop(
            "application/json"
        ),
        lambda doc: doc["paths"]["/items"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["required"].clear(),
    ],
)
def test_breaking_changes_are_detected(mutation: Any) -> None:
    baseline = _document()
    candidate = deepcopy(baseline)
    mutation(candidate)
    issues = _issues(baseline, candidate)
    assert any(item.severity is CompatibilitySeverity.BREAKING for item in issues)


def test_compatible_additions_pass_with_review_signal() -> None:
    baseline = _document()
    candidate = deepcopy(baseline)
    schema = candidate["paths"]["/items"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    schema["properties"]["optional"] = {"type": "string"}
    schema["properties"]["mode"]["enum"].append("c")
    candidate["paths"]["/health"] = {
        "get": {"operationId": "health", "responses": {"200": {}}}
    }
    issues = _issues(baseline, candidate)
    assert not any(item.severity is CompatibilitySeverity.BREAKING for item in issues)
    assert any(item.severity is CompatibilitySeverity.REVIEW for item in issues)


def test_request_correlation_parameter_removal_is_breaking() -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    candidate["paths"]["/api/v1/generate"]["post"]["parameters"] = []

    issues = _issues(baseline, candidate)

    assert any(
        issue.severity is CompatibilitySeverity.BREAKING
        and issue.message == "parameter was removed"
        for issue in issues
    )


def test_optional_request_correlation_parameter_becoming_required_is_breaking() -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    candidate["components"]["parameters"]["GeometryOsRequestId"]["required"] = True

    issues = _issues(baseline, candidate)

    assert any(
        issue.severity is CompatibilitySeverity.BREAKING
        and issue.message == "optional parameter became required"
        for issue in issues
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("maxLength", 64, "maxLength became stricter: 128 -> 64"),
        ("pattern", "^[A-Z]+$", "pattern changed"),
    ],
)
def test_request_correlation_schema_narrowing_is_breaking(
    field: str,
    value: object,
    message: str,
) -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    candidate["components"]["parameters"]["GeometryOsRequestId"]["schema"][field] = value

    issues = _issues(baseline, candidate)

    assert any(
        issue.severity is CompatibilitySeverity.BREAKING
        and issue.message == message
        for issue in issues
    )


def test_response_correlation_header_removal_is_breaking() -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    candidate["paths"]["/api/v1/generate"]["post"]["responses"]["200"]["headers"] = {}

    issues = _issues(baseline, candidate)

    assert any(
        issue.severity is CompatibilitySeverity.BREAKING
        and issue.message == "response header was removed"
        for issue in issues
    )


def test_required_response_correlation_header_becoming_optional_is_breaking() -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    candidate["components"]["headers"]["GeometryOsRequestId"]["required"] = False

    issues = _issues(baseline, candidate)

    assert any(
        issue.severity is CompatibilitySeverity.BREAKING
        and issue.message == "required response header became optional"
        for issue in issues
    )


def test_response_header_names_are_case_insensitive() -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    headers = candidate["paths"]["/api/v1/generate"]["post"]["responses"]["200"][
        "headers"
    ]
    headers["x-request-id"] = headers.pop("X-Request-ID")

    issues = _issues(baseline, candidate)

    assert not any(item.severity is CompatibilitySeverity.BREAKING for item in issues)


def test_new_response_status_produces_one_review_finding() -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    candidate["paths"]["/api/v1/generate"]["post"]["responses"]["503"] = {
        "content": {
            "application/problem+json": {"schema": {"type": "object"}}
        }
    }

    reviews = [
        issue
        for issue in _issues(baseline, candidate)
        if issue.severity is CompatibilitySeverity.REVIEW
        and issue.message == "response status was added"
    ]

    assert len(reviews) == 1


def test_new_response_header_produces_one_review_finding() -> None:
    baseline = _correlation_document()
    candidate = deepcopy(baseline)
    candidate["paths"]["/api/v1/generate"]["post"]["responses"]["200"]["headers"][
        "X-Trace-ID"
    ] = {"schema": {"type": "string"}}

    reviews = [
        issue
        for issue in _issues(baseline, candidate)
        if issue.severity is CompatibilitySeverity.REVIEW
        and issue.message == "response header was added"
    ]

    assert len(reviews) == 1

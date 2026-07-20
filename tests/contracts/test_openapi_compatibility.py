from copy import deepcopy
from typing import Any

import pytest

from gir_api.openapi_compatibility import (
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
        lambda doc: doc["paths"]["/items"]["post"]["responses"]["200"][
            "content"
        ].pop("application/json"),
        lambda doc: doc["paths"]["/items"]["post"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]["required"].clear(),
    ],
)
def test_breaking_changes_are_detected(mutation: Any) -> None:
    baseline = _document()
    candidate = deepcopy(baseline)
    mutation(candidate)
    issues = compare_openapi_documents(baseline, candidate)
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
    issues = compare_openapi_documents(baseline, candidate)
    assert not any(item.severity is CompatibilitySeverity.BREAKING for item in issues)
    assert any(item.severity is CompatibilitySeverity.REVIEW for item in issues)

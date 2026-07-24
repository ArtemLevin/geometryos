from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from gir_api.constants import API_V1_VERSION, REQUEST_ID_HEADER
from gir_api.problem_details import ProblemDetail
from gir_api.settings import ApiSettings
from gir_meta import SERVICE_VERSION

OPENAPI_ARTIFACT_PATH = Path("schemas/openapi.v1.json")
OPENAPI_EXTENSIONS: dict[str, str] = {
    "x-geometryos-api-major": "v1",
    "x-geometryos-gir-schema-version": "0.2.0",
    "x-geometryos-consumer-contract": "tutorboard/v1",
    "x-geometryos-service-version": SERVICE_VERSION,
}
_REQUEST_ID_PARAMETER_REF = "#/components/parameters/GeometryOsRequestId"
_REQUEST_ID_HEADER_REF = "#/components/headers/GeometryOsRequestId"
_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def install_openapi_contract(application: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if application.openapi_schema is not None:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
            tags=application.openapi_tags,
        )
        schema["info"].update(OPENAPI_EXTENSIONS)
        _install_problem_components(schema)
        _install_request_id_contract(schema)
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi  # type: ignore[method-assign]


def _install_problem_components(document: dict[str, Any]) -> None:
    schema = ProblemDetail.model_json_schema(ref_template="#/components/schemas/{model}")
    definitions = schema.pop("$defs", {})
    component_schemas = document.setdefault("components", {}).setdefault("schemas", {})
    component_schemas.update(definitions)
    component_schemas["ProblemDetail"] = schema


def _install_request_id_contract(document: dict[str, Any]) -> None:
    components = document.setdefault("components", {})
    components.setdefault("parameters", {})["GeometryOsRequestId"] = {
        "name": REQUEST_ID_HEADER,
        "in": "header",
        "required": False,
        "description": "Optional safe caller correlation identifier. Invalid values are replaced.",
        "schema": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128,
            "pattern": "^[A-Za-z0-9._-]{1,128}$",
        },
    }
    components.setdefault("headers", {})["GeometryOsRequestId"] = {
        "required": True,
        "description": "Resolved request correlation identifier.",
        "schema": {"type": "string", "minLength": 1, "maxLength": 128},
    }
    for path_item in document.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            parameters = operation.setdefault("parameters", [])
            if {"$ref": _REQUEST_ID_PARAMETER_REF} not in parameters:
                parameters.append({"$ref": _REQUEST_ID_PARAMETER_REF})
            for response in operation.get("responses", {}).values():
                if isinstance(response, dict):
                    response.setdefault("headers", {})[REQUEST_ID_HEADER] = {
                        "$ref": _REQUEST_ID_HEADER_REF
                    }


def build_openapi_document() -> dict[str, Any]:
    from gir_api.main import create_app

    application = create_app(
        settings=ApiSettings(
            generate_timeout_seconds=15.0,
            validate_timeout_seconds=5.0,
            render_timeout_seconds=10.0,
            max_input_chars=20_000,
            log_level="INFO",
            cors_allowed_origins="",
            cors_max_age_seconds=600,
        )
    )
    document = deepcopy(application.openapi())
    if document["info"]["version"] != API_V1_VERSION:
        raise RuntimeError("OpenAPI API version diverged from API_V1_VERSION.")
    if document["info"].get("x-geometryos-service-version") != SERVICE_VERSION:
        raise RuntimeError("OpenAPI service version diverged from installed package metadata.")
    return document


def canonical_openapi_json(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_openapi_artifact(output: Path = OPENAPI_ARTIFACT_PATH) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_openapi_json(build_openapi_document()), encoding="utf-8")
    return output


def check_openapi_artifact(output: Path = OPENAPI_ARTIFACT_PATH) -> bool:
    if not output.exists():
        return False
    return output.read_text(encoding="utf-8") == canonical_openapi_json(build_openapi_document())

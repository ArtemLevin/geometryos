from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from gir_api.constants import API_V1_VERSION
from gir_api.settings import ApiSettings

OPENAPI_ARTIFACT_PATH = Path("schemas/openapi.v1.json")
OPENAPI_EXTENSIONS: dict[str, str] = {
    "x-geometryos-api-major": "v1",
    "x-geometryos-gir-schema-version": "0.2.0",
    "x-geometryos-consumer-contract": "tutorboard/v1",
}


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
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi  # type: ignore[method-assign]


def build_openapi_document() -> dict[str, Any]:
    from gir_api.main import create_app

    application = create_app(
        settings=ApiSettings(
            generate_timeout_seconds=15.0,
            validate_timeout_seconds=5.0,
            render_timeout_seconds=10.0,
            max_input_chars=20_000,
            log_level="INFO",
        )
    )
    document = deepcopy(application.openapi())
    if document["info"]["version"] != API_V1_VERSION:
        raise RuntimeError("OpenAPI API version diverged from API_V1_VERSION.")
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
    return output.read_text(encoding="utf-8") == canonical_openapi_json(
        build_openapi_document()
    )

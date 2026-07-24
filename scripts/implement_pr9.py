from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace(path: str, old: str, new: str) -> None:
    content = read(path)
    if old not in content:
        raise RuntimeError(f"Expected text not found in {path}: {old[:120]!r}")
    write(path, content.replace(old, new))


write(
    "src/gir_api/settings.py",
    '''from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gir_api.constants import MAX_GENERATE_INPUT_CHARS

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
_MAX_CORS_ORIGINS = 32


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEOMETRYOS_",
        case_sensitive=False,
        extra="ignore",
    )

    generate_timeout_seconds: float = Field(default=15.0, gt=0, le=300)
    validate_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    render_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    max_input_chars: int = Field(
        default=MAX_GENERATE_INPUT_CHARS,
        ge=1,
        le=MAX_GENERATE_INPUT_CHARS,
    )
    log_level: LogLevel = "INFO"
    cors_allowed_origins: str = ""
    cors_max_age_seconds: int = Field(default=600, ge=0, le=86_400)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        _parse_cors_origins(value)
        return value

    @computed_field
    @property
    def parsed_cors_allowed_origins(self) -> tuple[str, ...]:
        return _parse_cors_origins(self.cors_allowed_origins)


def _parse_cors_origins(value: str) -> tuple[str, ...]:
    origins: list[str] = []
    seen: set[str] = set()
    for raw_origin in value.split(","):
        origin = raw_origin.strip()
        if not origin:
            continue
        if origin in {"*", "null"}:
            raise ValueError("CORS origins must be explicit HTTP(S) origins.")
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"Invalid CORS origin: {origin!r}.")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("CORS origins must not contain credentials.")
        if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("CORS origins must not contain paths, queries, or fragments.")
        canonical = origin[:-1] if origin.endswith("/") else origin
        if canonical not in seen:
            seen.add(canonical)
            origins.append(canonical)
    if len(origins) > _MAX_CORS_ORIGINS:
        raise ValueError(f"At most {_MAX_CORS_ORIGINS} CORS origins are allowed.")
    return tuple(origins)


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
''',
)

replace(
    "src/gir_api/errors.py",
    '''class OperationTimeoutError(ApiRuntimeError):
''',
    '''class ServiceUnavailableError(ApiRuntimeError):
    code = "service_unavailable"

    def __init__(self) -> None:
        super().__init__("GeometryOS is not ready to accept application requests.")


class OperationTimeoutError(ApiRuntimeError):
''',
)

write(
    "src/gir_api/dependencies.py",
    '''from typing import cast

from fastapi import Request

from gir_api.errors import InputTooLargeError, ServiceUnavailableError
from gir_api.execution import TimedApplicationExecutor
from gir_api.readiness import readiness_snapshot
from gir_api.settings import ApiSettings


def get_executor(request: Request) -> TimedApplicationExecutor:
    return cast(TimedApplicationExecutor, request.app.state.application_executor)


def get_runtime_settings(request: Request) -> ApiSettings:
    return cast(ApiSettings, request.app.state.settings)


def require_application_ready(request: Request) -> None:
    if readiness_snapshot(request.app).status != "ready":
        raise ServiceUnavailableError()


def enforce_input_limit(value: str, settings: ApiSettings) -> None:
    actual_chars = len(value)
    if actual_chars > settings.max_input_chars:
        raise InputTooLargeError(actual_chars=actual_chars, max_chars=settings.max_input_chars)
''',
)

write(
    "src/gir_api/router.py",
    '''from fastapi import APIRouter, Depends

from gir_api.constants import API_V1_PREFIX
from gir_api.dependencies import require_application_ready
from gir_api.routes.generate import legacy_router as legacy_generate_router
from gir_api.routes.generate import v1_router as v1_generate_router
from gir_api.routes.render import legacy_router as legacy_render_router
from gir_api.routes.render import v1_router as v1_render_router
from gir_api.routes.validate import legacy_router as legacy_validate_router
from gir_api.routes.validate import v1_router as v1_validate_router

v1_router = APIRouter(
    prefix=API_V1_PREFIX,
    dependencies=[Depends(require_application_ready)],
)
v1_router.include_router(v1_generate_router)
v1_router.include_router(v1_validate_router)
v1_router.include_router(v1_render_router)

legacy_router = APIRouter()
legacy_router.include_router(legacy_generate_router)
legacy_router.include_router(legacy_validate_router)
legacy_router.include_router(legacy_render_router)
''',
)

replace(
    "src/gir_api/exception_handlers.py",
    '''from gir_api.errors import InputTooLargeError, OperationTimeoutError, SemanticValidationError
''',
    '''from gir_api.errors import (
    InputTooLargeError,
    OperationTimeoutError,
    SemanticValidationError,
    ServiceUnavailableError,
)
''',
)
replace(
    "src/gir_api/exception_handlers.py",
    '''    app.add_exception_handler(OperationTimeoutError, operation_timeout_handler)
''',
    '''    app.add_exception_handler(OperationTimeoutError, operation_timeout_handler)
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_handler)
''',
)
replace(
    "src/gir_api/exception_handlers.py",
    '''async def operation_timeout_handler(request: Request, exc: Exception) -> Response:
''',
    '''async def service_unavailable_handler(request: Request, exc: Exception) -> Response:
    _expect_exception(exc, ServiceUnavailableError)
    return problem_response(
        status=503,
        problem_type="urn:geometryos:problem:service-unavailable",
        title="Service unavailable",
        detail="GeometryOS is not ready to accept application requests.",
        instance=request.url.path,
        code="service_unavailable",
        request_id=_request_id(),
        no_store=True,
    )


async def operation_timeout_handler(request: Request, exc: Exception) -> Response:
''',
)

replace(
    "src/gir_api/problem_details.py",
    '''    TIMEOUT_PROBLEM_EXAMPLE,
''',
    '''    SERVICE_UNAVAILABLE_PROBLEM_EXAMPLE,
    TIMEOUT_PROBLEM_EXAMPLE,
''',
)
replace(
    "src/gir_api/problem_details.py",
    '''                TIMEOUT_PROBLEM_EXAMPLE,
                INTERNAL_ERROR_PROBLEM_EXAMPLE,
''',
    '''                TIMEOUT_PROBLEM_EXAMPLE,
                SERVICE_UNAVAILABLE_PROBLEM_EXAMPLE,
                INTERNAL_ERROR_PROBLEM_EXAMPLE,
''',
)
replace(
    "src/gir_api/problem_details.py",
    '''        500: "Unexpected internal error.",
        504: "Operation exceeded its configured time limit.",
''',
    '''        500: "Unexpected internal error.",
        503: "Service is alive but not ready to accept application traffic.",
        504: "Operation exceeded its configured time limit.",
''',
)

replace(
    "src/gir_api/openapi_examples.py",
    '''INTERNAL_ERROR_PROBLEM_EXAMPLE = {
''',
    '''SERVICE_UNAVAILABLE_PROBLEM_EXAMPLE = {
    "type": "urn:geometryos:problem:service-unavailable",
    "title": "Service unavailable",
    "status": 503,
    "detail": "GeometryOS is not ready to accept application requests.",
    "instance": "/api/v1/generate",
    "code": "service_unavailable",
    "request_id": "tutorboard-contract",
    "errors": [],
}

INTERNAL_ERROR_PROBLEM_EXAMPLE = {
''',
)

replace("src/gir_api/routes/generate.py", "problem_responses(413, 422, 500, 504)", "problem_responses(413, 422, 500, 503, 504)")
replace("src/gir_api/routes/validate.py", "problem_responses(422, 500, 504)", "problem_responses(422, 500, 503, 504)")
replace("src/gir_api/routes/render.py", "problem_responses(422, 500, 504)", "problem_responses(422, 500, 503, 504)")

replace(
    "src/gir_api/main.py",
    '''from fastapi import FastAPI
''',
    '''from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
''',
)
replace(
    "src/gir_api/main.py",
    '''from gir_api.constants import API_TITLE, API_V1_VERSION, OPENAPI_TAGS
''',
    '''from gir_api.constants import API_TITLE, API_V1_VERSION, OPENAPI_TAGS, REQUEST_ID_HEADER
''',
)
replace(
    "src/gir_api/main.py",
    '''    register_exception_handlers(application)
    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)
''',
    '''    register_exception_handlers(application)
    cors_origins = resolved_settings.parsed_cors_allowed_origins
    if cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
            max_age=resolved_settings.cors_max_age_seconds,
        )
    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)
''',
)

write(
    "src/gir_api/openapi_contract.py",
    '''from __future__ import annotations

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
            if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            if not isinstance(operation, dict):
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
''',
)

replace(
    "src/gir_api/openapi_compatibility.py",
    '''            _compare_request_body(
''',
    '''            _compare_parameters(
                baseline_operation.get("parameters", []),
                candidate_operation.get("parameters", []),
                baseline,
                candidate,
                location,
                issues,
            )
            _compare_request_body(
''',
)
replace(
    "src/gir_api/openapi_compatibility.py",
    '''    for status, baseline_response in baseline_responses.items():
''',
    '''    for status in sorted(set(candidate_responses) - set(baseline_responses)):
        issues.append(_review(f"{location} response {status}", "response status added"))
    for status, baseline_response in baseline_responses.items():
''',
)
replace(
    "src/gir_api/openapi_compatibility.py",
    '''        if isinstance(baseline_response, dict):
            _compare_content(
''',
    '''        if isinstance(baseline_response, dict):
            _compare_response_headers(
                baseline_response.get("headers", {}),
                candidate_response.get("headers", {}),
                baseline_document,
                candidate_document,
                status_location,
                issues,
            )
            _compare_content(
''',
)
insert_marker = '''def _compare_request_body(
'''
helpers = '''def _compare_parameters(
    baseline_parameters: object,
    candidate_parameters: object,
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    issues: list[CompatibilityIssue],
) -> None:
    baseline_items = _parameter_map(baseline_parameters, baseline_document)
    candidate_items = _parameter_map(candidate_parameters, candidate_document)
    for key, baseline_parameter in baseline_items.items():
        candidate_parameter = candidate_items.get(key)
        parameter_location = f"{location} parameter {key[1]} {key[0]}"
        if candidate_parameter is None:
            issues.append(_breaking(parameter_location, "parameter was removed"))
            continue
        if not baseline_parameter.get("required", False) and candidate_parameter.get("required", False):
            issues.append(_breaking(parameter_location, "parameter became required"))
        _compare_schema(
            baseline_parameter.get("schema", {}),
            candidate_parameter.get("schema", {}),
            baseline_document,
            candidate_document,
            parameter_location,
            "request",
            issues,
            set(),
        )
    for key in sorted(set(candidate_items) - set(baseline_items)):
        issues.append(_review(f"{location} parameter {key[1]} {key[0]}", "parameter added"))


def _parameter_map(parameters: object, document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    if not isinstance(parameters, list):
        return result
    for item in parameters:
        resolved = _resolve_schema(item, document) if isinstance(item, dict) else {}
        name = resolved.get("name")
        location = resolved.get("in")
        if isinstance(name, str) and isinstance(location, str):
            result[(name.lower(), location)] = resolved
    return result


def _compare_response_headers(
    baseline_headers: object,
    candidate_headers: object,
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    issues: list[CompatibilityIssue],
) -> None:
    if not isinstance(baseline_headers, dict):
        return
    if not isinstance(candidate_headers, dict):
        issues.append(_breaking(location, "response headers disappeared"))
        return
    for name, baseline_header in baseline_headers.items():
        candidate_header = candidate_headers.get(name)
        header_location = f"{location} header {name}"
        if not isinstance(candidate_header, dict):
            issues.append(_breaking(header_location, "response header was removed"))
            continue
        baseline_resolved = _resolve_schema(baseline_header, baseline_document)
        candidate_resolved = _resolve_schema(candidate_header, candidate_document)
        if baseline_resolved.get("required", False) and not candidate_resolved.get("required", False):
            issues.append(_breaking(header_location, "required response header became optional"))
        _compare_schema(
            baseline_resolved.get("schema", {}),
            candidate_resolved.get("schema", {}),
            baseline_document,
            candidate_document,
            header_location,
            "response",
            issues,
            set(),
        )
    for name in sorted(set(candidate_headers) - set(baseline_headers)):
        issues.append(_review(f"{location} header {name}", "response header added"))


'''
replace("src/gir_api/openapi_compatibility.py", insert_marker, helpers + insert_marker)

write(
    "tests/api/test_cors.py",
    '''from typing import Any

from fastapi.testclient import TestClient

from gir_api.constants import REQUEST_ID_HEADER
from gir_api.main import create_app
from gir_api.settings import ApiSettings

ORIGIN = "http://localhost:5173"


def test_cors_is_disabled_by_default(client: Any) -> None:
    response = client.get("/health", headers={"Origin": ORIGIN})
    assert "access-control-allow-origin" not in response.headers


def test_allowed_preflight_exposes_request_context() -> None:
    app = create_app(settings=ApiSettings(cors_allowed_origins=ORIGIN, _env_file=None))
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/generate",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Request-ID",
                REQUEST_ID_HEADER: "cors-preflight",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "x-request-id" in response.headers["access-control-allow-headers"].lower()
    assert response.headers[REQUEST_ID_HEADER] == "cors-preflight"


def test_actual_response_exposes_request_id() -> None:
    app = create_app(settings=ApiSettings(cors_allowed_origins=ORIGIN, _env_file=None))
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={"Origin": ORIGIN, REQUEST_ID_HEADER: "cors-actual"},
        )
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert REQUEST_ID_HEADER.lower() in response.headers["access-control-expose-headers"].lower()
    assert response.headers[REQUEST_ID_HEADER] == "cors-actual"
    assert response.headers.get("access-control-allow-credentials") != "true"


def test_disallowed_origin_is_not_granted() -> None:
    app = create_app(settings=ApiSettings(cors_allowed_origins=ORIGIN, _env_file=None))
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
''',
)

replace(
    "tests/api/test_settings.py",
    '''    assert settings.log_level == "INFO"
''',
    '''    assert settings.log_level == "INFO"
    assert settings.parsed_cors_allowed_origins == ()
    assert settings.cors_max_age_seconds == 600
''',
)
replace(
    "tests/api/test_settings.py",
    '''def test_settings_reject_invalid_values(field: str, value: object) -> None:
''',
    '''def test_settings_parse_cors_origins() -> None:
    settings = ApiSettings(
        cors_allowed_origins=" http://localhost:5173,https://example.test/,http://localhost:5173 ",
        _env_file=None,
    )
    assert settings.parsed_cors_allowed_origins == (
        "http://localhost:5173",
        "https://example.test",
    )


@pytest.mark.parametrize(
    "origin",
    ["*", "null", "ftp://example.test", "https://user@example.test", "https://example.test/path"],
)
def test_settings_reject_unsafe_cors_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        ApiSettings(cors_allowed_origins=origin, _env_file=None)


def test_settings_reject_invalid_values(field: str, value: object) -> None:
''',
)
replace(
    "tests/api/test_settings.py",
    '''        ("log_level", "TRACE"),
''',
    '''        ("log_level", "TRACE"),
        ("cors_max_age_seconds", -1),
        ("cors_max_age_seconds", 86_401),
''',
)

replace(
    "tests/api/test_health_readiness.py",
    '''from gir_api.execution import TimedApplicationExecutor
''',
    '''from gir_api.constants import REQUEST_ID_HEADER
from gir_api.execution import TimedApplicationExecutor
from gir_api.openapi_examples import ALTITUDE_GIR_EXAMPLE
''',
)
append = '''

def test_stable_operations_return_problem_when_not_ready(
    app_factory: Callable[..., FastAPI],
) -> None:
    lifecycle = ServiceLifecycle()
    application = app_factory(lifecycle=lifecycle)
    with TestClient(application) as client:
        lifecycle.mark_stopping()
        requests = [
            ("/api/v1/generate", {"input_type": "text", "input": "Постройте треугольник ABC.", "mode": "strict"}),
            ("/api/v1/validate-gir", ALTITUDE_GIR_EXAMPLE),
            ("/api/v1/render/svg", ALTITUDE_GIR_EXAMPLE),
            ("/api/v1/render/tikz", ALTITUDE_GIR_EXAMPLE),
        ]
        for path, payload in requests:
            response = client.post(path, json=payload, headers={REQUEST_ID_HEADER: "not-ready"})
            assert response.status_code == 503
            assert response.headers["content-type"].startswith("application/problem+json")
            assert response.headers["cache-control"] == "no-store"
            assert response.headers[REQUEST_ID_HEADER] == "not-ready"
            assert response.json()["code"] == "service_unavailable"
            assert response.json()["request_id"] == "not-ready"
'''
write("tests/api/test_health_readiness.py", read("tests/api/test_health_readiness.py") + append)

replace(
    "tests/api/test_v1_openapi_legacy.py",
    '''def test_openapi_excludes_legacy_routes(client: Any) -> None:
''',
    '''def test_openapi_publishes_request_id_and_service_unavailable(client: Any) -> None:
    schema = client.get("/openapi.json").json()
    assert "GeometryOsRequestId" in schema["components"]["parameters"]
    assert "GeometryOsRequestId" in schema["components"]["headers"]
    for path in ("/health", "/ready", "/api/v1/generate", "/api/v1/validate-gir", "/api/v1/render/svg", "/api/v1/render/tikz"):
        method = "get" if path in {"/health", "/ready"} else "post"
        operation = schema["paths"][path][method]
        assert {"$ref": "#/components/parameters/GeometryOsRequestId"} in operation["parameters"]
        for response in operation["responses"].values():
            assert response["headers"]["X-Request-ID"] == {"$ref": "#/components/headers/GeometryOsRequestId"}
    generate_responses = schema["paths"]["/api/v1/generate"]["post"]["responses"]
    assert generate_responses["503"]["content"]["application/problem+json"]["schema"] == {"$ref": "#/components/schemas/ProblemDetail"}


def test_openapi_excludes_legacy_routes(client: Any) -> None:
''',
)

replace(
    ".env.example",
    '''GEOMETRYOS_LOG_LEVEL=INFO
''',
    '''GEOMETRYOS_LOG_LEVEL=INFO
GEOMETRYOS_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GEOMETRYOS_CORS_MAX_AGE_SECONDS=600
''',
)
replace(
    "compose.yaml",
    '''      GEOMETRYOS_LOG_LEVEL: ${GEOMETRYOS_LOG_LEVEL:-INFO}
''',
    '''      GEOMETRYOS_LOG_LEVEL: ${GEOMETRYOS_LOG_LEVEL:-INFO}
      GEOMETRYOS_CORS_ALLOWED_ORIGINS: ${GEOMETRYOS_CORS_ALLOWED_ORIGINS:-}
      GEOMETRYOS_CORS_MAX_AGE_SECONDS: ${GEOMETRYOS_CORS_MAX_AGE_SECONDS:-600}
''',
)

replace(
    "contracts/tutorboard/typescript/smoke.ts",
    '''type GenerateTimeout = paths["/api/v1/generate"]["post"]["responses"][504]["content"]["application/problem+json"];
''',
    '''type GenerateTimeout = paths["/api/v1/generate"]["post"]["responses"][504]["content"]["application/problem+json"];
type GenerateUnavailable = paths["/api/v1/generate"]["post"]["responses"][503]["content"]["application/problem+json"];
''',
)
replace(
    "contracts/tutorboard/typescript/smoke.ts",
    '''const timeoutCode: GenerateTimeout["code"] = "operation_timeout";
''',
    '''const timeoutCode: GenerateTimeout["code"] = "operation_timeout";
const unavailableCode: GenerateUnavailable["code"] = "service_unavailable";
''',
)
replace(
    "contracts/tutorboard/typescript/smoke.ts",
    '''void timeoutCode;
''',
    '''void timeoutCode;
void unavailableCode;
''',
)

replace(
    "scripts/export_tutorboard_contracts.py",
    '''    error_settings = ApiSettings()
''',
    '''    unavailable_lifecycle = __import__("gir_api.readiness", fromlist=["ServiceLifecycle"]).ServiceLifecycle()
    with TestClient(
        create_app(lifecycle=unavailable_lifecycle),
        raise_server_exceptions=False,
    ) as client:
        unavailable_lifecycle.mark_stopping()
        documents["service-unavailable.problem.json"] = _response_json(
            client.post(
                "/api/v1/generate",
                json=GENERATE_SUCCESS_REQUEST,
                headers=HEADERS,
            ),
            503,
        )

    error_settings = ApiSettings()
''',
)
replace(
    "scripts/export_tutorboard_contracts.py",
    '''        {
            "id": "internal-error",
''',
    '''        {
            "id": "service-unavailable",
            "method": "POST",
            "path": "/api/v1/generate",
            "request": "generate-success.request.json",
            "response": "service-unavailable.problem.json",
            "status": 503,
            "media_type": "application/problem+json",
            "mode": "injected_lifecycle",
        },
        {
            "id": "internal-error",
''',
)

replace(
    "docs/operations/API_RUNTIME.md",
    '''| `GEOMETRYOS_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
''',
    '''| `GEOMETRYOS_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `GEOMETRYOS_CORS_ALLOWED_ORIGINS` | empty | comma-separated exact HTTP(S) origins |
| `GEOMETRYOS_CORS_MAX_AGE_SECONDS` | `600` | `0..86400` |
''',
)
replace(
    "docs/operations/API_RUNTIME.md",
    '''## Request correlation
''',
    '''## Browser CORS boundary

CORS is disabled by default. Browser access must be enabled with exact origins, for example `http://localhost:5173`. Wildcards, credentialed origins, URL paths, queries and fragments are rejected at startup. Credentials are disabled. Preflight permits `GET`, `POST`, `OPTIONS`, `Content-Type` and `X-Request-ID`; actual responses expose `X-Request-ID` to browser JavaScript.

## Request correlation
''',
)
replace(
    "docs/contracts/API_CONTRACT.md",
    '''| Unexpected internal failure | 500 | `internal_error` |
''',
    '''| Unexpected internal failure | 500 | `internal_error` |
| Application lifecycle or runtime components not ready | 503 | `service_unavailable` |
''',
)
replace(
    "docs/contracts/API_CONTRACT.md",
    '''Every HTTP response carries `X-Request-ID`. Valid caller-provided identifiers are echoed; invalid or missing values are replaced with a generated UUID.
''',
    '''Every HTTP response carries `X-Request-ID`. Valid caller-provided identifiers are echoed; invalid or missing values are replaced with a generated UUID. The optional request header and required response header are published in OpenAPI for every public operation and response. Stable v1 POST operations return HTTP 503 Problem Details with code `service_unavailable` before invoking the application executor while readiness is degraded.
''',
)
replace(
    "docs/COMPATIBILITY.md",
    '''Changing a Problem Details code, removing request correlation or changing a published HTTP status requires a documented API compatibility review.
''',
    '''Changing a Problem Details code, removing request correlation or changing a published HTTP status requires a documented API compatibility review. The published optional `X-Request-ID` request parameter and required response header are stable v1 contract elements; removing either is breaking. `service_unavailable` is the stable code for readiness-gated v1 POST requests. CORS remains disabled by default and enabling exact browser origins is deployment configuration rather than a JSON contract change.
''',
)

# Remove this one-shot script from the implementation commit.
Path(__file__).unlink()
''
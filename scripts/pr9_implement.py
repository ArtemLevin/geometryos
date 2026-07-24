from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {path}, found {count}: {old[:80]!r}")
    write(path, content.replace(old, new, 1))


def append_once(path: str, marker: str, addition: str) -> None:
    content = read(path)
    if marker not in content:
        write(path, content.rstrip() + "\n\n" + addition.strip() + "\n")


write(
    "src/gir_api/settings.py",
    '''from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
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

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def validate_cors_allowed_origins(cls, value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("CORS allowed origins must be a comma-separated string.")

        origins: list[str] = []
        for raw_origin in value.split(","):
            candidate = raw_origin.strip()
            if not candidate:
                continue
            if candidate in {"*", "null"}:
                raise ValueError("Wildcard and null CORS origins are forbidden.")
            parsed = urlsplit(candidate)
            if parsed.scheme.lower() not in {"http", "https"} or parsed.hostname is None:
                raise ValueError(f"Invalid CORS origin: {candidate!r}.")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("CORS origins must not contain credentials.")
            if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError("CORS origins must not contain paths, queries, or fragments.")
            try:
                parsed.port
            except ValueError as exc:
                raise ValueError(f"Invalid CORS origin port: {candidate!r}.") from exc
            normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
            if normalized not in origins:
                origins.append(normalized)

        if len(origins) > _MAX_CORS_ORIGINS:
            raise ValueError(f"At most {_MAX_CORS_ORIGINS} CORS origins are allowed.")
        return ",".join(origins)

    @property
    def parsed_cors_allowed_origins(self) -> tuple[str, ...]:
        if not self.cors_allowed_origins:
            return ()
        return tuple(self.cors_allowed_origins.split(","))


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
''',
)

write(
    "src/gir_api/errors.py",
    '''from gir_api.context import ApiOperation
from gir_core.models.validation import ValidationReport


class ApiRuntimeError(Exception):
    code = "api_runtime_error"


class InputTooLargeError(ApiRuntimeError):
    code = "input_too_large"

    def __init__(self, *, actual_chars: int, max_chars: int) -> None:
        super().__init__("Input exceeds the configured operational limit.")
        self.actual_chars = actual_chars
        self.max_chars = max_chars


class OperationTimeoutError(ApiRuntimeError):
    code = "operation_timeout"

    def __init__(self, *, operation: ApiOperation, timeout_seconds: float) -> None:
        super().__init__(f"{operation.value} operation timed out.")
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class SemanticValidationError(ApiRuntimeError):
    code = "semantic_validation_failed"

    def __init__(self, validation_report: ValidationReport) -> None:
        super().__init__("GIR failed semantic validation.")
        self.validation_report = validation_report


class ServiceUnavailableError(ApiRuntimeError):
    code = "service_unavailable"

    def __init__(self) -> None:
        super().__init__("GeometryOS is not ready to accept application requests.")
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

replace_once(
    "src/gir_api/main.py",
    "from fastapi import FastAPI\n",
    "from fastapi import FastAPI\nfrom starlette.middleware.cors import CORSMiddleware\n",
)
replace_once(
    "src/gir_api/main.py",
    "from gir_api.constants import API_TITLE, API_V1_VERSION, OPENAPI_TAGS\n",
    "from gir_api.constants import API_TITLE, API_V1_VERSION, OPENAPI_TAGS, REQUEST_ID_HEADER\n",
)
replace_once(
    "src/gir_api/main.py",
    "    register_exception_handlers(application)\n    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)\n",
    '''    register_exception_handlers(application)
    if resolved_settings.parsed_cors_allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.parsed_cors_allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
            max_age=resolved_settings.cors_max_age_seconds,
        )
    # Added last so request correlation wraps CORS preflight and rejection responses.
    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)
''',
)

replace_once(
    "src/gir_api/exception_handlers.py",
    "from gir_api.errors import InputTooLargeError, OperationTimeoutError, SemanticValidationError\n",
    '''from gir_api.errors import (
    InputTooLargeError,
    OperationTimeoutError,
    SemanticValidationError,
    ServiceUnavailableError,
)
''',
)
replace_once(
    "src/gir_api/exception_handlers.py",
    "    app.add_exception_handler(OperationTimeoutError, operation_timeout_handler)\n",
    '''    app.add_exception_handler(OperationTimeoutError, operation_timeout_handler)
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_handler)
''',
)
replace_once(
    "src/gir_api/exception_handlers.py",
    "\n\nasync def operation_timeout_handler(request: Request, exc: Exception) -> Response:\n",
    '''

async def service_unavailable_handler(request: Request, exc: Exception) -> Response:
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

replace_once(
    "src/gir_api/problem_details.py",
    '        500: "Unexpected internal error.",\n        504: "Operation exceeded its configured time limit.",\n',
    '        500: "Unexpected internal error.",\n        503: "Service is alive but not ready to accept application traffic.",\n        504: "Operation exceeded its configured time limit.",\n',
)

for route_path in (
    "src/gir_api/routes/generate.py",
    "src/gir_api/routes/validate.py",
    "src/gir_api/routes/render.py",
):
    content = read(route_path)
    content = re.sub(
        r"problem_responses\(([^)]*)\)",
        lambda match: (
            match.group(0)
            if "503" in match.group(1)
            else "problem_responses("
            + ", ".join(
                sorted(
                    {item.strip() for item in match.group(1).split(",")} | {"503"},
                    key=int,
                )
            )
            + ")"
        ),
        content,
    )
    write(route_path, content)

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
_REQUEST_ID_COMPONENT = "GeometryOsRequestId"
_REQUEST_ID_PATTERN = "^[A-Za-z0-9._-]{1,128}$"


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
    components.setdefault("parameters", {})[_REQUEST_ID_COMPONENT] = {
        "name": REQUEST_ID_HEADER,
        "in": "header",
        "required": False,
        "description": (
            "Optional safe correlation identifier. Valid values are echoed; invalid or "
            "missing values are replaced with a generated identifier."
        ),
        "schema": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128,
            "pattern": _REQUEST_ID_PATTERN,
        },
    }
    components.setdefault("headers", {})[_REQUEST_ID_COMPONENT] = {
        "required": True,
        "description": "Request correlation identifier assigned by GeometryOS.",
        "schema": {"type": "string", "minLength": 1, "maxLength": 128},
    }

    parameter_ref = {"$ref": f"#/components/parameters/{_REQUEST_ID_COMPONENT}"}
    header_ref = {"$ref": f"#/components/headers/{_REQUEST_ID_COMPONENT}"}
    for path_item in document.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            if not isinstance(operation, dict):
                continue
            parameters = operation.setdefault("parameters", [])
            if parameter_ref not in parameters:
                parameters.append(parameter_ref)
            responses = operation.get("responses", {})
            if not isinstance(responses, dict):
                continue
            for response in responses.values():
                if not isinstance(response, dict):
                    continue
                response.setdefault("headers", {})[REQUEST_ID_HEADER] = header_ref


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

# Extend compatibility checking without replacing the existing schema comparison machinery.
replace_once(
    "src/gir_api/openapi_compatibility.py",
    '''            if baseline_operation.get("operationId") != candidate_operation.get("operationId"):
                issues.append(_breaking(location, "operationId changed"))
            _compare_request_body(
''',
    '''            if baseline_operation.get("operationId") != candidate_operation.get("operationId"):
                issues.append(_breaking(location, "operationId changed"))
            _compare_parameters(
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
replace_once(
    "src/gir_api/openapi_compatibility.py",
    '''        if isinstance(baseline_response, dict):
            _compare_content(
                baseline_response.get("content", {}),
                candidate_response.get("content", {}),
                baseline_document,
                candidate_document,
                status_location,
                "response",
                issues,
            )


def _compare_content(
''',
    '''        if isinstance(baseline_response, dict):
            _compare_content(
                baseline_response.get("content", {}),
                candidate_response.get("content", {}),
                baseline_document,
                candidate_document,
                status_location,
                "response",
                issues,
            )
            _compare_response_headers(
                baseline_response.get("headers", {}),
                candidate_response.get("headers", {}),
                baseline_document,
                candidate_document,
                status_location,
                issues,
            )
    for status in sorted(set(candidate_responses) - set(baseline_responses)):
        issues.append(_review(f"{location} response {status}", "response status was added"))


def _compare_parameters(
    baseline_parameters: object,
    candidate_parameters: object,
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    issues: list[CompatibilityIssue],
) -> None:
    if not isinstance(baseline_parameters, list):
        return
    if not isinstance(candidate_parameters, list):
        issues.append(_breaking(location, "operation parameters disappeared"))
        return

    def index(parameters: list[object], document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        result: dict[tuple[str, str], dict[str, Any]] = {}
        for item in parameters:
            if not isinstance(item, dict):
                continue
            resolved = _resolve_schema(item, document)
            name = resolved.get("name")
            parameter_in = resolved.get("in")
            if isinstance(name, str) and isinstance(parameter_in, str):
                result[(parameter_in, name.lower())] = resolved
        return result

    baseline_index = index(baseline_parameters, baseline_document)
    candidate_index = index(candidate_parameters, candidate_document)
    for key, baseline_parameter in baseline_index.items():
        candidate_parameter = candidate_index.get(key)
        parameter_location = f"{location} parameter {key[0]}:{key[1]}"
        if candidate_parameter is None:
            issues.append(_breaking(parameter_location, "parameter was removed"))
            continue
        if not baseline_parameter.get("required", False) and candidate_parameter.get(
            "required", False
        ):
            issues.append(_breaking(parameter_location, "optional parameter became required"))
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
    for key in sorted(set(candidate_index) - set(baseline_index)):
        issues.append(_review(f"{location} parameter {key[0]}:{key[1]}", "parameter was added"))


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
    baseline_by_name = {str(name).lower(): value for name, value in baseline_headers.items()}
    candidate_by_name = {str(name).lower(): value for name, value in candidate_headers.items()}
    for name, baseline_header in baseline_by_name.items():
        header_location = f"{location} header {name}"
        candidate_header = candidate_by_name.get(name)
        if not isinstance(candidate_header, dict):
            issues.append(_breaking(header_location, "response header was removed"))
            continue
        if not isinstance(baseline_header, dict):
            continue
        baseline_resolved = _resolve_schema(baseline_header, baseline_document)
        candidate_resolved = _resolve_schema(candidate_header, candidate_document)
        if baseline_resolved.get("required", False) and not candidate_resolved.get(
            "required", False
        ):
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
    for name in sorted(set(candidate_by_name) - set(baseline_by_name)):
        issues.append(_review(f"{location} header {name}", "response header was added"))


def _compare_content(
''',
)
replace_once(
    "src/gir_api/openapi_compatibility.py",
    '''    for key in stricter_max:
        before = baseline.get(key)
        after = candidate.get(key)
        if isinstance(before, (int, float)) and isinstance(after, (int, float)) and after < before:
            issues.append(_breaking(location, f"{key} became stricter: {before} -> {after}"))
''',
    '''    for key in stricter_max:
        before = baseline.get(key)
        after = candidate.get(key)
        if isinstance(before, (int, float)) and isinstance(after, (int, float)) and after < before:
            issues.append(_breaking(location, f"{key} became stricter: {before} -> {after}"))
    before_pattern = baseline.get("pattern")
    after_pattern = candidate.get("pattern")
    if isinstance(before_pattern, str) and before_pattern != after_pattern:
        issues.append(_breaking(location, "pattern changed"))
''',
)

# Make response correlation executable for every exported fixture.
replace_once(
    "scripts/export_tutorboard_contracts.py",
    "from gir_api.settings import ApiSettings  # noqa: E402\n",
    "from gir_api.readiness import ServiceLifecycle  # noqa: E402\nfrom gir_api.settings import ApiSettings  # noqa: E402\n",
)
replace_once(
    "scripts/export_tutorboard_contracts.py",
    '''def _response_json(response: Any, expected_status: int) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise RuntimeError(
            f"Unexpected status {response.status_code}, expected {expected_status}: {response.text}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Contract response must be a JSON object.")
    return payload
''',
    '''def _response_json(response: Any, expected_status: int) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise RuntimeError(
            f"Unexpected status {response.status_code}, expected {expected_status}: {response.text}"
        )
    response_request_id = response.headers.get("X-Request-ID")
    if response_request_id != REQUEST_ID:
        raise RuntimeError(f"Contract response request ID mismatch: {response_request_id!r}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Contract response must be a JSON object.")
    body_request_id = payload.get("request_id")
    if body_request_id is not None and body_request_id != response_request_id:
        raise RuntimeError("Problem Details request_id must match X-Request-ID.")
    return payload
''',
)
replace_once(
    "scripts/export_tutorboard_contracts.py",
    '''    cases = [
''',
    '''    unavailable_lifecycle = ServiceLifecycle()
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

    cases = [
''',
)
replace_once(
    "scripts/export_tutorboard_contracts.py",
    '''        {
            "id": "operation-timeout",
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
            "id": "operation-timeout",
''',
)

replace_once(
    "contracts/tutorboard/typescript/smoke.ts",
    'type GenerateTimeout = paths["/api/v1/generate"]["post"]["responses"][504]["content"]["application/problem+json"];\n',
    'type GenerateUnavailable = paths["/api/v1/generate"]["post"]["responses"][503]["content"]["application/problem+json"];\ntype GenerateTimeout = paths["/api/v1/generate"]["post"]["responses"][504]["content"]["application/problem+json"];\n',
)
replace_once(
    "contracts/tutorboard/typescript/smoke.ts",
    'const timeoutCode: GenerateTimeout["code"] = "operation_timeout";\n',
    'const unavailableCode: GenerateUnavailable["code"] = "service_unavailable";\nconst timeoutCode: GenerateTimeout["code"] = "operation_timeout";\n',
)
replace_once(
    "contracts/tutorboard/typescript/smoke.ts",
    "void timeoutCode;\n",
    "void unavailableCode;\nvoid timeoutCode;\n",
)

# Wire secure CORS settings through local deployment.
append_once(
    ".env.example",
    "GEOMETRYOS_CORS_ALLOWED_ORIGINS",
    '''# Browser access is disabled by default. Use exact origins only; wildcard is rejected.
GEOMETRYOS_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GEOMETRYOS_CORS_MAX_AGE_SECONDS=600''',
)
replace_once(
    "compose.yaml",
    "      GEOMETRYOS_LOG_LEVEL: ${GEOMETRYOS_LOG_LEVEL:-INFO}\n",
    '''      GEOMETRYOS_LOG_LEVEL: ${GEOMETRYOS_LOG_LEVEL:-INFO}
      GEOMETRYOS_CORS_ALLOWED_ORIGINS: ${GEOMETRYOS_CORS_ALLOWED_ORIGINS:-}
      GEOMETRYOS_CORS_MAX_AGE_SECONDS: ${GEOMETRYOS_CORS_MAX_AGE_SECONDS:-600}
''',
)

# Container smoke exercises actual CORS headers over a TCP socket.
replace_once(
    "scripts/container_smoke.py",
    '''def wait_for_endpoint(
''',
    '''def request_text(
    url: str,
    *,
    method: str,
    headers: dict[str, str],
    timeout: float = 3.0,
) -> tuple[int, dict[str, str], str]:
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        body = response.read().decode("utf-8")
        response_headers = {name.lower(): value for name, value in response.headers.items()}
        return response.status, response_headers, body


def wait_for_endpoint(
''',
)
replace_once(
    "scripts/container_smoke.py",
    '''                "--publish",
                f"127.0.0.1:{port}:8000",
                "--read-only",
''',
    '''                "--publish",
                f"127.0.0.1:{port}:8000",
                "--env",
                "GEOMETRYOS_CORS_ALLOWED_ORIGINS=http://localhost:5173",
                "--read-only",
''',
)
replace_once(
    "scripts/container_smoke.py",
    '''        wait_for_container_health(name, timeout_seconds=timeout_seconds)

        status, response_headers, body = request_json(
''',
    '''        wait_for_container_health(name, timeout_seconds=timeout_seconds)

        preflight_status, preflight_headers, _ = request_text(
            f"{base_url}/api/v1/generate",
            method="OPTIONS",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Request-ID",
                "X-Request-ID": "container-preflight",
            },
        )
        if preflight_status != 200:
            raise SmokeFailure(f"Unexpected CORS preflight status: {preflight_status}")
        if preflight_headers.get("access-control-allow-origin") != "http://localhost:5173":
            raise SmokeFailure("CORS preflight did not allow the configured origin.")
        if preflight_headers.get("x-request-id") != "container-preflight":
            raise SmokeFailure("CORS preflight did not preserve X-Request-ID.")
        print("[PASS] browser CORS preflight and request correlation", flush=True)

        status, response_headers, body = request_json(
''',
)
replace_once(
    "scripts/container_smoke.py",
    '            headers={"X-Request-ID": "container-smoke"},\n',
    '''            headers={
                "X-Request-ID": "container-smoke",
                "Origin": "http://localhost:5173",
            },
''',
)
replace_once(
    "scripts/container_smoke.py",
    '''        if response_headers.get("x-request-id") != "container-smoke":
            raise SmokeFailure("Request correlation header was not preserved.")
        print("[PASS] stable API generation and request correlation", flush=True)
''',
    '''        if response_headers.get("x-request-id") != "container-smoke":
            raise SmokeFailure("Request correlation header was not preserved.")
        if response_headers.get("access-control-allow-origin") != "http://localhost:5173":
            raise SmokeFailure("Configured browser origin was not allowed.")
        exposed = response_headers.get("access-control-expose-headers", "").lower()
        if "x-request-id" not in exposed:
            raise SmokeFailure("X-Request-ID was not exposed to browser JavaScript.")
        _, denied_headers, _ = request_json(
            f"{base_url}/health",
            headers={"Origin": "http://attacker.invalid"},
        )
        if "access-control-allow-origin" in denied_headers:
            raise SmokeFailure("Unconfigured browser origin was unexpectedly allowed.")
        print("[PASS] stable API generation, CORS, and request correlation", flush=True)
''',
)

write(
    "tests/api/test_cors.py",
    '''from fastapi.testclient import TestClient

from gir_api.main import create_app
from gir_api.settings import ApiSettings

_ALLOWED_ORIGIN = "http://localhost:5173"
_GENERATE_REQUEST = {
    "input_type": "text",
    "input": "Постройте треугольник ABC.",
    "mode": "strict",
}


def _client(origins: str) -> TestClient:
    return TestClient(create_app(settings=ApiSettings(cors_allowed_origins=origins)))


def test_cors_is_disabled_by_default() -> None:
    with _client("") as client:
        response = client.get("/health", headers={"Origin": _ALLOWED_ORIGIN})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_allowed_preflight_is_correlated() -> None:
    with _client(_ALLOWED_ORIGIN) as client:
        response = client.options(
            "/api/v1/generate",
            headers={
                "Origin": _ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-Request-ID",
                "X-Request-ID": "cors-preflight",
            },
        )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "x-request-id" in response.headers["Access-Control-Allow-Headers"].lower()
    assert response.headers["X-Request-ID"] == "cors-preflight"
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_actual_response_exposes_request_id() -> None:
    with _client(_ALLOWED_ORIGIN) as client:
        response = client.post(
            "/api/v1/generate",
            json=_GENERATE_REQUEST,
            headers={"Origin": _ALLOWED_ORIGIN, "X-Request-ID": "cors-actual"},
        )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert "x-request-id" in response.headers["Access-Control-Expose-Headers"].lower()
    assert response.headers["X-Request-ID"] == "cors-actual"


def test_unconfigured_origin_is_not_allowed() -> None:
    with _client(_ALLOWED_ORIGIN) as client:
        response = client.get("/health", headers={"Origin": "http://attacker.invalid"})
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
''',
)

write(
    "tests/api/test_pr9_settings.py",
    '''import pytest
from pydantic import ValidationError

from gir_api.settings import ApiSettings


def test_cors_settings_default_to_disabled() -> None:
    settings = ApiSettings(_env_file=None)
    assert settings.parsed_cors_allowed_origins == ()
    assert settings.cors_max_age_seconds == 600


def test_cors_origins_are_trimmed_deduplicated_and_canonicalized() -> None:
    settings = ApiSettings(
        cors_allowed_origins=(
            " HTTP://LOCALHOST:5173/, http://localhost:5173, https://example.com "
        ),
        _env_file=None,
    )
    assert settings.parsed_cors_allowed_origins == (
        "http://localhost:5173",
        "https://example.com",
    )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "null",
        "ftp://localhost:5173",
        "http://user:password@localhost:5173",
        "http://localhost:5173/path",
        "http://localhost:5173?query=yes",
        "http://localhost:5173#fragment",
        "http://localhost:invalid",
    ],
)
def test_cors_origins_reject_unsafe_values(origin: str) -> None:
    with pytest.raises(ValidationError):
        ApiSettings(cors_allowed_origins=origin, _env_file=None)
''',
)

write(
    "tests/api/test_service_unavailable.py",
    '''from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from gir_api.main import create_app
from gir_api.openapi_examples import ALTITUDE_GIR_EXAMPLE
from gir_api.readiness import ServiceLifecycle


class CountingExecutor:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("generate must not run while the service is not ready")

    async def validate(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("validate must not run while the service is not ready")

    async def render_svg(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("render_svg must not run while the service is not ready")

    async def render_tikz(self, command: object) -> object:
        del command
        self.calls += 1
        raise AssertionError("render_tikz must not run while the service is not ready")


RequestCall = Callable[[TestClient], Any]


@pytest.mark.parametrize(
    "call",
    [
        lambda client: client.post(
            "/api/v1/generate",
            json={"input_type": "text", "input": "Постройте треугольник ABC.", "mode": "strict"},
            headers={"X-Request-ID": "unavailable-generate"},
        ),
        lambda client: client.post(
            "/api/v1/validate-gir",
            json=ALTITUDE_GIR_EXAMPLE,
            headers={"X-Request-ID": "unavailable-validate"},
        ),
        lambda client: client.post(
            "/api/v1/render/svg",
            json=ALTITUDE_GIR_EXAMPLE,
            headers={"X-Request-ID": "unavailable-svg"},
        ),
        lambda client: client.post(
            "/api/v1/render/tikz",
            json=ALTITUDE_GIR_EXAMPLE,
            headers={"X-Request-ID": "unavailable-tikz"},
        ),
    ],
)
def test_stable_operations_return_problem_details_before_executor(call: RequestCall) -> None:
    lifecycle = ServiceLifecycle()
    executor = CountingExecutor()
    with TestClient(create_app(executor=executor, lifecycle=lifecycle)) as client:
        lifecycle.mark_stopping()
        response = call(client)

    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Type"].startswith("application/problem+json")
    assert response.json()["code"] == "service_unavailable"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert executor.calls == 0


def test_health_and_readiness_keep_their_probe_contracts() -> None:
    lifecycle = ServiceLifecycle()
    with TestClient(create_app(lifecycle=lifecycle)) as client:
        lifecycle.mark_stopping()
        health = client.get("/health")
        ready = client.get("/ready")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
    assert ready.headers["Content-Type"].startswith("application/json")
''',
)

write(
    "tests/contracts/test_pr9_openapi_contract.py",
    '''from gir_api.constants import REQUEST_ID_HEADER
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
        assert {"$ref": "#/components/parameters/GeometryOsRequestId"} in operation[
            "parameters"
        ]
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
''',
)

write(
    "tests/contracts/test_pr9_openapi_compatibility.py",
    '''from copy import deepcopy

from gir_api.openapi_compatibility import CompatibilitySeverity, compare_openapi_documents
from gir_api.openapi_contract import build_openapi_document


def _breaking_messages(candidate: dict[str, object]) -> list[str]:
    baseline = build_openapi_document()
    return [
        issue.message
        for issue in compare_openapi_documents(baseline, candidate)
        if issue.severity is CompatibilitySeverity.BREAKING
    ]


def test_request_correlation_parameter_removal_is_breaking() -> None:
    candidate = deepcopy(build_openapi_document())
    candidate["paths"]["/api/v1/generate"]["post"]["parameters"] = []
    assert "parameter was removed" in _breaking_messages(candidate)


def test_response_correlation_header_removal_is_breaking() -> None:
    candidate = deepcopy(build_openapi_document())
    del candidate["paths"]["/api/v1/generate"]["post"]["responses"]["200"]["headers"][
        "X-Request-ID"
    ]
    assert "response header was removed" in _breaking_messages(candidate)


def test_new_response_status_requires_review() -> None:
    candidate = build_openapi_document()
    baseline = deepcopy(candidate)
    del baseline["paths"]["/api/v1/generate"]["post"]["responses"]["503"]
    issues = compare_openapi_documents(baseline, candidate)
    assert any(
        issue.severity is CompatibilitySeverity.REVIEW
        and issue.message == "response status was added"
        for issue in issues
    )
''',
)

append_once(
    "README.md",
    "## TutorBoard browser development",
    '''## TutorBoard browser development

Browser access is disabled unless exact origins are configured. For the local TutorBoard Vite server:

```powershell
$env:GEOMETRYOS_CORS_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
uv run uvicorn gir_api.main:app --reload
```

GeometryOS never accepts wildcard origins or credentialed CORS. Browser responses expose `X-Request-ID`; stable v1 operations return `503 application/problem+json` with code `service_unavailable` while readiness is degraded.''',
)
append_once(
    "docs/contracts/API_CONTRACT.md",
    "## Browser and request-correlation contract",
    '''## Browser and request-correlation contract

Every published operation accepts the optional `X-Request-ID` header and declares the assigned `X-Request-ID` on every response. Stable v1 POST operations are guarded by the same local readiness snapshot as `/ready`; while unavailable they return HTTP `503`, `application/problem+json`, stable code `service_unavailable`, `Cache-Control: no-store`, and matching body/header request IDs.

CORS is an operational opt-in. Exact configured origins may use `GET`, `POST`, and preflight `OPTIONS`, may send `Content-Type` and `X-Request-ID`, and can read the exposed `X-Request-ID`. Wildcard origins and credentials are not supported.''',
)
append_once(
    "docs/operations/API_RUNTIME.md",
    "### Browser CORS boundary",
    '''### Browser CORS boundary

| Variable | Default | Contract |
|---|---:|---|
| `GEOMETRYOS_CORS_ALLOWED_ORIGINS` | empty | Comma-separated exact HTTP(S) origins; empty disables CORS |
| `GEOMETRYOS_CORS_MAX_AGE_SECONDS` | `600` | `0..86400` preflight cache duration |

Wildcard, `null`, credentialed origins, and origins with paths, queries, or fragments fail application configuration. Credentials remain disabled. Allowed browser requests may send `Content-Type` and `X-Request-ID`; responses expose `X-Request-ID`.

Stable v1 POST operations check local readiness before invoking the executor. A degraded service returns sanitized `503` Problem Details with code `service_unavailable`; `/health` and `/ready` preserve their existing probe response bodies.''',
)
append_once(
    "docs/COMPATIBILITY.md",
    "## Browser transport compatibility",
    '''## Browser transport compatibility

The published optional `X-Request-ID` request parameter, required response-correlation header, HTTP `503` service-unavailable outcome, and stable `service_unavailable` Problem Details code are part of API v1 compatibility. Removing them, making the request header mandatory, narrowing its accepted value contract, or changing the stable code requires a breaking-contract review.

CORS remains disabled by default and is enabled only for exact configured origins. This operational default may not be weakened to wildcard or credentialed cross-origin access without a separate security review.''',
)
append_once(
    "docs/operations/DEPLOYMENT.md",
    "## TutorBoard browser origin",
    '''## TutorBoard browser origin

Set `GEOMETRYOS_CORS_ALLOWED_ORIGINS` to the exact TutorBoard browser origins when direct browser integration is required. Localhost and `127.0.0.1` are distinct origins and must be listed separately. Do not use wildcard origins. Reverse proxies must preserve caller `X-Request-ID` and the response `X-Request-ID` header.''',
)
append_once(
    "docs/adr/ADR-004-api-resilience-boundary.md",
    "## Browser contract extension",
    '''## Browser contract extension

The resilience boundary also owns exact-origin CORS and the stable `service_unavailable` response. Request correlation remains the outer middleware so preflight and early CORS responses receive `X-Request-ID`; stable application operations are rejected before executor invocation whenever the local readiness snapshot is degraded.''',
)
append_once(
    "docs/adr/ADR-006-published-openapi-and-consumer-contract.md",
    "## Correlation headers and availability",
    '''## Correlation headers and availability

The published OpenAPI includes the optional `X-Request-ID` request parameter, response header declarations for every status, and the stable `503` Problem Details outcome. The compatibility checker treats removal or narrowing of these headers as breaking and newly declared response statuses as review-required additions.''',
)

# The temporary implementation script must not remain in the product tree.
Path(__file__).unlink()

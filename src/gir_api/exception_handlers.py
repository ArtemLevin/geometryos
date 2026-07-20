from collections.abc import Sequence
from typing import TypeVar

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from gir_api.constants import INTERNAL_ERROR_CODE_HEADER
from gir_api.context import get_request_id
from gir_api.errors import InputTooLargeError, OperationTimeoutError, SemanticValidationError
from gir_api.problem_details import ProblemError, is_v1_path, problem_response

ExceptionT = TypeVar("ExceptionT", bound=Exception)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(SemanticValidationError, semantic_validation_handler)
    app.add_exception_handler(InputTooLargeError, input_too_large_handler)
    app.add_exception_handler(OperationTimeoutError, operation_timeout_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_problem_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)


async def request_validation_handler(request: Request, exc: Exception) -> Response:
    validation_error = _expect_exception(exc, RequestValidationError)
    if not is_v1_path(request.url.path):
        return await request_validation_exception_handler(request, validation_error)

    errors = [
        ProblemError(
            code=str(item.get("type", "validation_error")),
            message=str(item.get("msg", "Invalid request value.")),
            location=_sanitize_location(item.get("loc", ())),
        )
        for item in validation_error.errors()
    ]
    return problem_response(
        status=422,
        problem_type="urn:geometryos:problem:request-validation",
        title="Request validation failed",
        detail="The request payload does not satisfy the API contract.",
        instance=request.url.path,
        code="request_validation_failed",
        request_id=_request_id(),
        errors=errors,
    )


async def semantic_validation_handler(request: Request, exc: Exception) -> Response:
    semantic_error = _expect_exception(exc, SemanticValidationError)
    if not is_v1_path(request.url.path):
        return JSONResponse(
            status_code=422,
            content={"detail": semantic_error.validation_report.model_dump(mode="json")},
            headers={INTERNAL_ERROR_CODE_HEADER: semantic_error.code},
        )

    errors = [
        ProblemError(
            code=issue.code,
            message=issue.message,
            location=[issue.path] if issue.path is not None else [],
        )
        for issue in semantic_error.validation_report.issues
    ]
    return problem_response(
        status=422,
        problem_type="urn:geometryos:problem:semantic-validation",
        title="Semantic validation failed",
        detail="The GIR scene is structurally valid but semantically invalid.",
        instance=request.url.path,
        code=semantic_error.code,
        request_id=_request_id(),
        errors=errors,
    )


async def input_too_large_handler(request: Request, exc: Exception) -> Response:
    input_error = _expect_exception(exc, InputTooLargeError)
    if not is_v1_path(request.url.path):
        return JSONResponse(
            status_code=413,
            content={"detail": "Input exceeds the configured limit."},
            headers={INTERNAL_ERROR_CODE_HEADER: input_error.code},
        )

    return problem_response(
        status=413,
        problem_type="urn:geometryos:problem:input-too-large",
        title="Input too large",
        detail="The input exceeds the configured operational character limit.",
        instance=request.url.path,
        code=input_error.code,
        request_id=_request_id(),
    )


async def operation_timeout_handler(request: Request, exc: Exception) -> Response:
    timeout_error = _expect_exception(exc, OperationTimeoutError)
    if not is_v1_path(request.url.path):
        return JSONResponse(
            status_code=504,
            content={"detail": "Operation timed out."},
            headers={INTERNAL_ERROR_CODE_HEADER: timeout_error.code},
        )

    return problem_response(
        status=504,
        problem_type="urn:geometryos:problem:operation-timeout",
        title="Operation timed out",
        detail=(
            f"The {timeout_error.operation.value} operation exceeded its configured time limit."
        ),
        instance=request.url.path,
        code=timeout_error.code,
        request_id=_request_id(),
        no_store=True,
    )


async def http_exception_problem_handler(request: Request, exc: Exception) -> Response:
    http_error = _expect_exception(exc, StarletteHTTPException)
    if not is_v1_path(request.url.path) or http_error.status_code not in {404, 405}:
        return await http_exception_handler(request, http_error)

    code = "not_found" if http_error.status_code == 404 else "method_not_allowed"
    title = "Not found" if http_error.status_code == 404 else "Method not allowed"
    return problem_response(
        status=http_error.status_code,
        problem_type=f"urn:geometryos:problem:{code.replace('_', '-')}",
        title=title,
        detail=str(http_error.detail),
        instance=request.url.path,
        code=code,
        request_id=_request_id(),
    )


async def unexpected_exception_handler(request: Request, exc: Exception) -> Response:
    del exc
    if is_v1_path(request.url.path):
        return problem_response(
            status=500,
            problem_type="urn:geometryos:problem:internal-error",
            title="Internal server error",
            detail="An unexpected internal error occurred.",
            instance=request.url.path,
            code="internal_error",
            request_id=_request_id(),
            no_store=True,
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
        headers={INTERNAL_ERROR_CODE_HEADER: "internal_error", "Cache-Control": "no-store"},
    )


def _expect_exception(exc: Exception, expected: type[ExceptionT]) -> ExceptionT:
    if not isinstance(exc, expected):
        raise TypeError(f"Expected {expected.__name__}, got {type(exc).__name__}.")
    return exc


def _request_id() -> str:
    return get_request_id() or "unknown"


def _sanitize_location(value: object) -> list[str | int]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item if isinstance(item, (str, int)) else str(item) for item in value]

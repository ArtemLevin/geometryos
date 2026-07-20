import logging
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from gir_api.constants import INTERNAL_ERROR_CODE_HEADER, REQUEST_ID_HEADER
from gir_api.context import operation_context, request_id_context, resolve_operation
from gir_api.logging import get_api_logger
from gir_api.problem_details import is_v1_path, problem_response
from gir_api.settings import ApiSettings

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_REQUEST_ID_HEADER_BYTES = REQUEST_ID_HEADER.lower().encode("ascii")
_INTERNAL_ERROR_HEADER_BYTES = INTERNAL_ERROR_CODE_HEADER.lower().encode("ascii")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, settings: ApiSettings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        method = str(scope.get("method", ""))
        request_id = _resolve_request_id(scope)
        operation = resolve_operation(path)
        request_token = request_id_context.set(request_id)
        operation_token = operation_context.set(operation)
        started_at = perf_counter()
        status_code = 500
        error_code: str | None = None
        response_started = False
        logger = get_api_logger()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, error_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = int(message["status"])
                raw_headers: list[tuple[bytes, bytes]] = []
                for name, value in message.get("headers", []):
                    lowered = name.lower()
                    if lowered == _INTERNAL_ERROR_HEADER_BYTES:
                        error_code = value.decode("latin-1")
                        continue
                    if lowered != _REQUEST_ID_HEADER_BYTES:
                        raw_headers.append((name, value))
                raw_headers.append((REQUEST_ID_HEADER.encode("ascii"), request_id.encode("ascii")))
                message["headers"] = raw_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            if response_started:
                raise
            error_code = "internal_error"
            status_code = 500
            _log_internal_error(
                logger,
                request_id,
                operation.value,
                method,
                path,
                exc,
                self.settings,
            )
            response = _internal_error_response(path, request_id)
            await response(scope, receive, send_wrapper)
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "request_id": request_id,
                    "operation": operation.value,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "error_code": error_code,
                },
            )
            request_id_context.reset(request_token)
            operation_context.reset(operation_token)


def _resolve_request_id(scope: Scope) -> str:
    candidate: str | None = None
    for name, value in scope.get("headers", []):
        if name.lower() == _REQUEST_ID_HEADER_BYTES:
            candidate = value.decode("latin-1")
            break
    if candidate and _REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return str(uuid4())


def _internal_error_response(path: str, request_id: str) -> Response:
    if is_v1_path(path):
        return problem_response(
            status=500,
            problem_type="urn:geometryos:problem:internal-error",
            title="Internal server error",
            detail="An unexpected internal error occurred.",
            instance=path,
            code="internal_error",
            request_id=request_id,
            no_store=True,
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
        headers={INTERNAL_ERROR_CODE_HEADER: "internal_error", "Cache-Control": "no-store"},
    )


def _log_internal_error(
    logger: logging.Logger,
    request_id: str,
    operation: str,
    method: str,
    path: str,
    exc: Exception,
    settings: ApiSettings,
) -> None:
    exc_info: Any = None
    if settings.log_level == "DEBUG":
        exc_info = (type(exc), exc, exc.__traceback__)
    logger.error(
        "internal_error",
        extra={
            "event": "internal_error",
            "request_id": request_id,
            "operation": operation,
            "method": method,
            "path": path,
            "error_code": "internal_error",
            "exception_type": type(exc).__name__,
        },
        exc_info=exc_info,
    )

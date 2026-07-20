from contextvars import ContextVar
from enum import StrEnum


class ApiOperation(StrEnum):
    HEALTH = "health"
    READY = "ready"
    GENERATE = "generate"
    VALIDATE_GIR = "validate_gir"
    RENDER_SVG = "render_svg"
    RENDER_TIKZ = "render_tikz"
    UNKNOWN = "unknown"


request_id_context: ContextVar[str | None] = ContextVar(
    "geometryos_request_id",
    default=None,
)
operation_context: ContextVar[ApiOperation] = ContextVar(
    "geometryos_operation",
    default=ApiOperation.UNKNOWN,
)


def get_request_id() -> str | None:
    return request_id_context.get()


def get_operation() -> ApiOperation:
    return operation_context.get()


def resolve_operation(path: str) -> ApiOperation:
    path_map = {
        "/health": ApiOperation.HEALTH,
        "/ready": ApiOperation.READY,
        "/api/v1/generate": ApiOperation.GENERATE,
        "/generate": ApiOperation.GENERATE,
        "/api/v1/validate-gir": ApiOperation.VALIDATE_GIR,
        "/validate-gir": ApiOperation.VALIDATE_GIR,
        "/api/v1/render/svg": ApiOperation.RENDER_SVG,
        "/render/svg": ApiOperation.RENDER_SVG,
        "/api/v1/render/tikz": ApiOperation.RENDER_TIKZ,
        "/render/tikz": ApiOperation.RENDER_TIKZ,
    }
    return path_map.get(path, ApiOperation.UNKNOWN)

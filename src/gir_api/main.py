from fastapi import FastAPI

from gir_api.constants import API_TITLE, API_V1_VERSION, OPENAPI_TAGS
from gir_api.exception_handlers import register_exception_handlers
from gir_api.execution import TimedApplicationExecutor
from gir_api.logging import configure_logging
from gir_api.middleware import RequestContextMiddleware
from gir_api.openapi_contract import install_openapi_contract
from gir_api.openapi_examples import HEALTH_RESPONSE_EXAMPLE
from gir_api.readiness import (
    ReadinessResponse,
    ServiceLifecycle,
    ready,
    service_lifespan,
)
from gir_api.router import legacy_router, v1_router
from gir_api.settings import ApiSettings, get_settings


def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(
    settings: ApiSettings | None = None,
    executor: TimedApplicationExecutor | None = None,
    lifecycle: ServiceLifecycle | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_lifecycle = lifecycle or ServiceLifecycle()
    configure_logging(resolved_settings)

    application = FastAPI(
        title=API_TITLE,
        version=API_V1_VERSION,
        description="GIR-first geometry compiler service.",
        openapi_tags=OPENAPI_TAGS,
        lifespan=service_lifespan,
    )
    application.state.settings = resolved_settings
    application.state.application_executor = executor or TimedApplicationExecutor(
        settings=resolved_settings
    )
    application.state.lifecycle = resolved_lifecycle

    register_exception_handlers(application)
    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)
    application.add_api_route(
        "/health",
        health,
        methods=["GET"],
        operation_id="geometryos_health",
        tags=["Service"],
        summary="Check process liveness",
        description="Return HTTP 200 while the process can serve HTTP requests.",
        response_model=dict[str, str],
        responses={200: {"content": {"application/json": {"example": HEALTH_RESPONSE_EXAMPLE}}}},
    )
    application.add_api_route(
        "/ready",
        ready,
        methods=["GET"],
        operation_id="geometryos_ready",
        tags=["Service"],
        summary="Check application readiness",
        description=(
            "Return HTTP 200 after startup while lifecycle, settings, and the "
            "application executor remain available; otherwise return HTTP 503."
        ),
        response_model=ReadinessResponse,
        responses={
            503: {
                "model": ReadinessResponse,
                "description": "Service is alive but not ready to accept application traffic.",
            }
        },
    )
    application.include_router(v1_router)
    application.include_router(legacy_router, include_in_schema=False)
    install_openapi_contract(application)
    return application


app = create_app()

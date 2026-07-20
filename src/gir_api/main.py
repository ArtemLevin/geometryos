from fastapi import FastAPI

from gir_api.constants import API_TITLE, API_V1_VERSION, OPENAPI_TAGS
from gir_api.exception_handlers import register_exception_handlers
from gir_api.execution import TimedApplicationExecutor
from gir_api.logging import configure_logging
from gir_api.middleware import RequestContextMiddleware
from gir_api.router import legacy_router, v1_router
from gir_api.settings import ApiSettings, get_settings


def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(
    settings: ApiSettings | None = None,
    executor: TimedApplicationExecutor | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    application = FastAPI(
        title=API_TITLE,
        version=API_V1_VERSION,
        description="GIR-first geometry compiler service.",
        openapi_tags=OPENAPI_TAGS,
    )
    application.state.settings = resolved_settings
    application.state.application_executor = executor or TimedApplicationExecutor(
        settings=resolved_settings
    )

    register_exception_handlers(application)
    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)
    application.add_api_route(
        "/health",
        health,
        methods=["GET"],
        operation_id="geometryos_health",
        tags=["Service"],
    )
    application.include_router(v1_router)
    application.include_router(legacy_router, include_in_schema=False)
    return application


app = create_app()

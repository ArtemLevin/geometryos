from fastapi import FastAPI

from gir_api.constants import API_TITLE, API_V1_VERSION, OPENAPI_TAGS
from gir_api.router import legacy_router, v1_router

app = FastAPI(
    title=API_TITLE,
    version=API_V1_VERSION,
    description="GIR-first geometry compiler service.",
    openapi_tags=OPENAPI_TAGS,
)


@app.get(
    "/health",
    operation_id="geometryos_health",
    tags=["Service"],
)
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(v1_router)
app.include_router(legacy_router, include_in_schema=False)

from fastapi import FastAPI

from gir_api.routes.generate import router as generate_router
from gir_api.routes.render import router as render_router
from gir_api.routes.validate import router as validate_router

app = FastAPI(title="GIR Geometry Compiler API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(generate_router)
app.include_router(validate_router)
app.include_router(render_router)

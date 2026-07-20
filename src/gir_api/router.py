from fastapi import APIRouter

from gir_api.constants import API_V1_PREFIX
from gir_api.routes.generate import legacy_router as legacy_generate_router
from gir_api.routes.generate import v1_router as v1_generate_router
from gir_api.routes.render import legacy_router as legacy_render_router
from gir_api.routes.render import v1_router as v1_render_router
from gir_api.routes.validate import legacy_router as legacy_validate_router
from gir_api.routes.validate import v1_router as v1_validate_router

v1_router = APIRouter(prefix=API_V1_PREFIX)
v1_router.include_router(v1_generate_router)
v1_router.include_router(v1_validate_router)
v1_router.include_router(v1_render_router)

legacy_router = APIRouter()
legacy_router.include_router(legacy_generate_router)
legacy_router.include_router(legacy_validate_router)
legacy_router.include_router(legacy_render_router)

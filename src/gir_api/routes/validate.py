from fastapi import APIRouter

from gir_api.models import ValidateGirV1Response
from gir_api.presenters import present_validate_v1
from gir_application import validate_geometry
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport

v1_router = APIRouter()
legacy_router = APIRouter()


@v1_router.post(
    "/validate-gir",
    response_model=ValidateGirV1Response,
    operation_id="geometryos_v1_validate_gir",
    tags=["Validation"],
)
def validate_gir_v1(scene: GirScene) -> ValidateGirV1Response:
    return present_validate_v1(scene, validate_geometry(scene))


@legacy_router.post(
    "/validate-gir",
    response_model=ValidationReport,
    include_in_schema=False,
)
def validate_gir_legacy(scene: GirScene) -> ValidationReport:
    return validate_geometry(scene)

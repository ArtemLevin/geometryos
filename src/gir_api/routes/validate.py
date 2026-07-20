from typing import Annotated

from fastapi import APIRouter, Depends

from gir_api.dependencies import get_executor
from gir_api.execution import TimedApplicationExecutor
from gir_api.models import ValidateGirV1Response
from gir_api.presenters import present_validate_v1
from gir_api.problem_details import problem_responses
from gir_application import validate_geometry
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport

v1_router = APIRouter()
legacy_router = APIRouter()

ExecutorDependency = Annotated[TimedApplicationExecutor, Depends(get_executor)]


@v1_router.post(
    "/validate-gir",
    response_model=ValidateGirV1Response,
    operation_id="geometryos_v1_validate_gir",
    tags=["Validation"],
    summary="Validate and canonicalize GIR",
    description=(
        "Accept canonical GIR 0.2 or the supported legacy GIR 0.1 marker, return "
        "canonical GIR 0.2, and report semantic validity without rendering."
    ),
    responses=problem_responses(422, 500, 504),
)
async def validate_gir_v1(
    scene: GirScene,
    executor: ExecutorDependency,
) -> ValidateGirV1Response:
    return present_validate_v1(scene, await executor.validate(scene))


@legacy_router.post(
    "/validate-gir",
    response_model=ValidationReport,
    include_in_schema=False,
)
async def validate_gir_legacy_http(
    scene: GirScene,
    executor: ExecutorDependency,
) -> ValidationReport:
    return await executor.validate(scene)


def validate_gir_legacy(scene: GirScene) -> ValidationReport:
    return validate_geometry(scene)


validate_gir = validate_gir_legacy
router = legacy_router

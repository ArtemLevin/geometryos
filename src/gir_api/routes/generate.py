from typing import Annotated

from fastapi import APIRouter, Depends

from gir_api.dependencies import enforce_input_limit, get_executor, get_runtime_settings
from gir_api.execution import TimedApplicationExecutor
from gir_api.models import (
    GenerateV1Request,
    GenerateV1Response,
    LegacyGenerateRequest,
    LegacyGenerateResponse,
)
from gir_api.presenters import present_generate_legacy, present_generate_v1
from gir_api.problem_details import problem_responses
from gir_api.settings import ApiSettings
from gir_application import (
    GenerateGeometryCommand,
    GenerationMode,
    OutputFormat,
    generate_geometry,
)

v1_router = APIRouter()
legacy_router = APIRouter()

ExecutorDependency = Annotated[TimedApplicationExecutor, Depends(get_executor)]
SettingsDependency = Annotated[ApiSettings, Depends(get_runtime_settings)]


@v1_router.post(
    "/generate",
    response_model=GenerateV1Response,
    operation_id="geometryos_v1_generate",
    tags=["Generation"],
    summary="Generate canonical geometry",
    description=(
        "Convert a supported natural-language construction into canonical GIR and "
        "optional SVG or TikZ output. Ambiguity and unsupported constructions are "
        "returned as typed HTTP 200 domain results."
    ),
    responses=problem_responses(413, 422, 500, 503, 504),
)
async def generate_v1(
    request: GenerateV1Request,
    executor: ExecutorDependency,
    settings: SettingsDependency,
) -> GenerateV1Response:
    enforce_input_limit(request.input, settings)
    result = await executor.generate(_to_command(request, GenerationMode.STRICT))
    return present_generate_v1(result)


@legacy_router.post(
    "/generate",
    response_model=LegacyGenerateResponse,
    include_in_schema=False,
)
async def generate_legacy_http(
    request: LegacyGenerateRequest,
    executor: ExecutorDependency,
    settings: SettingsDependency,
) -> LegacyGenerateResponse:
    enforce_input_limit(request.input, settings)
    result = await executor.generate(_to_command(request, GenerationMode(request.mode)))
    return present_generate_legacy(result)


def generate_legacy(request: LegacyGenerateRequest) -> LegacyGenerateResponse:
    result = generate_geometry(_to_command(request, GenerationMode(request.mode)))
    return present_generate_legacy(result)


def _to_command(
    request: GenerateV1Request | LegacyGenerateRequest,
    mode: GenerationMode,
) -> GenerateGeometryCommand:
    return GenerateGeometryCommand(
        input_type=request.input_type,
        input=request.input,
        outputs=frozenset(OutputFormat(item) for item in request.output),
        mode=mode,
    )


GenerateRequest = LegacyGenerateRequest
GenerateResponse = LegacyGenerateResponse
generate = generate_legacy
router = legacy_router

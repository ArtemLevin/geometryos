from fastapi import APIRouter

from gir_api.models import (
    GenerateV1Request,
    GenerateV1Response,
    LegacyGenerateRequest,
    LegacyGenerateResponse,
)
from gir_api.presenters import present_generate_legacy, present_generate_v1
from gir_application import (
    GenerateGeometryCommand,
    GenerationMode,
    OutputFormat,
    generate_geometry,
)

v1_router = APIRouter()
legacy_router = APIRouter()


@v1_router.post(
    "/generate",
    response_model=GenerateV1Response,
    operation_id="geometryos_v1_generate",
    tags=["Generation"],
)
def generate_v1(request: GenerateV1Request) -> GenerateV1Response:
    result = generate_geometry(
        GenerateGeometryCommand(
            input_type=request.input_type,
            input=request.input,
            outputs=frozenset(OutputFormat(item) for item in request.output),
            mode=GenerationMode.STRICT,
        )
    )
    return present_generate_v1(result)


@legacy_router.post(
    "/generate",
    response_model=LegacyGenerateResponse,
    include_in_schema=False,
)
def generate_legacy(request: LegacyGenerateRequest) -> LegacyGenerateResponse:
    result = generate_geometry(
        GenerateGeometryCommand(
            input_type=request.input_type,
            input=request.input,
            outputs=frozenset(OutputFormat(item) for item in request.output),
            mode=GenerationMode(request.mode),
        )
    )
    return present_generate_legacy(result)

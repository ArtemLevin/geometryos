from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from gir_api.dependencies import get_executor
from gir_api.errors import SemanticValidationError
from gir_api.execution import TimedApplicationExecutor
from gir_api.models import LegacyRenderResponse, RenderSvgV1Response, RenderTikzV1Response
from gir_api.presenters import present_render_v1
from gir_api.problem_details import problem_responses
from gir_application import (
    OutputFormat,
    RenderGeometryCommand,
    RenderGeometryResult,
    render_geometry,
)
from gir_core.models.scene import GirScene

v1_router = APIRouter()
legacy_router = APIRouter()

ExecutorDependency = Annotated[TimedApplicationExecutor, Depends(get_executor)]


@v1_router.post(
    "/render/svg",
    response_model=RenderSvgV1Response,
    operation_id="geometryos_v1_render_svg",
    tags=["Rendering"],
    responses=problem_responses(422, 500, 504),
)
async def render_svg_v1(
    scene: GirScene,
    executor: ExecutorDependency,
) -> RenderSvgV1Response:
    result = await executor.render_svg(_render_command(scene, OutputFormat.SVG))
    _require_valid(result)
    response = present_render_v1(result, OutputFormat.SVG)
    if not isinstance(response, RenderSvgV1Response):
        raise RuntimeError("SVG presenter returned an unexpected response type.")
    return response


@v1_router.post(
    "/render/tikz",
    response_model=RenderTikzV1Response,
    operation_id="geometryos_v1_render_tikz",
    tags=["Rendering"],
    responses=problem_responses(422, 500, 504),
)
async def render_tikz_v1(
    scene: GirScene,
    executor: ExecutorDependency,
) -> RenderTikzV1Response:
    result = await executor.render_tikz(_render_command(scene, OutputFormat.TIKZ))
    _require_valid(result)
    response = present_render_v1(result, OutputFormat.TIKZ)
    if not isinstance(response, RenderTikzV1Response):
        raise RuntimeError("TikZ presenter returned an unexpected response type.")
    return response


@legacy_router.post(
    "/render/svg",
    response_model=LegacyRenderResponse,
    include_in_schema=False,
)
async def render_svg_legacy_http(
    scene: GirScene,
    executor: ExecutorDependency,
) -> LegacyRenderResponse:
    result = await executor.render_svg(_render_command(scene, OutputFormat.SVG))
    _require_valid(result)
    content = result.artifacts.svg
    if content is None:
        raise RuntimeError("SVG renderer did not produce requested output.")
    return LegacyRenderResponse(content=content)


@legacy_router.post(
    "/render/tikz",
    response_model=LegacyRenderResponse,
    include_in_schema=False,
)
async def render_tikz_legacy_http(
    scene: GirScene,
    executor: ExecutorDependency,
) -> LegacyRenderResponse:
    result = await executor.render_tikz(_render_command(scene, OutputFormat.TIKZ))
    _require_valid(result)
    content = result.artifacts.tikz
    if content is None:
        raise RuntimeError("TikZ renderer did not produce requested output.")
    return LegacyRenderResponse(content=content)


def render_svg_legacy(scene: GirScene) -> LegacyRenderResponse:
    result = render_geometry(_render_command(scene, OutputFormat.SVG))
    _require_valid_sync(result)
    content = result.artifacts.svg
    if content is None:
        raise RuntimeError("SVG renderer did not produce requested output.")
    return LegacyRenderResponse(content=content)


def render_tikz_legacy(scene: GirScene) -> LegacyRenderResponse:
    result = render_geometry(_render_command(scene, OutputFormat.TIKZ))
    _require_valid_sync(result)
    content = result.artifacts.tikz
    if content is None:
        raise RuntimeError("TikZ renderer did not produce requested output.")
    return LegacyRenderResponse(content=content)


def _render_command(scene: GirScene, output: OutputFormat) -> RenderGeometryCommand:
    return RenderGeometryCommand(scene=scene, outputs=frozenset({output}))


def _require_valid(result: RenderGeometryResult) -> None:
    if not result.is_valid:
        raise SemanticValidationError(result.validation_report)


def _require_valid_sync(result: RenderGeometryResult) -> None:
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=result.validation_report.model_dump())


# Source-level aliases preserve pre-v1 imports for current Python consumers and tests.
RenderResponse = LegacyRenderResponse
render_svg_endpoint = render_svg_legacy
render_tikz_endpoint = render_tikz_legacy
router = legacy_router

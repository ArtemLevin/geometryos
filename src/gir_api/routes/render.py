from fastapi import APIRouter, HTTPException

from gir_api.models import (
    LegacyRenderResponse,
    RenderSvgV1Response,
    RenderTikzV1Response,
)
from gir_api.presenters import present_render_v1
from gir_application import (
    OutputFormat,
    RenderGeometryCommand,
    RenderGeometryResult,
    render_geometry,
)
from gir_core.models.scene import GirScene

v1_router = APIRouter()
legacy_router = APIRouter()


@v1_router.post(
    "/render/svg",
    response_model=RenderSvgV1Response,
    operation_id="geometryos_v1_render_svg",
    tags=["Rendering"],
)
def render_svg_v1(scene: GirScene) -> RenderSvgV1Response:
    result = _render(scene, OutputFormat.SVG)
    response = present_render_v1(result, OutputFormat.SVG)
    if not isinstance(response, RenderSvgV1Response):
        raise RuntimeError("SVG presenter returned an unexpected response type.")
    return response


@v1_router.post(
    "/render/tikz",
    response_model=RenderTikzV1Response,
    operation_id="geometryos_v1_render_tikz",
    tags=["Rendering"],
)
def render_tikz_v1(scene: GirScene) -> RenderTikzV1Response:
    result = _render(scene, OutputFormat.TIKZ)
    response = present_render_v1(result, OutputFormat.TIKZ)
    if not isinstance(response, RenderTikzV1Response):
        raise RuntimeError("TikZ presenter returned an unexpected response type.")
    return response


@legacy_router.post(
    "/render/svg",
    response_model=LegacyRenderResponse,
    include_in_schema=False,
)
def render_svg_legacy(scene: GirScene) -> LegacyRenderResponse:
    result = _render(scene, OutputFormat.SVG)
    content = result.artifacts.svg
    if content is None:
        raise RuntimeError("SVG renderer did not produce requested output.")
    return LegacyRenderResponse(content=content)


@legacy_router.post(
    "/render/tikz",
    response_model=LegacyRenderResponse,
    include_in_schema=False,
)
def render_tikz_legacy(scene: GirScene) -> LegacyRenderResponse:
    result = _render(scene, OutputFormat.TIKZ)
    content = result.artifacts.tikz
    if content is None:
        raise RuntimeError("TikZ renderer did not produce requested output.")
    return LegacyRenderResponse(content=content)


def _render(scene: GirScene, output: OutputFormat) -> RenderGeometryResult:
    result = render_geometry(RenderGeometryCommand(scene=scene, outputs=frozenset({output})))
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=result.validation_report.model_dump())
    return result


# Source-level aliases preserve pre-v1 imports for current Python consumers and tests.
RenderResponse = LegacyRenderResponse
render_svg_endpoint = render_svg_legacy
render_tikz_endpoint = render_tikz_legacy
router = legacy_router

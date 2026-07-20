from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gir_application import OutputFormat, RenderGeometryCommand, render_geometry
from gir_core.models.scene import GirScene

router = APIRouter()


class RenderResponse(BaseModel):
    content: str


@router.post("/render/svg")
def render_svg_endpoint(scene: GirScene) -> RenderResponse:
    return RenderResponse(content=_render_content(scene, OutputFormat.SVG))


@router.post("/render/tikz")
def render_tikz_endpoint(scene: GirScene) -> RenderResponse:
    return RenderResponse(content=_render_content(scene, OutputFormat.TIKZ))


def _render_content(scene: GirScene, output: OutputFormat) -> str:
    result = render_geometry(RenderGeometryCommand(scene=scene, outputs=frozenset({output})))
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=result.validation_report.model_dump())

    content = result.artifacts.svg if output is OutputFormat.SVG else result.artifacts.tikz
    if content is None:
        raise RuntimeError(f"Renderer did not produce requested output: {output.value}.")
    return content

from fastapi import APIRouter
from pydantic import BaseModel

from gir_core.models.scene import GirScene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz

router = APIRouter()


class RenderResponse(BaseModel):
    content: str


@router.post("/render/svg")
def render_svg_endpoint(scene: GirScene) -> RenderResponse:
    return RenderResponse(content=render_svg(scene))


@router.post("/render/tikz")
def render_tikz_endpoint(scene: GirScene) -> RenderResponse:
    return RenderResponse(content=render_tikz(scene))

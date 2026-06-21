from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gir_core.models.scene import GirScene
from gir_core.normalize import normalize_gir
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz

router = APIRouter()


class RenderResponse(BaseModel):
    content: str


@router.post("/render/svg")
def render_svg_endpoint(scene: GirScene) -> RenderResponse:
    valid_scene = _validated_normalized_scene(scene)
    return RenderResponse(content=render_svg(valid_scene))


@router.post("/render/tikz")
def render_tikz_endpoint(scene: GirScene) -> RenderResponse:
    valid_scene = _validated_normalized_scene(scene)
    return RenderResponse(content=render_tikz(valid_scene))


def _validated_normalized_scene(scene: GirScene) -> GirScene:
    draft_report = validate_scene(scene)
    if not draft_report.is_valid:
        raise HTTPException(status_code=422, detail=draft_report.model_dump())

    normalized_scene = normalize_gir(scene)
    normalized_report = validate_scene(normalized_scene)
    if not normalized_report.is_valid:
        raise HTTPException(status_code=422, detail=normalized_report.model_dump())

    return normalized_scene

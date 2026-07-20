from dataclasses import dataclass
from typing import Protocol

from gir_ai.text_to_gir.adapter import AiAdapterResult
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


class TextToGirPort(Protocol):
    def __call__(self, text: str, /) -> AiAdapterResult: ...


class ValidateScenePort(Protocol):
    def __call__(self, scene: GirScene, /) -> ValidationReport: ...


class NormalizeScenePort(Protocol):
    def __call__(self, scene: GirScene, /) -> GirScene: ...


class RenderScenePort(Protocol):
    def __call__(self, scene: GirScene, /) -> str: ...


@dataclass(frozen=True)
class GeometryPipelineDependencies:
    text_to_gir: TextToGirPort
    validate_scene: ValidateScenePort
    normalize_scene: NormalizeScenePort
    render_svg: RenderScenePort
    render_tikz: RenderScenePort

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gir_core.models.scene import GirScene


class AiAmbiguity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    options: list[str] = Field(default_factory=list)


class AiAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success", "needs_clarification", "error"]
    confidence: float
    gir: GirScene | None = None
    ambiguities: list[AiAmbiguity] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: str | None = None


def text_to_gir(text: str) -> AiAdapterResult:
    # Design note: the MVP adapter is intentionally rule-based. This keeps tests
    # deterministic and prevents accidental Text -> LLM -> Render shortcuts before
    # the GIR contract and benchmark suite are strong enough for real LLM output.
    normalized = text.lower().replace("ё", "е")
    if "треугольник abc" in normalized and "высот" in normalized:
        return AiAdapterResult(
            status="success",
            confidence=0.9,
            gir=_altitude_scene(),
            explanation="Rule-based altitude MVP case.",
        )
    if "треугольник abc" in normalized and "медиан" in normalized:
        return AiAdapterResult(
            status="success",
            confidence=0.88,
            gir=_median_scene(),
            explanation="Rule-based median MVP case.",
        )
    if "биссектрис" in normalized:
        return AiAdapterResult(
            status="needs_clarification",
            confidence=0.4,
            ambiguities=[
                AiAmbiguity(
                    code="missing_angle",
                    message="Не указано, биссектрису какого угла нужно построить.",
                    options=["angle_A", "angle_B", "angle_C"],
                )
            ],
            explanation="Bisector request lacks angle target.",
        )
    return AiAdapterResult(
        status="error",
        confidence=0.0,
        warnings=["No rule matched input."],
        explanation="Skeleton adapter supports only MVP benchmark prompts.",
    )


def _base_objects(extra: list[dict[str, object]]) -> list[dict[str, object]]:
    # Design note: object ids are stable human-readable labels in the skeleton so
    # benchmark diffs stay understandable; a future normalizer can add canonical ids.
    return [
        {"id": "A", "type": "point", "label": "A"},
        {"id": "B", "type": "point", "label": "B"},
        {"id": "C", "type": "point", "label": "C"},
        {"id": "BC", "type": "segment", "points": ["B", "C"]},
        {"id": "ABC", "type": "triangle", "vertices": ["A", "B", "C"]},
        *extra,
    ]


def _altitude_scene() -> GirScene:
    return GirScene.model_validate(
        {
            "version": "0.1",
            "scene_type": "2d",
            "objects": _base_objects(
                [
                    {"id": "H", "type": "point", "label": "H"},
                    {"id": "AH", "type": "segment", "points": ["A", "H"]},
                ]
            ),
            "constraints": [
                {"id": "c_noncol_abc", "type": "non_collinear", "points": ["A", "B", "C"]},
                {"id": "c_h_on_bc", "type": "belongs_to", "point": "H", "object": "BC"},
                {"id": "c_ah_perp_bc", "type": "perpendicular", "objects": ["AH", "BC"]},
                {
                    "id": "c_altitude_a_bc",
                    "type": "altitude",
                    "from_point": "A",
                    "to_object": "BC",
                    "foot": "H",
                    "segment": "AH",
                },
            ],
            "construction_steps": [
                {
                    "id": "s1",
                    "action": "create_triangle",
                    "objects": ["A", "B", "C", "BC", "ABC"],
                    "constraints": ["c_noncol_abc"],
                },
                {
                    "id": "s2",
                    "action": "draw_altitude",
                    "objects": ["H", "AH"],
                    "constraints": ["c_h_on_bc", "c_ah_perp_bc", "c_altitude_a_bc"],
                },
            ],
            "metadata": {"source": "rule_based_stub"},
        }
    )


def _median_scene() -> GirScene:
    return GirScene.model_validate(
        {
            "version": "0.1",
            "scene_type": "2d",
            "objects": _base_objects(
                [
                    {"id": "M", "type": "point", "label": "M"},
                    {"id": "AM", "type": "segment", "points": ["A", "M"]},
                ]
            ),
            "constraints": [
                {"id": "c_noncol_abc", "type": "non_collinear", "points": ["A", "B", "C"]},
                {"id": "c_mid_m_bc", "type": "midpoint", "point": "M", "object": "BC"},
                {
                    "id": "c_median_a_bc",
                    "type": "median",
                    "from_point": "A",
                    "to_object": "BC",
                    "midpoint": "M",
                    "segment": "AM",
                },
            ],
            "construction_steps": [
                {
                    "id": "s1",
                    "action": "create_triangle",
                    "objects": ["A", "B", "C", "BC", "ABC"],
                    "constraints": ["c_noncol_abc"],
                },
                {
                    "id": "s2",
                    "action": "draw_median",
                    "objects": ["M", "AM"],
                    "constraints": ["c_mid_m_bc", "c_median_a_bc"],
                },
            ],
            "metadata": {"source": "rule_based_stub"},
        }
    )

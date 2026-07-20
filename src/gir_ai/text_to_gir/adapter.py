from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gir_core.models.scene import GirScene
from gir_core.versioning import GIR_SCHEMA_VERSION


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
    normalized = _normalize_text(text)
    if "треугольник abc" not in normalized:
        return _unsupported_result()

    if "биссектрис" in normalized and not _mentions_angle_a(normalized):
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
    if "биссектрис" in normalized and _mentions_angle_a(normalized):
        return AiAdapterResult(
            status="success",
            confidence=0.86,
            gir=_angle_bisector_scene(),
            explanation="Rule-based angle bisector MVP case.",
        )
    if "высот" in normalized:
        return AiAdapterResult(
            status="success",
            confidence=0.9,
            gir=_altitude_scene(),
            explanation="Rule-based altitude MVP case.",
        )
    if "медиан" in normalized:
        return AiAdapterResult(
            status="success",
            confidence=0.88,
            gir=_median_scene(),
            explanation="Rule-based median MVP case.",
        )
    if "середин" in normalized:
        return AiAdapterResult(
            status="success",
            confidence=0.86,
            gir=_midpoint_scene(),
            explanation="Rule-based midpoint MVP case.",
        )
    if _is_triangle_only(normalized):
        return AiAdapterResult(
            status="success",
            confidence=0.86,
            gir=_triangle_scene(),
            explanation="Rule-based triangle MVP case.",
        )

    return _unsupported_result()


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").strip().split())


def _mentions_angle_a(text: str) -> bool:
    return "угла a" in text or "угол a" in text


def _is_triangle_only(text: str) -> bool:
    return text.rstrip(" .") == "постройте треугольник abc"


def _unsupported_result() -> AiAdapterResult:
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


def _triangle_scene() -> GirScene:
    return GirScene.model_validate(
        {
            "schema_version": GIR_SCHEMA_VERSION,
            "scene_type": "2d",
            "objects": _base_objects(
                [
                    {"id": "AB", "type": "segment", "points": ["A", "B"]},
                    {"id": "CA", "type": "segment", "points": ["C", "A"]},
                ]
            ),
            "constraints": [
                {"id": "c_noncol_abc", "type": "non_collinear", "points": ["A", "B", "C"]}
            ],
            "construction_steps": [
                {
                    "id": "s1",
                    "action": "create_triangle",
                    "objects": ["A", "B", "C", "AB", "BC", "CA", "ABC"],
                    "constraints": ["c_noncol_abc"],
                }
            ],
            "metadata": {"source": "rule_based_stub"},
        }
    )


def _midpoint_scene() -> GirScene:
    return GirScene.model_validate(
        {
            "schema_version": GIR_SCHEMA_VERSION,
            "scene_type": "2d",
            "objects": _base_objects(
                [
                    {"id": "AB", "type": "segment", "points": ["A", "B"]},
                    {"id": "CA", "type": "segment", "points": ["C", "A"]},
                    {"id": "M", "type": "point", "label": "M"},
                ]
            ),
            "constraints": [
                {"id": "c_noncol_abc", "type": "non_collinear", "points": ["A", "B", "C"]},
                {"id": "c_mid_m_bc", "type": "midpoint", "point": "M", "object": "BC"},
            ],
            "construction_steps": [
                {
                    "id": "s1",
                    "action": "create_triangle",
                    "objects": ["A", "B", "C", "AB", "BC", "CA", "ABC"],
                    "constraints": ["c_noncol_abc"],
                },
                {
                    "id": "s2",
                    "action": "construct_midpoint",
                    "objects": ["M"],
                    "constraints": ["c_mid_m_bc"],
                },
            ],
            "metadata": {"source": "rule_based_stub"},
        }
    )


def _angle_bisector_scene() -> GirScene:
    return GirScene.model_validate(
        {
            "schema_version": GIR_SCHEMA_VERSION,
            "scene_type": "2d",
            "objects": _base_objects(
                [
                    {"id": "AB", "type": "segment", "points": ["A", "B"]},
                    {"id": "CA", "type": "segment", "points": ["C", "A"]},
                    {"id": "D", "type": "point", "label": "D"},
                    {"id": "angle_BAC", "type": "angle", "points": ["B", "A", "C"]},
                    {"id": "bisector_A", "type": "ray", "start": "A", "through": "D"},
                ]
            ),
            "constraints": [
                {"id": "c_noncol_abc", "type": "non_collinear", "points": ["A", "B", "C"]},
                {
                    "id": "angle_bisector_A",
                    "type": "angle_bisector",
                    "angle": "angle_BAC",
                    "ray": "bisector_A",
                },
            ],
            "construction_steps": [
                {
                    "id": "s1",
                    "action": "create_triangle",
                    "objects": ["A", "B", "C", "AB", "BC", "CA", "ABC"],
                    "constraints": ["c_noncol_abc"],
                },
                {
                    "id": "s2",
                    "action": "construct_angle_bisector",
                    "objects": ["D", "angle_BAC", "bisector_A"],
                    "constraints": ["angle_bisector_A"],
                },
            ],
            "metadata": {"source": "rule_based_stub"},
        }
    )


def _altitude_scene() -> GirScene:
    return GirScene.model_validate(
        {
            "schema_version": GIR_SCHEMA_VERSION,
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
            "schema_version": GIR_SCHEMA_VERSION,
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

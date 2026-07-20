from __future__ import annotations

from collections.abc import Generator
from copy import deepcopy
from typing import Any

import pytest

from gir_api.main import app


@pytest.fixture
def client() -> Generator[Any, None, None]:
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_altitude_payload() -> dict[str, Any]:
    return {
        "schema_version": "0.2.0",
        "scene_type": "2d",
        "objects": [
            {"id": "A", "type": "point", "label": "A"},
            {"id": "B", "type": "point", "label": "B"},
            {"id": "C", "type": "point", "label": "C"},
            {"id": "H", "type": "point", "label": "H"},
            {"id": "BC", "type": "segment", "points": ["B", "C"]},
            {"id": "AH", "type": "segment", "points": ["A", "H"]},
            {"id": "ABC", "type": "triangle", "vertices": ["A", "B", "C"]},
        ],
        "constraints": [
            {
                "id": "c_noncol_abc",
                "type": "non_collinear",
                "points": ["A", "B", "C"],
            },
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
                "id": "step_construct_triangle",
                "action": "construct_triangle",
                "objects": ["A", "B", "C", "BC", "ABC"],
                "constraints": ["c_noncol_abc"],
                "reason": "Construct triangle ABC.",
            },
            {
                "id": "step_construct_altitude",
                "action": "construct_altitude",
                "objects": ["H", "AH"],
                "constraints": ["c_altitude_a_bc"],
                "reason": "Construct altitude from A to BC.",
            },
        ],
        "metadata": {},
    }


@pytest.fixture
def semantic_invalid_altitude_payload(
    valid_altitude_payload: dict[str, Any],
) -> dict[str, Any]:
    payload = deepcopy(valid_altitude_payload)
    payload["constraints"][1]["foot"] = "MISSING_POINT"
    return payload

from __future__ import annotations

from collections.abc import Callable, Generator
from copy import deepcopy
from typing import Any

import pytest
from fastapi import FastAPI

from gir_api.execution import TimedApplicationExecutor
from gir_api.main import create_app
from gir_api.readiness import ServiceLifecycle
from gir_api.settings import ApiSettings


@pytest.fixture
def app_factory() -> Callable[..., FastAPI]:
    def factory(
        *,
        settings: ApiSettings | None = None,
        executor: TimedApplicationExecutor | None = None,
        lifecycle: ServiceLifecycle | None = None,
    ) -> FastAPI:
        return create_app(
            settings=settings or ApiSettings(),
            executor=executor,
            lifecycle=lifecycle,
        )

    return factory


@pytest.fixture
def client(app_factory: Callable[..., FastAPI]) -> Generator[Any, None, None]:
    from fastapi.testclient import TestClient

    with TestClient(app_factory()) as test_client:
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

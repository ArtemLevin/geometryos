from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "contracts" / "tutorboard" / "v1"


@pytest.fixture
def contract_json() -> Any:
    def load(name: str) -> dict[str, Any]:
        value = json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8"))
        assert isinstance(value, dict), name
        return value

    return load

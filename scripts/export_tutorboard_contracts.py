from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gir_api.execution import TimedApplicationExecutor  # noqa: E402
from gir_api.main import create_app  # noqa: E402
from gir_api.openapi_examples import ALTITUDE_GIR_EXAMPLE  # noqa: E402
from gir_api.settings import ApiSettings  # noqa: E402
from gir_application import GenerateGeometryCommand, generate_geometry  # noqa: E402

CONTRACT_ROOT = ROOT / "contracts" / "tutorboard" / "v1"
REQUEST_ID = "tutorboard-contract"
HEADERS = {"X-Request-ID": REQUEST_ID}
GENERATE_SUCCESS_REQUEST = {
    "input_type": "text",
    "input": "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
    "output": ["svg"],
    "mode": "strict",
}
GENERATE_AMBIGUITY_REQUEST = {
    **GENERATE_SUCCESS_REQUEST,
    "input": "Постройте треугольник ABC. Проведите биссектрису.",
}
GENERATE_UNSUPPORTED_REQUEST = {
    **GENERATE_SUCCESS_REQUEST,
    "input": "Постройте невозможную конструкцию с магическим квадратом.",
}
GENERATE_INVALID_REQUEST = {**GENERATE_SUCCESS_REQUEST, "mode": "draft"}
LEGACY_ALTITUDE_GIR = {
    "version": "0.1",
    **{
        key: value
        for key, value in ALTITUDE_GIR_EXAMPLE.items()
        if key != "schema_version"
    },
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _response_json(response: Any, expected_status: int) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise RuntimeError(
            f"Unexpected status {response.status_code}, expected {expected_status}: "
            f"{response.text}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Contract response must be a JSON object.")
    return payload


def _case(identifier: str, method: str, path: str, status: int) -> dict[str, object]:
    return {
        "id": identifier,
        "method": method,
        "path": path,
        "request": f"{identifier}.request.json",
        "response": f"{identifier}.response.json",
        "status": status,
        "media_type": "application/json",
        "mode": "executable",
    }


def build_contract_documents() -> dict[str, object]:
    documents: dict[str, object] = {
        "generate-success.request.json": GENERATE_SUCCESS_REQUEST,
        "generate-ambiguity.request.json": GENERATE_AMBIGUITY_REQUEST,
        "generate-unsupported.request.json": GENERATE_UNSUPPORTED_REQUEST,
        "generate-invalid.request.json": GENERATE_INVALID_REQUEST,
        "validate-canonical.request.json": ALTITUDE_GIR_EXAMPLE,
        "validate-legacy.request.json": LEGACY_ALTITUDE_GIR,
        "render-svg.request.json": ALTITUDE_GIR_EXAMPLE,
        "render-tikz.request.json": ALTITUDE_GIR_EXAMPLE,
    }
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        documents["generate-success.response.json"] = _response_json(
            client.post(
                "/api/v1/generate",
                json=GENERATE_SUCCESS_REQUEST,
                headers=HEADERS,
            ),
            200,
        )
        documents["generate-ambiguity.response.json"] = _response_json(
            client.post(
                "/api/v1/generate",
                json=GENERATE_AMBIGUITY_REQUEST,
                headers=HEADERS,
            ),
            200,
        )
        documents["generate-unsupported.response.json"] = _response_json(
            client.post(
                "/api/v1/generate",
                json=GENERATE_UNSUPPORTED_REQUEST,
                headers=HEADERS,
            ),
            200,
        )
        documents["validate-canonical.response.json"] = _response_json(
            client.post(
                "/api/v1/validate-gir",
                json=ALTITUDE_GIR_EXAMPLE,
                headers=HEADERS,
            ),
            200,
        )
        documents["validate-legacy.response.json"] = _response_json(
            client.post(
                "/api/v1/validate-gir",
                json=LEGACY_ALTITUDE_GIR,
                headers=HEADERS,
            ),
            200,
        )
        documents["render-svg.response.json"] = _response_json(
            client.post(
                "/api/v1/render/svg",
                json=ALTITUDE_GIR_EXAMPLE,
                headers=HEADERS,
            ),
            200,
        )
        documents["render-tikz.response.json"] = _response_json(
            client.post(
                "/api/v1/render/tikz",
                json=ALTITUDE_GIR_EXAMPLE,
                headers=HEADERS,
            ),
            200,
        )
        documents["request-validation.problem.json"] = _response_json(
            client.post(
                "/api/v1/generate",
                json=GENERATE_INVALID_REQUEST,
                headers=HEADERS,
            ),
            422,
        )
        documents["health.response.json"] = _response_json(
            client.get("/health", headers=HEADERS),
            200,
        )
        documents["readiness.response.json"] = _response_json(
            client.get("/ready", headers=HEADERS),
            200,
        )

    timeout_settings = ApiSettings(generate_timeout_seconds=0.001)

    def slow_generate(command: GenerateGeometryCommand) -> Any:
        time.sleep(0.05)
        return generate_geometry(command)

    timeout_executor = TimedApplicationExecutor(
        settings=timeout_settings,
        generate_fn=slow_generate,
    )
    with TestClient(
        create_app(settings=timeout_settings, executor=timeout_executor),
        raise_server_exceptions=False,
    ) as client:
        documents["operation-timeout.problem.json"] = _response_json(
            client.post(
                "/api/v1/generate",
                json=GENERATE_SUCCESS_REQUEST,
                headers=HEADERS,
            ),
            504,
        )

    error_settings = ApiSettings()

    def failing_generate(command: GenerateGeometryCommand) -> Any:
        del command
        raise RuntimeError("SECRET INTERNAL FAILURE")

    error_executor = TimedApplicationExecutor(
        settings=error_settings,
        generate_fn=failing_generate,
    )
    with TestClient(
        create_app(settings=error_settings, executor=error_executor),
        raise_server_exceptions=False,
    ) as client:
        documents["internal-error.problem.json"] = _response_json(
            client.post(
                "/api/v1/generate",
                json=GENERATE_SUCCESS_REQUEST,
                headers=HEADERS,
            ),
            500,
        )

    cases = [
        _case("generate-success", "POST", "/api/v1/generate", 200),
        _case("generate-ambiguity", "POST", "/api/v1/generate", 200),
        _case("generate-unsupported", "POST", "/api/v1/generate", 200),
        _case("validate-canonical", "POST", "/api/v1/validate-gir", 200),
        _case("validate-legacy", "POST", "/api/v1/validate-gir", 200),
        _case("render-svg", "POST", "/api/v1/render/svg", 200),
        _case("render-tikz", "POST", "/api/v1/render/tikz", 200),
        {
            "id": "request-validation",
            "method": "POST",
            "path": "/api/v1/generate",
            "request": "generate-invalid.request.json",
            "response": "request-validation.problem.json",
            "status": 422,
            "media_type": "application/problem+json",
            "mode": "executable",
        },
        {
            "id": "operation-timeout",
            "method": "POST",
            "path": "/api/v1/generate",
            "request": "generate-success.request.json",
            "response": "operation-timeout.problem.json",
            "status": 504,
            "media_type": "application/problem+json",
            "mode": "injected_executor",
        },
        {
            "id": "internal-error",
            "method": "POST",
            "path": "/api/v1/generate",
            "request": "generate-success.request.json",
            "response": "internal-error.problem.json",
            "status": 500,
            "media_type": "application/problem+json",
            "mode": "injected_executor",
        },
    ]
    documents["manifest.json"] = {
        "contract": "tutorboard/v1",
        "openapi": "../../../schemas/openapi.v1.json",
        "cases": cases,
    }
    return documents


def write_contracts(output: Path = CONTRACT_ROOT) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, document in build_contract_documents().items():
        (output / name).write_text(_canonical_json(document), encoding="utf-8")


def contracts_are_fresh(output: Path = CONTRACT_ROOT) -> bool:
    for name, document in build_contract_documents().items():
        path = output / name
        if not path.exists() or path.read_text(encoding="utf-8") != _canonical_json(
            document
        ):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Export TutorBoard v1 contract fixtures.")
    parser.add_argument("--output", type=Path, default=CONTRACT_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        if contracts_are_fresh(args.output):
            print(f"TutorBoard v1 contracts are up to date: {args.output}")
            return 0
        print(
            f"TutorBoard v1 contracts are missing or stale: {args.output}",
            file=sys.stderr,
        )
        print(
            "Run: uv run python scripts/export_tutorboard_contracts.py",
            file=sys.stderr,
        )
        return 1
    write_contracts(args.output)
    print(f"Exported TutorBoard v1 contracts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

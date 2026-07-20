from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from gir_api.openapi_examples import READINESS_RESPONSE_EXAMPLE

_REQUIRED_EXECUTOR_METHODS = ("generate", "validate", "render_svg", "render_tikz")


class LifecyclePhase(StrEnum):
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    FAILED = "failed"


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class ReadinessCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: CheckStatus


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [READINESS_RESPONSE_EXAMPLE]},
    )

    status: Literal["ready", "not_ready"]
    checks: list[ReadinessCheck]


class ServiceLifecycle:
    def __init__(self) -> None:
        self._phase = LifecyclePhase.STARTING

    @property
    def phase(self) -> LifecyclePhase:
        return self._phase

    def mark_ready(self) -> None:
        self._phase = LifecyclePhase.READY

    def mark_stopping(self) -> None:
        self._phase = LifecyclePhase.STOPPING

    def mark_failed(self) -> None:
        self._phase = LifecyclePhase.FAILED


def readiness_snapshot(application: FastAPI) -> ReadinessResponse:
    lifecycle = getattr(application.state, "lifecycle", None)
    settings = getattr(application.state, "settings", None)
    executor = getattr(application.state, "application_executor", None)

    checks = [
        ReadinessCheck(
            name="lifecycle",
            status=(
                CheckStatus.PASS
                if isinstance(lifecycle, ServiceLifecycle)
                and lifecycle.phase is LifecyclePhase.READY
                else CheckStatus.FAIL
            ),
        ),
        ReadinessCheck(
            name="settings",
            status=CheckStatus.PASS if settings is not None else CheckStatus.FAIL,
        ),
        ReadinessCheck(
            name="executor",
            status=(
                CheckStatus.PASS
                if executor is not None
                and all(
                    callable(getattr(executor, name, None)) for name in _REQUIRED_EXECUTOR_METHODS
                )
                else CheckStatus.FAIL
            ),
        ),
    ]
    ready = all(check.status is CheckStatus.PASS for check in checks)
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        checks=checks,
    )


def validate_runtime_state(application: FastAPI) -> None:
    snapshot = readiness_snapshot(application)
    failed = [
        check.name
        for check in snapshot.checks
        if check.name != "lifecycle" and check.status is CheckStatus.FAIL
    ]
    if failed:
        raise RuntimeError("Runtime components are not ready: " + ", ".join(failed))


@asynccontextmanager
async def service_lifespan(application: FastAPI) -> AsyncIterator[None]:
    lifecycle = application.state.lifecycle
    try:
        validate_runtime_state(application)
        lifecycle.mark_ready()
    except Exception:
        lifecycle.mark_failed()
        raise

    try:
        yield
    finally:
        lifecycle.mark_stopping()


async def ready(request: Request) -> JSONResponse:
    snapshot = readiness_snapshot(request.app)
    status_code = 200 if snapshot.status == "ready" else 503
    return JSONResponse(
        status_code=status_code,
        content=snapshot.model_dump(mode="json"),
        headers={"Cache-Control": "no-store"},
    )

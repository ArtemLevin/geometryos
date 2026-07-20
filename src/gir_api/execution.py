from collections.abc import Callable
from functools import partial
from typing import TypeVar

import anyio

from gir_api.context import ApiOperation
from gir_api.errors import OperationTimeoutError
from gir_api.settings import ApiSettings
from gir_application import (
    GenerateGeometryCommand,
    GenerateGeometryResult,
    RenderGeometryCommand,
    RenderGeometryResult,
    generate_geometry,
    render_geometry,
    validate_geometry,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

GenerateFunction = Callable[[GenerateGeometryCommand], GenerateGeometryResult]
ValidateFunction = Callable[[GirScene], ValidationReport]
RenderFunction = Callable[[RenderGeometryCommand], RenderGeometryResult]


class TimedApplicationExecutor:
    def __init__(
        self,
        *,
        settings: ApiSettings,
        generate_fn: GenerateFunction = generate_geometry,
        validate_fn: ValidateFunction = validate_geometry,
        render_fn: RenderFunction = render_geometry,
    ) -> None:
        self._settings = settings
        self._generate_fn = generate_fn
        self._validate_fn = validate_fn
        self._render_fn = render_fn

    async def generate(self, command: GenerateGeometryCommand) -> GenerateGeometryResult:
        return await self._run(
            self._generate_fn,
            command,
            operation=ApiOperation.GENERATE,
            timeout_seconds=self._settings.generate_timeout_seconds,
        )

    async def validate(self, scene: GirScene) -> ValidationReport:
        return await self._run(
            self._validate_fn,
            scene,
            operation=ApiOperation.VALIDATE_GIR,
            timeout_seconds=self._settings.validate_timeout_seconds,
        )

    async def render_svg(self, command: RenderGeometryCommand) -> RenderGeometryResult:
        return await self._run(
            self._render_fn,
            command,
            operation=ApiOperation.RENDER_SVG,
            timeout_seconds=self._settings.render_timeout_seconds,
        )

    async def render_tikz(self, command: RenderGeometryCommand) -> RenderGeometryResult:
        return await self._run(
            self._render_fn,
            command,
            operation=ApiOperation.RENDER_TIKZ,
            timeout_seconds=self._settings.render_timeout_seconds,
        )

    async def _run(
        self,
        function: Callable[[InputT], OutputT],
        argument: InputT,
        *,
        operation: ApiOperation,
        timeout_seconds: float,
    ) -> OutputT:
        call: Callable[[], OutputT] = partial(function, argument)
        try:
            with anyio.fail_after(timeout_seconds):
                return await anyio.to_thread.run_sync(call, abandon_on_cancel=True)
        except TimeoutError as exc:
            raise OperationTimeoutError(
                operation=operation,
                timeout_seconds=timeout_seconds,
            ) from exc

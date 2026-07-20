from collections.abc import Iterable
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from gir_api.constants import INTERNAL_ERROR_CODE_HEADER, PROBLEM_MEDIA_TYPE


class StrictProblemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProblemError(StrictProblemModel):
    code: str
    message: str
    location: list[str | int] = Field(default_factory=list)


class ProblemDetail(StrictProblemModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str
    errors: list[ProblemError] = Field(default_factory=list)


def problem_response(
    *,
    status: int,
    problem_type: str,
    title: str,
    detail: str,
    instance: str,
    code: str,
    request_id: str,
    errors: Iterable[ProblemError] = (),
    no_store: bool = False,
) -> JSONResponse:
    headers = {INTERNAL_ERROR_CODE_HEADER: code}
    if no_store:
        headers["Cache-Control"] = "no-store"
    problem = ProblemDetail(
        type=problem_type,
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        code=code,
        request_id=request_id,
        errors=list(errors),
    )
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def problem_responses(*statuses: int) -> dict[int, dict[str, Any]]:
    descriptions = {
        413: "Request exceeds the configured operational limit.",
        422: "Request or GIR validation failed.",
        500: "Unexpected internal error.",
        504: "Operation exceeded its configured time limit.",
    }
    schema = ProblemDetail.model_json_schema()
    return {
        status: {
            "description": descriptions[status],
            "content": {PROBLEM_MEDIA_TYPE: {"schema": schema}},
        }
        for status in statuses
    }


def is_v1_path(path: str) -> bool:
    return path == "/api/v1" or path.startswith("/api/v1/")

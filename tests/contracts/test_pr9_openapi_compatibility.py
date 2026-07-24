from copy import deepcopy

from gir_api.openapi_compatibility import CompatibilitySeverity, compare_openapi_documents
from gir_api.openapi_contract import build_openapi_document


def _breaking_messages(candidate: dict[str, object]) -> list[str]:
    baseline = build_openapi_document()
    return [
        issue.message
        for issue in compare_openapi_documents(baseline, candidate)
        if issue.severity is CompatibilitySeverity.BREAKING
    ]


def test_request_correlation_parameter_removal_is_breaking() -> None:
    candidate = deepcopy(build_openapi_document())
    candidate["paths"]["/api/v1/generate"]["post"]["parameters"] = []
    assert "parameter was removed" in _breaking_messages(candidate)


def test_response_correlation_header_removal_is_breaking() -> None:
    candidate = deepcopy(build_openapi_document())
    del candidate["paths"]["/api/v1/generate"]["post"]["responses"]["200"]["headers"][
        "X-Request-ID"
    ]
    assert "response header was removed" in _breaking_messages(candidate)


def test_new_response_status_requires_review() -> None:
    candidate = build_openapi_document()
    baseline = deepcopy(candidate)
    del baseline["paths"]["/api/v1/generate"]["post"]["responses"]["503"]
    issues = compare_openapi_documents(baseline, candidate)
    assert any(
        issue.severity is CompatibilitySeverity.REVIEW
        and issue.message == "response status was added"
        for issue in issues
    )

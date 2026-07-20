from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CompatibilitySeverity(StrEnum):
    BREAKING = "breaking"
    REVIEW = "review"


@dataclass(frozen=True)
class CompatibilityIssue:
    severity: CompatibilitySeverity
    location: str
    message: str


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def compare_openapi_documents(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> list[CompatibilityIssue]:
    issues: list[CompatibilityIssue] = []
    baseline_paths = baseline.get("paths", {})
    candidate_paths = candidate.get("paths", {})
    for path, baseline_path_item in baseline_paths.items():
        candidate_path_item = candidate_paths.get(path)
        if not isinstance(candidate_path_item, dict):
            issues.append(_breaking(path, "endpoint was removed"))
            continue
        for method, baseline_operation in baseline_path_item.items():
            if method not in HTTP_METHODS or not isinstance(baseline_operation, dict):
                continue
            candidate_operation = candidate_path_item.get(method)
            location = f"{method.upper()} {path}"
            if not isinstance(candidate_operation, dict):
                issues.append(_breaking(location, "operation was removed"))
                continue
            if baseline_operation.get("operationId") != candidate_operation.get("operationId"):
                issues.append(_breaking(location, "operationId changed"))
            _compare_request_body(
                baseline_operation.get("requestBody"),
                candidate_operation.get("requestBody"),
                baseline,
                candidate,
                location,
                issues,
            )
            _compare_responses(
                baseline_operation.get("responses", {}),
                candidate_operation.get("responses", {}),
                baseline,
                candidate,
                location,
                issues,
            )
    return issues


def _compare_request_body(
    baseline_body: object,
    candidate_body: object,
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    issues: list[CompatibilityIssue],
) -> None:
    if not isinstance(baseline_body, dict):
        return
    if not isinstance(candidate_body, dict):
        issues.append(_breaking(location, "request body was removed"))
        return
    if not baseline_body.get("required", False) and candidate_body.get("required", False):
        issues.append(_breaking(location, "request body became required"))
    _compare_content(
        baseline_body.get("content", {}),
        candidate_body.get("content", {}),
        baseline_document,
        candidate_document,
        f"{location} request",
        "request",
        issues,
    )


def _compare_responses(
    baseline_responses: object,
    candidate_responses: object,
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    issues: list[CompatibilityIssue],
) -> None:
    if not isinstance(baseline_responses, dict) or not isinstance(candidate_responses, dict):
        issues.append(_breaking(location, "responses disappeared"))
        return
    for status, baseline_response in baseline_responses.items():
        candidate_response = candidate_responses.get(status)
        status_location = f"{location} response {status}"
        if not isinstance(candidate_response, dict):
            issues.append(_breaking(status_location, "response disappeared"))
            continue
        if isinstance(baseline_response, dict):
            _compare_content(
                baseline_response.get("content", {}),
                candidate_response.get("content", {}),
                baseline_document,
                candidate_document,
                status_location,
                "response",
                issues,
            )


def _compare_content(
    baseline_content: object,
    candidate_content: object,
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    direction: str,
    issues: list[CompatibilityIssue],
) -> None:
    if not isinstance(baseline_content, dict):
        return
    if not isinstance(candidate_content, dict):
        issues.append(_breaking(location, "response/request content disappeared"))
        return
    for media_type, baseline_media in baseline_content.items():
        candidate_media = candidate_content.get(media_type)
        media_location = f"{location} {media_type}"
        if not isinstance(candidate_media, dict):
            issues.append(_breaking(media_location, "media type was removed"))
            continue
        if isinstance(baseline_media, dict):
            _compare_schema(
                baseline_media.get("schema", {}),
                candidate_media.get("schema", {}),
                baseline_document,
                candidate_document,
                media_location,
                direction,
                issues,
                set(),
            )


def _compare_schema(
    baseline_schema: object,
    candidate_schema: object,
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    direction: str,
    issues: list[CompatibilityIssue],
    seen: set[tuple[str, str]],
) -> None:
    if not isinstance(baseline_schema, dict) or not isinstance(candidate_schema, dict):
        if baseline_schema != candidate_schema:
            issues.append(_breaking(location, "schema changed"))
        return

    pair = (
        str(baseline_schema.get("$ref", id(baseline_schema))),
        str(candidate_schema.get("$ref", id(candidate_schema))),
    )
    if pair in seen:
        return
    seen.add(pair)
    baseline_schema = _resolve_schema(baseline_schema, baseline_document)
    candidate_schema = _resolve_schema(candidate_schema, candidate_document)

    baseline_type = baseline_schema.get("type")
    candidate_type = candidate_schema.get("type")
    if baseline_type != candidate_type and baseline_type is not None:
        issues.append(
            _breaking(location, f"type changed from {baseline_type!r} to {candidate_type!r}")
        )

    baseline_enum = baseline_schema.get("enum")
    candidate_enum = candidate_schema.get("enum")
    if isinstance(baseline_enum, list) and isinstance(candidate_enum, list):
        removed = [value for value in baseline_enum if value not in candidate_enum]
        added = [value for value in candidate_enum if value not in baseline_enum]
        if removed:
            issues.append(_breaking(location, f"enum values removed: {removed!r}"))
        if added:
            issues.append(_review(location, f"enum values added: {added!r}"))
    elif isinstance(baseline_enum, list) and candidate_enum is None:
        issues.append(_review(location, "enum constraint was removed"))

    _compare_limits(baseline_schema, candidate_schema, location, direction, issues)
    _compare_compositions(
        baseline_schema,
        candidate_schema,
        baseline_document,
        candidate_document,
        location,
        issues,
    )

    baseline_properties = baseline_schema.get("properties", {})
    candidate_properties = candidate_schema.get("properties", {})
    if isinstance(baseline_properties, dict) and isinstance(candidate_properties, dict):
        baseline_required = set(baseline_schema.get("required", []))
        candidate_required = set(candidate_schema.get("required", []))
        if direction == "request":
            for name in sorted(candidate_required - baseline_required):
                issues.append(_breaking(f"{location}.{name}", "new required request field"))
        else:
            for name in sorted(baseline_required - candidate_required):
                issues.append(
                    _breaking(f"{location}.{name}", "required response field became optional")
                )
            for name in sorted(candidate_required - baseline_required):
                issues.append(_review(f"{location}.{name}", "new required response field"))
        for name, baseline_property in baseline_properties.items():
            if name not in candidate_properties:
                issues.append(_breaking(f"{location}.{name}", "property was removed"))
                continue
            _compare_schema(
                baseline_property,
                candidate_properties[name],
                baseline_document,
                candidate_document,
                f"{location}.{name}",
                direction,
                issues,
                seen,
            )

    baseline_items = baseline_schema.get("items")
    candidate_items = candidate_schema.get("items")
    if isinstance(baseline_items, dict):
        if not isinstance(candidate_items, dict):
            issues.append(_breaking(location, "array item schema disappeared"))
        else:
            _compare_schema(
                baseline_items,
                candidate_items,
                baseline_document,
                candidate_document,
                f"{location}[]",
                direction,
                issues,
                seen,
            )


def _compare_limits(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    location: str,
    direction: str,
    issues: list[CompatibilityIssue],
) -> None:
    if direction != "request":
        return
    stricter_min = {"minLength", "minItems", "minimum", "exclusiveMinimum"}
    stricter_max = {"maxLength", "maxItems", "maximum", "exclusiveMaximum"}
    for key in stricter_min:
        before = baseline.get(key)
        after = candidate.get(key)
        if (
            isinstance(before, (int, float))
            and isinstance(after, (int, float))
            and after > before
        ):
            issues.append(_breaking(location, f"{key} became stricter: {before} -> {after}"))
    for key in stricter_max:
        before = baseline.get(key)
        after = candidate.get(key)
        if (
            isinstance(before, (int, float))
            and isinstance(after, (int, float))
            and after < before
        ):
            issues.append(_breaking(location, f"{key} became stricter: {before} -> {after}"))


def _compare_compositions(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    baseline_document: dict[str, Any],
    candidate_document: dict[str, Any],
    location: str,
    issues: list[CompatibilityIssue],
) -> None:
    for keyword in ("oneOf", "anyOf"):
        baseline_options = baseline.get(keyword)
        candidate_options = candidate.get(keyword)
        if not isinstance(baseline_options, list):
            continue
        if not isinstance(candidate_options, list):
            issues.append(_breaking(location, f"{keyword} disappeared"))
            continue
        baseline_keys = {_schema_identity(option, baseline_document) for option in baseline_options}
        candidate_keys = {_schema_identity(option, candidate_document) for option in candidate_options}
        for removed in sorted(baseline_keys - candidate_keys):
            issues.append(_breaking(location, f"{keyword} branch removed: {removed}"))
        for added in sorted(candidate_keys - baseline_keys):
            issues.append(_review(location, f"{keyword} branch added: {added}"))
    baseline_discriminator = baseline.get("discriminator")
    candidate_discriminator = candidate.get("discriminator")
    if isinstance(baseline_discriminator, dict):
        if not isinstance(candidate_discriminator, dict):
            issues.append(_breaking(location, "discriminator disappeared"))
        elif baseline_discriminator.get("propertyName") != candidate_discriminator.get(
            "propertyName"
        ):
            issues.append(_breaking(location, "discriminator property changed"))


def _resolve_schema(schema: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if not isinstance(reference, str):
        return schema
    if not reference.startswith("#/"):
        raise ValueError(f"Only local OpenAPI refs are supported: {reference}")
    current: Any = document
    for segment in reference[2:].split("/"):
        current = current[segment.replace("~1", "/").replace("~0", "~")]
    if not isinstance(current, dict):
        raise ValueError(f"OpenAPI ref does not resolve to an object: {reference}")
    return current


def _schema_identity(schema: object, document: dict[str, Any]) -> str:
    if not isinstance(schema, dict):
        return repr(schema)
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return reference
    resolved = _resolve_schema(schema, document)
    properties = resolved.get("properties", {})
    if isinstance(properties, dict):
        for property_schema in properties.values():
            if isinstance(property_schema, dict) and "const" in property_schema:
                return f"const:{property_schema['const']!r}"
    return repr(sorted(resolved.keys()))


def _breaking(location: str, message: str) -> CompatibilityIssue:
    return CompatibilityIssue(CompatibilitySeverity.BREAKING, location, message)


def _review(location: str, message: str) -> CompatibilityIssue:
    return CompatibilityIssue(CompatibilitySeverity.REVIEW, location, message)

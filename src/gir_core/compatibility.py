from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from pydantic_core import PydanticCustomError

from gir_core.versioning import GIR_SCHEMA_VERSION, LEGACY_GIR_VERSION


@dataclass(frozen=True)
class GirCompatibilityResult:
    payload: dict[str, Any]
    source_version: str
    target_version: str
    upgraded: bool


def canonicalize_gir_payload(value: object) -> GirCompatibilityResult | object:
    """Convert a supported raw GIR payload to the canonical schema version.

    This function only handles the top-level version marker. It never repairs,
    normalizes or semantically validates geometry.
    """
    if not isinstance(value, Mapping):
        return value

    mapping = cast(Mapping[str, Any], value)
    payload = dict(mapping)
    has_schema_version = "schema_version" in payload
    has_legacy_version = "version" in payload

    if has_schema_version and has_legacy_version:
        raise PydanticCustomError(
            "gir_schema_version_conflict",
            "Use either 'schema_version' or legacy 'version', not both.",
        )

    if not has_schema_version and not has_legacy_version:
        raise PydanticCustomError(
            "gir_schema_version_missing",
            "GIR schema version is required.",
        )

    if has_schema_version:
        source_version = payload["schema_version"]
        if source_version != GIR_SCHEMA_VERSION:
            raise PydanticCustomError(
                "gir_schema_version_unsupported",
                "Unsupported GIR schema version '{version}'.",
                {"version": str(source_version)},
            )
        return GirCompatibilityResult(
            payload=payload,
            source_version=GIR_SCHEMA_VERSION,
            target_version=GIR_SCHEMA_VERSION,
            upgraded=False,
        )

    source_version = payload["version"]
    if source_version != LEGACY_GIR_VERSION:
        raise PydanticCustomError(
            "gir_legacy_version_unsupported",
            "Unsupported legacy GIR version '{version}'.",
            {"version": str(source_version)},
        )

    canonical = dict(payload)
    del canonical["version"]
    canonical["schema_version"] = GIR_SCHEMA_VERSION
    return GirCompatibilityResult(
        payload=canonical,
        source_version=LEGACY_GIR_VERSION,
        target_version=GIR_SCHEMA_VERSION,
        upgraded=True,
    )

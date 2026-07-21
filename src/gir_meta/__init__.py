from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Final

DISTRIBUTION_NAME: Final = "gir"
SERVICE_NAME: Final = "GeometryOS"
API_MAJOR: Final = "v1"
API_VERSION: Final = "1.0.0"
GIR_SCHEMA_VERSION: Final = "0.2.0"
TUTORBOARD_CONTRACT: Final = "tutorboard/v1"


def get_service_version() -> str:
    """Return the installed GeometryOS distribution version.

    Source-only tooling can import this package before the distribution is installed;
    that state is explicit rather than silently pretending to be a release.
    """

    try:
        return version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return "0+unknown"


SERVICE_VERSION: Final = get_service_version()

__all__ = [
    "API_MAJOR",
    "API_VERSION",
    "DISTRIBUTION_NAME",
    "GIR_SCHEMA_VERSION",
    "SERVICE_NAME",
    "SERVICE_VERSION",
    "TUTORBOARD_CONTRACT",
    "get_service_version",
]

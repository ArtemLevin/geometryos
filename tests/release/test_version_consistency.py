from __future__ import annotations

from gir_api.constants import API_V1_VERSION
from gir_meta import GIR_SCHEMA_VERSION, SERVICE_VERSION, TUTORBOARD_CONTRACT
from scripts.check_release_version import check_version
from scripts.release_common import project_version, release_tag


def test_release_version_matrix_is_explicit() -> None:
    assert project_version() == "0.2.0"
    assert SERVICE_VERSION == "0.2.0"
    assert release_tag() == "v0.2.0"
    assert API_V1_VERSION == "1.0.0"
    assert GIR_SCHEMA_VERSION == "0.2.0"
    assert TUTORBOARD_CONTRACT == "tutorboard/v1"


def test_all_committed_version_surfaces_are_consistent() -> None:
    assert check_version() == []


def test_wrong_release_tag_is_rejected() -> None:
    errors = check_version("v0.2.1")
    assert any("release tag" in error for error in errors)

from __future__ import annotations

import json

from scripts.export_release_manifest import release_manifest_is_fresh
from scripts.release_common import RELEASE_MANIFEST_PATH, release_manifest


def test_release_manifest_is_fresh_and_canonical() -> None:
    assert release_manifest_is_fresh()
    assert json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8")) == release_manifest()


def test_release_manifest_publishes_expected_contract_matrix() -> None:
    manifest = release_manifest()
    assert manifest["version"] == "0.2.0"
    assert manifest["tag"] == "v0.2.0"
    assert manifest["api"] == {"namespace": "v1", "version": "1.0.0"}
    assert manifest["gir_schema_version"] == "0.2.0"
    assert manifest["tutorboard_contract"] == "tutorboard/v1"
    assert manifest["container"]["platforms"] == ["linux/amd64"]
    assert "cyclonedx-sbom" in manifest["artifacts"]

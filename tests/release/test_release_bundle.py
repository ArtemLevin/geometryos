from __future__ import annotations

from pathlib import Path

import pytest

from scripts.release_common import project_version, sha256_file
from scripts.release_smoke import expected_files, verify_checksums


def _write_checksum_fixture(root: Path) -> None:
    names = expected_files(project_version()) - {"SHA256SUMS"}
    for name in names:
        (root / name).write_bytes(f"fixture:{name}".encode())
    lines = [f"{sha256_file(root / name)}  {name}" for name in sorted(names)]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_release_bundle_uses_versioned_distribution_names() -> None:
    names = expected_files("0.2.0")
    assert "gir-0.2.0-py3-none-any.whl" in names
    assert "gir-0.2.0.tar.gz" in names
    assert "geometryos-0.2.0.release-manifest.json" in names
    assert "geometryos-0.2.0.cdx.json" in names
    assert "SHA256SUMS" in names


def test_checksum_verification_detects_tampering(tmp_path: Path) -> None:
    _write_checksum_fixture(tmp_path)
    verify_checksums(tmp_path)
    (tmp_path / "openapi.v1.json").write_text("tampered", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        verify_checksums(tmp_path)

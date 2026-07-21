from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_release_workflow_is_tag_driven_and_non_cancelling() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert '"v[0-9]+.[0-9]+.[0-9]+"' in text
    assert "group: release-${{ github.ref }}" in text
    assert "cancel-in-progress: false" in text
    assert "--expected-tag" in text
    assert "git merge-base --is-ancestor" in text


def test_release_workflow_publishes_only_immutable_supported_tags() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "sha-${REVISION}" in text
    assert '--tag "${IMAGE}:${VERSION}"' in text
    assert '--tag "${IMAGE}:${MINOR}"' in text
    assert "${IMAGE}:latest" not in text
    release_commands = "\n".join(
        line for line in text.splitlines() if "runs-on:" not in line
    ).lower()
    assert ":latest" not in release_commands
    assert "twine" not in text.lower()
    assert "pypi" not in text.lower()


def test_release_workflow_tests_registry_digest_before_promotion() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    pull_index = text.index("Pull published digest")
    smoke_index = text.index("Smoke-test published digest")
    scan_index = text.index("Scan published image")
    promote_index = text.index("Promote tested digest to SemVer tags")
    assert pull_index < smoke_index < scan_index < promote_index
    assert "--skip-build" in text
    assert "@${{ steps.image.outputs.digest }}" in text


def test_release_workflow_uses_minimal_job_permissions_and_attestations() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "packages: write" in text
    assert "attestations: write" in text
    assert "id-token: write" in text
    assert "actions/attest-build-provenance@" in text
    assert "--provenance=mode=max" in text
    assert "--sbom=true" in text
    assert "aquasecurity/trivy-action@" in text


def test_pull_request_ci_has_release_dry_run_after_all_existing_gates() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "release-dry-run:" in text
    release_section = text.split("release-dry-run:", maxsplit=1)[1]
    for job in ("verify", "package-smoke", "consumer-contract", "container-smoke"):
        assert f"- {job}" in release_section
    assert "make dependency-audit" in release_section
    assert "make release-build" in release_section
    assert "make release-smoke" in release_section
    assert "packages: write" not in release_section

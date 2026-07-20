from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_is_multi_stage_and_pins_the_python_image() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "python:3.11-slim-bookworm@sha256:" in dockerfile
    assert dockerfile.count("FROM ${PYTHON_IMAGE}") == 2
    assert "ARG UV_VERSION=" in dockerfile
    assert "uv sync --frozen --no-dev --no-editable" in dockerfile
    assert "COPY --from=builder" in dockerfile


def test_runtime_image_is_non_root_and_uses_readiness_healthcheck() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "USER 10001:10001" in dockerfile
    assert "STOPSIGNAL SIGTERM" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8000/ready" in dockerfile
    assert '"--host", "0.0.0.0"' in dockerfile
    assert '"--timeout-graceful-shutdown", "20"' in dockerfile
    assert "--reload" not in dockerfile


def test_runtime_stage_does_not_copy_the_repository() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime_stage = dockerfile.split("FROM ${PYTHON_IMAGE} AS runtime", maxsplit=1)[1]

    assert "COPY src" not in runtime_stage
    assert "COPY tests" not in runtime_stage
    assert "COPY benchmarks" not in runtime_stage
    assert "COPY --from=builder --chown=10001:10001 /opt/venv /opt/venv" in runtime_stage


def test_compose_uses_loopback_and_hardened_runtime_options() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert '"127.0.0.1:${GEOMETRYOS_PORT:-8000}:8000"' in compose
    assert "read_only: true" in compose
    assert "/tmp:size=16m,mode=1777" in compose
    assert "cap_drop:" in compose
    assert "- ALL" in compose
    assert "no-new-privileges:true" in compose
    assert "pids_limit: 128" in compose
    assert "stop_grace_period: 30s" in compose
    assert "restart: unless-stopped" in compose


def test_dockerignore_excludes_local_state_and_secrets() -> None:
    ignored = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {".git", ".github", ".venv", "tests", "benchmarks", "docs", ".env"} <= ignored
    assert "!.env.example" in ignored

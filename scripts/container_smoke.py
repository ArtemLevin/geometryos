from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "0.2.0"


class SmokeFailure(RuntimeError):
    pass


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("$ " + " ".join(command), flush=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() if capture_output else ""
        raise SmokeFailure(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
            + (f"\n{detail}" if detail else "")
        )
    return completed


def output(command: list[str], *, check: bool = True) -> str:
    return run(command, capture_output=True, check=check).stdout.strip()


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def inspect_image(image: str, revision: str, version: str) -> None:
    document = json.loads(output(["docker", "image", "inspect", image]))[0]
    config = document["Config"]

    user = str(config.get("User") or "")
    if not user or user in {"0", "0:0", "root"}:
        raise SmokeFailure(f"Runtime image must use a non-root user, got {user!r}.")

    command = [str(item) for item in config.get("Cmd") or []]
    joined_command = " ".join(command)
    if "--reload" in command:
        raise SmokeFailure("Runtime image command must not enable Uvicorn reload.")
    if "--host" not in command or "0.0.0.0" not in command:
        raise SmokeFailure(f"Runtime image must bind to 0.0.0.0: {joined_command}")

    healthcheck = config.get("Healthcheck") or {}
    health_test = " ".join(str(item) for item in healthcheck.get("Test") or [])
    if "/ready" not in health_test:
        raise SmokeFailure("Image healthcheck must call /ready.")

    labels = config.get("Labels") or {}
    expected_labels = {
        "org.opencontainers.image.title": "GeometryOS",
        "org.opencontainers.image.source": "https://github.com/ArtemLevin/geometryos",
        "org.opencontainers.image.revision": revision,
        "org.opencontainers.image.version": version,
    }
    for name, expected in expected_labels.items():
        if labels.get(name) != expected:
            raise SmokeFailure(
                f"Image label {name!r} must be {expected!r}, got {labels.get(name)!r}."
            )

    print("[PASS] image metadata and command contract", flush=True)


def verify_runtime_contents(image: str) -> None:
    code = (
        "import importlib.util, os, pathlib, shutil\n"
        "assert os.getuid() != 0, os.getuid()\n"
        "for module in ('pytest', 'ruff', 'mypy'):\n"
        "    assert importlib.util.find_spec(module) is None, module\n"
        "assert shutil.which('uv') is None\n"
        "assert not pathlib.Path('/app/src').exists()\n"
        "assert not pathlib.Path('/app/tests').exists()\n"
        "assert not pathlib.Path('/app/benchmarks').exists()\n"
        "print('runtime contents: ok')\n"
    )
    run(
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--tmpfs",
            "/tmp:size=16m,mode=1777",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            image,
            "python",
            "-c",
            code,
        ]
    )
    print("[PASS] non-root runtime excludes development tooling and source tree", flush=True)


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 3.0,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json; charset=utf-8"

    request = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
        response_headers = {name.lower(): value for name, value in response.headers.items()}
        return response.status, response_headers, body


def wait_for_endpoint(
    url: str,
    *,
    timeout_seconds: float,
) -> tuple[dict[str, str], dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, headers, body = request_json(url)
            if status == 200:
                return headers, body
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise SmokeFailure(f"Endpoint did not become ready: {url}; last error={last_error!r}")


def wait_for_container_health(name: str, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"
    while time.monotonic() < deadline:
        document = json.loads(output(["docker", "inspect", name]))[0]
        health = document.get("State", {}).get("Health") or {}
        last_status = str(health.get("Status", "missing"))
        if last_status == "healthy":
            print("[PASS] Docker health status is healthy", flush=True)
            return
        if last_status == "unhealthy":
            break
        time.sleep(0.5)
    raise SmokeFailure(f"Container did not become healthy; last status={last_status!r}.")


def run_container_smoke(image: str, *, timeout_seconds: float) -> None:
    name = f"geometryos-smoke-{uuid4().hex[:12]}"
    port = reserve_port()
    base_url = f"http://127.0.0.1:{port}"
    container_created = False
    stopped = False

    try:
        run(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                name,
                "--publish",
                f"127.0.0.1:{port}:8000",
                "--read-only",
                "--tmpfs",
                "/tmp:size=16m,mode=1777",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                image,
            ]
        )
        container_created = True

        health_headers, health_body = wait_for_endpoint(
            f"{base_url}/health",
            timeout_seconds=timeout_seconds,
        )
        if health_body != {"status": "ok"}:
            raise SmokeFailure(f"Unexpected /health body: {health_body!r}")
        if not health_headers.get("x-request-id"):
            raise SmokeFailure("/health did not return X-Request-ID.")
        print("[PASS] liveness endpoint", flush=True)

        ready_headers, ready_body = wait_for_endpoint(
            f"{base_url}/ready",
            timeout_seconds=timeout_seconds,
        )
        if ready_body.get("status") != "ready":
            raise SmokeFailure(f"Unexpected /ready body: {ready_body!r}")
        if ready_headers.get("cache-control") != "no-store":
            raise SmokeFailure("/ready must return Cache-Control: no-store.")
        if any(item.get("status") != "pass" for item in ready_body.get("checks", [])):
            raise SmokeFailure(f"Readiness checks did not pass: {ready_body!r}")
        print("[PASS] readiness endpoint", flush=True)

        wait_for_container_health(name, timeout_seconds=timeout_seconds)

        status, response_headers, body = request_json(
            f"{base_url}/api/v1/generate",
            method="POST",
            payload={
                "input_type": "text",
                "input": ("Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."),
                "output": ["svg"],
                "mode": "strict",
            },
            headers={"X-Request-ID": "container-smoke"},
            timeout=10,
        )
        if status != 200 or body.get("status") != "success":
            raise SmokeFailure(f"Unexpected generate response: status={status}, body={body!r}")
        if body.get("schema_version") != "0.2.0":
            raise SmokeFailure(f"Unexpected GIR schema version: {body!r}")
        if response_headers.get("x-request-id") != "container-smoke":
            raise SmokeFailure("Request correlation header was not preserved.")
        print("[PASS] stable API generation and request correlation", flush=True)

        run(["docker", "stop", "--time", "30", name])
        stopped = True
        state = json.loads(output(["docker", "inspect", name]))[0]["State"]
        if int(state["ExitCode"]) != 0:
            raise SmokeFailure(f"Container exited with code {state['ExitCode']}.")
        logs = output(["docker", "logs", name], check=False)
        if "Traceback (most recent call last)" in logs:
            raise SmokeFailure("Container logs contain a Python traceback after shutdown.")
        print("[PASS] graceful SIGTERM shutdown", flush=True)
    except Exception:
        if container_created:
            logs = output(["docker", "logs", name], check=False)
            if logs:
                print("\n--- container logs ---\n" + logs, file=sys.stderr, flush=True)
        raise
    finally:
        if container_created and not stopped:
            run(["docker", "stop", "--time", "5", name], check=False)
        if container_created:
            run(["docker", "rm", "--force", name], check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and smoke-test the GeometryOS image.")
    parser.add_argument("--image", default="geometryos:smoke")
    parser.add_argument("--revision", default="local")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--skip-build", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run(["docker", "version"])
        if not args.skip_build:
            run(
                [
                    "docker",
                    "build",
                    "--tag",
                    args.image,
                    "--build-arg",
                    f"BUILD_REVISION={args.revision}",
                    "--build-arg",
                    f"BUILD_VERSION={args.version}",
                    ".",
                ]
            )
        inspect_image(args.image, args.revision, args.version)
        verify_runtime_contents(args.image)
        run_container_smoke(args.image, timeout_seconds=args.timeout_seconds)
    except (OSError, SmokeFailure, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"\n[FAIL] container smoke: {exc}", file=sys.stderr, flush=True)
        return 1

    print("\nAll container smoke checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

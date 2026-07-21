# GeometryOS deployment

## Scope

GeometryOS ships one hardened single-process container for local integration and deployment validation. The image exposes the stable HTTP API on port `8000`, preserves the request-correlation and Problem Details contracts, and separates process liveness from application readiness.

This deployment does not include TLS, a reverse proxy, authentication, rate limiting, Kubernetes resources, metrics or tracing. GeometryOS `0.2.0` is published to GHCR after tag verification and registry smoke.

## Prerequisites

- Docker Engine with the Compose v2 plugin;
- Git for build revision metadata;
- `uv` and Python 3.11 only when running Makefile or smoke-test commands outside Docker.

Check the environment:

```bash
docker version
docker compose version
uv --version
```

## Image architecture

The `Dockerfile` is multi-stage:

1. the builder stage uses the committed `uv.lock`, installs runtime dependencies only and installs GeometryOS non-editably into `/opt/venv`;
2. the runtime stage copies only `/opt/venv` into the same pinned Python base image;
3. the final process runs as UID/GID `10001:10001` and does not contain `uv`, test tools or repository sources.

The base Python image is pinned by immutable digest. Updating that digest is an explicit dependency change and must pass the complete container smoke test.

## Build

```bash
make container-build
```

Equivalent command:

```bash
docker build \
  --tag geometryos:local \
  --build-arg BUILD_REVISION="$(git rev-parse HEAD)" \
  --build-arg BUILD_VERSION=0.2.0 \
  .
```

PowerShell:

```powershell
$revision = git rev-parse HEAD

docker build `
  --tag geometryos:local `
  --build-arg "BUILD_REVISION=$revision" `
  --build-arg "BUILD_VERSION=0.2.0" `
  .
```

## Direct Docker run

```bash
docker run --rm \
  --name geometryos \
  --publish 127.0.0.1:8000:8000 \
  --read-only \
  --tmpfs /tmp:size=16m,mode=1777 \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  geometryos:local
```

PowerShell:

```powershell
docker run --rm `
  --name geometryos `
  --publish 127.0.0.1:8000:8000 `
  --read-only `
  --tmpfs /tmp:size=16m,mode=1777 `
  --cap-drop ALL `
  --security-opt no-new-privileges:true `
  geometryos:local
```

The default bind address is loopback. Exposing GeometryOS outside the host requires an explicit deployment decision and normally a reverse proxy with TLS and access control.

## Docker Compose

Validate the deployment definition:

```bash
make compose-config
```

Start the service:

```bash
make compose-up
```

Follow structured logs:

```bash
make compose-logs
```

Stop the service:

```bash
make compose-down
```

Direct Compose commands are also supported:

```bash
docker compose config --quiet
docker compose up --build --detach
docker compose logs --follow geometryos
docker compose down --remove-orphans
```

Copy `.env.example` to `.env` only for local overrides. Never commit `.env` or secrets.

## Runtime environment

| Variable | Default | Meaning |
|---|---:|---|
| `GEOMETRYOS_PORT` | `8000` | Host-side Compose port bound to loopback |
| `GEOMETRYOS_IMAGE_TAG` | `local` | Local Compose image tag |
| `GEOMETRYOS_BUILD_REVISION` | `local` | OCI revision label |
| `GEOMETRYOS_BUILD_VERSION` | `0.2.0` | OCI version label |
| `GEOMETRYOS_GENERATE_TIMEOUT_SECONDS` | `15` | Generate soft deadline |
| `GEOMETRYOS_VALIDATE_TIMEOUT_SECONDS` | `5` | Validation soft deadline |
| `GEOMETRYOS_RENDER_TIMEOUT_SECONDS` | `10` | Render soft deadline |
| `GEOMETRYOS_MAX_INPUT_CHARS` | `20000` | Operational input limit |
| `GEOMETRYOS_LOG_LEVEL` | `INFO` | Structured API log level |

Invalid application settings fail fast during process startup.

## Liveness

```text
GET /health
```

A `200` response with `{"status":"ok"}` means the process and event loop can serve HTTP. Liveness intentionally does not depend on readiness and remains healthy while the service is stopping.

```bash
curl --fail http://127.0.0.1:8000/health
```

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Readiness

```text
GET /ready
```

Readiness returns `200` only when:

- FastAPI startup completed;
- lifecycle phase is `ready`;
- validated settings remain registered;
- the application executor exposes all required operations.

It returns `503` with `status: not_ready` during startup, shutdown, failure or runtime-state degradation. The response always carries `Cache-Control: no-store` and `X-Request-ID`.

```bash
curl --fail http://127.0.0.1:8000/ready
```

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Docker uses `/ready` for the image healthcheck.

## Stable API check

```bash
curl -X POST http://127.0.0.1:8000/api/v1/generate \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: deployment-check' \
  -d '{
    "input_type": "text",
    "input": "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
    "output": ["svg"],
    "mode": "strict"
  }'
```

Swagger UI remains available at:

```text
http://127.0.0.1:8000/docs
```

## Security posture

The provided Compose service enforces:

- non-root UID/GID `10001:10001`;
- read-only root filesystem;
- tmpfs-backed `/tmp` as the only writable location;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- process count limited to `128`;
- no source-code or development-tool installation in the runtime image;
- loopback-only host binding by default.

Do not weaken these controls merely to work around an application error. GeometryOS does not require filesystem persistence.

## Logging

Uvicorn access logs are disabled because GeometryOS already emits one structured `request_completed` JSON event per request. Uvicorn lifecycle and server errors remain enabled.

Logs never intentionally include prompts, GIR payloads, rendered output, authorization headers or exception messages.

## Graceful shutdown

The image declares `STOPSIGNAL SIGTERM`. Uvicorn is configured with a `20`-second graceful-shutdown timeout, while Compose grants a `30`-second stop period.

```bash
docker stop --time 30 geometryos
```

Expected behavior:

1. Docker sends `SIGTERM` to the exec-form Uvicorn process;
2. Uvicorn stops accepting new connections and drains in-flight requests;
3. FastAPI lifespan marks readiness as stopping;
4. the process exits without a traceback and with exit code `0`.

GeometryOS does not install custom OS signal handlers.

## Container smoke test

Run the complete local gate:

```bash
make container-smoke
```

The smoke test:

1. builds the image with revision/version labels;
2. inspects the non-root user, command and healthcheck;
3. verifies the runtime excludes `pytest`, `ruff`, `mypy`, `uv` and repository sources;
4. starts the container with read-only filesystem and restricted privileges;
5. checks `/health`, `/ready` and Docker health status;
6. sends a stable API generation request with request correlation;
7. stops the process with `SIGTERM` and verifies a clean exit;
8. removes the test container in all cases.

## Upgrade procedure

1. pull the intended source revision;
2. run `uv sync --frozen --dev`;
3. run `make verify`, `make package-smoke` and `make container-smoke`;
4. build the intended image tag with explicit revision/version labels;
5. start the replacement service;
6. wait for `/ready` and Docker health to become healthy;
7. move client traffic only after readiness succeeds;
8. retain the previous image tag for rollback.

## Rollback procedure

1. stop the failed/new service;
2. start the previously verified image tag with the same environment;
3. verify `/health`, `/ready` and one supported `/api/v1/generate` request;
4. restore client traffic;
5. retain request IDs and logs for diagnosis.

No persistent application data or migration rollback is required in the current GeometryOS service.

## Troubleshooting

### Container is running but unhealthy

```bash
docker inspect geometryos --format '{{json .State.Health}}'
docker logs geometryos
```

Call `/health` and `/ready` separately. A live process with failing readiness should not receive application traffic.

### Container exits immediately

Check environment validation and OCI logs:

```bash
docker logs geometryos
```

Invalid `GEOMETRYOS_*` values intentionally prevent startup.

### Permission or read-only filesystem error

GeometryOS must run without writing outside `/tmp`. Treat a write attempt elsewhere as an application defect; do not switch the container to root or a writable root filesystem.

### Port already in use

Override the host port:

```bash
GEOMETRYOS_PORT=8010 docker compose up --build --detach
```

PowerShell:

```powershell
$env:GEOMETRYOS_PORT = "8010"
docker compose up --build --detach
```

## Known limitations

- one Uvicorn worker per container;
- no TLS or reverse proxy;
- the first published image target is `linux/amd64`;
- no Kubernetes manifests;
- no Prometheus metrics or distributed tracing;
- soft application-operation timeouts cannot forcibly terminate an already running Python worker thread.

## Published release image

    GeometryOS `0.2.0` is published as `ghcr.io/artemlevin/geometryos:0.2.0` and `sha-<commit>`. Production deployments should pin `ghcr.io/artemlevin/geometryos@sha256:<digest>`. The workflow tests the registry digest before assigning SemVer aliases and does not publish `latest`.

    Release and rollback details are documented in `docs/RELEASE_PROCESS.md`.

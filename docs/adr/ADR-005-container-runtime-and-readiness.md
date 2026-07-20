# ADR-005: Container runtime and readiness

## Status

Accepted for the GeometryOS integration-ready phase.

## Context

GeometryOS already exposes a stable HTTP API v1 and a transport resilience boundary, but it did not have a reproducible deployment artifact, a production process command or separate liveness and readiness semantics. The development command used Uvicorn reload on loopback, while CI verified only source and wheel behavior.

TutorBoard integration and later deployment automation require one hardened image that behaves the same locally and in CI, can be observed by an orchestrator and terminates predictably.

## Decision

- package GeometryOS as a multi-stage Docker image built from the committed `uv.lock`;
- pin the Python base image by immutable digest and pin the builder-only `uv` version;
- copy only the non-editable runtime environment into the final image;
- run one Uvicorn process as UID/GID `10001:10001`;
- bind the container process to `0.0.0.0:8000` without reload or duplicate access logs;
- preserve `/health` as unconditional process liveness;
- add `/ready` as an additive operational endpoint driven by FastAPI lifespan state;
- keep readiness checks local, deterministic and side-effect-free;
- use `/ready` for the Docker healthcheck;
- delegate `SIGTERM` and graceful request draining to Uvicorn;
- run containers with a read-only root filesystem, tmpfs `/tmp`, all Linux capabilities dropped and privilege escalation disabled;
- validate the image, security options, probes, stable API and shutdown behavior in a dedicated CI container-smoke job;
- defer image publication and release metadata to the release PR.

## Consequences

### Positive

- local Compose and CI execute the same deployment artifact;
- liveness and readiness have distinct, testable meanings;
- the runtime image excludes repository sources and development tooling;
- the service operates without root privileges or a writable root filesystem;
- TutorBoard can wait for application readiness before sending geometry traffic;
- the container can later be published without changing its process architecture;
- deployment failures are caught before release.

### Negative

- Docker builds add time and network dependency to CI;
- one Uvicorn worker limits throughput inside one container;
- image base digests require intentional maintenance;
- the current deployment has no TLS, reverse proxy or external authentication;
- readiness becomes an additional operational compatibility contract.

## Rejected alternatives

- reusing `/health` for readiness would prevent an orchestrator from distinguishing a live process from an application that is starting or stopping;
- executing a generate or render request in readiness would create unnecessary work and could amplify failures;
- a single-stage image would retain build tools and repository content;
- running as root or granting Linux capabilities was unnecessary;
- installing dependencies at container startup would make startup network-dependent and non-reproducible;
- shell-form `CMD` would weaken signal propagation;
- `--reload` is a development feature and is not appropriate for a production process;
- Gunicorn or multiple workers were rejected until profiling demonstrates a need;
- bundling Nginx or Caddy into the same image would mix reverse-proxy and application responsibilities;
- Kubernetes and Helm were deferred until the target infrastructure is selected;
- publishing an image from every pull request was deferred to release automation.

## Follow-up

A later contract PR will commit the OpenAPI artifact and generate TutorBoard client types. The release PR may publish the image with versioned tags, provenance and additional supply-chain metadata while preserving the runtime contract defined here.

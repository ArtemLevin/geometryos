# ADR-007: Versioning and Release Publication

## Status

Accepted for GeometryOS `0.2.0`.

## Context

GeometryOS now has independently versioned machine contracts:

- Python service/distribution;
- HTTP API v1;
- GIR schema `0.2.0`;
- TutorBoard consumer contract v1;
- Docker image and release artifacts.

Treating all contracts as one version would force unnecessary API or GIR changes during ordinary service patch releases. The project also needs a reproducible path from a tested commit to immutable downloadable artifacts and a tested container digest.

## Decision

1. Semantic Versioning applies to the GeometryOS service and Python distribution.
2. `pyproject.toml` is the canonical service-version source.
3. HTTP API, GIR schema and TutorBoard contracts remain independently versioned.
4. Git tags use the `v<semver>` form.
5. GitHub Release stores wheel, sdist, schemas, contract fixtures, manifest, SBOM and checksums.
6. GHCR stores the container image.
7. PyPI publication is deferred until distribution naming and project ownership are explicitly resolved.
8. Versioned Git tags, GitHub Release assets and full SemVer image tags are immutable.
9. No mutable `latest` image is published.
10. Release workflows rerun verification on the tagged commit rather than trusting a previous PR run.
11. A registry image is first published under a commit-SHA tag, smoke-tested, then promoted to SemVer aliases without rebuilding.
12. Release assets receive SHA-256 checksums and provenance attestations.
13. A defective release is superseded by a patch release instead of being silently replaced.

## Consequences

### Positive

- TutorBoard can pin a complete, reproducible integration release.
- API and GIR compatibility are not coupled to package patch versions.
- Container promotion tests the exact registry artifact that will be deployed.
- Release files can be verified independently through checksums and attestations.
- Rollback can target a known digest.

### Negative

- Release workflows are more complex than ordinary CI.
- Multiple version surfaces must be validated even though only one is canonical.
- Registry publication requires repository configuration outside the source tree.
- PyPI users must install release assets directly until package naming is resolved.
- Initial container publication is limited to `linux/amd64`.

## Rejected alternatives

### Use API version as package version

Rejected because API v1 may remain stable across many service releases.

### Use GIR schema version as package version

Rejected because implementation, deployment and security fixes do not necessarily alter GIR.

### Publish from pull-request CI

Rejected because unmerged code must not create immutable release artifacts.

### Publish `latest`

Rejected because it prevents deterministic deployment and rollback.

### Manually upload wheel and image

Rejected because manual publication breaks provenance and makes artifact drift likely.

### Rewrite a defective version

Rejected because consumers cannot distinguish original and replaced artifacts.

### Publish to PyPI as `gir` immediately

Rejected until ownership and long-term distribution naming are confirmed.

# GeometryOS Release Process

## Release model

GeometryOS uses Semantic Versioning for the service/Python distribution. API v1, GIR `0.2.0` and TutorBoard contract v1 are independent contracts.

Published release channels:

- GitHub Release assets for wheel, sdist, schemas, contracts, manifest, SBOM and checksums;
- GHCR for the hardened container image;
- PyPI publication is intentionally deferred.

## Pre-release preparation

Create a release branch from current `main`:

```bash
git switch main
git pull --ff-only
git switch -c release/geometryos-0.2.0
```

Update package metadata, changelog and release manifest. Regenerate committed artifacts:

```bash
uv lock
make openapi
make release-manifest
```

Run the complete local candidate gate:

```bash
uv sync --frozen --dev
make release-all
```

The gate includes source verification, package smoke, TutorBoard contracts, TypeScript generation, container smoke, version consistency, locked runtime dependency audit, release bundle build and release bundle smoke.

## Pull request requirements

The release PR must:

- target `main`;
- contain no new geometry features;
- preserve API paths, operation IDs and existing response bodies;
- pass `verify`, `package-smoke`, `consumer-contract`, `container-smoke` and `release-dry-run`;
- contain a current OpenAPI artifact, GIR schema, TutorBoard fixtures and release manifest;
- document known limitations and rollback.

Use squash merge with a release-specific message:

```text
release: GeometryOS 0.2.0 (#<pr>)
```

## Tagging

After the release PR is merged and the `main` checks are green:

```bash
git switch main
git pull --ff-only
git tag -a v0.2.0 -m "GeometryOS 0.2.0"
git push origin v0.2.0
```

The tag must point to the tested merge commit. Never create the tag from a working tree or before the release PR is merged.

## Automated publication

The tag triggers `.github/workflows/release.yml`.

The workflow:

1. validates tag/version consistency;
2. repeats source, package, consumer and release verification;
3. builds release files;
4. publishes `sha-<commit>` to GHCR;
5. smoke-tests the registry image by digest;
6. promotes the same digest to `0.2.0` and `0.2`;
7. generates provenance attestations;
8. creates the GitHub Release from the versioned changelog section.

The workflow never publishes `latest`.

## Release assets

Expected assets:

```text
gir-0.2.0-py3-none-any.whl
gir-0.2.0.tar.gz
openapi.v1.json
gir-0.2.schema.json
tutorboard-v1-contracts.tar.gz
geometryos-0.2.0.release-manifest.json
geometryos-0.2.0.cdx.json
SHA256SUMS
```

Verify downloaded assets:

```bash
sha256sum --check SHA256SUMS
```

## Image tags

Published tags:

```text
ghcr.io/artemlevin/geometryos:0.2.0
ghcr.io/artemlevin/geometryos:0.2
ghcr.io/artemlevin/geometryos:sha-<commit>
```

Production deployments should pin the image digest. The `0.2.0` tag is immutable. The minor tag `0.2` may advance only to a compatible patch release.

## Rollback

1. Record the failing deployment digest and request IDs.
2. Stop routing new traffic to the failing container.
3. Deploy the previous known-good digest.
4. Verify `/health` and `/ready`.
5. Execute the canonical generate smoke request.
6. Confirm TutorBoard request correlation.
7. Open an incident or defect with the affected version/digest.

Do not move `v0.2.0`, rewrite release assets or overwrite the `0.2.0` image. Publish a patch release such as `0.2.1`.

## Release withdrawal

When a released artifact is affected:

- retain the Git tag and immutable artifacts for auditability;
- mark the GitHub Release as affected and add remediation guidance;
- publish a patched release;
- update the compatible minor tag only after the patch image passes registry smoke;
- preserve provenance and checksum records.

## Repository settings

Recommended settings:

- protect `main` and require all release PR checks;
- protect tags matching `v*`;
- create a `release` environment with required review;
- permit GHCR publication only from the tag workflow;
- enable private vulnerability reporting;
- require review for workflow-file changes.

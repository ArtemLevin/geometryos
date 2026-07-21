# Security Policy

## Supported versions

GeometryOS `0.2.x` is the first supported integration release line. Pre-release versions and unpublished development branches do not receive security fixes.

| Version | Supported |
|---|---|
| 0.2.x | Yes |
| < 0.2.0 | No |

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private prompts, GIR payloads or infrastructure information.

Use GitHub private vulnerability reporting when it is enabled for the repository. Include:

- affected GeometryOS version or container digest;
- affected endpoint or package;
- minimal reproduction steps;
- expected and observed impact;
- whether the issue is remotely reachable;
- any temporary mitigation already identified.

Reports should avoid real student data and production secrets.

## Response process

The maintainer will:

1. acknowledge the report;
2. reproduce and classify the issue;
3. prepare a patch release when required;
4. publish remediation and upgrade guidance;
5. mark affected release artifacts without rewriting immutable version tags.

## Release security controls

GeometryOS release candidates are expected to pass:

- frozen dependency installation;
- source, package, consumer and container tests;
- locked runtime dependency auditing;
- non-root/read-only container smoke tests;
- release checksums;
- CycloneDX SBOM generation;
- GitHub and container provenance attestations.

Versioned release tags and container tags are immutable. A defective release is superseded by a patch release rather than silently replaced.

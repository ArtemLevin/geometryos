from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

SBOM_PROGRAM = r"""
import importlib.metadata
import json
import re
import uuid


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


distributions = {}
for dist in importlib.metadata.distributions():
    name = dist.metadata.get("Name")
    version = dist.version
    if not name or not version:
        continue
    normalized = normalize(name)
    distributions[normalized] = dist

components = []
dependencies = []
for normalized in sorted(distributions):
    dist = distributions[normalized]
    name = dist.metadata["Name"]
    version = dist.version
    ref = f"pkg:pypi/{normalized}@{version}"
    component = {
        "bom-ref": ref,
        "name": name,
        "purl": ref,
        "type": "library",
        "version": version,
    }
    license_expression = dist.metadata.get("License-Expression") or dist.metadata.get("License")
    if license_expression and license_expression != "UNKNOWN":
        component["licenses"] = [{"license": {"name": license_expression}}]
    components.append(component)

    depends_on = []
    for requirement in dist.requires or []:
        match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
        if match is None:
            continue
        dependency_name = normalize(match.group(1))
        dependency = distributions.get(dependency_name)
        if dependency is None:
            continue
        depends_on.append(f"pkg:pypi/{dependency_name}@{dependency.version}")
    dependencies.append({"ref": ref, "dependsOn": sorted(set(depends_on))})

serial_seed = "|".join(component["purl"] for component in components)
document = {
    "bomFormat": "CycloneDX",
    "components": components,
    "dependencies": dependencies,
    "metadata": {
        "component": next(
            component for component in components if component["name"].lower() == "gir"
        ),
        "tools": {
            "components": [
                {
                    "name": "GeometryOS release tooling",
                    "type": "application",
                    "version": "0.2.0",
                }
            ]
        },
    },
    "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, serial_seed)}",
    "specVersion": "1.5",
    "version": 1,
}
print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))
"""


def generate_sbom(python: Path, output: Path) -> Path:
    completed = subprocess.run(
        [str(python), "-c", SBOM_PROGRAM],
        check=True,
        capture_output=True,
        text=True,
    )
    document = json.loads(completed.stdout)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a CycloneDX SBOM from a Python environment."
    )
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = generate_sbom(args.python, args.output)
    print(f"Generated CycloneDX SBOM: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

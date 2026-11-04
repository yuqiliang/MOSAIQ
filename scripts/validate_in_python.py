"""Validate and inspect a MOSAIQ package with the Frictionless Python API."""

from __future__ import annotations

import argparse
from pathlib import Path

from frictionless import Package, system


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "datasets" / "ISD" / "datapackage.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and inspect one MOSAIQ Frictionless package"
    )
    parser.add_argument(
        "package",
        nargs="?",
        type=Path,
        default=DEFAULT_PACKAGE,
        help="Data Package descriptor (default: datasets/ISD/datapackage.yaml)",
    )
    parser.add_argument(
        "--resource",
        default="clips",
        help="Resource to inspect after validation (default: clips)",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=3,
        help="Number of resource rows to preview (default: 3)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_path = args.package.resolve()
    if not package_path.is_file():
        raise FileNotFoundError(f"Package descriptor not found: {package_path}")
    if args.rows < 0:
        raise ValueError("--rows must be zero or greater")

    # MOSAIQ packages intentionally reuse schemas above each dataset directory.
    with system.use_context(trusted=True):
        package = Package(str(package_path))
        report = package.validate()

        print(f"Package: {package_path}")
        print(f"Resources: {', '.join(resource.name for resource in package.resources)}")
        print(f"Validation: {'VALID' if report.valid else 'INVALID'}")
        if not report.valid:
            for message in report.flatten(["message"])[:5]:
                print(f"- {message[0]}")
            return 1

        resource = package.get_resource(args.resource)
        print(f"Inspecting: {resource.name} ({len(resource.schema.fields)} fields)")
        print("Fields: " + ", ".join(field.name for field in resource.schema.fields[:8]))

        with resource:
            for index, row in enumerate(resource.row_stream, start=1):
                if index > args.rows:
                    break
                values = row.to_dict()
                preview = ", ".join(
                    f"{key}={values[key]!r}" for key in list(values)[:5]
                )
                print(f"Row {index}: {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

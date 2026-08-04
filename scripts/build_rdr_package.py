#!/usr/bin/env python3
"""Build a deterministic, no-audio MOSAIQ archive for a private RDR draft."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path


ROOT_FILES = (
    ".python-version",
    "CITATION.cff",
    "DATA_LICENSE.md",
    "LICENSE",
    "README.md",
    "RELEASE_NOTES.md",
    "datacatalog.yaml",
    "pyproject.toml",
    "uv.lock",
)

ROOT_DIRS = (
    "benchmark",
    "catalogue",
    "config",
    "datasets",
    "docs",
    "examples",
    "mappings",
    "notebooks",
    "papers",
    "scripts",
    "shared_schemas",
    "tests",
)

EXCLUDED_NAMES = {
    ".DS_Store",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}

EXCLUDED_SUFFIXES = {
    ".docx",
    ".mp3",
    ".mp4",
    ".mov",
    ".wav",
}

PACKAGE_README_SOURCE = Path("docs/release/RDR_README.md")
PACKAGE_README_DESTINATION = Path("RDR_README.md")


def is_included(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_NAMES for part in relative.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file() and not path.is_symlink()


def collect_files(root: Path) -> list[Path]:
    selected: list[Path] = []
    for name in ROOT_FILES:
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"Required release file is missing: {path}")
        selected.append(path)
    for name in ROOT_DIRS:
        directory = root / name
        if not directory.is_dir():
            raise FileNotFoundError(f"Required release directory is missing: {directory}")
        selected.extend(path for path in directory.rglob("*") if is_included(path, root))
    return sorted(set(selected), key=lambda path: path.relative_to(root).as_posix())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_release(root: Path, stage: Path, files: list[Path]) -> None:
    for source in files:
        destination = stage / source.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copy2(root / PACKAGE_README_SOURCE, stage / PACKAGE_README_DESTINATION)


def write_manifests(stage: Path) -> None:
    content_files = sorted(
        (
            path
            for path in stage.rglob("*")
            if path.is_file()
            and path not in {stage / "checksums.sha256", stage / "file_manifest.csv"}
        ),
        key=lambda path: path.relative_to(stage).as_posix(),
    )
    rows = []
    checksum_lines = []
    for path in content_files:
        relative = path.relative_to(stage).as_posix()
        digest = sha256(path)
        rows.append((relative, path.stat().st_size, digest))
        checksum_lines.append(f"{digest}  {relative}\n")

    with (stage / "file_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("path", "size_bytes", "sha256"))
        writer.writerows(rows)

    (stage / "checksums.sha256").write_text("".join(checksum_lines), encoding="ascii")


def normalise_permissions(stage: Path) -> None:
    for path in stage.rglob("*"):
        mode = 0o755 if path.is_dir() else 0o644
        if path.is_file() and path.suffix == ".py":
            mode = 0o755
        path.chmod(mode)


def build_zip(
    stage: Path,
    destination: Path,
    package_name: str,
    archive_date: dt.date,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(stage.rglob("*"), key=lambda item: item.relative_to(stage).as_posix()):
            if not path.is_file():
                continue
            relative = Path(package_name) / path.relative_to(stage)
            info = zipfile.ZipInfo(
                relative.as_posix(),
                date_time=(archive_date.year, archive_date.month, archive_date.day, 0, 0, 0),
            )
            permissions = stat.S_IFREG | (0o755 if os.access(path, os.X_OK) else 0o644)
            info.external_attr = permissions << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--package-name",
        default="MOSAIQ_tabular_v0.1.0-dev_2026-07-24",
    )
    parser.add_argument("--archive-date", type=dt.date.fromisoformat, default=dt.date(2026, 7, 24))
    args = parser.parse_args()

    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    archive_path = output_dir / f"{args.package_name}.zip"

    with tempfile.TemporaryDirectory(prefix="mosaiq-rdr-") as temporary:
        stage = Path(temporary) / args.package_name
        stage.mkdir()
        files = collect_files(root)
        copy_release(root, stage, files)
        write_manifests(stage)
        normalise_permissions(stage)
        build_zip(stage, archive_path, args.package_name, args.archive_date)

    archive_digest = sha256(archive_path)
    checksum_path = archive_path.with_suffix(f"{archive_path.suffix}.sha256")
    checksum_path.write_text(
        f"{archive_digest}  {archive_path.name}\n",
        encoding="ascii",
    )
    print(f"Built {archive_path}")
    print(f"Archive SHA-256: {archive_digest}")
    print(f"Checksum sidecar: {checksum_path}")


if __name__ == "__main__":
    main()

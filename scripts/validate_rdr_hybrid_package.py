#!/usr/bin/env python3
"""Validate the consolidated seven-file MOSAIQ UCL RDR package set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath


RELEASE_STEM = "MOSAIQ-v0.2.0-rc1"
EXPECTED_SPLITS = {"train": 546, "dev": 154, "test": 120}
EXPECTED_FILES = {
    f"{RELEASE_STEM}_README.md",
    f"{RELEASE_STEM}_LICENSES.md",
    f"{RELEASE_STEM}_MANIFEST.csv",
    f"{RELEASE_STEM}_SHA256SUMS.txt",
    f"{RELEASE_STEM}_benchmark-kit.zip",
    f"{RELEASE_STEM}_ISD-audio.zip",
    f"{RELEASE_STEM}_ISD-audio-manifest.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def zip_member_sha256(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_checksum_lines(payload: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in payload.splitlines():
        digest, name = line.split(maxsplit=1)
        if name in result:
            raise ValueError(f"Duplicate checksum entry: {name}")
        result[name] = digest
    return result


def validate_audio_package(path: Path, external_manifest: Path) -> None:
    root = f"{RELEASE_STEM}_ISD-audio"
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        roots = {PurePosixPath(name).parts[0] for name in names if name}
        if roots != {root}:
            raise ValueError(f"Unexpected audio package roots: {sorted(roots)}")

        manifest_name = f"{root}/audio_manifest.csv"
        readme_name = f"{root}/README.md"
        checksums_name = f"{root}/checksums.sha256"
        for required in (manifest_name, readme_name, checksums_name):
            if required not in names:
                raise ValueError(f"Missing audio package member: {required}")

        manifest_bytes = archive.read(manifest_name)
        if manifest_bytes != external_manifest.read_bytes():
            raise ValueError("Internal and external audio manifests differ")
        manifest = list(csv.DictReader(io.StringIO(manifest_bytes.decode("utf-8"))))
        if len(manifest) != 820:
            raise ValueError(f"Expected 820 audio manifest rows, found {len(manifest)}")
        if dict(Counter(row["split"] for row in manifest)) != EXPECTED_SPLITS:
            raise ValueError("Audio manifest split counts do not match the frozen cohort")
        if any(row["use_for_benchmark"].lower() != "true" for row in manifest):
            raise ValueError("Audio package includes a non-accepted manifest row")

        wav_names = [name for name in names if name.lower().endswith(".wav")]
        expected_members = {row["package_member"] for row in manifest}
        if len(wav_names) != 820 or set(wav_names) != expected_members:
            raise ValueError("Audio ZIP members do not match the external manifest")
        for split, count in EXPECTED_SPLITS.items():
            observed = sum(f"/{split}/" in name for name in wav_names)
            if observed != count:
                raise ValueError(f"Audio ZIP {split} count mismatch: {observed} != {count}")

        checksums = read_checksum_lines(archive.read(checksums_name).decode("ascii"))
        if len(checksums) != 822:
            raise ValueError(f"Expected 822 internal checksums, found {len(checksums)}")
        for relative, expected in checksums.items():
            member = f"{root}/{relative}"
            if member not in names:
                raise ValueError(f"Missing checksummed audio member: {member}")
            if zip_member_sha256(archive, member) != expected:
                raise ValueError(f"Audio member checksum mismatch: {member}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir", type=Path)
    args = parser.parse_args()
    package_dir = args.package_dir.resolve()

    observed_files = {path.name for path in package_dir.iterdir() if path.is_file()}
    if observed_files != EXPECTED_FILES:
        missing = sorted(EXPECTED_FILES - observed_files)
        extra = sorted(observed_files - EXPECTED_FILES)
        raise SystemExit(f"Unexpected package file set; missing={missing}, extra={extra}")

    manifest_path = package_dir / f"{RELEASE_STEM}_MANIFEST.csv"
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        manifest = list(csv.DictReader(stream))
    if len(manifest) != 6:
        raise SystemExit(f"Expected 6 deposited-file manifest rows, found {len(manifest)}")

    errors: list[str] = []
    for row in manifest:
        path = package_dir / row["file_name"]
        if row["file_name"] == manifest_path.name:
            errors.append("Upload manifest must not contain a circular self-entry")
        elif not path.is_file():
            errors.append(f"Missing manifested file: {path.name}")
        elif path.stat().st_size != int(row["size_bytes"]):
            errors.append(f"Size mismatch: {path.name}")
        elif sha256(path) != row["sha256"]:
            errors.append(f"Checksum mismatch: {path.name}")

    checksum_path = package_dir / f"{RELEASE_STEM}_SHA256SUMS.txt"
    top_checksums = read_checksum_lines(checksum_path.read_text(encoding="ascii"))
    expected_checksum_names = EXPECTED_FILES - {manifest_path.name, checksum_path.name}
    if set(top_checksums) != expected_checksum_names:
        errors.append("Top-level checksum inventory has incorrect coverage")
    else:
        for name, expected in top_checksums.items():
            if sha256(package_dir / name) != expected:
                errors.append(f"Top-level checksum mismatch: {name}")

    benchmark_kit = package_dir / f"{RELEASE_STEM}_benchmark-kit.zip"
    try:
        with zipfile.ZipFile(benchmark_kit) as archive:
            if archive.testzip():
                errors.append("Benchmark kit failed ZIP integrity validation")
            if any(name.lower().endswith(".wav") for name in archive.namelist()):
                errors.append("Benchmark kit contains WAV payloads")
    except zipfile.BadZipFile:
        errors.append("Benchmark kit is not a valid ZIP")

    audio_package = package_dir / f"{RELEASE_STEM}_ISD-audio.zip"
    audio_manifest = package_dir / f"{RELEASE_STEM}_ISD-audio-manifest.csv"
    try:
        validate_audio_package(audio_package, audio_manifest)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        errors.append(f"Audio package: {error}")

    if errors:
        print(f"RDR package validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(
        "RDR package validation passed: 7 top-level files, 1 benchmark kit, "
        "1 ZIP64 audio package, 820 unique WAV files (546 train / 154 dev / 120 test)"
    )


if __name__ == "__main__":
    main()

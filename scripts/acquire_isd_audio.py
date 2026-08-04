#!/usr/bin/env python3
"""Acquire and verify selected ISD files from the official Zenodo record."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD_ID = "10672568"
DEFAULT_REGISTRY = ROOT / "benchmark/governance/isd_zenodo_source_registry.csv"
REGISTRY_FIELDS = [
    "dataset_id",
    "source_record",
    "source_version",
    "file_name",
    "file_role",
    "benchmark_scope_status",
    "size_bytes",
    "checksum_algorithm",
    "checksum",
    "download_url",
    "licence_spdx",
    "redistribution_status",
    "metadata_checked_at",
    "local_status",
    "local_relative_path",
]


def fetch_record(record_id: str) -> dict:
    url = f"https://zenodo.org/api/records/{record_id}"
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def file_role(name: str) -> str:
    if name.startswith("WAV_") and name.endswith(".zip"):
        return "audio_archive"
    if name.startswith("SLM_") and name.endswith(".zip"):
        return "sound_level_archive"
    if name == "ISD v1.0 Data.csv":
        return "tabular_data"
    if "Metadata" in name:
        return "metadata"
    if name == "Survey_Data.zip":
        return "survey_archive"
    if name == "Scripts.zip":
        return "source_code"
    return "other"


def benchmark_scope_status(name: str) -> str:
    if name in {"WAV_Lockdown_London.zip", "WAV_Lockdown_Venice.zip"}:
        return "source_audit_only_pending_label_linkage"
    if file_role(name) == "audio_archive":
        return "benchmark_candidate"
    return "supporting_source_file"


def checksum(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_size: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    existing = destination.stat().st_size if destination.exists() else 0
    if existing == expected_size:
        return
    if existing > expected_size:
        destination.unlink()
        existing = 0

    request = urllib.request.Request(url)
    if existing:
        request.add_header("Range", f"bytes={existing}-")
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as error:
        if error.code != 416:
            raise
        destination.unlink(missing_ok=True)
        response = urllib.request.urlopen(url)
        existing = 0

    append = existing > 0 and getattr(response, "status", 200) == 206
    mode = "ab" if append else "wb"
    with response, destination.open(mode) as stream:
        shutil.copyfileobj(response, stream, length=1024 * 1024)

    if destination.stat().st_size != expected_size:
        raise RuntimeError(
            f"Size mismatch for {destination.name}: "
            f"{destination.stat().st_size} != {expected_size}"
        )


def safe_extract_wavs(archive: Path, extraction_root: Path) -> int:
    extracted = 0
    archive_root = extraction_root / archive.stem
    archive_root.mkdir(parents=True, exist_ok=True)
    root = archive_root.resolve()
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            member_path = Path(member.filename)
            if member.is_dir() or "__MACOSX" in member_path.parts:
                continue
            if member_path.suffix.lower() != ".wav":
                continue
            relative = member_path
            if member_path.parts and member_path.parts[0] == archive.stem:
                relative = Path(*member_path.parts[1:])
            destination = (archive_root / relative).resolve()
            if not destination.is_relative_to(root):
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with package.open(member) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            extracted += 1
    return extracted


def write_registry(
    record: dict,
    storage_root: Path,
    selected: set[str],
    registry_path: Path,
    checked_at: str,
) -> None:
    version = str(record["metadata"].get("version", ""))
    licence = record["metadata"].get("license", {})
    licence_id = licence.get("id", "unknown").upper()
    if licence_id == "CC-BY-4.0":
        licence_id = "CC-BY-4.0"

    rows = []
    for item in sorted(record["files"], key=lambda value: value["key"]):
        name = item["key"]
        algorithm, expected = item["checksum"].split(":", 1)
        local = storage_root / "archives" / name
        status = "not_downloaded"
        relative = ""
        if local.exists():
            relative = local.relative_to(storage_root).as_posix()
            valid = (
                local.stat().st_size == int(item["size"])
                and checksum(local, algorithm) == expected
            )
            status = "downloaded_verified" if valid else "downloaded_invalid"
        rows.append(
            {
                "dataset_id": "ISD",
                "source_record": f"https://doi.org/10.5281/zenodo.{record['id']}",
                "source_version": version,
                "file_name": name,
                "file_role": file_role(name),
                "benchmark_scope_status": benchmark_scope_status(name),
                "size_bytes": item["size"],
                "checksum_algorithm": algorithm,
                "checksum": expected,
                "download_url": item["links"]["self"],
                "licence_spdx": licence_id,
                "redistribution_status": "permitted_with_attribution",
                "metadata_checked_at": checked_at,
                "local_status": status,
                "local_relative_path": relative,
            }
        )

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-id", default=DEFAULT_RECORD_ID)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--all-audio", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--registry-out", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args()

    record = fetch_record(args.record_id)
    available = {item["key"]: item for item in record["files"]}
    selected = set(args.file)
    if args.all_audio:
        selected.update(name for name in available if file_role(name) == "audio_archive")
    unknown = sorted(selected - available.keys())
    if unknown:
        raise SystemExit(f"Unknown Zenodo file(s): {', '.join(unknown)}")
    if not selected and not args.metadata_only:
        raise SystemExit("Select --file, --all-audio, or --metadata-only")

    for name in sorted(selected):
        item = available[name]
        destination = args.storage_root / "archives" / name
        download(item["links"]["self"], destination, int(item["size"]))
        algorithm, expected = item["checksum"].split(":", 1)
        actual = checksum(destination, algorithm)
        if actual != expected:
            raise RuntimeError(f"Checksum mismatch for {name}: {actual} != {expected}")
        print(f"VERIFIED {name} ({item['size']} bytes, {algorithm}:{actual})")
        if args.extract and name.endswith(".zip") and file_role(name) == "audio_archive":
            count = safe_extract_wavs(destination, args.storage_root / "extracted")
            print(f"EXTRACTED {count} WAV files from {name}")

    write_registry(
        record,
        args.storage_root,
        selected,
        args.registry_out,
        args.as_of,
    )
    print(f"WROTE {args.registry_out}")


if __name__ == "__main__":
    main()

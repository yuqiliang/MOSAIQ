#!/usr/bin/env python3
"""Freeze and optionally download the official ARAUS v1 audio sources."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


DATASET_DOI = "doi:10.21979/N9/9OTEVX"
DATASET_API = (
    "https://researchdata.ntu.edu.sg/api/datasets/:persistentId/"
    f"?persistentId={DATASET_DOI}"
)
ACCESS_API = "https://researchdata.ntu.edu.sg/api/access/datafile/{file_id}"
USOTW_RECORD_ID = "10106181"
USOTW_API = f"https://zenodo.org/api/records/{USOTW_RECORD_ID}"
USOTW_DOI = "doi:10.5281/zenodo.10106181"
EXPECTED_VERSION = "4.2"
EXPECTED_LICENSE = "CC BY-NC 4.0"
V1_INCLUDE_FILES = {
    "data.zip",
    "maskers.zip",
    "soundscapes.zip",
}
V2_DEFERRED_FILES = {"datav2.zip", "maskersv2.zip"}
NON_BENCHMARK_FILES = {"figures.zip"}
VISUAL_DEFERRED_FILES = {"videos.zip"}
REFERENCE_ONLY_FILES = {"soundscapes_raw.zip"}
EXPECTED_NTU_FILES = (
    V1_INCLUDE_FILES
    | V2_DEFERRED_FILES
    | NON_BENCHMARK_FILES
    | VISUAL_DEFERRED_FILES
    | REFERENCE_ONLY_FILES
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "MOSAIQ/0.2.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def classify_file(name: str, restricted: bool) -> tuple[str, str]:
    if name in REFERENCE_ONLY_FILES or restricted:
        return (
            "reference_only",
            "Official record restricts access and states that ARAUS cannot redistribute the USotW recordings.",
        )
    if name in V1_INCLUDE_FILES:
        return (
            "private_draft_candidate",
            "Required by the ARAUS v1 benchmark; public MOSAIQ redistribution rights remain under review.",
        )
    if name in V2_DEFERRED_FILES:
        return "deferred_araus_v2", "ARAUS v2 is outside the current MOSAIQ task scope."
    if name in VISUAL_DEFERRED_FILES:
        return "deferred_visual", "Visual stimuli are outside the current audio benchmark scope."
    if name in NON_BENCHMARK_FILES:
        return "excluded_nonbenchmark", "Paper figures are not benchmark input data."
    return "excluded_unexpected", "File is outside the frozen ARAUS draft scope."


def freeze_metadata(payload: dict[str, object], storage_root: Path) -> list[dict[str, object]]:
    if payload.get("status") != "OK":
        raise ValueError("Dataverse API did not return status OK")
    data = payload["data"]
    assert isinstance(data, dict)
    version = data["latestVersion"]
    assert isinstance(version, dict)
    observed_version = f"{version['versionNumber']}.{version['versionMinorNumber']}"
    if observed_version != EXPECTED_VERSION:
        raise ValueError(
            f"Expected ARAUS version {EXPECTED_VERSION}, found {observed_version}"
        )
    license_data = version.get("license", {})
    assert isinstance(license_data, dict)
    if license_data.get("name") != EXPECTED_LICENSE:
        raise ValueError(
            f"Expected {EXPECTED_LICENSE}, found {license_data.get('name')}"
        )

    metadata_path = storage_root / "source_metadata_v4.2.json"
    metadata_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    records: list[dict[str, object]] = []
    for item in version["files"]:
        assert isinstance(item, dict)
        data_file = item["dataFile"]
        assert isinstance(data_file, dict)
        name = str(data_file["filename"])
        restricted = bool(item.get("restricted", False))
        status, note = classify_file(name, restricted)
        records.append(
            {
                "file_name": name,
                "file_id": data_file["id"],
                "source_provider": "Nanyang Technological University Dataverse",
                "source_record": DATASET_DOI,
                "version": observed_version,
                "license": license_data["name"],
                "restricted": str(restricted).lower(),
                "draft_status": status,
                "size_bytes": data_file["filesize"],
                "source_md5": data_file["md5"],
                "download_url": ACCESS_API.format(file_id=data_file["id"]),
                "local_status": "not_downloaded",
                "local_sha256": "",
                "rights_note": note,
            }
        )
    names = {str(record["file_name"]) for record in records}
    if names != EXPECTED_NTU_FILES:
        raise ValueError(
            f"Official ARAUS file set changed; missing={sorted(EXPECTED_NTU_FILES - names)}, "
            f"extra={sorted(names - EXPECTED_NTU_FILES)}"
        )
    return records


def freeze_usotw_metadata(payload: dict[str, object], storage_root: Path) -> dict[str, object]:
    metadata = payload.get("metadata", {})
    assert isinstance(metadata, dict)
    if payload.get("id") != int(USOTW_RECORD_ID) or metadata.get("title") != "Urban Soundscapes of the World":
        raise ValueError("Unexpected USotW Zenodo record")
    license_data = metadata.get("license", {})
    assert isinstance(license_data, dict)
    if license_data.get("id") != "cc-by-4.0":
        raise ValueError(f"Expected USotW CC BY 4.0, found {license_data.get('id')}")

    metadata_path = storage_root / "usotw_source_metadata_10106181.json"
    metadata_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    files = payload.get("files", [])
    assert isinstance(files, list)
    matches = [item for item in files if isinstance(item, dict) and item.get("key") == "binaural.zip"]
    if len(matches) != 1:
        raise ValueError("USotW record does not contain exactly one binaural.zip")
    item = matches[0]
    links = item.get("links", {})
    assert isinstance(links, dict)
    checksum = str(item["checksum"])
    if not checksum.startswith("md5:"):
        raise ValueError("Unexpected USotW checksum format")
    return {
        "file_name": "binaural.zip",
        "file_id": f"zenodo:{USOTW_RECORD_ID}:binaural.zip",
        "source_provider": "Zenodo",
        "source_record": USOTW_DOI,
        "version": str(metadata.get("publication_date", "record-10106181")),
        "license": "CC BY 4.0",
        "restricted": "false",
        "draft_status": "private_draft_candidate",
        "size_bytes": item["size"],
        "source_md5": checksum.removeprefix("md5:"),
        "download_url": links["self"],
        "local_status": "not_downloaded",
        "local_sha256": "",
        "rights_note": (
            "Official USotW binaural source used by ARAUS; included in the private draft "
            "while record-level redistribution wording is reviewed."
        ),
    }


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "file_name",
        "file_id",
        "source_provider",
        "source_record",
        "version",
        "license",
        "restricted",
        "draft_status",
        "size_bytes",
        "source_md5",
        "download_url",
        "local_status",
        "local_sha256",
        "rights_note",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: str(row["file_name"])))


def download_file(record: dict[str, object], archive_dir: Path) -> None:
    destination = archive_dir / str(record["file_name"])
    expected_size = int(record["size_bytes"])
    expected_md5 = str(record["source_md5"])
    if destination.is_file():
        if destination.stat().st_size == expected_size and md5(destination) == expected_md5:
            record["local_status"] = "verified"
            record["local_sha256"] = sha256(destination)
            return
        raise ValueError(f"Existing local archive does not match source: {destination}")

    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    subprocess.run(
        [
            "curl",
            "--location",
            "--fail",
            "--show-error",
            "--retry",
            "5",
            "--retry-all-errors",
            "--connect-timeout",
            "30",
            "--remove-on-error",
            "--output",
            str(temporary),
            str(record["download_url"]),
        ],
        check=True,
    )
    if temporary.stat().st_size != expected_size:
        raise ValueError(f"Downloaded size mismatch: {record['file_name']}")
    if md5(temporary) != expected_md5:
        raise ValueError(f"Downloaded MD5 mismatch: {record['file_name']}")
    temporary.replace(destination)
    record["local_status"] = "verified"
    record["local_sha256"] = sha256(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()

    storage_root = args.storage_root.resolve()
    archive_dir = storage_root / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    payload = fetch_json(DATASET_API)
    records = freeze_metadata(payload, storage_root)
    records.append(freeze_usotw_metadata(fetch_json(USOTW_API), storage_root))
    if args.download:
        for record in records:
            if record["draft_status"] == "private_draft_candidate":
                print(f"Downloading {record['file_name']}...")
                download_file(record, archive_dir)
    manifest_path = storage_root / "araus_source_manifest_v4.2.csv"
    write_manifest(manifest_path, records)
    verified = sum(record["local_status"] == "verified" for record in records)
    print(
        f"Frozen ARAUS v{EXPECTED_VERSION} and USotW record {USOTW_RECORD_ID}: "
        f"{len(records)} source files, {verified} verified locally, "
        "1 reference-only restricted archive"
    )
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()

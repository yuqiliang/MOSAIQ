#!/usr/bin/env python3
"""Build the consolidated MOSAIQ release-candidate package set for UCL RDR."""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import stat
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DATE = (2026, 7, 31, 0, 0, 0)
RELEASE_STEM = "MOSAIQ-v0.2.0-rc1"
SOURCE_RECORD = "https://doi.org/10.5281/zenodo.10672568"
SOURCE_VERSION = "1.0.1-alpha.1"
EXPECTED_SPLITS = {"train": 546, "dev": 154, "test": 120}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_manifest(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"Manifest has no header: {path}")
        rows = [row for row in reader if row["use_for_benchmark"].lower() == "true"]
        return list(reader.fieldnames), rows


def validate_member_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe archive member path: {value}")
    return path


def write_csv(
    path: Path, fieldnames: list[str], rows: list[dict[str, str | int]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def add_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=ARCHIVE_DATE)
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)


def audio_package_readme() -> str:
    return f"""# MOSAIQ ISD audio reference extension

This ZIP64 package contains 820 accepted stereo WAV files used by the MOSAIQ
ISD audio reference track v0.1.0: 546 train, 154 development, and 120 test.

Source: {SOURCE_RECORD}
Source version: `{SOURCE_VERSION}`
Source licence: CC BY 4.0

Audio is organised under `audio/train`, `audio/dev`, and `audio/test`. The
embedded `audio_manifest.csv` maps every member to its MOSAIQ clip ID, frozen
split, original source archive and member path, byte size, and SHA-256 digest.
`checksums.sha256` covers the README, manifest, and all 820 WAV members.

All included files passed technical readability, finite-sample, non-empty,
non-silent, stereo, and duration checks. Calibration remains pending, so
waveform amplitudes must not be interpreted as calibrated sound levels.

This extension is ISD-only. It contains no ARAUS, SATP, DeLTA, lockdown,
visual, participant-response, or Paper 2 manuscript payloads. Consult the
top-level MOSAIQ README, licence statement, and audio manifest before reuse.
"""


def with_package_members(
    fieldnames: list[str], rows: list[dict[str, str]], root: PurePosixPath
) -> tuple[list[str], list[dict[str, str]]]:
    output_fields = [*fieldnames, "package_member"]
    output_rows: list[dict[str, str]] = []
    for row in sorted(rows, key=lambda item: (item["split"], item["member_path"])):
        split = row["split"]
        if split not in EXPECTED_SPLITS:
            raise ValueError(f"Unexpected split for accepted audio: {split}")
        member = root / "audio" / split / validate_member_path(row["member_path"])
        output_rows.append({**row, "package_member": member.as_posix()})
    return output_fields, output_rows


def build_audio_package(
    output: Path,
    audio_root: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> tuple[Path, Path]:
    package_stem = f"{RELEASE_STEM}_ISD-audio"
    package_path = output / f"{package_stem}.zip"
    public_manifest_path = output / f"{RELEASE_STEM}_ISD-audio-manifest.csv"
    root = PurePosixPath(package_stem)
    manifest_fields, package_rows = with_package_members(fieldnames, rows, root)
    write_csv(public_manifest_path, manifest_fields, package_rows)
    manifest_bytes = public_manifest_path.read_bytes()
    readme_bytes = audio_package_readme().encode("utf-8")
    checksum_lines = [
        f"{sha256_bytes(readme_bytes)}  README.md\n",
        f"{sha256_bytes(manifest_bytes)}  audio_manifest.csv\n",
    ]

    with zipfile.ZipFile(
        package_path,
        "w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
    ) as archive:
        add_bytes(archive, (root / "README.md").as_posix(), readme_bytes)
        add_bytes(archive, (root / "audio_manifest.csv").as_posix(), manifest_bytes)

        for row in package_rows:
            source = audio_root / row["local_relative_path"]
            if not source.is_file():
                raise FileNotFoundError(f"Missing accepted audio asset: {source}")
            if source.stat().st_size != int(row["bytes"]):
                raise ValueError(f"Byte-size mismatch: {source}")
            observed_digest = sha256(source)
            if observed_digest != row["audio_sha256"]:
                raise ValueError(f"SHA-256 mismatch: {source}")

            member = PurePosixPath(row["package_member"])
            checksum_lines.append(
                f"{observed_digest}  {member.relative_to(root).as_posix()}\n"
            )
            info = zipfile.ZipInfo(member.as_posix(), date_time=ARCHIVE_DATE)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_STORED
            with source.open("rb") as stream, archive.open(
                info, "w", force_zip64=True
            ) as target:
                shutil.copyfileobj(stream, target, length=8 * 1024 * 1024)

        add_bytes(
            archive,
            (root / "checksums.sha256").as_posix(),
            "".join(checksum_lines).encode("ascii"),
        )

    return package_path, public_manifest_path


def release_readme(benchmark_kit: Path, audio_package: Path) -> str:
    return f"""# MOSAIQ soundscape benchmark v0.2.0-rc1

## Start here

This private UCL RDR draft contains the MOSAIQ benchmark kit and a separate
ISD-only audio reference extension. It is a release candidate, not a public
MOSAIQ-v1.0 release, and must not be submitted for review or assigned a DOI
until the outstanding governance and authorship gates are complete.

## Files

- `{benchmark_kit.name}`: harmonised tabular data, schemas, seven task
  contracts, deterministic splits, evaluation code, baseline predictions,
  robustness outputs, model/data cards, tests, and Paper 2 fixed outputs.
- `{audio_package.name}`: one ZIP64 archive containing 820 accepted ISD WAV
  files organised as 546 train, 154 development, and 120 test files.
- `{RELEASE_STEM}_ISD-audio-manifest.csv`: inspect audio provenance, split,
  source archive, QC metadata, package member path, byte size, and SHA-256
  without downloading the 9.6 GiB audio archive.
- `{RELEASE_STEM}_LICENSES.md`: licensing scope, rights, and attribution.
- `{RELEASE_STEM}_MANIFEST.csv`: role, size, and checksum for each deposited
  package file.
- `{RELEASE_STEM}_SHA256SUMS.txt`: checksums for the downloadable content.

## Use

For the no-audio tabular benchmark, download only the benchmark kit. For the
ISD audio reference track, also download the audio ZIP and audio manifest.
After extraction, follow `RDR_README.md` and `docs/reproduce_benchmark.md` in
the benchmark kit.

Verify downloaded files with:

```bash
shasum -a 256 -c {RELEASE_STEM}_SHA256SUMS.txt
```

## Scope boundary

The audio extension contains ISD audio only. No ARAUS, SATP, or DeLTA raw
media are redistributed. Waveform calibration remains under review, so audio
amplitudes must not be interpreted as calibrated sound levels. The Word
manuscript is not part of this deposit.
"""


def licences_text() -> str:
    data_licence = (REPO_ROOT / "DATA_LICENSE.md").read_text(encoding="utf-8")
    attribution = (
        REPO_ROOT / "benchmark/audio/RIGHTS_AND_ATTRIBUTION.md"
    ).read_text(encoding="utf-8")
    return (
        "# MOSAIQ release-candidate licences and attribution\n\n"
        "This consolidated file is an access aid. Source-specific terms remain "
        "authoritative.\n\n"
        "## MOSAIQ data licensing policy\n\n"
        f"{data_licence.removeprefix('# MOSAIQ data licensing').lstrip()}\n\n"
        "## ISD audio rights and attribution\n\n"
        f"{attribution.removeprefix('# ISD audio rights and attribution').lstrip()}"
    )


def record(path: Path, role: str, n_assets: str | int = "") -> dict[str, str | int]:
    return {
        "file_name": path.name,
        "role": role,
        "version": "0.2.0-rc1",
        "n_assets": n_assets,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--benchmark-kit", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "benchmark/audio/manifests/isd_audio_manifest_v0.1.0.csv",
    )
    args = parser.parse_args()

    output = args.output_dir.resolve()
    audio_root = args.audio_root.resolve()
    benchmark_source = args.benchmark_kit.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError(f"Output directory must be empty: {output}")
    if not benchmark_source.is_file():
        raise FileNotFoundError(f"Missing benchmark kit: {benchmark_source}")

    fieldnames, rows = read_manifest(args.manifest.resolve())
    if len(rows) != 820:
        raise ValueError(f"Expected 820 accepted assets, found {len(rows)}")
    if dict(Counter(row["split"] for row in rows)) != EXPECTED_SPLITS:
        raise ValueError("Accepted audio split counts do not match the frozen cohort")

    benchmark_kit = output / f"{RELEASE_STEM}_benchmark-kit.zip"
    shutil.copy2(benchmark_source, benchmark_kit)
    with zipfile.ZipFile(benchmark_kit) as archive:
        if archive.testzip():
            raise ValueError("Benchmark kit failed ZIP integrity validation")
        if any(name.lower().endswith(".wav") for name in archive.namelist()):
            raise ValueError("Benchmark kit unexpectedly contains WAV files")

    audio_package, audio_manifest = build_audio_package(
        output, audio_root, fieldnames, rows
    )
    readme = output / f"{RELEASE_STEM}_README.md"
    readme.write_text(release_readme(benchmark_kit, audio_package), encoding="utf-8")
    licences = output / f"{RELEASE_STEM}_LICENSES.md"
    licences.write_text(licences_text(), encoding="utf-8")

    content_records = [
        record(readme, "entry_documentation"),
        record(licences, "licensing_and_attribution"),
        record(benchmark_kit, "benchmark_kit"),
        record(audio_package, "isd_audio_extension", 820),
        record(audio_manifest, "isd_audio_manifest", 820),
    ]
    checksums = output / f"{RELEASE_STEM}_SHA256SUMS.txt"
    checksums.write_text(
        "".join(f"{row['sha256']}  {row['file_name']}\n" for row in content_records),
        encoding="ascii",
    )
    deposited_records = [*content_records, record(checksums, "checksum_inventory")]
    deposited_records.sort(key=lambda row: str(row["file_name"]))
    upload_manifest = output / f"{RELEASE_STEM}_MANIFEST.csv"
    write_csv(
        upload_manifest,
        ["file_name", "role", "version", "n_assets", "size_bytes", "sha256"],
        deposited_records,
    )

    print(f"Built 1 ZIP64 audio package containing {len(rows)} accepted WAV files")
    print(f"Audio package: {audio_package}")
    print(f"Audio bytes: {audio_package.stat().st_size}")
    print(f"Wrote 7-file RDR package set to {output}")


if __name__ == "__main__":
    main()

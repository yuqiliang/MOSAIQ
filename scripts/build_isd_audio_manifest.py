#!/usr/bin/env python3
"""Build a source-aware ISD audio manifest linked to MOSAIQ clips and splits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import yaml
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RECORD = "https://doi.org/10.5281/zenodo.10672568"
SOURCE_VERSION = "1.0.1-alpha.1"
FIELDS = [
    "asset_id",
    "dataset_id",
    "clip_id",
    "split",
    "source_record",
    "source_version",
    "archive_name",
    "member_path",
    "local_relative_path",
    "source_uri",
    "licence_spdx",
    "redistribution_status",
    "access_class",
    "group_id_normalized",
    "location_hint",
    "audio_sha256",
    "bytes",
    "format",
    "sample_rate_hz",
    "channels",
    "frames",
    "duration_s",
    "expected_duration_s",
    "sample_dtype",
    "calibration_status",
    "materialization_status",
    "mapping_status",
    "use_for_benchmark",
    "mapping_notes",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_group_id(filename: str) -> str:
    value = Path(filename).stem
    value = re.sub(r"\.hdf$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\.\d+$", "", value)
    return value.strip()


def asset_id(member_path: str) -> str:
    return f"isd_audio_{hashlib.sha256(member_path.encode('utf-8')).hexdigest()[:20]}"


def wav_metadata(path: Path) -> dict:
    rate, data = wavfile.read(path, mmap=True)
    frames = int(data.shape[0])
    channels = 1 if data.ndim == 1 else int(data.shape[1])
    return {
        "sample_rate_hz": int(rate),
        "channels": channels,
        "frames": frames,
        "duration_s": frames / float(rate),
        "sample_dtype": str(data.dtype),
    }


def expected_duration(row: pd.Series) -> float | None:
    start = pd.to_numeric(row.get("binaural_start_s"), errors="coerce")
    end = pd.to_numeric(row.get("binaural_end_s"), errors="coerce")
    if pd.isna(end):
        return None
    return float(end - (0.0 if pd.isna(start) else start))


def build_rows(
    storage_root: Path,
    archive_names: list[str],
    clips_path: Path,
    splits_path: Path,
) -> list[dict]:
    clips = pd.read_csv(clips_path, dtype=str, keep_default_na=False)
    splits = pd.read_csv(splits_path, dtype=str, keep_default_na=False)
    split_by_clip = dict(zip(splits["clip_id"], splits["split"], strict=True))
    clips_by_group: dict[str, list[pd.Series]] = defaultdict(list)
    for _, row in clips.iterrows():
        clips_by_group[str(row["GroupID"]).strip()].append(row)

    rows: list[dict] = []
    scope_locations: set[str] = set()
    for archive_name in archive_names:
        archive_stem = Path(archive_name).stem
        audio_root = storage_root / "extracted" / archive_stem
        archive_path = storage_root / "archives" / archive_name
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive is not materialized: {archive_path}")
        with zipfile.ZipFile(archive_path) as package:
            members = sorted(
                member.filename
                for member in package.infolist()
                if not member.is_dir()
                and "__MACOSX" not in Path(member.filename).parts
                and Path(member.filename).suffix.lower() == ".wav"
            )
        if not members:
            raise FileNotFoundError(f"No WAV members found in {archive_path}")

        for member in members:
            member_path = Path(member)
            local_subpath = member_path
            if member_path.parts and member_path.parts[0] == archive_stem:
                local_subpath = Path(*member_path.parts[1:])
            path = audio_root / local_subpath
            if not path.exists():
                raise FileNotFoundError(
                    f"Extracted WAV is missing for {archive_name}:{member}"
                )
            relative = path.relative_to(storage_root).as_posix()
            location = member_path.parent.name
            scope_locations.add(location.casefold())
            group = normalize_group_id(member_path.name)
            candidates = clips_by_group.get(group, [])
            location_candidates = [
                row
                for row in candidates
                if str(row["LocationID"]).strip().casefold() == location.casefold()
            ]
            if len(location_candidates) == 1:
                match = location_candidates[0]
                status = "matched"
                note = "Matched by normalized GroupID and LocationID."
            elif len(candidates) == 1:
                match = candidates[0]
                status = "matched"
                note = "Matched by normalized GroupID; source location hint was not required."
            elif not candidates:
                match = None
                status = "unmatched_source_asset"
                note = "No MOSAIQ clip has this normalized GroupID."
            else:
                match = None
                status = "ambiguous_clip_match"
                note = f"{len(candidates)} MOSAIQ clips share this normalized GroupID."

            digest = sha256(path)
            technical = wav_metadata(path)
            clip_id = "" if match is None else str(match["clip_id"])
            clip_split = split_by_clip.get(clip_id, "")
            use_for_benchmark = status == "matched" and clip_split in {
                "train",
                "dev",
                "test",
            }
            if status == "matched" and not use_for_benchmark:
                note += " Linked clip is excluded by the frozen split."
            row = {
                "asset_id": asset_id(f"{archive_name}:{member}"),
                "dataset_id": "ISD",
                "clip_id": clip_id,
                "split": clip_split,
                "source_record": SOURCE_RECORD,
                "source_version": SOURCE_VERSION,
                "archive_name": archive_name,
                "member_path": member,
                "local_relative_path": relative,
                "source_uri": (
                    "https://zenodo.org/api/records/10672568/files/"
                    f"{quote(archive_name)}/content"
                ),
                "licence_spdx": "CC-BY-4.0",
                "redistribution_status": "permitted_with_attribution",
                "access_class": "open",
                "group_id_normalized": group,
                "location_hint": location,
                "audio_sha256": digest,
                "bytes": path.stat().st_size,
                "format": "WAV",
                **technical,
                "expected_duration_s": "" if match is None else expected_duration(match),
                "calibration_status": "source_metadata_review_pending",
                "materialization_status": "materialized",
                "mapping_status": status,
                "use_for_benchmark": use_for_benchmark,
                "mapping_notes": note,
            }
            rows.append(row)

    by_clip: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["mapping_status"] == "matched":
            by_clip[row["clip_id"]].append(row)
    for clip_id, matches in by_clip.items():
        if len(matches) < 2:
            continue
        digests = {row["audio_sha256"] for row in matches}
        if len(digests) == 1:
            for duplicate in sorted(matches, key=lambda row: row["member_path"])[1:]:
                duplicate["mapping_status"] = "exact_duplicate_excluded"
                duplicate["use_for_benchmark"] = False
                duplicate["mapping_notes"] = (
                    f"Byte-identical duplicate for {clip_id}; canonical member is "
                    f"{sorted(matches, key=lambda row: row['member_path'])[0]['member_path']}."
                )
        else:
            for conflict in matches:
                conflict["mapping_status"] = "duplicate_conflict"
                conflict["use_for_benchmark"] = False
                conflict["mapping_notes"] = (
                    f"Multiple non-identical source files map to {clip_id}; manual review required."
                )

    represented = {
        row["clip_id"]
        for row in rows
        if row["clip_id"] and row["mapping_status"] in {"matched", "exact_duplicate_excluded"}
    }
    scope = clips[
        clips["LocationID"].str.strip().str.casefold().isin(scope_locations)
    ]
    for _, clip in scope.iterrows():
        clip_id = str(clip["clip_id"])
        if clip_id in represented:
            continue
        group = str(clip["GroupID"]).strip()
        rows.append(
            {
                "asset_id": f"isd_audio_missing_{hashlib.sha256(clip_id.encode()).hexdigest()[:16]}",
                "dataset_id": "ISD",
                "clip_id": clip_id,
                "split": split_by_clip.get(clip_id, ""),
                "source_record": SOURCE_RECORD,
                "source_version": SOURCE_VERSION,
                "archive_name": ";".join(archive_names),
                "member_path": "",
                "local_relative_path": "",
                "source_uri": SOURCE_RECORD,
                "licence_spdx": "CC-BY-4.0",
                "redistribution_status": "permitted_with_attribution",
                "access_class": "open",
                "group_id_normalized": group,
                "location_hint": str(clip["LocationID"]).strip(),
                "audio_sha256": "",
                "bytes": "",
                "format": "",
                "sample_rate_hz": "",
                "channels": "",
                "frames": "",
                "duration_s": "",
                "expected_duration_s": expected_duration(clip),
                "sample_dtype": "",
                "calibration_status": "not_available",
                "materialization_status": "source_missing",
                "mapping_status": "missing_source_asset",
                "use_for_benchmark": False,
                "mapping_notes": "MOSAIQ clip is in the archive location scope but no WAV candidate exists.",
            }
        )
    return sorted(rows, key=lambda row: (row["clip_id"], row["member_path"], row["asset_id"]))


def write_manifest(rows: list[dict], output: Path, summary: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    statuses = Counter(row["mapping_status"] for row in rows)
    usable = [row for row in rows if row["use_for_benchmark"]]
    scope_clips = {row["clip_id"] for row in rows if row["clip_id"]}
    summary_data = {
        "schema_version": "0.1",
        "source_record": SOURCE_RECORD,
        "source_version": SOURCE_VERSION,
        "rows": len(rows),
        "scope_clips": len(scope_clips),
        "usable_assets": len(usable),
        "usable_clips": len({row["clip_id"] for row in usable}),
        "mapping_status_counts": dict(sorted(statuses.items())),
        "split_counts": dict(sorted(Counter(row["split"] for row in usable).items())),
        "complete": all(row["mapping_status"] == "matched" for row in rows),
    }
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(yaml.safe_dump(summary_data, sort_keys=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--archive", action="append", required=True)
    parser.add_argument(
        "--clips",
        type=Path,
        default=ROOT / "datasets/ISD/data/clips.csv",
    )
    parser.add_argument(
        "--splits",
        type=Path,
        default=ROOT / "benchmark/splits/isd_split.csv",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    rows = build_rows(args.storage_root, args.archive, args.clips, args.splits)
    write_manifest(rows, args.output, args.summary)
    print(f"WROTE {args.output} ({len(rows)} rows)")
    print(f"WROTE {args.summary}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate MOSAIQ audio manifests and split-leakage constraints."""

from __future__ import annotations

import argparse
import re
from pathlib import Path, PurePosixPath

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = {
    "asset_id",
    "dataset_id",
    "clip_id",
    "split",
    "source_record",
    "source_version",
    "archive_name",
    "member_path",
    "local_relative_path",
    "licence_spdx",
    "audio_sha256",
    "sample_rate_hz",
    "channels",
    "duration_s",
    "materialization_status",
    "mapping_status",
    "use_for_benchmark",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().map({"true": True, "false": False})


def validate(
    manifest_path: Path,
    clips_path: Path,
    splits_path: Path,
    require_complete: bool,
) -> tuple[list[str], list[str]]:
    manifest = pd.read_csv(manifest_path, dtype=str, keep_default_na=False)
    missing_columns = sorted(REQUIRED_COLUMNS - set(manifest.columns))
    if missing_columns:
        return [f"Missing columns: {', '.join(missing_columns)}"], []

    errors: list[str] = []
    warnings: list[str] = []
    if manifest["asset_id"].duplicated().any():
        errors.append("asset_id must be unique")

    clips = pd.read_csv(clips_path, dtype=str, keep_default_na=False)
    splits = pd.read_csv(splits_path, dtype=str, keep_default_na=False)
    valid_clips = set(clips["clip_id"])
    split_by_clip = dict(zip(splits["clip_id"], splits["split"], strict=True))
    use = as_bool(manifest["use_for_benchmark"])
    if use.isna().any():
        errors.append("use_for_benchmark must contain only true/false")
        use = use.fillna(False)

    for index, row in manifest.iterrows():
        label = f"row {index + 2} ({row['asset_id']})"
        clip_id = row["clip_id"]
        if clip_id and clip_id not in valid_clips:
            errors.append(f"{label}: unknown clip_id {clip_id}")
        if clip_id and row["split"] != split_by_clip.get(clip_id, ""):
            errors.append(f"{label}: split does not match frozen clip split")
        local_path = row["local_relative_path"]
        if local_path:
            pure = PurePosixPath(local_path)
            if pure.is_absolute() or ".." in pure.parts:
                errors.append(f"{label}: local_relative_path must be safe and relative")
        if use.iloc[index]:
            if row["mapping_status"] != "matched":
                errors.append(f"{label}: benchmark asset must have mapping_status=matched")
            if row["materialization_status"] != "materialized":
                errors.append(f"{label}: benchmark asset must be materialized")
            if not SHA256_PATTERN.fullmatch(row["audio_sha256"]):
                errors.append(f"{label}: benchmark asset requires a SHA-256")
            for field in ("sample_rate_hz", "channels", "duration_s"):
                try:
                    if float(row[field]) <= 0:
                        raise ValueError
                except ValueError:
                    errors.append(f"{label}: {field} must be positive")

    usable = manifest[use].copy()
    if usable["clip_id"].duplicated().any():
        duplicates = sorted(usable.loc[usable["clip_id"].duplicated(False), "clip_id"].unique())
        errors.append(f"Multiple usable assets map to clip(s): {', '.join(duplicates)}")

    for digest, rows in usable.groupby("audio_sha256"):
        partitions = {value for value in rows["split"] if value}
        if len(partitions) > 1:
            errors.append(
                f"Audio SHA-256 {digest} crosses split partitions: {sorted(partitions)}"
            )

    incomplete = manifest[~manifest["mapping_status"].eq("matched")]
    if not incomplete.empty:
        counts = incomplete["mapping_status"].value_counts().to_dict()
        message = f"Incomplete mapping states present: {counts}"
        if require_complete:
            errors.append(message)
        else:
            warnings.append(message)
    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
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
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    errors, warnings = validate(
        args.manifest,
        args.clips,
        args.splits,
        args.require_complete,
    )
    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    frame = pd.read_csv(args.manifest)
    usable = frame["use_for_benchmark"].astype(str).str.lower().eq("true").sum()
    print(f"Audio manifest validation passed: {len(frame)} rows, {usable} usable assets")


if __name__ == "__main__":
    main()

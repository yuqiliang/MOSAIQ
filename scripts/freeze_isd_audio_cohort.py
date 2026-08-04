#!/usr/bin/env python3
"""Freeze the QC-passing ISD audio cohort and explicit exclusions."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
import yaml


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--qc", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", default="0.1.0-audio")
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, dtype=str, keep_default_na=False)
    qc = pd.read_csv(args.qc, dtype=str, keep_default_na=False)
    qc_status = dict(zip(qc["asset_id"], qc["status"], strict=True))
    use = manifest["use_for_benchmark"].str.lower().eq("true")
    accepted = manifest[use].copy()
    accepted["qc_status"] = accepted["asset_id"].map(qc_status)
    accepted = accepted[~accepted["qc_status"].eq("fail")]
    accepted = accepted[
        [
            "asset_id",
            "dataset_id",
            "clip_id",
            "split",
            "archive_name",
            "member_path",
            "audio_sha256",
            "sample_rate_hz",
            "channels",
            "duration_s",
            "sample_dtype",
            "qc_status",
        ]
    ].sort_values(["split", "clip_id"])

    excluded = manifest[~use].copy()
    excluded["exclusion_reason"] = excluded["mapping_status"]
    excluded.loc[
        excluded["mapping_status"].eq("matched")
        & excluded["split"].eq("excluded"),
        "exclusion_reason",
    ] = "frozen_split_excluded"
    failed = manifest[use & manifest["asset_id"].isin(
        qc.loc[qc["status"].eq("fail"), "asset_id"]
    )].copy()
    if not failed.empty:
        failed["exclusion_reason"] = "technical_qc_fail"
        excluded = pd.concat([excluded, failed], ignore_index=True)
    excluded = excluded[
        [
            "asset_id",
            "clip_id",
            "split",
            "archive_name",
            "member_path",
            "mapping_status",
            "exclusion_reason",
            "mapping_notes",
        ]
    ].sort_values(["exclusion_reason", "clip_id", "member_path"])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cohort_path = args.output_dir / "isd_audio_cohort.csv"
    exclusion_path = args.output_dir / "isd_audio_exclusions.csv"
    accepted.to_csv(cohort_path, index=False)
    excluded.to_csv(exclusion_path, index=False)

    summary = {
        "schema_version": "0.1",
        "cohort_version": args.version,
        "source_manifest": args.manifest.as_posix(),
        "source_qc": args.qc.as_posix(),
        "accepted_assets": len(accepted),
        "accepted_clips": accepted["clip_id"].nunique(),
        "split_counts": accepted["split"].value_counts().sort_index().to_dict(),
        "excluded_rows": len(excluded),
        "exclusion_reason_counts": (
            excluded["exclusion_reason"].value_counts().sort_index().to_dict()
        ),
        "audio_sha_cross_split_count": int(
            (
                accepted.groupby("audio_sha256")["split"].nunique()
                > 1
            ).sum()
        ),
        "technical_qc_failures": int((qc["status"] == "fail").sum()),
    }
    if summary["audio_sha_cross_split_count"]:
        raise SystemExit("Cannot freeze: an audio SHA-256 crosses split partitions")
    summary_path = args.output_dir / "isd_audio_cohort_summary.yaml"
    summary_path.write_text(yaml.safe_dump(summary, sort_keys=False), encoding="utf-8")

    checksum_paths = [cohort_path, exclusion_path, summary_path, args.manifest, args.qc]
    checksums = "".join(
        f"{sha256(path)}  {path.as_posix()}\n" for path in checksum_paths
    )
    (args.output_dir / "checksums.sha256").write_text(checksums, encoding="ascii")
    print(
        f"FROZE {len(accepted)} accepted assets and {len(excluded)} exclusions "
        f"as {args.version}"
    )


if __name__ == "__main__":
    main()

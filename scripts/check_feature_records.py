"""Simple FeatureRecord validator for MOSAIQ (pandas + json only).

Usage:
  uv run python scripts/check_feature_records.py --dataset ISD
  uv run python scripts/check_feature_records.py --dataset ARAUS
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ALLOWED_FEATURE_TYPES = {
    "audio_embedding",
    "visual_clip_embedding",
    "visual_semantic_summary",
    "behavioural_attention",
    "contextual_descriptor",
    "psychoacoustic_descriptor",
    "other",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check MOSAIQ FeatureRecords")
    parser.add_argument("--dataset", required=True, choices=["ISD", "ARAUS", "SATP"], help="Dataset id")
    parser.add_argument("--clips", default=None, help="Optional clips.csv path")
    parser.add_argument("--features", default=None, help="Optional features.csv path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_dir = Path("datasets") / args.dataset
    clips_path = Path(args.clips) if args.clips else dataset_dir / "data" / "clips.csv"
    features_path = Path(args.features) if args.features else dataset_dir / "data" / "features.csv"

    clips = pd.read_csv(clips_path)
    features = pd.read_csv(features_path)

    errors: list[str] = []
    clip_ids = set(clips["clip_id"].dropna().astype(str).tolist())

    if "feature_id" not in features.columns:
        errors.append("Missing column: feature_id")
    else:
        dup = features["feature_id"].dropna().astype(str)
        dup_ids = dup[dup.duplicated()].unique().tolist()
        if dup_ids:
            errors.append(f"Duplicate feature_id values: {dup_ids[:10]}")

    if "clip_id" not in features.columns:
        errors.append("Missing column: clip_id")
    else:
        missing_clip = features[~features["clip_id"].astype(str).isin(clip_ids)]
        if not missing_clip.empty:
            errors.append(
                f"features.clip_id values not found in clips.clip_id: {missing_clip['clip_id'].astype(str).head(10).tolist()}"
            )

    if "dataset_id" in features.columns and "dataset_id" in clips.columns:
        bad_dataset = features.merge(
            clips[["clip_id", "dataset_id"]],
            on="clip_id",
            suffixes=("_feature", "_clip"),
            how="left",
        )
        bad_dataset = bad_dataset[
            bad_dataset["dataset_id_clip"].notna()
            & (bad_dataset["dataset_id_feature"].astype(str) != bad_dataset["dataset_id_clip"].astype(str))
        ]
        if not bad_dataset.empty:
            errors.append("features.dataset_id does not match clips.dataset_id for some rows")

    if "feature_type" not in features.columns:
        errors.append("Missing column: feature_type")
    else:
        bad_types = sorted(set(features["feature_type"].dropna().astype(str)) - ALLOWED_FEATURE_TYPES)
        if bad_types:
            errors.append(f"Invalid feature_type values: {bad_types}")

    if "provenance_json" not in features.columns:
        errors.append("Missing column: provenance_json")
    else:
        for idx, value in features["provenance_json"].items():
            if pd.isna(value):
                errors.append(f"Row {idx + 2}: provenance_json is empty")
                continue
            try:
                parsed = json.loads(str(value))
                if not isinstance(parsed, dict):
                    errors.append(f"Row {idx + 2}: provenance_json must decode to object")
            except Exception:
                errors.append(f"Row {idx + 2}: provenance_json is invalid JSON")

    print("FeatureRecord validation report")
    print(f"- dataset: {args.dataset}")
    print(f"- clips rows: {len(clips)}")
    print(f"- features rows: {len(features)}")

    if errors:
        print(f"- status: FAIL ({len(errors)} issue(s))")
        for err in errors:
            print(f"  * {err}")
        raise SystemExit(1)

    print("- status: PASS")


if __name__ == "__main__":
    main()

"""Validate MOSAIQ feature resources with CitySeg-specific checks.

Usage:
  uv run python scripts/validate_mosaiq.py --dataset-dir datasets/ISD
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ALLOWED_FEATURE_TYPES = {
    "cityseg_summary",
    "cityseg_temporal_summary",
    "cityseg_gaze_on_class",
    "clip_embedding",
    "psychoacoustic",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MOSAIQ features against clips")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--clips", type=Path, default=None)
    parser.add_argument("--features", type=Path, default=None)
    parser.add_argument("--skip-file-check", action="store_true")
    return parser.parse_args()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def is_number_01(x: Any) -> bool:
    try:
        v = float(x)
    except Exception:
        return False
    return 0.0 <= v <= 1.0


def validate_cityseg_feature(feature_json: dict[str, Any], idx: int, errors: list[str]) -> None:
    class_ratio = feature_json.get("class_ratio")
    if not isinstance(class_ratio, dict) or not class_ratio:
        errors.append(f"row {idx}: cityseg_summary missing class_ratio dict")
    else:
        for cname, val in class_ratio.items():
            if not is_number_01(val):
                errors.append(f"row {idx}: class_ratio[{cname}] must be numeric in [0,1]")

    grouped = feature_json.get("grouped_categories")
    if grouped is not None:
        if not isinstance(grouped, dict):
            errors.append(f"row {idx}: grouped_categories must be a dict")
        else:
            for gname, val in grouped.items():
                if not is_number_01(val):
                    errors.append(f"row {idx}: grouped_categories[{gname}] must be numeric in [0,1]")

    sampled_frame_count = feature_json.get("sampled_frame_count")
    try:
        if int(sampled_frame_count) <= 0:
            errors.append(f"row {idx}: sampled_frame_count must be > 0")
    except Exception:
        errors.append(f"row {idx}: sampled_frame_count must be an integer")

    frame_sampling_rule = str(feature_json.get("frame_sampling_rule", "")).strip()
    if not frame_sampling_rule:
        errors.append(f"row {idx}: frame_sampling_rule must be non-empty")


def main() -> None:
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    clips_path = (args.clips or (dataset_dir / "data" / "clips.csv")).resolve()
    features_path = (args.features or (dataset_dir / "data" / "features.csv")).resolve()

    clips = load_csv(clips_path)
    features = load_csv(features_path)

    clip_ids = {r.get("clip_id") for r in clips if r.get("clip_id")}
    errors: list[str] = []

    seen_feature_ids: set[str] = set()
    for idx, row in enumerate(features, start=2):
        feature_id = (row.get("feature_id") or "").strip()
        clip_id = (row.get("clip_id") or "").strip()
        feature_type = (row.get("feature_type") or "").strip()

        if not feature_id:
            errors.append(f"row {idx}: feature_id is required")
        elif feature_id in seen_feature_ids:
            errors.append(f"row {idx}: duplicate feature_id={feature_id}")
        else:
            seen_feature_ids.add(feature_id)

        if not clip_id:
            errors.append(f"row {idx}: clip_id is required")
        elif clip_id not in clip_ids:
            errors.append(f"row {idx}: clip_id not found in clips.csv: {clip_id}")

        if feature_type not in ALLOWED_FEATURE_TYPES:
            errors.append(f"row {idx}: invalid feature_type={feature_type}")

        provenance_json_raw = (row.get("provenance_json") or "").strip()
        if not provenance_json_raw:
            errors.append(f"row {idx}: provenance_json is required")
            provenance_json = None
        else:
            try:
                provenance_json = json.loads(provenance_json_raw)
                if not isinstance(provenance_json, dict):
                    errors.append(f"row {idx}: provenance_json must decode to an object")
            except Exception:
                errors.append(f"row {idx}: provenance_json is not valid JSON")
                provenance_json = None

        feature_json_raw = (row.get("feature_json") or "").strip()
        if feature_json_raw:
            try:
                feature_json = json.loads(feature_json_raw)
                if not isinstance(feature_json, dict):
                    errors.append(f"row {idx}: feature_json must decode to an object")
                    feature_json = None
            except Exception:
                errors.append(f"row {idx}: feature_json is not valid JSON")
                feature_json = None
        else:
            feature_json = None

        feature_path = (row.get("feature_path") or "").strip()
        if feature_path and not args.skip_file_check:
            p = Path(feature_path)
            if not p.is_absolute():
                p = dataset_dir / p
            if not p.exists():
                errors.append(f"row {idx}: feature_path does not exist: {feature_path}")

        if feature_type == "cityseg_summary":
            if feature_json is None:
                errors.append(f"row {idx}: cityseg_summary requires valid feature_json")
            else:
                validate_cityseg_feature(feature_json, idx, errors)

    if errors:
        print(f"Validation failed with {len(errors)} error(s):")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print(f"Validation passed: {features_path} ({len(features)} feature rows)")


if __name__ == "__main__":
    main()

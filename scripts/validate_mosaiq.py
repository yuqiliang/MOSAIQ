"""Validate MOSAIQ clip-linked feature, rating, and preprocessing resources.

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
    "audio_embedding",
    "visual_clip_embedding",
    "visual_semantic_summary",
    "behavioural_attention",
    "contextual_descriptor",
    "psychoacoustic_descriptor",
    "other",
}
ALLOWED_TRANSFORMATION_TYPES = {
    "scale_conversion",
    "aggregation",
    "iso_coordinate_derivation",
    "normalisation",
    "feature_extraction",
    "filtering",
    "renaming",
    "other",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MOSAIQ features against clips")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--clips", type=Path, default=None)
    parser.add_argument("--features", type=Path, default=None)
    parser.add_argument("--ratings", type=Path, default=None)
    parser.add_argument("--preprocessing", type=Path, default=None)
    parser.add_argument("--skip-file-check", action="store_true")
    return parser.parse_args()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return load_csv(path)


def csv_fields(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return set(reader.fieldnames or [])


def is_number_01(x: Any) -> bool:
    try:
        v = float(x)
    except Exception:
        return False
    return 0.0 <= v <= 1.0


def to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def validate_required(row: dict[str, str], fields: list[str], idx: int, errors: list[str]) -> None:
    for field in fields:
        if not (row.get(field) or "").strip():
            errors.append(f"row {idx}: {field} is required")


def validate_json_object(raw: str, label: str, idx: int, errors: list[str]) -> dict[str, Any] | None:
    raw = raw.strip()
    if not raw:
        errors.append(f"row {idx}: {label} is required")
        return None
    try:
        decoded = json.loads(raw)
    except Exception:
        errors.append(f"row {idx}: {label} is not valid JSON")
        return None
    if not isinstance(decoded, dict):
        errors.append(f"row {idx}: {label} must decode to an object")
        return None
    return decoded


def validate_cityseg_feature(feature_json: dict[str, Any], idx: int, errors: list[str]) -> None:
    class_ratio = feature_json.get("class_ratio")
    if not isinstance(class_ratio, dict) or not class_ratio:
        errors.append(f"row {idx}: visual_semantic_summary missing class_ratio dict")
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


def validate_features(
    dataset_dir: Path,
    clips: list[dict[str, str]],
    features_path: Path,
    skip_file_check: bool,
    errors: list[str],
) -> int:
    features = load_csv_if_exists(features_path)
    if not features:
        return 0
    clip_ids = {r.get("clip_id") for r in clips if r.get("clip_id")}
    clip_dataset = {r.get("clip_id"): r.get("dataset_id") for r in clips if r.get("clip_id")}
    seen_feature_ids: set[str] = set()
    for idx, row in enumerate(features, start=2):
        feature_id = (row.get("feature_id") or "").strip()
        dataset_id = (row.get("dataset_id") or "").strip()
        clip_id = (row.get("clip_id") or "").strip()
        feature_type = (row.get("feature_type") or "").strip()
        modality = (row.get("modality") or row.get("source_modality") or "").strip()

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

        if not dataset_id:
            errors.append(f"row {idx}: dataset_id is required")
        elif clip_id in clip_dataset and clip_dataset[clip_id] and dataset_id != clip_dataset[clip_id]:
            errors.append(
                f"row {idx}: dataset_id={dataset_id} does not match clips.csv dataset_id={clip_dataset[clip_id]}"
            )

        if feature_type not in ALLOWED_FEATURE_TYPES:
            errors.append(f"row {idx}: invalid feature_type={feature_type}")

        if not modality:
            errors.append(f"row {idx}: modality or source_modality is required")

        provenance_json_raw = (row.get("provenance_json") or "").strip()
        _provenance_json = validate_json_object(provenance_json_raw, "provenance_json", idx, errors)

        feature_json_raw = (
            row.get("feature_value_json") or row.get("feature_json") or ""
        ).strip()
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
        if feature_path and not skip_file_check:
            notes = (row.get("notes") or "").lower()
            provenance_notes = (row.get("provenance_notes") or "").lower()
            status = str((feature_json or {}).get("status", "")).lower()
            placeholder_path = (
                "placeholder" in notes
                or "placeholder" in provenance_notes
                or "placeholder" in status
            )
            if not placeholder_path:
                p = Path(feature_path)
                if not p.is_absolute():
                    p = dataset_dir / p
                if not p.exists():
                    errors.append(f"row {idx}: feature_path does not exist: {feature_path}")

        if feature_type == "visual_semantic_summary":
            if feature_json is None:
                errors.append(f"row {idx}: visual_semantic_summary requires valid feature_value_json")
            else:
                validate_cityseg_feature(feature_json, idx, errors)

    return len(features)


def validate_ratings(
    clips: list[dict[str, str]],
    responses: list[dict[str, str]],
    preprocessing_ids: set[str],
    ratings_path: Path,
    errors: list[str],
) -> int:
    ratings = load_csv_if_exists(ratings_path)
    if not ratings:
        return 0
    clip_ids = {r.get("clip_id") for r in clips if r.get("clip_id")}
    response_ids = {r.get("response_id") for r in responses if r.get("response_id")}
    seen_rating_ids: set[str] = set()
    for idx, row in enumerate(ratings, start=2):
        validate_required(
            row,
            [
                "rating_id",
                "dataset_id",
                "clip_id",
                "rating_item_original",
                "rating_dimension",
                "rating_framework",
                "rating_value_original",
                "rating_scale_min_original",
                "rating_scale_max_original",
            ],
            idx,
            errors,
        )
        rating_id = (row.get("rating_id") or "").strip()
        if rating_id:
            if rating_id in seen_rating_ids:
                errors.append(f"row {idx}: duplicate rating_id={rating_id}")
            seen_rating_ids.add(rating_id)

        clip_id = (row.get("clip_id") or "").strip()
        if clip_id and clip_id not in clip_ids:
            errors.append(f"row {idx}: clip_id not found in clips.csv: {clip_id}")

        response_id = (row.get("response_id") or "").strip()
        if response_id and response_ids and response_id not in response_ids:
            errors.append(f"row {idx}: response_id not found in responses.csv: {response_id}")

        original_value = to_float(row.get("rating_value_original"))
        original_min = to_float(row.get("rating_scale_min_original"))
        original_max = to_float(row.get("rating_scale_max_original"))
        if original_value is None:
            errors.append(f"row {idx}: rating_value_original must be numeric")
        if original_min is None or original_max is None:
            errors.append(f"row {idx}: original scale min/max must be numeric")
        elif original_min >= original_max:
            errors.append(f"row {idx}: original scale min must be lower than max")
        elif original_value is not None and not (original_min <= original_value <= original_max):
            errors.append(f"row {idx}: original value outside original scale bounds")

        harmonised_value = to_float(row.get("rating_value_harmonised"))
        if harmonised_value is not None:
            hmin = to_float(row.get("rating_scale_min_harmonised"))
            hmax = to_float(row.get("rating_scale_max_harmonised"))
            if hmin is None or hmax is None:
                errors.append(f"row {idx}: harmonised scale min/max required when harmonised value exists")
            elif hmin >= hmax:
                errors.append(f"row {idx}: harmonised scale min must be lower than max")
            elif not (hmin <= harmonised_value <= hmax):
                errors.append(f"row {idx}: harmonised value outside harmonised scale bounds")
            if not (row.get("harmonisation_method") or "").strip():
                errors.append(f"row {idx}: harmonisation_method required when harmonised value exists")

        preprocessing_id = (row.get("preprocessing_id") or "").strip()
        if preprocessing_id and preprocessing_ids and preprocessing_id not in preprocessing_ids:
            errors.append(f"row {idx}: preprocessing_id not found in preprocessing.csv: {preprocessing_id}")

        if not (row.get("provenance") or "").strip():
            errors.append(f"row {idx}: provenance is required")
    return len(ratings)


def field_reference_is_valid(value: str, known_fields: set[str]) -> bool:
    value = value.strip()
    if not value:
        return False
    if value in known_fields:
        return True
    if ";" in value:
        return all(field_reference_is_valid(part, known_fields) for part in value.split(";"))
    # Descriptive references are allowed for aggregate records.
    return ".csv" in value or " " in value or "*" in value


def validate_preprocessing(
    clips: list[dict[str, str]],
    preprocessing_path: Path,
    known_fields: set[str],
    errors: list[str],
) -> tuple[int, set[str]]:
    preprocessing = load_csv_if_exists(preprocessing_path)
    preprocessing_ids = {row.get("preprocessing_id", "") for row in preprocessing}
    if not preprocessing:
        return 0, set()
    clip_ids = {r.get("clip_id") for r in clips if r.get("clip_id")}
    seen_ids: set[str] = set()
    for idx, row in enumerate(preprocessing, start=2):
        validate_required(
            row,
            [
                "preprocessing_id",
                "dataset_id",
                "input_field",
                "output_field",
                "transformation_type",
                "software_or_script",
            ],
            idx,
            errors,
        )
        preprocessing_id = (row.get("preprocessing_id") or "").strip()
        if preprocessing_id:
            if preprocessing_id in seen_ids:
                errors.append(f"row {idx}: duplicate preprocessing_id={preprocessing_id}")
            seen_ids.add(preprocessing_id)

        clip_id = (row.get("clip_id") or "").strip()
        if clip_id and clip_id not in clip_ids:
            errors.append(f"row {idx}: clip_id not found in clips.csv: {clip_id}")

        transformation_type = (row.get("transformation_type") or "").strip()
        if transformation_type and transformation_type not in ALLOWED_TRANSFORMATION_TYPES:
            errors.append(f"row {idx}: invalid transformation_type={transformation_type}")

        for field_name in ["input_field", "output_field"]:
            reference = (row.get(field_name) or "").strip()
            if reference and not field_reference_is_valid(reference, known_fields):
                errors.append(f"row {idx}: {field_name} does not reference a known field: {reference}")

        if not (row.get("transformation_formula") or "").strip():
            errors.append(f"row {idx}: transformation_formula is required")
        if not (row.get("code_version") or "").strip():
            errors.append(f"row {idx}: code_version is required")
        if not (row.get("date_created") or "").strip():
            errors.append(f"row {idx}: date_created is required")

    return len(preprocessing), preprocessing_ids


def main() -> None:
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    clips_path = (args.clips or (dataset_dir / "data" / "clips.csv")).resolve()
    responses_path = (dataset_dir / "data" / "responses.csv").resolve()
    features_path = (args.features or (dataset_dir / "data" / "features.csv")).resolve()
    ratings_path = (args.ratings or (dataset_dir / "data" / "ratings.csv")).resolve()
    preprocessing_path = (
        args.preprocessing or (dataset_dir / "data" / "preprocessing.csv")
    ).resolve()

    clips = load_csv(clips_path)
    responses = load_csv_if_exists(responses_path)
    known_fields = set()
    for path in [clips_path, responses_path, features_path, ratings_path]:
        known_fields.update(csv_fields(path))

    errors: list[str] = []
    preprocessing_count, preprocessing_ids = validate_preprocessing(
        clips, preprocessing_path, known_fields, errors
    )
    feature_count = validate_features(
        dataset_dir, clips, features_path, args.skip_file_check, errors
    )
    rating_count = validate_ratings(
        clips, responses, preprocessing_ids, ratings_path, errors
    )

    if errors:
        print(f"Validation failed with {len(errors)} error(s):")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print(
        "Validation passed: "
        f"{len(clips)} clips, {feature_count} feature rows, "
        f"{rating_count} rating rows, {preprocessing_count} preprocessing rows"
    )


if __name__ == "__main__":
    main()

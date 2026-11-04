#!/usr/bin/env python3
"""Validate the frozen ISD audio cohort and executed reference baselines."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from extract_audio_descriptors import FEATURE_COLUMNS, MODEL_FEATURE_COLUMNS
from validate_audio_manifest import validate


ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "benchmark/audio"
VERSION = "v0.1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> None:
    manifest_path = AUDIO / f"manifests/isd_audio_manifest_{VERSION}.csv"
    manifest_summary = load_yaml(
        AUDIO / f"manifests/isd_audio_summary_{VERSION}.yaml"
    )
    qc_path = AUDIO / f"qc/isd_audio_qc_{VERSION}.csv"
    qc_summary = load_yaml(AUDIO / f"qc/isd_audio_qc_summary_{VERSION}.yaml")
    feature_path = AUDIO / f"features/isd_audio_descriptors_{VERSION}.csv"
    feature_summary = load_yaml(
        AUDIO / f"features/isd_audio_descriptors_summary_{VERSION}.yaml"
    )
    cohort_dir = AUDIO / "cohort/v0.1.0"
    cohort_summary = load_yaml(cohort_dir / "isd_audio_cohort_summary.yaml")
    result_dir = AUDIO / "results/v0.1.0"
    run = json.loads((result_dir / "run.json").read_text(encoding="utf-8"))

    errors, warnings = validate(
        manifest_path,
        ROOT / "datasets/ISD/data/clips.csv",
        ROOT / "benchmark/splits/isd_split.csv",
        require_complete=False,
    )
    manifest = pd.read_csv(manifest_path)
    usable = manifest[
        manifest["use_for_benchmark"].astype(str).str.lower().eq("true")
    ]
    qc = pd.read_csv(qc_path)
    features = pd.read_csv(feature_path)
    cohort = pd.read_csv(cohort_dir / "isd_audio_cohort.csv")
    exclusions = pd.read_csv(cohort_dir / "isd_audio_exclusions.csv")
    metrics = pd.read_csv(result_dir / "metrics.csv")
    predictions = pd.read_csv(result_dir / "predictions.csv")
    intervals = pd.read_csv(result_dir / "evaluation/bootstrap_intervals.csv")
    comparisons = pd.read_csv(result_dir / "evaluation/paired_comparisons.csv")
    registry = pd.read_csv(ROOT / "benchmark/governance/isd_zenodo_source_registry.csv")

    checks = {
        "manifest summary count": len(manifest) == manifest_summary["rows"],
        "usable manifest count": len(usable) == manifest_summary["usable_assets"],
        "usable clip uniqueness": usable["clip_id"].nunique() == len(usable),
        "QC coverage": set(qc["asset_id"]) == set(usable["asset_id"]),
        "QC has no failures": not qc["status"].eq("fail").any(),
        "QC summary passed": qc_summary["technical_qc_passed"] is True,
        "calibration remains explicit": qc_summary["calibration_review_complete"] is False,
        "feature coverage": set(features["asset_id"]) == set(usable["asset_id"]),
        "features finite": np.isfinite(
            features[FEATURE_COLUMNS].to_numpy(dtype=float)
        ).all(),
        "model features are scale-safe": not {"rms", "peak_abs"}.intersection(
            MODEL_FEATURE_COLUMNS
        ),
        "feature summary count": len(features) == feature_summary["assets_processed"],
        "cohort matches manifest": set(cohort["asset_id"]) == set(usable["asset_id"]),
        "exclusions cover rejected rows": len(exclusions) == len(manifest) - len(usable),
        "cohort has no cross-split SHA": cohort_summary["audio_sha_cross_split_count"] == 0,
        "cohort has no technical failures": cohort_summary["technical_qc_failures"] == 0,
        "run uses audio": run["audio_used"] is True,
        "run uses frozen split": str(run["split_version"]) == "0.1.0",
        "executed model set": set(run["models"])
        == {"audio_target_mean", "audio_descriptor_ridge"},
        "executed task set": set(run["tasks"])
        == {
            "isd_audio_clip_iso_coordinates",
            "isd_audio_response_iso_coordinates",
        },
        "prediction key uniqueness": not predictions.duplicated(
            ["model_id", "task_id", "record_id", "partition", "target"]
        ).any(),
        "prediction split scope": set(predictions["partition"]) == {"dev", "test"},
        "prediction values finite": np.isfinite(
            predictions[["observed", "prediction"]].to_numpy(dtype=float)
        ).all(),
        "metric values finite": np.isfinite(metrics["value"]).all(),
        "metric audio flag": metrics["audio_used"].astype(bool).all(),
        "bootstrap interval order": (intervals["ci_low"] <= intervals["estimate"]).all()
        and (intervals["estimate"] <= intervals["ci_high"]).all(),
        "paired interval order": (comparisons["ci_low"] <= comparisons["estimate"]).all()
        and (comparisons["estimate"] <= comparisons["ci_high"]).all(),
        "paired probabilities valid": comparisons[
            "candidate_better_probability"
        ].between(0, 1).all(),
        "cluster bootstrap declared": set(intervals["bootstrap_unit"]) == {"clip_id"}
        and set(comparisons["bootstrap_unit"]) == {"clip_id"},
    }
    errors.extend(name for name, passed in checks.items() if not passed)

    split_by_clip = dict(zip(usable["clip_id"], usable["split"], strict=True))
    inherited = predictions["clip_id"].map(split_by_clip)
    if not inherited.eq(predictions["partition"]).all():
        errors.append("held-out predictions do not inherit the frozen clip split")

    expected_splits = {"train": 546, "dev": 154, "test": 120}
    if usable["split"].value_counts().to_dict() != expected_splits:
        errors.append("accepted audio split counts differ from the v0.1.0 freeze")

    expected_exclusions = {
        "ambiguous_clip_match": 3,
        "exact_duplicate_excluded": 1,
        "frozen_split_excluded": 2,
        "missing_source_asset": 143,
        "unmatched_source_asset": 52,
    }
    if cohort_summary["exclusion_reason_counts"] != expected_exclusions:
        errors.append("audio exclusion counts differ from the v0.1.0 freeze")

    for keys, group in predictions.groupby(
        ["model_id", "task_id", "partition", "target"]
    ):
        observed = group["observed"].to_numpy(dtype=float)
        predicted = group["prediction"].to_numpy(dtype=float)
        expected = {
            "rmse": float(np.sqrt(mean_squared_error(observed, predicted))),
            "mae": float(mean_absolute_error(observed, predicted)),
            "r2": float(r2_score(observed, predicted)),
        }
        rows = metrics[
            metrics["model_id"].eq(keys[0])
            & metrics["task_id"].eq(keys[1])
            & metrics["partition"].eq(keys[2])
            & metrics["target"].eq(keys[3])
        ]
        if set(rows["metric"]) != set(expected):
            errors.append(f"{keys}: metric rows are incomplete")
            continue
        observed_metrics = dict(zip(rows["metric"], rows["value"], strict=True))
        if any(
            not np.isclose(observed_metrics[name], value, rtol=0, atol=1e-12)
            for name, value in expected.items()
        ):
            errors.append(f"{keys}: metrics do not reproduce from predictions")

    candidate_archives = registry[
        registry["benchmark_scope_status"].eq("benchmark_candidate")
        & registry["file_role"].eq("audio_archive")
    ]
    if len(candidate_archives) != 7 or not candidate_archives["local_status"].eq(
        "downloaded_verified"
    ).all():
        errors.append("the seven benchmark-candidate source archives are not verified")

    declared = {}
    for line in (cohort_dir / "checksums.sha256").read_text(
        encoding="ascii"
    ).splitlines():
        digest, path_text = line.split("  ", 1)
        declared[path_text] = digest
    for path_text, digest in declared.items():
        path = Path(path_text)
        path = path if path.is_absolute() else ROOT / path
        if not path.exists() or sha256(path) != digest:
            errors.append(f"cohort checksum mismatch: {path_text}")

    for model_id in run["models"]:
        card = AUDIO / f"model_cards/v0.1.0/{model_id}.md"
        if not card.exists():
            errors.append(f"missing audio model card: {model_id}")
            continue
        text = card.read_text(encoding="utf-8")
        for required in [model_id, "Audio used: `true`", *run["tasks"]]:
            if required not in text:
                errors.append(f"{card.name}: missing provenance text {required}")

    if errors:
        print(f"ISD audio output validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    for warning in warnings:
        print(f"WARN: {warning}")
    print(
        "ISD audio output validation passed: "
        f"{len(usable)} assets, {len(exclusions)} exclusions, "
        f"{len(run['tasks'])} tasks, {len(run['models'])} models, "
        f"{len(predictions)} held-out prediction rows"
    )


if __name__ == "__main__":
    main()

"""Validate generated MOSAIQ tabular baseline outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "benchmark" / "baselines" / "baseline_config.yaml"
RESULT_DIR = REPO_ROOT / "benchmark" / "results"
CARD_DIR = REPO_ROOT / "benchmark" / "model_cards"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    results = pd.read_csv(RESULT_DIR / "baseline_results.csv")
    expected_models = {item["id"] for item in config["experiments"]}
    observed_models = set(results["model_id"])
    errors: list[str] = []

    shared6 = config["feature_sets"]["shared6"]
    if set(shared6["numeric"]) != set(shared6["complete_case"]):
        errors.append("shared6 numeric predictors must all be complete-case fields")
    cohort_only = config["feature_sets"]["shared6_cohort_only"]
    if cohort_only["numeric"] or set(cohort_only["complete_case"]) != set(
        shared6["complete_case"]
    ):
        errors.append("shared6_cohort_only must match shared6 eligibility without inputs")
    tong_reduced = config["feature_sets"]["tong_style_reduced"]
    if set(tong_reduced["complete_case"]) != set(shared6["complete_case"]):
        errors.append("tong_style_reduced must use the shared6 complete-case cohort")
    delta_sources = config["feature_sets"]["delta_source_indicators"]
    if set(delta_sources["numeric"]) != set(delta_sources["complete_case"]):
        errors.append("all DeLTA source-indicator predictors must be complete-case fields")

    if observed_models != expected_models:
        errors.append(
            f"result models differ from config: missing={sorted(expected_models - observed_models)}, "
            f"unexpected={sorted(observed_models - expected_models)}"
        )
    if set(results["partition"]) != {"dev", "test"}:
        errors.append("results must contain exactly dev and test partitions")
    if set(results["split_version"].astype(str)) != {str(config["split_version"])}:
        errors.append("result split version does not match baseline config")
    if set(results["random_seed"]) != {int(config["random_seed"])}:
        errors.append("result random seed does not match baseline config")

    for experiment in config["experiments"]:
        task = load_yaml(REPO_ROOT / experiment["task_config"])
        targets = set(task["target"]["columns"])
        features = config["feature_sets"][experiment["feature_set"]]
        predictors = set(features["numeric"]) | set(features["categorical"])
        overlap = sorted(targets & predictors)
        if overlap:
            errors.append(f"{experiment['id']}: target leakage columns: {overlap}")

    core = results[results["metric"].isin(["rmse", "mae", "r2"])]
    if not np.isfinite(core["value"]).all():
        errors.append("RMSE, MAE, and R2 must all be finite")
    distribution = results[results["scope"].eq("group_kde")]
    if distribution.empty or not (
        np.isfinite(distribution["value"]).all() and (distribution["value"] >= 0).all()
    ):
        errors.append("KL, JS, and DME rows must be present, finite, and non-negative")

    source_results = results[results["task_id"].eq("delta_source_multilabel")]
    aggregate_metrics = {
        "macro_average_precision",
        "micro_average_precision",
        "macro_f1",
        "micro_f1",
    }
    source_aggregate = source_results[source_results["scope"].eq("aggregate")]
    source_per_label = source_results[source_results["scope"].eq("per_label")]
    if set(source_aggregate["metric"]) != aggregate_metrics:
        errors.append("DeLTA aggregate source metrics are incomplete")
    if len(source_aggregate) != 2 * 2 * len(aggregate_metrics):
        errors.append("unexpected number of DeLTA aggregate source metric rows")
    if set(source_per_label["metric"]) != {"average_precision", "f1"}:
        errors.append("DeLTA per-label source metrics are incomplete")
    if len(source_per_label) != 2 * 2 * 24 * 2:
        errors.append("unexpected number of DeLTA per-label metric rows")
    classification_values = pd.concat(
        [source_aggregate["value"], source_per_label["value"]], ignore_index=True
    )
    if not (
        np.isfinite(classification_values).all()
        and classification_values.between(0, 1).all()
    ):
        errors.append("classification metrics must be finite and in [0, 1]")

    prediction_ids: dict[tuple[str, str], set[str]] = {}
    for run_id in sorted(set(results["run_id"])):
        prediction_path = RESULT_DIR / "predictions" / f"{run_id}.csv"
        metadata_path = RESULT_DIR / "runs" / f"{run_id}.json"
        if not prediction_path.exists() or not metadata_path.exists():
            errors.append(f"missing prediction or metadata file for {run_id}")
            continue
        predictions = pd.read_csv(prediction_path)
        if predictions.duplicated(["partition", "record_id", "target"]).any():
            errors.append(f"duplicate held-out prediction keys in {run_id}")
        if set(predictions["partition"]) != {"dev", "test"}:
            errors.append(f"{run_id}: predictions must contain dev and test only")
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        if metadata.get("audio_used") is not False:
            errors.append(f"{run_id}: audio_used must be false for tabular v0.1")
        if predictions["task_id"].eq("delta_source_multilabel").all():
            required = {"y_score", "threshold", "y_pred", "y_true"}
            if not required.issubset(predictions.columns):
                errors.append(f"{run_id}: missing multilabel prediction columns")
            elif not (
                predictions["y_score"].between(0, 1).all()
                and predictions["threshold"].between(0, 1).all()
                and set(predictions["y_pred"]).issubset({0, 1})
                and set(predictions["y_true"]).issubset({0, 1})
            ):
                errors.append(f"{run_id}: invalid multilabel scores or decisions")
            threshold_counts = predictions.groupby("target")["threshold"].nunique()
            if not threshold_counts.eq(1).all():
                errors.append(f"{run_id}: dev-selected thresholds vary by partition")
            if metadata.get("threshold_selection_partition") != "dev":
                errors.append(f"{run_id}: classification thresholds must be selected on dev")
        model_id = predictions["run_id"].iloc[0].split("__")[-2]
        for partition in ["dev", "test"]:
            ids = set(
                predictions[
                    (predictions["partition"] == partition)
                    & (predictions["target"] == predictions["target"].iloc[0])
                ]["record_id"].astype(str)
            )
            prediction_ids[(model_id, partition)] = ids

    response_models = {
        "isd_response_target_mean_shared6",
        "tong_style_reduced_lr",
        "tong_style_reduced_rf",
        "tong_style_reduced_xgboost",
        "tong_style_reduced_gpr",
    }
    for partition in ["dev", "test"]:
        cohorts = [prediction_ids.get((model, partition), set()) for model in response_models]
        if not cohorts or any(cohort != cohorts[0] for cohort in cohorts[1:]):
            errors.append(f"response models do not share the same {partition} cohort")

    split = pd.read_csv(REPO_ROOT / "benchmark" / "splits" / "isd_split.csv")
    split_map = dict(zip(split["clip_id"].astype(str), split["split"].astype(str), strict=True))
    for path in (RESULT_DIR / "predictions").glob(
        "isd_individual_iso_prediction__*.csv"
    ):
        predictions = pd.read_csv(path, dtype={"clip_id": str})
        inherited = predictions["clip_id"].map(split_map)
        if not inherited.eq(predictions["partition"]).all():
            errors.append(f"response predictions do not inherit clip splits in {path.name}")

    delta_split = pd.read_csv(REPO_ROOT / "benchmark" / "splits" / "delta_split.csv")
    delta_map = dict(
        zip(
            delta_split["clip_id"].astype(str),
            delta_split["split"].astype(str),
            strict=True,
        )
    )
    for path in (RESULT_DIR / "predictions").glob("delta_*__delta__*.csv"):
        predictions = pd.read_csv(path, dtype={"clip_id": str})
        inherited = predictions["clip_id"].map(delta_map)
        if not inherited.eq(predictions["partition"]).all():
            errors.append(f"DeLTA predictions do not match released splits in {path.name}")

    expected_card_names = {f"{model_id}.md" for model_id in expected_models} | {
        "README.md"
    }
    observed_card_names = {path.name for path in CARD_DIR.glob("*.md")}
    if observed_card_names != expected_card_names:
        errors.append(
            f"model card files differ from config: missing={sorted(expected_card_names - observed_card_names)}, "
            f"unexpected={sorted(observed_card_names - expected_card_names)}"
        )
    for model_id in expected_models:
        path = CARD_DIR / f"{model_id}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        model_rows = results[results["model_id"].eq(model_id)]
        if model_rows.empty:
            continue
        run_id = model_rows["run_id"].iloc[0]
        for required_text in [
            f"model_id: {model_id}",
            "audio_used: false",
            f"Run ID: `{run_id}`",
        ]:
            if required_text not in text:
                errors.append(f"{path.name}: missing generated provenance: {required_text}")

    if errors:
        print(f"Tabular baseline validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(
        f"Tabular baseline validation passed: {len(expected_models)} experiments, "
        f"{len(results)} metric rows, audio_used=false"
    )


if __name__ == "__main__":
    main()

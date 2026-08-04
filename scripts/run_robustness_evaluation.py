"""Run MOSAIQ Step 7 robustness analyses from frozen Step 6 predictions."""

from __future__ import annotations

import argparse
import copy
import hashlib
import math
import shutil
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.metrics import average_precision_score, f1_score

from run_tabular_baselines import (
    load_yaml,
    point_metrics,
    prepare_data,
    run_experiment,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "benchmark" / "robustness" / "robustness_config.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "benchmark" / "robustness"
BASELINE_RESULTS = REPO_ROOT / "benchmark" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MOSAIQ robustness evaluation")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--bootstrap-resamples",
        type=int,
        help="Override the configured number of bootstrap resamples.",
    )
    return parser.parse_args()


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def stable_seed(base_seed: int, *parts: str) -> int:
    payload = "::".join([str(base_seed), *parts]).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def prediction_path(run_id: str) -> Path:
    return BASELINE_RESULTS / "predictions" / f"{run_id}.csv"


def run_id_by_model() -> dict[str, str]:
    results = pd.read_csv(BASELINE_RESULTS / "baseline_results.csv")
    mapping: dict[str, str] = {}
    for model_id, group in results.groupby("model_id", sort=True):
        run_ids = group["run_id"].unique()
        if len(run_ids) != 1:
            raise ValueError(f"{model_id}: expected exactly one Step 6 run ID")
        mapping[str(model_id)] = str(run_ids[0])
    return mapping


def clear_generated_output(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "multiseed_results.csv",
        "multiseed_summary.csv",
        "bootstrap_intervals.csv",
        "paired_comparisons.csv",
        "feature_coverage_sensitivity.csv",
        "gpr_calibration.csv",
        "robustness_report.md",
    ]:
        path = output_dir / name
        if path.exists():
            path.unlink()
    multiseed = output_dir / "multiseed"
    if multiseed.exists():
        shutil.rmtree(multiseed)


def cluster_groups(clusters: np.ndarray) -> list[np.ndarray]:
    unique = pd.unique(clusters)
    return [np.flatnonzero(clusters == value) for value in unique]


def cluster_indices(groups: list[np.ndarray], rng: np.random.Generator) -> np.ndarray:
    sampled = rng.integers(0, len(groups), size=len(groups))
    return np.concatenate([groups[index] for index in sampled])


def percentile_summary(
    values: list[float], confidence: float
) -> tuple[float, float, float, int]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return math.nan, math.nan, math.nan, 0
    alpha = (1.0 - confidence) / 2.0
    return (
        float(np.quantile(finite, alpha)),
        float(np.quantile(finite, 1.0 - alpha)),
        float(np.std(finite, ddof=1)) if len(finite) > 1 else 0.0,
        int(len(finite)),
    )


def classification_values(
    observed: np.ndarray, scores: np.ndarray, predicted: np.ndarray
) -> dict[str, float]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UndefinedMetricWarning)
        warnings.simplefilter("ignore", category=UserWarning)
        return {
            "macro_average_precision": float(
                average_precision_score(observed, scores, average="macro")
            ),
            "micro_average_precision": float(
                average_precision_score(observed, scores, average="micro")
            ),
            "macro_f1": float(
                f1_score(observed, predicted, average="macro", zero_division=0)
            ),
            "micro_f1": float(
                f1_score(observed, predicted, average="micro", zero_division=0)
            ),
        }


def classification_matrices(
    predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    keys = predictions[["record_id", "clip_id"]].drop_duplicates().sort_values("record_id")
    targets = sorted(predictions["target"].unique())

    def matrix(column: str) -> np.ndarray:
        pivot = predictions.pivot(index="record_id", columns="target", values=column)
        return pivot.reindex(index=keys["record_id"], columns=targets).to_numpy()

    return keys, matrix("y_true").astype(int), matrix("y_score"), matrix("y_pred").astype(int)


def run_multiseed(
    robustness: dict[str, Any], baseline: dict[str, Any], output_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    section = robustness["multiseed"]
    experiment_map = {item["id"]: item for item in baseline["experiments"]}
    metric_rows: list[dict[str, Any]] = []
    run_output = output_dir / "multiseed"
    for model_id in section["experiments"]:
        if model_id not in experiment_map:
            raise ValueError(f"Unknown multiseed experiment: {model_id}")
        for seed in section["seeds"]:
            config = copy.deepcopy(baseline)
            config["random_seed"] = int(seed)
            print(f"Multiseed: {model_id}, seed={seed}")
            rows, _ = run_experiment(experiment_map[model_id], config, run_output)
            metric_rows.extend(rows)

    results = pd.DataFrame(metric_rows).sort_values(
        ["model_id", "random_seed", "partition", "target", "scope", "metric"]
    )
    results.to_csv(output_dir / "multiseed_results.csv", index=False)
    group_columns = [
        "benchmark_version",
        "task_id",
        "task_version",
        "split_version",
        "dataset_id",
        "partition",
        "scope",
        "feature_set",
        "model_id",
        "target",
        "metric",
        "n_train",
        "n_eval",
    ]
    summary = (
        results.groupby(group_columns, dropna=False)["value"]
        .agg(mean="mean", std="std", minimum="min", maximum="max", n_seeds="count")
        .reset_index()
        .sort_values(["model_id", "partition", "target", "scope", "metric"])
    )
    summary.to_csv(output_dir / "multiseed_summary.csv", index=False)
    return results, summary


def bootstrap_regression(
    predictions: pd.DataFrame,
    model_id: str,
    run_id: str,
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    confidence = float(settings["confidence_level"])
    n_resamples = int(settings["n_resamples"])
    base_seed = int(settings["random_seed"])
    for target, group in predictions.groupby("target", sort=True):
        group = group.sort_values("record_id").reset_index(drop=True)
        observed = group["y_true"].to_numpy(dtype=float)
        predicted = group["y_pred"].to_numpy(dtype=float)
        clusters = group[settings["cluster_column"]].astype(str).to_numpy()
        rng = np.random.default_rng(stable_seed(base_seed, model_id, str(target)))
        groups = cluster_groups(clusters)
        estimates = point_metrics(observed, predicted)
        replicate_values = {
            metric: [] for metric in settings["regression_metrics"]
        }
        for _ in range(n_resamples):
            index = cluster_indices(groups, rng)
            current = point_metrics(observed[index], predicted[index])
            for metric in replicate_values:
                replicate_values[metric].append(current[metric])
        for metric, values in replicate_values.items():
            estimate = estimates[metric]
            low, high, standard_error, valid = percentile_summary(
                values, confidence
            )
            rows.append(
                {
                    "task_id": group["task_id"].iloc[0],
                    "dataset_id": group["dataset_id"].iloc[0],
                    "model_id": model_id,
                    "run_id": run_id,
                    "target": target,
                    "metric": metric,
                    "estimate": estimate,
                    "ci_low": low,
                    "ci_high": high,
                    "standard_error": standard_error,
                    "confidence_level": confidence,
                    "n_resamples": n_resamples,
                    "n_valid": valid,
                    "n_eval": len(group),
                    "n_clusters": len(pd.unique(clusters)),
                    "bootstrap_unit": settings["cluster_column"],
                    "status": "ok" if valid else "not_estimable",
                }
            )
    return rows


def bootstrap_classification(
    predictions: pd.DataFrame,
    model_id: str,
    run_id: str,
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    confidence = float(settings["confidence_level"])
    n_resamples = int(settings["n_resamples"])
    keys, observed, scores, predicted = classification_matrices(predictions)
    clusters = keys[settings["cluster_column"]].astype(str).to_numpy()
    groups = cluster_groups(clusters)
    rng = np.random.default_rng(
        stable_seed(int(settings["random_seed"]), model_id, "aggregate")
    )
    estimates = classification_values(observed, scores, predicted)
    replicate_values = {metric: [] for metric in settings["classification_metrics"]}
    for _ in range(n_resamples):
        index = cluster_indices(groups, rng)
        current = classification_values(
            observed[index], scores[index], predicted[index]
        )
        for metric in replicate_values:
            replicate_values[metric].append(current[metric])

    rows: list[dict[str, Any]] = []
    for metric, values in replicate_values.items():
        low, high, standard_error, valid = percentile_summary(values, confidence)
        rows.append(
            {
                "task_id": predictions["task_id"].iloc[0],
                "dataset_id": predictions["dataset_id"].iloc[0],
                "model_id": model_id,
                "run_id": run_id,
                "target": "__all__",
                "metric": metric,
                "estimate": estimates[metric],
                "ci_low": low,
                "ci_high": high,
                "standard_error": standard_error,
                "confidence_level": confidence,
                "n_resamples": n_resamples,
                "n_valid": valid,
                "n_eval": len(keys),
                "n_clusters": len(pd.unique(clusters)),
                "bootstrap_unit": settings["cluster_column"],
                "status": "ok" if valid else "not_estimable",
            }
        )
    return rows


def run_bootstrap(
    robustness: dict[str, Any], output_dir: Path, model_runs: dict[str, str]
) -> pd.DataFrame:
    settings = robustness["bootstrap"]
    rows: list[dict[str, Any]] = []
    partition = settings["partition"]
    for model_id, run_id in sorted(model_runs.items()):
        predictions = pd.read_csv(prediction_path(run_id), dtype={"clip_id": str})
        predictions = predictions[predictions["partition"].eq(partition)].copy()
        print(f"Bootstrap: {model_id}")
        if "y_score" in predictions.columns:
            rows.extend(
                bootstrap_classification(predictions, model_id, run_id, settings)
            )
        else:
            rows.extend(bootstrap_regression(predictions, model_id, run_id, settings))
    intervals = pd.DataFrame(rows).sort_values(["task_id", "model_id", "target", "metric"])
    intervals.to_csv(output_dir / "bootstrap_intervals.csv", index=False)
    return intervals


def paired_regression(
    reference: pd.DataFrame,
    candidate: pd.DataFrame,
    reference_id: str,
    candidate_id: str,
    metrics: list[str],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    confidence = float(settings["confidence_level"])
    n_resamples = int(settings["n_resamples"])
    for target in sorted(reference["target"].unique()):
        left = reference[reference["target"].eq(target)][
            ["record_id", "clip_id", "y_true", "y_pred"]
        ].rename(columns={"y_true": "y_true_ref", "y_pred": "y_pred_ref"})
        right = candidate[candidate["target"].eq(target)][
            ["record_id", "clip_id", "y_true", "y_pred"]
        ].rename(columns={"y_true": "y_true_candidate", "y_pred": "y_pred_candidate"})
        if set(left["record_id"]) != set(right["record_id"]):
            raise ValueError(
                f"Paired comparison requires identical records: {reference_id} vs {candidate_id}"
            )
        merged = left.merge(
            right,
            on="record_id",
            how="inner",
            validate="one_to_one",
            suffixes=("_ref", "_candidate"),
        ).sort_values("record_id")
        if not np.allclose(merged["y_true_ref"], merged["y_true_candidate"]):
            raise ValueError(f"Observed targets differ for {reference_id} vs {candidate_id}")
        observed = merged["y_true_ref"].to_numpy(dtype=float)
        ref_pred = merged["y_pred_ref"].to_numpy(dtype=float)
        candidate_pred = merged["y_pred_candidate"].to_numpy(dtype=float)
        clusters = merged["clip_id_ref"].astype(str).to_numpy()
        rng = np.random.default_rng(
            stable_seed(
                int(settings["random_seed"]), reference_id, candidate_id, str(target)
            )
        )
        groups = cluster_groups(clusters)
        reference_metrics = point_metrics(observed, ref_pred)
        candidate_metrics = point_metrics(observed, candidate_pred)
        replicate_values = {metric: [] for metric in metrics}
        for _ in range(n_resamples):
            index = cluster_indices(groups, rng)
            ref_boot = point_metrics(observed[index], ref_pred[index])
            candidate_boot = point_metrics(observed[index], candidate_pred[index])
            for metric in metrics:
                minimize = metric in {"rmse", "mae"}
                replicate_values[metric].append(
                    ref_boot[metric] - candidate_boot[metric]
                    if minimize
                    else candidate_boot[metric] - ref_boot[metric]
                )
        for metric, values in replicate_values.items():
            ref_value = reference_metrics[metric]
            candidate_value = candidate_metrics[metric]
            minimize = metric in {"rmse", "mae"}
            improvement = (
                ref_value - candidate_value if minimize else candidate_value - ref_value
            )
            low, high, standard_error, valid = percentile_summary(
                values, confidence
            )
            finite = np.asarray(values, dtype=float)
            finite = finite[np.isfinite(finite)]
            rows.append(
                {
                    "task_id": reference["task_id"].iloc[0],
                    "reference_model": reference_id,
                    "candidate_model": candidate_id,
                    "target": target,
                    "metric": metric,
                    "reference_value": ref_value,
                    "candidate_value": candidate_value,
                    "improvement": improvement,
                    "ci_low": low,
                    "ci_high": high,
                    "standard_error": standard_error,
                    "probability_improvement_gt_zero": float(np.mean(finite > 0))
                    if len(finite)
                    else math.nan,
                    "confidence_level": confidence,
                    "n_resamples": n_resamples,
                    "n_valid": valid,
                    "n_eval": len(merged),
                    "n_clusters": len(pd.unique(clusters)),
                    "bootstrap_unit": settings["cluster_column"],
                    "direction_normalized": True,
                }
            )
    return rows


def paired_classification(
    reference: pd.DataFrame,
    candidate: pd.DataFrame,
    reference_id: str,
    candidate_id: str,
    metrics: list[str],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    ref_keys, ref_observed, ref_scores, ref_predicted = classification_matrices(reference)
    candidate_keys, candidate_observed, candidate_scores, candidate_predicted = (
        classification_matrices(candidate)
    )
    if not ref_keys.equals(candidate_keys) or not np.array_equal(
        ref_observed, candidate_observed
    ):
        raise ValueError(
            f"Paired classification requires identical records: {reference_id} vs {candidate_id}"
        )
    clusters = ref_keys[settings["cluster_column"]].astype(str).to_numpy()
    groups = cluster_groups(clusters)
    reference_values = classification_values(ref_observed, ref_scores, ref_predicted)
    candidate_values = classification_values(
        candidate_observed, candidate_scores, candidate_predicted
    )
    rng = np.random.default_rng(
        stable_seed(int(settings["random_seed"]), reference_id, candidate_id)
    )
    replicates = {metric: [] for metric in metrics}
    for _ in range(int(settings["n_resamples"])):
        index = cluster_indices(groups, rng)
        ref_boot = classification_values(
            ref_observed[index], ref_scores[index], ref_predicted[index]
        )
        candidate_boot = classification_values(
            candidate_observed[index],
            candidate_scores[index],
            candidate_predicted[index],
        )
        for metric in metrics:
            replicates[metric].append(candidate_boot[metric] - ref_boot[metric])

    rows: list[dict[str, Any]] = []
    confidence = float(settings["confidence_level"])
    for metric in metrics:
        values = np.asarray(replicates[metric], dtype=float)
        low, high, standard_error, valid = percentile_summary(values.tolist(), confidence)
        finite = values[np.isfinite(values)]
        rows.append(
            {
                "task_id": reference["task_id"].iloc[0],
                "reference_model": reference_id,
                "candidate_model": candidate_id,
                "target": "__all__",
                "metric": metric,
                "reference_value": reference_values[metric],
                "candidate_value": candidate_values[metric],
                "improvement": candidate_values[metric] - reference_values[metric],
                "ci_low": low,
                "ci_high": high,
                "standard_error": standard_error,
                "probability_improvement_gt_zero": float(np.mean(finite > 0)),
                "confidence_level": confidence,
                "n_resamples": int(settings["n_resamples"]),
                "n_valid": valid,
                "n_eval": len(ref_keys),
                "n_clusters": len(pd.unique(clusters)),
                "bootstrap_unit": settings["cluster_column"],
                "direction_normalized": True,
            }
        )
    return rows


def run_paired_comparisons(
    robustness: dict[str, Any], output_dir: Path, model_runs: dict[str, str]
) -> pd.DataFrame:
    settings = robustness["bootstrap"]
    partition = settings["partition"]
    rows: list[dict[str, Any]] = []
    for comparison in robustness["paired_comparisons"]:
        reference_id = comparison["reference"]
        reference = pd.read_csv(
            prediction_path(model_runs[reference_id]), dtype={"clip_id": str}
        )
        reference = reference[reference["partition"].eq(partition)].copy()
        for candidate_id in comparison["candidates"]:
            print(f"Paired bootstrap: {candidate_id} vs {reference_id}")
            candidate = pd.read_csv(
                prediction_path(model_runs[candidate_id]), dtype={"clip_id": str}
            )
            candidate = candidate[candidate["partition"].eq(partition)].copy()
            if "y_score" in reference.columns:
                rows.extend(
                    paired_classification(
                        reference,
                        candidate,
                        reference_id,
                        candidate_id,
                        comparison["metrics"],
                        settings,
                    )
                )
            else:
                rows.extend(
                    paired_regression(
                        reference,
                        candidate,
                        reference_id,
                        candidate_id,
                        comparison["metrics"],
                        settings,
                    )
                )
    paired = pd.DataFrame(rows).sort_values(
        ["task_id", "reference_model", "candidate_model", "target", "metric"]
    )
    paired.to_csv(output_dir / "paired_comparisons.csv", index=False)
    return paired


def run_feature_coverage(
    robustness: dict[str, Any], baseline: dict[str, Any], output_dir: Path
) -> pd.DataFrame:
    section = robustness["feature_coverage_sensitivity"]
    dataset_id = section["dataset_id"]
    cohort_frames: dict[tuple[str, str], pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []
    for task_path in section["tasks"]:
        task = load_yaml(repo_path(task_path))
        task_id = task["task"]["id"]
        for cohort in section["cohorts"]:
            frame, _, _, _ = prepare_data(
                task, dataset_id, baseline["feature_sets"][cohort["feature_set"]]
            )
            cohort_frames[(task_id, cohort["id"])] = frame

        all_frame = cohort_frames[(task_id, "all_eligible")]
        complete_frame = cohort_frames[(task_id, "shared6_complete")]
        targets = task["target"]["columns"]
        for cohort_id, frame in [
            ("all_eligible", all_frame),
            ("shared6_complete", complete_frame),
        ]:
            train = frame[frame["partition"].eq("train")]
            for partition in ["train", "dev", "test"]:
                subset = frame[frame["partition"].eq(partition)]
                all_subset = all_frame[all_frame["partition"].eq(partition)]
                complete_subset = complete_frame[
                    complete_frame["partition"].eq(partition)
                ]
                for target in targets:
                    train_mean = float(train[target].mean())
                    predicted = np.full(len(subset), train_mean)
                    current = point_metrics(
                        subset[target].to_numpy(dtype=float), predicted
                    )
                    all_mean = float(all_subset[target].mean())
                    complete_mean = float(complete_subset[target].mean())
                    all_std = float(all_subset[target].std(ddof=1))
                    rows.append(
                        {
                            "task_id": task_id,
                            "unit_of_analysis": task["task"]["unit_of_analysis"],
                            "dataset_id": dataset_id,
                            "partition": partition,
                            "cohort": cohort_id,
                            "target": target,
                            "n_records": len(subset),
                            "n_clips": subset["clip_id"].nunique(),
                            "n_all_eligible": len(all_subset),
                            "coverage_fraction": len(complete_subset) / len(all_subset),
                            "target_mean": float(subset[target].mean()),
                            "target_std": float(subset[target].std(ddof=1)),
                            "all_eligible_target_mean": all_mean,
                            "shared6_target_mean": complete_mean,
                            "shared6_minus_all_mean": complete_mean - all_mean,
                            "standardized_mean_shift": (complete_mean - all_mean) / all_std
                            if all_std > 0
                            else math.nan,
                            "target_mean_train_value": train_mean,
                            "target_mean_rmse": current["rmse"],
                            "target_mean_mae": current["mae"],
                        }
                    )
    sensitivity = pd.DataFrame(rows).sort_values(
        ["task_id", "partition", "cohort", "target"]
    )
    sensitivity.to_csv(output_dir / "feature_coverage_sensitivity.csv", index=False)
    return sensitivity


def run_gpr_calibration(
    robustness: dict[str, Any], output_dir: Path, model_runs: dict[str, str]
) -> pd.DataFrame:
    section = robustness["gpr_calibration"]
    model_id = section["experiment"]
    predictions = pd.read_csv(
        prediction_path(model_runs[model_id]), dtype={"clip_id": str}
    )
    predictions = predictions[
        predictions["partition"].eq(section["partition"])
    ].copy()
    rows: list[dict[str, Any]] = []
    for target, group in predictions.groupby("target", sort=True):
        observed = group["y_true"].to_numpy(dtype=float)
        predicted = group["y_pred"].to_numpy(dtype=float)
        std = group["y_std"].to_numpy(dtype=float)
        if not np.isfinite(std).all() or (std <= 0).any():
            raise ValueError(f"{model_id}/{target}: invalid predictive standard deviations")
        for nominal in section["nominal_coverage"]:
            nominal = float(nominal)
            z_value = float(norm.ppf((1.0 + nominal) / 2.0))
            lower = predicted - z_value * std
            upper = predicted + z_value * std
            covered = (observed >= lower) & (observed <= upper)
            alpha = 1.0 - nominal
            interval_score = upper - lower
            interval_score += (2.0 / alpha) * (lower - observed) * (observed < lower)
            interval_score += (2.0 / alpha) * (observed - upper) * (observed > upper)
            empirical = float(np.mean(covered))
            rows.append(
                {
                    "task_id": group["task_id"].iloc[0],
                    "model_id": model_id,
                    "partition": section["partition"],
                    "target": target,
                    "nominal_coverage": nominal,
                    "empirical_coverage": empirical,
                    "calibration_error": empirical - nominal,
                    "absolute_calibration_error": abs(empirical - nominal),
                    "mean_interval_width": float(np.mean(upper - lower)),
                    "mean_interval_score": float(np.mean(interval_score)),
                    "n_eval": len(group),
                    "n_clips": group["clip_id"].nunique(),
                }
            )
    calibration = pd.DataFrame(rows).sort_values(["target", "nominal_coverage"])
    calibration.to_csv(output_dir / "gpr_calibration.csv", index=False)
    return calibration


def markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    display = frame.copy()
    for column in display.select_dtypes(include=["number"]).columns:
        display[column] = display[column].map(
            lambda value: f"{value:.{digits}f}" if pd.notna(value) else "NA"
        )
    columns = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for values in display.astype(str).itertuples(index=False, name=None):
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_report(
    robustness: dict[str, Any],
    output_dir: Path,
    multiseed_summary: pd.DataFrame,
    intervals: pd.DataFrame,
    paired: pd.DataFrame,
    sensitivity: pd.DataFrame,
    calibration: pd.DataFrame,
) -> None:
    seed_table = multiseed_summary[
        (multiseed_summary["partition"].eq("test"))
        & (multiseed_summary["metric"].eq("rmse"))
        & (multiseed_summary["scope"].isin(["individual", "record"]))
    ][["model_id", "target", "mean", "std", "minimum", "maximum", "n_seeds"]]
    paired_table = paired[
        paired["metric"].isin(
            [
                "rmse",
                "macro_average_precision",
                "micro_average_precision",
                "macro_f1",
                "micro_f1",
            ]
        )
    ][
        [
            "candidate_model",
            "target",
            "metric",
            "improvement",
            "ci_low",
            "ci_high",
            "probability_improvement_gt_zero",
        ]
    ]
    coverage_table = sensitivity[
        (sensitivity["partition"].eq("test"))
        & (sensitivity["cohort"].eq("shared6_complete"))
    ][
        [
            "task_id",
            "target",
            "n_records",
            "n_all_eligible",
            "coverage_fraction",
            "shared6_minus_all_mean",
            "standardized_mean_shift",
        ]
    ]
    calibration_table = calibration[
        [
            "target",
            "nominal_coverage",
            "empirical_coverage",
            "calibration_error",
            "mean_interval_width",
        ]
    ]
    estimable = intervals[intervals["status"].eq("ok")]
    max_seed_std = float(seed_table["std"].max())
    clip_eventful = coverage_table[
        (coverage_table["task_id"].eq("iso_coordinate_regression"))
        & (coverage_table["target"].eq("mean_ISOEventful"))
    ].iloc[0]
    response_eventful = coverage_table[
        (coverage_table["task_id"].eq("isd_individual_iso_prediction"))
        & (coverage_table["target"].eq("ISOEventful"))
    ].iloc[0]
    eventful_gpr = calibration[
        (calibration["target"].eq("ISOEventful"))
        & (calibration["nominal_coverage"].eq(0.80))
    ].iloc[0]
    report = f"""# MOSAIQ Step 7 robustness report

Robustness version: `{robustness['robustness_version']}`<br>
Benchmark version: `{robustness['benchmark_version']}`<br>
Split version: `{robustness['split_version']}`

## What each analysis does

1. **Multi-seed stability.** RF and XGBoost are trained five times with seeds
   {', '.join(str(value) for value in robustness['multiseed']['seeds'])}. The mean shows typical performance and the standard deviation shows how much the answer changes because of estimator randomness.
2. **Cluster bootstrap confidence intervals.** Test `clip_id` values are sampled
   with replacement {robustness['bootstrap']['n_resamples']} times. All responses attached to a sampled clip stay together. Percentile intervals therefore describe held-out sample uncertainty without treating repeated assessments as independent.
3. **Paired model comparison.** Reference and candidate predictions are aligned
   on exactly the same records and resampled together. Improvement is direction-normalized, so a positive value always favours the candidate. An interval crossing zero means the current test sample does not establish a stable advantage.
4. **Feature-coverage sensitivity.** ISD all-eligible and shared6-complete cohorts
   are compared within every partition at both clip and response level. Retention, target shifts, and target-mean errors reveal whether complete-case filtering changes the population being evaluated.
5. **GPR interval calibration.** Gaussian prediction intervals at 50%, 80%, and
   95% nominal coverage are compared with their empirical coverage. Negative calibration error means intervals are too narrow; positive error means they are conservative.

## Multi-seed test RMSE

{markdown_table(seed_table)}

## Paired improvements

{markdown_table(paired_table)}

## ISD shared6 test-cohort sensitivity

{markdown_table(coverage_table)}

## GPR prediction-interval calibration

{markdown_table(calibration_table)}

## Main findings

- Estimator randomness is small relative to the observed model differences: the largest test RMSE standard deviation across the stochastic models is {max_seed_std:.4f}.
- Both DeLTA source-conditioned annoyance models have positive paired RMSE, MAE, and R2 improvement intervals against Target Mean. This supports conditional predictability when source labels are observed; it does not establish audio-to-annoyance prediction.
- No reduced Tong-style model stably improves both ISD targets on held-out locations. RF and XGBoost have better Eventfulness point estimates, but their paired 95% intervals cross zero, while both significantly worsen Pleasantness. GPR is worse than Target Mean for both RMSE targets.
- The DeLTA annoyance-conditioned source classifier improves macro average precision, macro F1, and micro F1, but worsens pooled micro average precision. The prevalence baseline receives a high micro AP because its label-specific constant scores rank frequent labels above rare labels when every label-record decision is pooled. Macro and per-label results must therefore remain visible.
- Shared6 retains only {clip_eventful['coverage_fraction']:.1%} of ISD test clips and {response_eventful['coverage_fraction']:.1%} of ISD test responses. Eventfulness is shifted by {clip_eventful['standardized_mean_shift']:.2f} SD at clip level and {response_eventful['standardized_mean_shift']:.2f} SD at response level, so shared6 results describe a selected subset rather than the full ISD test population.
- GPR intervals under-cover at every tested level. For Eventfulness, the nominal 80% interval covers only {eventful_gpr['empirical_coverage']:.1%}, indicating overconfident uncertainty estimates under the current held-out-location split.

## Validation scope and limits

- {len(estimable)} bootstrap intervals were estimable; constant predictors have undefined correlation intervals and are retained as `not_estimable` rather than silently removed.
- Confidence intervals condition on the released test partitions and the current datasets. They do not prove external or cross-dataset generalisation.
- Multiple assessments from one soundscape remain a key dependence structure; cluster resampling is used wherever those assessments occur.
- The feature sensitivity analysis describes complete-case selection. It does not infer or impute missing psychoacoustic features.
- GPR coverage assesses the current Gaussian uncertainty output. It does not establish that the model is probabilistically calibrated in a new city or dataset.
- All Step 7 runs remain tabular and record `audio_used=false`; audio evaluation is outside v0.1.
"""
    (output_dir / "robustness_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    args = parse_args()
    robustness = load_yaml(args.config.resolve())
    if args.bootstrap_resamples is not None:
        robustness["bootstrap"]["n_resamples"] = args.bootstrap_resamples
    baseline = load_yaml(repo_path(robustness["baseline_config"]))
    if str(baseline["benchmark_version"]) != str(robustness["benchmark_version"]):
        raise ValueError("Robustness and baseline benchmark versions differ")
    if str(baseline["split_version"]) != str(robustness["split_version"]):
        raise ValueError("Robustness and baseline split versions differ")

    output_dir = args.output_dir.resolve()
    clear_generated_output(output_dir)
    model_runs = run_id_by_model()
    _, multiseed_summary = run_multiseed(robustness, baseline, output_dir)
    intervals = run_bootstrap(robustness, output_dir, model_runs)
    paired = run_paired_comparisons(robustness, output_dir, model_runs)
    sensitivity = run_feature_coverage(robustness, baseline, output_dir)
    calibration = run_gpr_calibration(robustness, output_dir, model_runs)
    build_report(
        robustness,
        output_dir,
        multiseed_summary,
        intervals,
        paired,
        sensitivity,
        calibration,
    )
    print(
        "Step 7 complete: "
        f"{len(multiseed_summary)} multiseed summaries, "
        f"{len(intervals)} bootstrap intervals, "
        f"{len(paired)} paired comparisons, "
        f"{len(sensitivity)} coverage rows, and "
        f"{len(calibration)} calibration rows"
    )


if __name__ == "__main__":
    main()

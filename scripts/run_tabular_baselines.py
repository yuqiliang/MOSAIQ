"""Run the reproducible MOSAIQ tabular baseline suite.

Usage:
  uv run python scripts/run_tabular_baselines.py
  uv run python scripts/run_tabular_baselines.py --experiment tong_style_reduced_lr
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from scipy.integrate import trapezoid
from scipy.spatial.distance import jensenshannon
from scipy.stats import gaussian_kde, pearsonr, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNetCV, LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "benchmark" / "baselines" / "baseline_config.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "benchmark" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MOSAIQ tabular baselines")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--experiment", action="append", default=[])
    parser.add_argument(
        "--seed",
        type=int,
        help="Override the config seed, for example during robustness runs.",
    )
    return parser.parse_args()


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def apply_filters(frame: pd.DataFrame, filters: list[dict[str, Any]]) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for rule in filters:
        values = frame[rule["column"]]
        operator = rule["operator"]
        if operator == "equals":
            current = values.astype(str).str.lower().eq(str(rule.get("value")).lower())
        elif operator == "not_equals":
            current = ~values.astype(str).str.lower().eq(str(rule.get("value")).lower())
        elif operator == "in":
            current = values.isin(rule.get("values", []))
        elif operator == "not_in":
            current = ~values.isin(rule.get("values", []))
        elif operator == "not_null":
            current = values.notna()
        else:
            raise ValueError(f"Unsupported filter operator: {operator}")
        mask &= current
    return frame.loc[mask].copy()


def assignment_frame(dataset_id: str, path: Path) -> pd.DataFrame:
    assignments = load_csv(path)
    if dataset_id == "SATP":
        assignments["partition"] = "fold_" + assignments["fold"].astype(str)
    else:
        assignments = assignments.rename(columns={"split": "partition"})
    return assignments


def prepare_data(
    task: dict[str, Any],
    dataset_id: str,
    features: dict[str, Any],
) -> tuple[pd.DataFrame, list[str], list[str], list[str]]:
    dataset = next(
        item for item in task["input"]["datasets"] if item["dataset_id"] == dataset_id
    )
    frame = apply_filters(load_csv(repo_path(dataset["path"])), dataset.get("filters", []))
    id_column = task["input"]["id_column"]
    split_link = task["input"].get("split_link_column", "clip_id")
    numeric = list(features.get("numeric", []))
    categorical = list(features.get("categorical", []))
    complete_case = list(features.get("complete_case", []))
    feature_columns = numeric + categorical

    required_feature_columns = list(dict.fromkeys([*feature_columns, *complete_case]))
    missing_features = [
        column for column in required_feature_columns if column not in frame.columns
    ]
    if missing_features and task["input"]["record_type"] == "responses":
        clip_path = REPO_ROOT / "datasets" / dataset_id / "data" / "clips.csv"
        clips = load_csv(clip_path)
        available = [column for column in missing_features if column in clips.columns]
        unavailable = sorted(set(missing_features).difference(available))
        if unavailable:
            raise ValueError(f"Features not found in response or clip table: {unavailable}")
        frame = frame.merge(
            clips[["clip_id", *available]],
            on="clip_id",
            how="left",
            validate="many_to_one",
        )

    assignment_path = repo_path(task["split_protocol"]["assignment_files"][dataset_id])
    assignments = assignment_frame(dataset_id, assignment_path)
    frame = frame.merge(
        assignments[["clip_id", "partition", "split_version"]],
        left_on=split_link,
        right_on="clip_id",
        how="left",
        validate="one_to_one" if id_column == "clip_id" else "many_to_one",
        suffixes=("", "_assignment"),
    )
    if split_link != "clip_id" and "clip_id_assignment" in frame:
        frame = frame.drop(columns="clip_id_assignment")
    frame = frame[frame["partition"].isin(["train", "dev", "test"])].copy()

    targets = task["target"]["columns"]
    overlap = sorted(set(feature_columns).intersection(targets))
    if overlap:
        raise ValueError(f"Target leakage: feature columns overlap targets: {overlap}")
    for column in list(dict.fromkeys([*targets, *numeric, *complete_case])):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=targets)
    if complete_case:
        frame = frame.dropna(subset=complete_case)
    frame["record_id"] = frame[id_column].astype(str)
    if "clip_id" not in frame:
        frame["clip_id"] = frame[split_link].astype(str)
    return frame, targets, numeric, categorical


def make_preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical,
            )
        )
    return ColumnTransformer(transformers, remainder="drop")


def make_estimator(model: str, parameters: dict[str, Any], seed: int) -> Any:
    if model == "ridge":
        return Ridge(alpha=float(parameters.get("alpha", 1.0)))
    if model == "linear_regression":
        return LinearRegression()
    if model == "elastic_net_cv":
        return ElasticNetCV(
            l1_ratio=parameters.get("l1_ratio", [0.1, 0.5, 0.9, 1.0]),
            alphas=np.logspace(-4, 0, 40),
            cv=int(parameters.get("cv", 5)),
            max_iter=20_000,
            n_jobs=int(parameters.get("n_jobs", 1)),
            random_state=seed,
        )
    if model == "random_forest":
        return RandomForestRegressor(
            n_estimators=int(parameters.get("n_estimators", 300)),
            min_samples_leaf=int(parameters.get("min_samples_leaf", 3)),
            n_jobs=int(parameters.get("n_jobs", 1)),
            random_state=seed,
        )
    if model == "xgboost":
        from xgboost import XGBRegressor

        return XGBRegressor(
            objective="reg:squarederror",
            n_estimators=int(parameters.get("n_estimators", 300)),
            max_depth=int(parameters.get("max_depth", 4)),
            learning_rate=float(parameters.get("learning_rate", 0.03)),
            subsample=float(parameters.get("subsample", 0.9)),
            colsample_bytree=float(parameters.get("colsample_bytree", 0.9)),
            n_jobs=int(parameters.get("n_jobs", 1)),
            random_state=seed,
        )
    if model == "gaussian_process":
        noise = float(parameters.get("noise_level", 0.1))
        kernel = ConstantKernel(1.0) * RBF(1.0) + WhiteKernel(noise_level=noise)
        return GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-6,
            normalize_y=True,
            optimizer=None,
            random_state=seed,
        )
    raise ValueError(f"Unsupported model: {model}")


def safe_correlation(function: Any, observed: np.ndarray, predicted: np.ndarray) -> float:
    if np.std(observed) <= 1e-12 or np.std(predicted) <= 1e-12:
        return math.nan
    return float(function(observed, predicted).statistic)


def point_metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rmse": float(np.sqrt(mean_squared_error(observed, predicted))),
        "mae": float(mean_absolute_error(observed, predicted)),
        "r2": float(r2_score(observed, predicted)),
        "pearson_r": safe_correlation(pearsonr, observed, predicted),
        "spearman_rho": safe_correlation(spearmanr, observed, predicted),
    }


def kde_density(values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=float), grid[0], grid[-1])
    if len(clipped) < 2 or np.std(clipped) < 1e-8:
        bandwidth = 0.05
        density = np.exp(-0.5 * ((grid - float(np.mean(clipped))) / bandwidth) ** 2)
    else:
        density = gaussian_kde(clipped)(grid)
    area = trapezoid(density, grid)
    return density / area


def distribution_metrics(
    observed: np.ndarray, predicted: np.ndarray
) -> tuple[dict[str, float], pd.DataFrame]:
    grid = np.linspace(-1.0, 1.0, 401)
    observed_density = kde_density(observed, grid)
    predicted_density = kde_density(predicted, grid)
    epsilon = 1e-12
    p = np.maximum(observed_density, epsilon)
    q = np.maximum(predicted_density, epsilon)
    p /= p.sum()
    q /= q.sum()
    metrics = {
        "kl_divergence": float(np.sum(p * np.log(p / q))),
        "js_divergence": float(jensenshannon(p, q, base=math.e) ** 2),
        "dme": float(trapezoid(np.abs(observed_density - predicted_density), grid) / 2.0),
    }
    curves = pd.DataFrame(
        {
            "grid": grid,
            "observed_density": observed_density,
            "predicted_density": predicted_density,
        }
    )
    return metrics, curves


def package_versions() -> dict[str, str]:
    packages = ["numpy", "pandas", "scipy", "scikit-learn", "xgboost", "pyyaml"]
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def select_f1_threshold(observed: np.ndarray, scores: np.ndarray) -> float:
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], scores)))
    if len(candidates) > 202:
        candidates = np.unique(
            np.concatenate(([0.0, 0.5, 1.0], np.quantile(scores, np.linspace(0, 1, 199))))
        )
    ranked = []
    for threshold in candidates:
        predicted = (scores >= threshold).astype(int)
        score = f1_score(observed, predicted, zero_division=0)
        ranked.append((float(score), -abs(float(threshold) - 0.5), float(threshold)))
    return max(ranked)[2]


def classification_result_row(
    config: dict[str, Any],
    task: dict[str, Any],
    dataset_id: str,
    partition: str,
    scope: str,
    feature_set_id: str,
    model_id: str,
    target: str,
    metric: str,
    value: float,
    n_train: int,
    n_eval: int,
    seed: int,
    run_id: str,
) -> dict[str, Any]:
    return {
        "benchmark_version": config["benchmark_version"],
        "task_id": task["task"]["id"],
        "task_version": task["task"]["version"],
        "split_version": config["split_version"],
        "dataset_id": dataset_id,
        "partition": partition,
        "scope": scope,
        "feature_set": feature_set_id,
        "model_id": model_id,
        "target": target,
        "metric": metric,
        "value": value,
        "n_train": n_train,
        "n_eval": n_eval,
        "random_seed": seed,
        "run_id": run_id,
    }


def run_multilabel_experiment(
    experiment: dict[str, Any],
    config: dict[str, Any],
    output_dir: Path,
) -> tuple[list[dict[str, Any]], list[pd.DataFrame]]:
    task = load_yaml(repo_path(experiment["task_config"]))
    dataset_id = experiment["dataset_id"]
    feature_set_id = experiment["feature_set"]
    features = config["feature_sets"][feature_set_id]
    frame, targets, numeric, categorical = prepare_data(task, dataset_id, features)
    seed = int(config["random_seed"])
    model_id = experiment["id"]
    run_id = f"{task['task']['id']}__{dataset_id.lower()}__{model_id}__seed{seed}"
    parameters = experiment.get("parameters", {})
    model = experiment["model"]

    train = frame[frame["partition"].eq("train")].copy()
    dev = frame[frame["partition"].eq("dev")].copy()
    if train.empty or dev.empty:
        raise ValueError(f"{model_id}: train and dev rows are required")

    feature_columns = numeric + categorical
    transformed: dict[str, np.ndarray] = {}
    fitted: dict[str, Any] = {"model_id": model_id, "targets": {}, "thresholds": {}}
    if model == "one_vs_rest_logistic":
        preprocessor = make_preprocessor(numeric, categorical)
        transformed["train"] = preprocessor.fit_transform(train[feature_columns])
        for partition in ["dev", "test"]:
            subset = frame[frame["partition"].eq(partition)]
            transformed[partition] = preprocessor.transform(subset[feature_columns])
        fitted["preprocessor"] = preprocessor
    elif model != "label_prevalence":
        raise ValueError(f"Unsupported multilabel model: {model}")

    scores: dict[str, dict[str, np.ndarray]] = {"dev": {}, "test": {}}
    for target in targets:
        observed_train = train[target].to_numpy(dtype=int)
        if model == "label_prevalence":
            prevalence = float(observed_train.mean())
            estimator: Any = {"prevalence": prevalence}
            for partition in ["dev", "test"]:
                n_rows = int(frame["partition"].eq(partition).sum())
                scores[partition][target] = np.full(n_rows, prevalence)
        elif len(np.unique(observed_train)) < 2:
            prevalence = float(observed_train.mean())
            estimator = {"prevalence": prevalence, "constant_training_label": True}
            for partition in ["dev", "test"]:
                n_rows = int(frame["partition"].eq(partition).sum())
                scores[partition][target] = np.full(n_rows, prevalence)
        else:
            estimator = LogisticRegression(
                C=float(parameters.get("C", 1.0)),
                class_weight=parameters.get("class_weight"),
                max_iter=2_000,
                random_state=seed,
            )
            estimator.fit(transformed["train"], observed_train)
            for partition in ["dev", "test"]:
                scores[partition][target] = estimator.predict_proba(
                    transformed[partition]
                )[:, 1]
        fitted["targets"][target] = estimator
        threshold = select_f1_threshold(
            dev[target].to_numpy(dtype=int), scores["dev"][target]
        )
        fitted["thresholds"][target] = threshold

    result_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    for partition in ["dev", "test"]:
        subset = frame[frame["partition"].eq(partition)].copy()
        observed_matrix = subset[targets].to_numpy(dtype=int)
        score_matrix = np.column_stack([scores[partition][target] for target in targets])
        thresholds = np.array([fitted["thresholds"][target] for target in targets])
        predicted_matrix = (score_matrix >= thresholds).astype(int)

        aggregate_metrics = {
            "macro_average_precision": float(
                average_precision_score(observed_matrix, score_matrix, average="macro")
            ),
            "micro_average_precision": float(
                average_precision_score(observed_matrix, score_matrix, average="micro")
            ),
            "macro_f1": float(
                f1_score(observed_matrix, predicted_matrix, average="macro", zero_division=0)
            ),
            "micro_f1": float(
                f1_score(observed_matrix, predicted_matrix, average="micro", zero_division=0)
            ),
        }
        for metric, value in aggregate_metrics.items():
            result_rows.append(
                classification_result_row(
                    config,
                    task,
                    dataset_id,
                    partition,
                    "aggregate",
                    feature_set_id,
                    model_id,
                    "__all__",
                    metric,
                    value,
                    len(train),
                    len(subset),
                    seed,
                    run_id,
                )
            )

        for index, target in enumerate(targets):
            observed = observed_matrix[:, index]
            predicted = predicted_matrix[:, index]
            target_metrics = {
                "average_precision": float(
                    average_precision_score(observed, score_matrix[:, index])
                ),
                "f1": float(f1_score(observed, predicted, zero_division=0)),
            }
            for metric, value in target_metrics.items():
                result_rows.append(
                    classification_result_row(
                        config,
                        task,
                        dataset_id,
                        partition,
                        "per_label",
                        feature_set_id,
                        model_id,
                        target,
                        metric,
                        value,
                        len(train),
                        len(subset),
                        seed,
                        run_id,
                    )
                )
            prediction_frames.append(
                pd.DataFrame(
                    {
                        "run_id": run_id,
                        "task_id": task["task"]["id"],
                        "dataset_id": dataset_id,
                        "partition": partition,
                        "record_id": subset["record_id"].to_numpy(),
                        "clip_id": subset["clip_id"].astype(str).to_numpy(),
                        "target": target,
                        "y_true": observed,
                        "y_score": score_matrix[:, index],
                        "y_pred": predicted,
                        "threshold": thresholds[index],
                        "y_std": np.nan,
                    }
                )
            )

    prediction_dir = output_dir / "predictions"
    artifact_dir = output_dir / "artifacts"
    metadata_dir = output_dir / "runs"
    for directory in [prediction_dir, artifact_dir, metadata_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    pd.concat(prediction_frames, ignore_index=True).to_csv(
        prediction_dir / f"{run_id}.csv", index=False
    )
    joblib.dump(fitted, artifact_dir / f"{run_id}.joblib")

    config_digest = hashlib.sha256(
        json.dumps(experiment, sort_keys=True).encode("utf-8")
    ).hexdigest()
    metadata = {
        "run_id": run_id,
        "experiment": experiment,
        "experiment_sha256": config_digest,
        "benchmark_version": config["benchmark_version"],
        "split_version": config["split_version"],
        "random_seed": seed,
        "n_rows": {key: int(value) for key, value in frame.groupby("partition").size().items()},
        "threshold_selection_partition": "dev",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": package_versions(),
        "audio_used": False,
    }
    with (metadata_dir / f"{run_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result_rows, []


def run_experiment(
    experiment: dict[str, Any],
    config: dict[str, Any],
    output_dir: Path,
) -> tuple[list[dict[str, Any]], list[pd.DataFrame]]:
    task = load_yaml(repo_path(experiment["task_config"]))
    if task["task"]["task_type"] == "multilabel_classification":
        return run_multilabel_experiment(experiment, config, output_dir)
    dataset_id = experiment["dataset_id"]
    feature_set_id = experiment["feature_set"]
    features = config["feature_sets"][feature_set_id]
    frame, targets, numeric, categorical = prepare_data(task, dataset_id, features)
    seed = int(config["random_seed"])
    model_id = experiment["id"]
    run_id = f"{task['task']['id']}__{dataset_id.lower()}__{model_id}__seed{seed}"
    parameters = experiment.get("parameters", {})

    train = frame[frame["partition"].eq("train")].copy()
    if train.empty:
        raise ValueError(f"{model_id}: no training rows")
    feature_columns = numeric + categorical
    fitted: dict[str, Any] = {"model_id": model_id, "targets": {}}
    transformed: dict[str, np.ndarray] = {}
    preprocessor = None
    if experiment["model"] != "target_mean":
        preprocessor = make_preprocessor(numeric, categorical)
        transformed["train"] = preprocessor.fit_transform(train[feature_columns])
        for partition in ["dev", "test"]:
            subset = frame[frame["partition"].eq(partition)]
            transformed[partition] = preprocessor.transform(subset[feature_columns])
        fitted["preprocessor"] = preprocessor

    predictions: list[pd.DataFrame] = []
    result_rows: list[dict[str, Any]] = []
    curves: list[pd.DataFrame] = []
    for target in targets:
        if experiment["model"] == "target_mean":
            estimator = {"mean": float(train[target].mean())}
        else:
            estimator = make_estimator(experiment["model"], parameters, seed)
            estimator.fit(transformed["train"], train[target].to_numpy())
        fitted["targets"][target] = estimator

        for partition in ["dev", "test"]:
            subset = frame[frame["partition"].eq(partition)].copy()
            observed = subset[target].to_numpy(dtype=float)
            predicted_std = np.full(len(subset), np.nan)
            if experiment["model"] == "target_mean":
                predicted = np.full(len(subset), estimator["mean"])
            elif experiment["model"] == "gaussian_process":
                predicted, predicted_std = estimator.predict(
                    transformed[partition], return_std=True
                )
            else:
                predicted = estimator.predict(transformed[partition])

            prediction_frame = pd.DataFrame(
                {
                    "run_id": run_id,
                    "task_id": task["task"]["id"],
                    "dataset_id": dataset_id,
                    "partition": partition,
                    "record_id": subset["record_id"].to_numpy(),
                    "clip_id": subset["clip_id"].astype(str).to_numpy(),
                    "target": target,
                    "y_true": observed,
                    "y_pred": predicted,
                    "y_std": predicted_std,
                }
            )
            predictions.append(prediction_frame)

            metrics = point_metrics(observed, predicted)
            for metric, value in metrics.items():
                result_rows.append(
                    {
                        "benchmark_version": config["benchmark_version"],
                        "task_id": task["task"]["id"],
                        "task_version": task["task"]["version"],
                        "split_version": config["split_version"],
                        "dataset_id": dataset_id,
                        "partition": partition,
                        "scope": "individual" if task["task"]["unit_of_analysis"] == "response" else "record",
                        "feature_set": feature_set_id,
                        "model_id": model_id,
                        "target": target,
                        "metric": metric,
                        "value": value,
                        "n_train": len(train),
                        "n_eval": len(subset),
                        "random_seed": seed,
                        "run_id": run_id,
                    }
                )

            if task["task"]["unit_of_analysis"] == "response":
                distribution, curve = distribution_metrics(observed, predicted)
                for metric, value in distribution.items():
                    result_rows.append(
                        {
                            "benchmark_version": config["benchmark_version"],
                            "task_id": task["task"]["id"],
                            "task_version": task["task"]["version"],
                            "split_version": config["split_version"],
                            "dataset_id": dataset_id,
                            "partition": partition,
                            "scope": "group_kde",
                            "feature_set": feature_set_id,
                            "model_id": model_id,
                            "target": target,
                            "metric": metric,
                            "value": value,
                            "n_train": len(train),
                            "n_eval": len(subset),
                            "random_seed": seed,
                            "run_id": run_id,
                        }
                    )
                curve.insert(0, "target", target)
                curve.insert(0, "partition", partition)
                curve.insert(0, "model_id", model_id)
                curve.insert(0, "run_id", run_id)
                curves.append(curve)

    prediction_dir = output_dir / "predictions"
    artifact_dir = output_dir / "artifacts"
    metadata_dir = output_dir / "runs"
    for directory in [prediction_dir, artifact_dir, metadata_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    pd.concat(predictions, ignore_index=True).to_csv(
        prediction_dir / f"{run_id}.csv", index=False
    )
    joblib.dump(fitted, artifact_dir / f"{run_id}.joblib")

    config_digest = hashlib.sha256(
        json.dumps(experiment, sort_keys=True).encode("utf-8")
    ).hexdigest()
    metadata = {
        "run_id": run_id,
        "experiment": experiment,
        "experiment_sha256": config_digest,
        "benchmark_version": config["benchmark_version"],
        "split_version": config["split_version"],
        "random_seed": seed,
        "n_rows": {key: int(value) for key, value in frame.groupby("partition").size().items()},
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": package_versions(),
        "audio_used": False,
    }
    with (metadata_dir / f"{run_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result_rows, curves


def main() -> None:
    args = parse_args()
    config = load_yaml(args.config.resolve())
    if args.seed is not None:
        config["random_seed"] = args.seed
    output_dir = args.output_dir.resolve()
    selected = set(args.experiment)
    experiments = [
        item
        for item in config["experiments"]
        if not selected or item["id"] in selected
    ]
    unknown = selected.difference(item["id"] for item in experiments)
    if unknown:
        raise SystemExit(f"Unknown experiment(s): {', '.join(sorted(unknown))}")

    if not selected:
        for folder, pattern in [
            (output_dir / "predictions", "*.csv"),
            (output_dir / "artifacts", "*.joblib"),
            (output_dir / "runs", "*.json"),
        ]:
            if folder.exists():
                for path in folder.glob(pattern):
                    path.unlink()

    all_results: list[dict[str, Any]] = []
    all_curves: list[pd.DataFrame] = []
    for experiment in experiments:
        print(f"Running {experiment['id']}...")
        results, curves = run_experiment(experiment, config, output_dir)
        all_results.extend(results)
        all_curves.extend(curves)

    output_dir.mkdir(parents=True, exist_ok=True)
    result_frame = pd.DataFrame(all_results)
    result_path = output_dir / "baseline_results.csv"
    if selected and result_path.exists():
        previous = pd.read_csv(result_path)
        previous = previous[~previous["model_id"].isin(selected)]
        result_frame = pd.concat([previous, result_frame], ignore_index=True)
    result_frame = result_frame.sort_values(
        ["task_id", "dataset_id", "model_id", "partition", "target", "scope", "metric"]
    )
    result_frame.to_csv(result_path, index=False)
    if all_curves:
        curve_frame = pd.concat(all_curves, ignore_index=True)
        curve_path = output_dir / "distribution_curves.csv"
        if selected and curve_path.exists():
            previous_curves = pd.read_csv(curve_path)
            previous_curves = previous_curves[
                ~previous_curves["model_id"].isin(selected)
            ]
            curve_frame = pd.concat([previous_curves, curve_frame], ignore_index=True)
        curve_frame.to_csv(curve_path, index=False)
    print(
        f"Wrote {len(result_frame)} metric rows from {len(experiments)} experiments "
        f"to {output_dir.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()

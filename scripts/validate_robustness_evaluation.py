"""Validate frozen MOSAIQ Step 7 robustness outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_DIR = REPO_ROOT / "benchmark" / "robustness"
CONFIG_PATH = ROBUSTNESS_DIR / "robustness_config.yaml"
BASELINE_RESULTS = REPO_ROOT / "benchmark" / "results" / "baseline_results.csv"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    errors: list[str] = []
    required_files = [
        "multiseed_results.csv",
        "multiseed_summary.csv",
        "bootstrap_intervals.csv",
        "paired_comparisons.csv",
        "feature_coverage_sensitivity.csv",
        "gpr_calibration.csv",
        "robustness_report.md",
    ]
    for name in required_files:
        if not (ROBUSTNESS_DIR / name).exists():
            errors.append(f"missing generated robustness output: {name}")
    if errors:
        raise SystemExit("\n".join(errors))

    multiseed = pd.read_csv(ROBUSTNESS_DIR / "multiseed_results.csv")
    summary = pd.read_csv(ROBUSTNESS_DIR / "multiseed_summary.csv")
    intervals = pd.read_csv(ROBUSTNESS_DIR / "bootstrap_intervals.csv")
    paired = pd.read_csv(ROBUSTNESS_DIR / "paired_comparisons.csv")
    sensitivity = pd.read_csv(
        ROBUSTNESS_DIR / "feature_coverage_sensitivity.csv"
    )
    calibration = pd.read_csv(ROBUSTNESS_DIR / "gpr_calibration.csv")

    expected_models = set(config["multiseed"]["experiments"])
    expected_seeds = set(config["multiseed"]["seeds"])
    if set(multiseed["model_id"]) != expected_models:
        errors.append("multiseed experiment IDs differ from the robustness config")
    for model_id, group in multiseed.groupby("model_id"):
        if set(group["random_seed"]) != expected_seeds:
            errors.append(f"{model_id}: incomplete multiseed seed set")
    if not np.isfinite(multiseed["value"]).all():
        errors.append("multiseed metrics must be finite")
    if not summary["n_seeds"].eq(len(expected_seeds)).all():
        errors.append("every multiseed summary row must contain all configured seeds")
    if not (summary["std"].ge(0).all() and np.isfinite(summary["std"]).all()):
        errors.append("multiseed standard deviations must be finite and non-negative")

    baseline = pd.read_csv(BASELINE_RESULTS)
    key = ["model_id", "partition", "scope", "target", "metric"]
    frozen_seed = multiseed[multiseed["random_seed"].eq(2026)]
    expected_frozen = baseline[baseline["model_id"].isin(expected_models)]
    comparison = frozen_seed.merge(
        expected_frozen[key + ["value"]],
        on=key,
        how="outer",
        suffixes=("_robustness", "_baseline"),
        indicator=True,
    )
    if not comparison["_merge"].eq("both").all() or not np.allclose(
        comparison["value_robustness"], comparison["value_baseline"], atol=1e-12
    ):
        errors.append("seed 2026 multiseed metrics do not reproduce Step 6")

    for path in (ROBUSTNESS_DIR / "multiseed" / "runs").glob("*.json"):
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if metadata.get("audio_used") is not False:
            errors.append(f"{path.name}: audio_used must remain false")
        if metadata.get("random_seed") not in expected_seeds:
            errors.append(f"{path.name}: unexpected seed")
    expected_run_count = len(expected_models) * len(expected_seeds)
    observed_run_count = len(list((ROBUSTNESS_DIR / "multiseed" / "runs").glob("*.json")))
    if observed_run_count != expected_run_count:
        errors.append(
            f"expected {expected_run_count} multiseed metadata files, found {observed_run_count}"
        )

    configured_resamples = int(config["bootstrap"]["n_resamples"])
    if not intervals["n_resamples"].eq(configured_resamples).all():
        errors.append("bootstrap interval resample count differs from config")
    expected_baseline_models = set(baseline["model_id"])
    if set(intervals["model_id"]) != expected_baseline_models:
        errors.append("bootstrap intervals do not cover every Step 6 model")
    if not intervals["bootstrap_unit"].eq(config["bootstrap"]["cluster_column"]).all():
        errors.append("bootstrap unit must be clip_id")
    estimable = intervals[intervals["status"].eq("ok")]
    if not (
        np.isfinite(
            estimable[["estimate", "ci_low", "ci_high", "standard_error"]]
        ).all().all()
        and (estimable["ci_low"] <= estimable["ci_high"]).all()
        and estimable["n_valid"].eq(configured_resamples).all()
    ):
        errors.append("estimable bootstrap intervals are invalid or incomplete")
    not_estimable = intervals[intervals["status"].eq("not_estimable")]
    if not set(not_estimable["metric"]).issubset({"pearson_r", "spearman_rho"}):
        errors.append("only correlations may be marked not_estimable")

    expected_pair_rows = 0
    for item in config["paired_comparisons"]:
        target_count = (
            1
            if item["reference"] == "delta_source_label_prevalence"
            else baseline[baseline["model_id"].eq(item["reference"])]["target"].nunique()
        )
        expected_pair_rows += len(item["candidates"]) * len(item["metrics"]) * target_count
    if len(paired) != expected_pair_rows:
        errors.append(
            f"expected {expected_pair_rows} paired rows, found {len(paired)}"
        )
    if not (
        paired["direction_normalized"].all()
        and paired["bootstrap_unit"].eq("clip_id").all()
        and paired["n_resamples"].eq(configured_resamples).all()
        and paired["probability_improvement_gt_zero"].between(0, 1).all()
        and np.isfinite(
            paired[
                [
                    "reference_value",
                    "candidate_value",
                    "improvement",
                    "ci_low",
                    "ci_high",
                ]
            ]
        ).all().all()
    ):
        errors.append("paired comparison values or provenance are invalid")

    expected_sensitivity_rows = 2 * 2 * 3 * 2
    if len(sensitivity) != expected_sensitivity_rows:
        errors.append(
            f"expected {expected_sensitivity_rows} feature-sensitivity rows"
        )
    if set(sensitivity["cohort"]) != {"all_eligible", "shared6_complete"}:
        errors.append("feature-sensitivity cohorts are incomplete")
    if not sensitivity["coverage_fraction"].between(0, 1).all():
        errors.append("feature coverage must be in [0, 1]")
    clip_test = sensitivity[
        (sensitivity["task_id"].eq("iso_coordinate_regression"))
        & (sensitivity["partition"].eq("test"))
        & (sensitivity["cohort"].eq("shared6_complete"))
    ]
    if not (
        clip_test["n_records"].eq(184).all()
        and clip_test["n_all_eligible"].eq(581).all()
        and np.allclose(clip_test["coverage_fraction"], 184 / 581)
    ):
        errors.append("ISD test shared6 coverage differs from the frozen report")

    expected_levels = set(float(value) for value in config["gpr_calibration"]["nominal_coverage"])
    if len(calibration) != 2 * len(expected_levels):
        errors.append("unexpected GPR calibration row count")
    for _, group in calibration.groupby("target"):
        if set(group["nominal_coverage"]) != expected_levels:
            errors.append("GPR nominal coverage levels are incomplete")
    if not (
        calibration["empirical_coverage"].between(0, 1).all()
        and (calibration["mean_interval_width"] > 0).all()
        and (calibration["mean_interval_score"] >= 0).all()
    ):
        errors.append("GPR calibration values are outside valid ranges")

    report = (ROBUSTNESS_DIR / "robustness_report.md").read_text(encoding="utf-8")
    for required in [
        "Multi-seed stability",
        "Cluster bootstrap confidence intervals",
        "Paired model comparison",
        "Feature-coverage sensitivity",
        "GPR interval calibration",
    ]:
        if required not in report:
            errors.append(f"robustness report is missing section: {required}")

    if errors:
        print(f"Robustness validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(
        "Robustness validation passed: "
        f"{len(expected_models)} stochastic models x {len(expected_seeds)} seeds, "
        f"{len(intervals)} bootstrap intervals, {len(paired)} paired comparisons, "
        f"{len(sensitivity)} coverage rows, {len(calibration)} GPR calibration rows"
    )


if __name__ == "__main__":
    main()

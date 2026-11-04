"""Generate MOSAIQ baseline model cards from configs and validated results."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

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


def format_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    if isinstance(value, (float, int)):
        return f"{float(value):.4f}"
    return str(value)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(format_value(value) for value in row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def limitation_lines(model_id: str, dataset_id: str, feature_set: str) -> list[str]:
    lines = [
        "This is a reference baseline, not a proposed state-of-the-art architecture.",
        "No audio waveform is consumed; the run metadata records `audio_used=false`.",
        "Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.",
    ]
    if dataset_id == "ARAUS":
        lines.append("The independent ARAUS test partition contains only 48 eligible clips.")
    if "elastic_net_shared6" in model_id:
        lines.append("This uses six shared features and is not the published 264-candidate ARAUS replication.")
    if model_id.startswith("tong_style_reduced"):
        lines.append("The feature set omits unavailable CitySeg, OSM, THD, and other Tong et al. predictors.")
        lines.append("ISD evaluation holds out locations rather than randomly splitting individual responses.")
    if feature_set in {"shared6", "shared6_cohort_only", "tong_style_reduced"} and dataset_id == "ISD":
        lines.append("The shared-six complete-case cohort covers 43.3% of ISD clips.")
    if model_id == "delta_source_from_observed_annoyance_logistic":
        lines.append("This diagnostic model conditions on observed mean annoyance and is not an automatic audio source-recognition model.")
    if model_id.startswith("delta_annoyance_from_observed_sources"):
        lines.append("Inference assumes that the 24 source annotations are already observed; predicted-source propagation is not evaluated here.")
    if model_id.endswith("target_mean") or "target_mean" in model_id:
        lines.append("The model ignores all predictors and represents an intentionally weak reference point.")
    return lines


def regression_tables(test: pd.DataFrame) -> str:
    point = test[test["scope"].isin(["record", "individual"])]
    point_metrics = ["rmse", "mae", "r2", "pearson_r", "spearman_rho"]
    rows = []
    for target in sorted(point["target"].unique()):
        target_rows = point[point["target"].eq(target)].set_index("metric")["value"]
        rows.append([target, *[target_rows.get(metric, math.nan) for metric in point_metrics]])
    text = "### Test Point Metrics\n\n" + markdown_table(
        ["Target", "RMSE", "MAE", "R2", "Pearson r", "Spearman rho"], rows
    )
    distribution = test[test["scope"].eq("group_kde")]
    if not distribution.empty:
        rows = []
        for target in sorted(distribution["target"].unique()):
            target_rows = distribution[distribution["target"].eq(target)].set_index("metric")["value"]
            rows.append(
                [
                    target,
                    target_rows.get("kl_divergence", math.nan),
                    target_rows.get("js_divergence", math.nan),
                    target_rows.get("dme", math.nan),
                ]
            )
        text += "\n\n### Test Distribution Metrics\n\n" + markdown_table(
            ["Target", "KL", "JS", "DME"], rows
        )
    return text


def classification_tables(test: pd.DataFrame) -> str:
    aggregate = test[test["scope"].eq("aggregate")].set_index("metric")["value"]
    rows = [
        [
            "All 24 labels",
            aggregate.get("macro_average_precision", math.nan),
            aggregate.get("micro_average_precision", math.nan),
            aggregate.get("macro_f1", math.nan),
            aggregate.get("micro_f1", math.nan),
        ]
    ]
    return "### Test Aggregate Metrics\n\n" + markdown_table(
        ["Scope", "Macro AP", "Micro AP", "Macro F1", "Micro F1"], rows
    )


def build_card(
    experiment: dict[str, Any],
    config: dict[str, Any],
    results: pd.DataFrame,
) -> tuple[str, str, str, str]:
    model_id = experiment["id"]
    task = load_yaml(REPO_ROOT / experiment["task_config"])
    task_id = task["task"]["id"]
    dataset_id = experiment["dataset_id"]
    feature_set_id = experiment["feature_set"]
    model_results = results[results["model_id"].eq(model_id)]
    if model_results.empty:
        raise ValueError(f"No result rows found for {model_id}")
    run_id = model_results["run_id"].iloc[0]
    with (RESULT_DIR / "runs" / f"{run_id}.json").open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    feature_set = config["feature_sets"][feature_set_id]
    test = model_results[model_results["partition"].eq("test")]
    n_train = int(test["n_train"].iloc[0])
    n_test = int(test["n_eval"].iloc[0])
    n_dev = int(metadata["n_rows"]["dev"])
    task_type = task["task"]["task_type"]

    metrics_text = (
        classification_tables(test)
        if task_type == "multilabel_classification"
        else regression_tables(test)
    )
    predictors = [*feature_set["numeric"], *feature_set["categorical"]]
    predictor_text = ", ".join(f"`{value}`" for value in predictors) or "None"
    target_text = ", ".join(f"`{value}`" for value in task["target"]["columns"])
    parameter_text = json.dumps(experiment.get("parameters", {}), sort_keys=True)
    limitations = "\n".join(
        f"- {line}" for line in limitation_lines(model_id, dataset_id, feature_set_id)
    )
    threshold_note = (
        "Decision thresholds were selected per label on the development partition only."
        if task_type == "multilabel_classification"
        else "No classification threshold is used."
    )

    card = f"""---
model_id: {model_id}
task_id: {task_id}
dataset_id: {dataset_id}
benchmark_version: {config['benchmark_version']}
split_version: {config['split_version']}
status: reference-baseline
audio_used: false
---

# {model_id}

## Model Summary

- **Task:** `{task_id}` ({task_type})
- **Dataset:** `{dataset_id}`
- **Estimator family:** `{experiment['model']}`
- **Feature set:** `{feature_set_id}`
- **Predictors:** {predictor_text}
- **Targets:** {target_text}
- **Parameters:** `{parameter_text}`
- **Random seed:** `{config['random_seed']}`
- **Audio used:** `false`

## Intended Use

This model establishes reproducible reference performance for MOSAIQ Paper 2
and validates the corresponding task, split, feature, prediction, and metric
interfaces. It is not intended for consequential decisions about individuals
or places.

## Data and Evaluation

- Training records: {n_train}
- Development records: {n_dev}
- Test records: {n_test}
- Split protocol: `{task['split_protocol']['protocol']}` version `{config['split_version']}`
- Preprocessing is fitted on training records only.
- {threshold_note}

{metrics_text}

## Limitations

{limitations}

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment {model_id}
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `{run_id}`
- Experiment SHA-256: `{metadata['experiment_sha256']}`
- Task config: `{experiment['task_config']}`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/{run_id}.csv`
"""
    return model_id, task_id, dataset_id, card


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    results = pd.read_csv(RESULT_DIR / "baseline_results.csv")
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    for path in CARD_DIR.glob("*.md"):
        path.unlink()

    index_rows = []
    for experiment in config["experiments"]:
        model_id, task_id, dataset_id, card = build_card(experiment, config, results)
        filename = f"{model_id}.md"
        (CARD_DIR / filename).write_text(card, encoding="utf-8")
        index_rows.append([f"[`{model_id}`]({filename})", task_id, dataset_id, "No"])

    readme = """# MOSAIQ Baseline Model Cards

These cards are generated from the executable baseline config, run metadata,
and validated result table by `scripts/build_model_cards.py`. Do not edit an
individual card manually; regenerate after changing a model or result.

""" + markdown_table(["Model", "Task", "Dataset", "Audio"], index_rows) + "\n"
    (CARD_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(f"Wrote {len(index_rows)} model cards to {CARD_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

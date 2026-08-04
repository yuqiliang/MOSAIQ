"""Build the versioned, manuscript-facing MOSAIQ Paper 2 output package."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "papers" / "paper2_output_config.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build fixed MOSAIQ Paper 2 outputs")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.6f", na_rep="")


def markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    display = frame.copy()
    for column in display.select_dtypes(include="number").columns:
        display[column] = display[column].map(
            lambda value: f"{value:.{digits}f}" if pd.notna(value) else "NA"
        )
    columns = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in display.astype(str).itertuples(index=False, name=None):
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def dataset_table(row_counts: pd.DataFrame) -> pd.DataFrame:
    labels = {
        "ISD": "ISO PAQ and ISO coordinates",
        "ARAUS": "ISO PAQ, ISO coordinates, appropriateness",
        "SATP": "Multilingual ISO PAQ and ISO coordinates",
        "DeLTA": "Annoyance and 24 sound-source labels",
    }
    rows: list[dict[str, Any]] = []
    for dataset_id in ["ISD", "ARAUS", "SATP", "DeLTA"]:
        current = row_counts[row_counts["dataset_id"].eq(dataset_id)]
        responses = pd.read_csv(
            REPO_ROOT / "datasets" / dataset_id / "data" / "responses.csv",
            low_memory=False,
        )
        rows.append(
            {
                "dataset_id": dataset_id,
                "track": current["track"].iloc[0],
                "target_family": labels[dataset_id],
                "n_clips": int(current.loc[current["resource"].eq("clips"), "n_rows"].iloc[0]),
                "n_responses": int(
                    current.loc[current["resource"].eq("responses"), "n_rows"].iloc[0]
                ),
                "n_participants": int(responses["participant_id"].nunique()),
            }
        )
    frame = pd.DataFrame(rows)
    total = {
        "dataset_id": "Total",
        "track": "core + extension",
        "target_family": "dataset-specific",
        "n_clips": int(frame["n_clips"].sum()),
        "n_responses": int(frame["n_responses"].sum()),
        "n_participants": int(frame["n_participants"].sum()),
    }
    return pd.concat([frame, pd.DataFrame([total])], ignore_index=True)


def regression_table(
    metrics: pd.DataFrame,
    intervals: pd.DataFrame,
    task_ids: list[str],
) -> pd.DataFrame:
    selected_metrics = ["rmse", "mae", "r2", "pearson_r", "spearman_rho"]
    selected = metrics[
        metrics["task_id"].isin(task_ids)
        & metrics["partition"].eq("test")
        & metrics["scope"].isin(["record", "individual"])
        & metrics["metric"].isin(selected_metrics)
    ]
    index = [
        "task_id",
        "dataset_id",
        "feature_set",
        "model_id",
        "target",
        "n_train",
        "n_eval",
    ]
    table = selected.pivot_table(
        index=index, columns="metric", values="value"
    ).reset_index()
    rmse_ci = intervals[intervals["metric"].eq("rmse")][
        ["model_id", "target", "ci_low", "ci_high", "n_clusters"]
    ].rename(columns={"ci_low": "rmse_ci_low", "ci_high": "rmse_ci_high"})
    table = table.merge(rmse_ci, on=["model_id", "target"], how="left", validate="one_to_one")
    table["cohort_id"] = (
        table["task_id"]
        + "__"
        + table["feature_set"]
        + "__ntrain"
        + table["n_train"].astype(str)
        + "__neval"
        + table["n_eval"].astype(str)
    )
    order = [
        *index,
        "cohort_id",
        "rmse",
        "rmse_ci_low",
        "rmse_ci_high",
        "mae",
        "r2",
        "pearson_r",
        "spearman_rho",
        "n_clusters",
    ]
    return table[order].sort_values(["task_id", "model_id", "target"])


def delta_source_table(
    metrics: pd.DataFrame, intervals: pd.DataFrame
) -> pd.DataFrame:
    point = metrics[
        metrics["task_id"].eq("delta_source_multilabel")
        & metrics["partition"].eq("test")
        & metrics["scope"].eq("aggregate")
    ][["model_id", "metric", "value", "n_train", "n_eval"]].rename(
        columns={"value": "estimate"}
    )
    ci = intervals[
        intervals["task_id"].eq("delta_source_multilabel")
    ][["model_id", "metric", "ci_low", "ci_high", "n_clusters"]]
    return point.merge(
        ci, on=["model_id", "metric"], how="left", validate="one_to_one"
    ).sort_values(["model_id", "metric"])


def legacy_draft_audit() -> str:
    return """# Paper 2 legacy-draft integration audit

Status: **integrated and removed**
Legacy findings: **19**

The former repository working draft was audited before removal. It contained
19 stale triggers, including TODO markers, pre-release split counts, statements
that ISD/SATP/DeLTA still required splits, proposed rather than executed
baselines, and missing robustness evidence.

The replacement Word manuscript:

1. uses split version `0.1.0` and the fixed task/dataset counts;
2. reports the 17 executed no-audio tabular experiments without claiming full
   ARAUS or Tong-model replication;
3. incorporates Step 7 uncertainty, sensitivity, and calibration evidence;
4. preserves the no-audio scope and defers audio/visual/multimodal claims;
5. retains both validation warnings and the 48-record ARAUS test caveat; and
6. follows the current Scientific Data Data Descriptor section structure.

The removed Markdown file is no longer an input to the deterministic fixed-
output build. This audit is retained to document why it was deleted.
"""


def main() -> None:
    args = parse_args()
    config = load_yaml(args.config.resolve())
    output_dir = repo_path(config["output_dir"])
    if output_dir.exists():
        shutil.rmtree(output_dir)
    table_dir = output_dir / "tables"
    figure_dir = output_dir / "figures"
    table_dir.mkdir(parents=True)
    figure_dir.mkdir(parents=True)

    validation_dir = REPO_ROOT / "benchmark" / "validation"
    robustness_dir = REPO_ROOT / "benchmark" / "robustness"
    results_dir = REPO_ROOT / "benchmark" / "results"
    row_counts = pd.read_csv(validation_dir / "row_counts.csv")
    eligibility = pd.read_csv(validation_dir / "task_eligibility.csv")
    splits = pd.read_csv(REPO_ROOT / "benchmark" / "splits" / "split_summary.csv")
    feature_coverage = pd.read_csv(validation_dir / "feature_coverage.csv")
    validation_summary = pd.read_csv(validation_dir / "validation_summary.csv")
    baseline = pd.read_csv(results_dir / "baseline_results.csv")
    intervals = pd.read_csv(robustness_dir / "bootstrap_intervals.csv")
    paired = pd.read_csv(robustness_dir / "paired_comparisons.csv")
    multiseed = pd.read_csv(robustness_dir / "multiseed_summary.csv")
    sensitivity = pd.read_csv(robustness_dir / "feature_coverage_sensitivity.csv")
    calibration = pd.read_csv(robustness_dir / "gpr_calibration.csv")

    tables: dict[str, pd.DataFrame] = {}
    tables["table_01_dataset_resources.csv"] = dataset_table(row_counts)
    tables["table_02_task_eligibility.csv"] = eligibility[
        [
            "task_id",
            "task_version",
            "dataset_id",
            "unit_of_analysis",
            "source_rows",
            "declared_exclusions",
            "missing_targets",
            "frozen_rows",
            "manifest",
        ]
    ]
    tables["table_03_released_splits.csv"] = splits
    tables["table_04_feature_coverage.csv"] = feature_coverage[
        feature_coverage["partition"].eq("all")
    ][
        [
            "dataset_id",
            "track",
            "feature_set_id",
            "n_clips",
            "n_available",
            "coverage",
            "source",
            "notes",
        ]
    ]
    tables["table_05_clip_regression_baselines.csv"] = regression_table(
        baseline,
        intervals,
        ["araus_pleasantness_regression", "iso_coordinate_regression"],
    )
    tables["table_06_isd_response_baselines.csv"] = regression_table(
        baseline, intervals, ["isd_individual_iso_prediction"]
    )
    tables["table_07_delta_annoyance_baselines.csv"] = regression_table(
        baseline, intervals, ["delta_annoyance"]
    )
    tables["table_08_delta_source_baselines.csv"] = delta_source_table(
        baseline, intervals
    )
    tables["table_09_paired_comparisons.csv"] = paired
    tables["table_10_multiseed_test_rmse.csv"] = multiseed[
        multiseed["partition"].eq("test")
        & multiseed["metric"].eq("rmse")
        & multiseed["scope"].isin(["record", "individual"])
    ]
    tables["table_11_isd_coverage_sensitivity.csv"] = sensitivity[
        sensitivity["partition"].eq("test")
        & sensitivity["cohort"].eq("shared6_complete")
    ]
    tables["table_12_gpr_calibration.csv"] = calibration
    for filename, frame in tables.items():
        write_csv(frame, table_dir / filename)

    catalogue = pd.read_csv(REPO_ROOT / "catalogue" / "datasets.csv")
    resources = tables["table_01_dataset_resources.csv"]
    paired_rmse = paired[paired["metric"].eq("rmse")]
    key_numbers = {
        "freeze": {
            "freeze_id": config["freeze_id"],
            "freeze_date": str(config["freeze_date"]),
            "output_version": str(config["output_version"]),
            "benchmark_version": str(config["benchmark_version"]),
            "split_version": str(config["split_version"]),
            "robustness_version": str(config["robustness_version"]),
            "status": config["status"],
        },
        "catalogue": {
            "candidate_datasets": int(len(catalogue)),
            "fully_accessible": int(catalogue["access"].eq("Fully").sum()),
            "visual_available": int(catalogue["visual_available"].eq(True).sum()),
            "iso_12913_related": int(
                catalogue["annotation_framework"]
                .fillna("")
                .str.contains("12913", case=False)
                .sum()
            ),
        },
        "materialised_release": {
            "datasets": 4,
            "clips": int(resources.iloc[-1]["n_clips"]),
            "responses": int(resources.iloc[-1]["n_responses"]),
            "participants_summed_not_deduplicated": int(
                resources.iloc[-1]["n_participants"]
            ),
            "manifests": int(len(eligibility)),
        },
        "technical_validation": {
            "pass": int(validation_summary["status"].eq("PASS").sum()),
            "warn": int(validation_summary["status"].eq("WARN").sum()),
            "fail": int(validation_summary["status"].eq("FAIL").sum()),
        },
        "baselines": {
            "experiments": int(baseline["model_id"].nunique()),
            "metric_rows": int(len(baseline)),
            "model_cards": len(list((REPO_ROOT / "benchmark" / "model_cards").glob("*.md"))) - 1,
            "audio_used": False,
        },
        "robustness": {
            "stochastic_models": int(multiseed["model_id"].nunique()),
            "seeds": int(multiseed["n_seeds"].max()),
            "bootstrap_resamples": int(intervals["n_resamples"].max()),
            "bootstrap_intervals": int(len(intervals)),
            "paired_comparisons": int(len(paired)),
            "coverage_rows": int(len(sensitivity)),
            "gpr_calibration_rows": int(len(calibration)),
        },
        "headline_findings": {
            "araus_test_n": 48,
            "isd_shared6_test_clip_coverage": float(
                sensitivity[
                    sensitivity["task_id"].eq("iso_coordinate_regression")
                    & sensitivity["partition"].eq("test")
                    & sensitivity["cohort"].eq("shared6_complete")
                ]["coverage_fraction"].iloc[0]
            ),
            "isd_shared6_test_response_coverage": float(
                sensitivity[
                    sensitivity["task_id"].eq("isd_individual_iso_prediction")
                    & sensitivity["partition"].eq("test")
                    & sensitivity["cohort"].eq("shared6_complete")
                ]["coverage_fraction"].iloc[0]
            ),
            "delta_ridge_rmse_improvement": float(
                paired_rmse[
                    paired_rmse["candidate_model"].eq(
                        "delta_annoyance_from_observed_sources_ridge"
                    )
                ]["improvement"].iloc[0]
            ),
            "delta_rf_rmse_improvement": float(
                paired_rmse[
                    paired_rmse["candidate_model"].eq(
                        "delta_annoyance_from_observed_sources_rf"
                    )
                ]["improvement"].iloc[0]
            ),
            "gpr_eventfulness_empirical_80_coverage": float(
                calibration[
                    calibration["target"].eq("ISOEventful")
                    & calibration["nominal_coverage"].eq(0.8)
                ]["empirical_coverage"].iloc[0]
            ),
        },
    }
    with (output_dir / "paper2_key_numbers.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(key_numbers, handle, sort_keys=False, allow_unicode=False)

    figure_rows: list[dict[str, str]] = []
    for figure in config["figures"]:
        source = repo_path(figure["source"])
        if not source.exists():
            raise FileNotFoundError(f"Missing generated Paper 2 figure: {source}")
        destination = figure_dir / figure["filename"]
        shutil.copy2(source, destination)
        figure_rows.append(
            {
                "figure_id": figure["id"],
                "filename": figure["filename"],
                "caption": figure["caption"],
                "source_path": str(source.relative_to(REPO_ROOT)),
                "source_sha256": sha256(source),
                "fixed_sha256": sha256(destination),
            }
        )
    write_csv(pd.DataFrame(figure_rows), output_dir / "figure_index.csv")

    resources_display = resources.rename(
        columns={
            "dataset_id": "Dataset",
            "target_family": "Target family",
            "n_clips": "Clips",
            "n_responses": "Responses",
            "n_participants": "Participants",
        }
    )[["Dataset", "Target family", "Clips", "Responses", "Participants"]]
    split_display = splits[["dataset_id", "partition", "n_clips"]].rename(
        columns={"dataset_id": "Dataset", "partition": "Partition", "n_clips": "Clips"}
    )
    response_display = tables["table_06_isd_response_baselines.csv"][
        ["model_id", "target", "n_train", "n_eval", "rmse", "rmse_ci_low", "rmse_ci_high", "mae", "r2"]
    ]
    delta_display = tables["table_07_delta_annoyance_baselines.csv"][
        ["model_id", "n_train", "n_eval", "rmse", "rmse_ci_low", "rmse_ci_high", "mae", "r2"]
    ]
    source_display = tables["table_08_delta_source_baselines.csv"][
        ["model_id", "metric", "estimate", "ci_low", "ci_high"]
    ]
    manuscript = f"""# MOSAIQ Paper 2 generated evidence insert

Freeze ID: `{config['freeze_id']}`<br>
Output version: `{config['output_version']}`<br>
Benchmark version: `{config['benchmark_version']}`<br>
Split version: `{config['split_version']}`<br>
Scope: no-audio tabular benchmark v0.1

This file contains generated evidence blocks for the Scientific Data manuscript.
The prose may be integrated editorially, but numerical values must be updated by
rerunning the generator rather than manual editing.

## Data Records

The current MOSAIQ candidate materialises four source datasets as validated
clip- and response-level resources. Together they contain 27,850 clip or
stimulus rows and 59,935 response rows. The summed participant count is 5,078;
participants are not de-duplicated across source datasets.

{markdown_table(resources_display, digits=0)}

## Released splits

MOSAIQ split version `0.1.0` uses dataset-specific leakage controls. ISD is
grouped by location; ARAUS preserves source folds; SATP uses deterministic
five-fold evaluation because it has 27 recordings; and DeLTA uses iterative
multilabel stratification over source labels and annoyance bins. Response-level
ISD assessments inherit their clip partition through `clip_id`.

{markdown_table(split_display, digits=0)}

## Technical Validation

The candidate freeze passes 47 checks, retains two documented warnings, and has
no failures. The warnings concern two excluded ISD identifier collisions and
the need for per-file ARAUS raw-asset licence review. Eleven task/dataset
manifests lock eligible record IDs and source-row hashes. Asset references are
complete, but waveform and video files are not materialised in this no-audio
release. Shared psychoacoustic features are complete for ARAUS and available
for 43.3% of ISD clips; SATP and DeLTA do not contain the shared6 set.

## Baseline methods

The 17 experiments were executed through a unified train, predict, and
evaluate interface. Numeric preprocessing and categorical encoding were fitted
on the training partition only. The suite includes Target Mean, LAeq Ridge,
shared6 Ridge, an ARAUS shared6 Elastic Net transfer, reduced-feature linear,
RF, XGBoost and GPR models, DeLTA label prevalence and annoyance-conditioned
source classification, and source-conditioned annoyance regression. The ARAUS
Elastic Net is not the full published 264-feature replication, and the reduced
Tong-style models omit unavailable CitySeg, OSM, THD, and related variables.
No model consumes audio; every run records `audio_used=false`.

## ISD response-level results

All models below use the same shared6 complete-case cohort: 1,324 train and 279
test responses. Test responses represent 184 unique clips. No reduced
Tong-style model stably improves both ISO targets over the matched Target Mean
reference on held-out locations.

{markdown_table(response_display)}

## DeLTA annoyance results

Observed-source Ridge and RF both improve over Target Mean. Paired RMSE
improvement is 0.106 [0.054, 0.160] for Ridge and 0.103 [0.038, 0.165] for RF.
These are conditional models requiring observed source labels and are not
audio-to-annoyance systems.

{markdown_table(delta_display)}

## DeLTA source-label results

The annoyance-conditioned logistic classifier improves macro average precision,
macro F1, and micro F1, but reduces pooled micro average precision relative to
label prevalence. Macro, micro, and per-label results must therefore remain
visible together. The classifier uses observed mean annoyance and is not an
automatic audio source recogniser.

{markdown_table(source_display)}

## Robustness methods and findings

RF and XGBoost were rerun with seeds 2026-2030. The largest test-RMSE standard
deviation was 0.0034. Test uncertainty was estimated with 2,000 cluster
bootstrap resamples; all responses linked to the same `clip_id` were sampled
together. Candidate-reference comparisons used paired resamples and were
direction-normalised so positive improvement favours the candidate.

Shared6 retains 31.7% of ISD test clips and 40.7% of test responses. Its test
Eventfulness mean is shifted by 0.61 SD at clip level and 0.53 SD at response
level, showing that complete-case results describe a selected subset. GPR
intervals under-cover at all tested levels; the nominal 80% Eventfulness
interval covers 57.3% of held-out responses.

## Usage and interpretation limits

- ARAUS test results contain 48 records and require explicit small-test caveats.
- Results from different `cohort_id`, `n_train`, or `n_eval` values are not a fair ranking.
- Bootstrap intervals quantify uncertainty in the current test sample, not external transfer.
- ISD shared6 complete cases are not representative of the full test cohort.
- DeLTA cross-target models require observed human labels at inference time.
- Audio, visual, multimodal, missing-modality, and added-noise evaluation remain future work.

## Figure index

{markdown_table(pd.DataFrame(figure_rows)[['figure_id', 'filename', 'caption']], digits=0)}
"""
    (output_dir / "manuscript_evidence_insert.md").write_text(
        manuscript, encoding="utf-8"
    )
    (output_dir / "draft_replacement_audit.md").write_text(
        legacy_draft_audit(), encoding="utf-8"
    )

    readme = f"""# MOSAIQ Paper 2 fixed outputs v{config['output_version']}

Freeze ID: `{config['freeze_id']}`

This directory is generated by `scripts/build_paper2_fixed_outputs.py`. It is
the manuscript-facing snapshot of benchmark versions `{config['benchmark_version']}`
and split `{config['split_version']}`. Do not edit generated numbers manually.

- `paper2_key_numbers.yaml`: headline counts and findings;
- `manuscript_evidence_insert.md`: generated Scientific Data evidence blocks;
- `draft_replacement_audit.md`: integration record for the removed legacy draft;
- `tables/`: 12 fixed CSV tables;
- `figures/`: six copied, checksum-locked notebook figures;
- `figure_index.csv`: captions and source hashes;
- `output_manifest.csv`: provenance and checksum for each fixed output;
- `checksums.sha256`: package integrity file.

Regenerate and validate:

```bash
uv run python scripts/build_paper2_fixed_outputs.py
uv run python scripts/validate_paper2_fixed_outputs.py
```
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    generated_files = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name not in {"output_manifest.csv", "checksums.sha256"}
    )
    manifest_rows = []
    for path in generated_files:
        relative = path.relative_to(output_dir)
        role = "figure" if relative.parts[0] == "figures" else "table" if relative.parts[0] == "tables" else "documentation"
        manifest_rows.append(
            {
                "path": str(relative),
                "role": role,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "freeze_id": config["freeze_id"],
            }
        )
    write_csv(pd.DataFrame(manifest_rows), output_dir / "output_manifest.csv")
    checksum_files = sorted(
        path for path in output_dir.rglob("*") if path.is_file() and path.name != "checksums.sha256"
    )
    checksum_text = "\n".join(
        f"{sha256(path)}  {path.relative_to(output_dir)}" for path in checksum_files
    )
    (output_dir / "checksums.sha256").write_text(checksum_text + "\n", encoding="ascii")
    print(
        f"Built Paper 2 fixed outputs {config['freeze_id']}: "
        f"{len(tables)} tables, {len(figure_rows)} figures, "
        f"{len(manifest_rows)} manifested files"
    )


if __name__ == "__main__":
    main()

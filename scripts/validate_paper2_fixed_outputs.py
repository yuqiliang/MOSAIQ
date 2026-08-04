"""Validate the generated MOSAIQ Paper 2 fixed-output package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "papers" / "paper2_output_config.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    output_dir = repo_path(config["output_dir"])
    errors: list[str] = []
    expected_tables = {f"table_{index:02d}" for index in range(1, 13)}
    table_paths = sorted((output_dir / "tables").glob("*.csv"))
    observed_tables = {path.stem.split("_", 2)[0] + "_" + path.stem.split("_", 2)[1] for path in table_paths}
    if observed_tables != expected_tables:
        errors.append(
            f"fixed table IDs differ: missing={sorted(expected_tables - observed_tables)}, "
            f"unexpected={sorted(observed_tables - expected_tables)}"
        )
    if len(table_paths) != 12:
        errors.append(f"expected 12 fixed tables, found {len(table_paths)}")

    figure_index = pd.read_csv(output_dir / "figure_index.csv")
    if len(figure_index) != len(config["figures"]):
        errors.append("figure index count differs from config")
    for figure in config["figures"]:
        source = repo_path(figure["source"])
        fixed = output_dir / "figures" / figure["filename"]
        if not source.exists() or not fixed.exists():
            errors.append(f"missing source or fixed figure: {figure['filename']}")
            continue
        if sha256(source) != sha256(fixed):
            errors.append(f"fixed figure differs from notebook output: {figure['filename']}")

    checksum_path = output_dir / "checksums.sha256"
    declared: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        digest, relative = line.split("  ", 1)
        declared[relative] = digest
    actual_files = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    )
    actual_relatives = {str(path.relative_to(output_dir)) for path in actual_files}
    if set(declared) != actual_relatives:
        errors.append("checksum inventory differs from fixed package files")
    for path in actual_files:
        relative = str(path.relative_to(output_dir))
        if declared.get(relative) != sha256(path):
            errors.append(f"checksum mismatch: {relative}")

    manifest = pd.read_csv(output_dir / "output_manifest.csv")
    manifest_expected = actual_relatives - {"output_manifest.csv"}
    if set(manifest["path"]) != manifest_expected:
        errors.append("output manifest inventory is incomplete")
    for row in manifest.itertuples(index=False):
        path = output_dir / row.path
        if row.sha256 != sha256(path) or int(row.bytes) != path.stat().st_size:
            errors.append(f"manifest provenance mismatch: {row.path}")
        if row.freeze_id != config["freeze_id"]:
            errors.append(f"manifest freeze ID mismatch: {row.path}")

    key_numbers = load_yaml(output_dir / "paper2_key_numbers.yaml")
    freeze = key_numbers["freeze"]
    for key in [
        "freeze_id",
        "output_version",
        "benchmark_version",
        "split_version",
        "robustness_version",
        "status",
    ]:
        if str(freeze[key]) != str(config[key]):
            errors.append(f"key-number freeze metadata differs for {key}")

    row_counts = pd.read_csv(REPO_ROOT / "benchmark" / "validation" / "row_counts.csv")
    expected_clips = int(row_counts[row_counts["resource"].eq("clips")]["n_rows"].sum())
    expected_responses = int(
        row_counts[row_counts["resource"].eq("responses")]["n_rows"].sum()
    )
    release = key_numbers["materialised_release"]
    if release["clips"] != expected_clips or release["responses"] != expected_responses:
        errors.append("fixed release totals differ from technical-validation sources")

    dataset_resources = pd.read_csv(table_paths[0])
    total = dataset_resources[dataset_resources["dataset_id"].eq("Total")].iloc[0]
    if not (
        int(total["n_clips"]) == 27850
        and int(total["n_responses"]) == 59935
        and int(total["n_participants"]) == 5078
    ):
        errors.append("dataset resource headline totals differ from the frozen release")

    eligibility = pd.read_csv(output_dir / "tables" / "table_02_task_eligibility.csv")
    if len(eligibility) != 11 or eligibility["manifest"].duplicated().any():
        errors.append("task eligibility table must contain 11 unique manifests")
    splits = pd.read_csv(output_dir / "tables" / "table_03_released_splits.csv")
    source_splits = pd.read_csv(REPO_ROOT / "benchmark" / "splits" / "split_summary.csv")
    if not splits.equals(source_splits):
        errors.append("fixed split table differs from split release")

    clip_models = pd.read_csv(
        output_dir / "tables" / "table_05_clip_regression_baselines.csv"
    )
    if clip_models.duplicated(["model_id", "target"]).any():
        errors.append("clip baseline table contains duplicate model-target rows")
    expected_cohort = (
        clip_models["task_id"]
        + "__"
        + clip_models["feature_set"]
        + "__ntrain"
        + clip_models["n_train"].astype(str)
        + "__neval"
        + clip_models["n_eval"].astype(str)
    )
    if not expected_cohort.eq(clip_models["cohort_id"]).all():
        errors.append("clip regression cohort IDs are not reproducible")
    araus = clip_models[clip_models["dataset_id"].eq("ARAUS")]
    if araus.empty or not araus["n_eval"].eq(48).all():
        errors.append("ARAUS fixed results must retain n_eval=48")

    response = pd.read_csv(
        output_dir / "tables" / "table_06_isd_response_baselines.csv"
    )
    if not (
        len(response) == 10
        and response["n_train"].eq(1324).all()
        and response["n_eval"].eq(279).all()
        and response["n_clusters"].eq(184).all()
    ):
        errors.append("ISD response fixed table differs from the matched cohort")
    delta = pd.read_csv(
        output_dir / "tables" / "table_07_delta_annoyance_baselines.csv"
    )
    if not (
        len(delta) == 3
        and delta["n_train"].eq(2012).all()
        and delta["n_eval"].eq(437).all()
    ):
        errors.append("DeLTA annoyance fixed table has invalid sample counts")
    delta_source = pd.read_csv(
        output_dir / "tables" / "table_08_delta_source_baselines.csv"
    )
    if not (
        len(delta_source) == 8
        and delta_source["estimate"].between(0, 1).all()
        and (delta_source["ci_low"] <= delta_source["ci_high"]).all()
    ):
        errors.append("DeLTA source fixed table is incomplete or invalid")

    paired = pd.read_csv(output_dir / "tables" / "table_09_paired_comparisons.csv")
    multiseed = pd.read_csv(output_dir / "tables" / "table_10_multiseed_test_rmse.csv")
    sensitivity = pd.read_csv(
        output_dir / "tables" / "table_11_isd_coverage_sensitivity.csv"
    )
    calibration = pd.read_csv(output_dir / "tables" / "table_12_gpr_calibration.csv")
    if len(paired) != 34 or not paired["direction_normalized"].all():
        errors.append("paired comparison table must contain 34 normalised rows")
    if len(multiseed) != 5 or not multiseed["n_seeds"].eq(5).all():
        errors.append("multiseed fixed table must contain five test-RMSE summaries")
    if len(sensitivity) != 4 or not sensitivity["coverage_fraction"].between(0, 1).all():
        errors.append("coverage sensitivity fixed table must contain four test rows")
    if len(calibration) != 6 or not calibration["empirical_coverage"].between(0, 1).all():
        errors.append("GPR calibration fixed table must contain six valid rows")

    manuscript = (output_dir / "manuscript_evidence_insert.md").read_text(
        encoding="utf-8"
    )
    if "TODO" in manuscript:
        errors.append("generated manuscript evidence must not contain TODO placeholders")
    for required in [
        "27,850",
        "59,935",
        "47 checks",
        "17 experiments",
        "2,000 cluster",
        "31.7%",
        "57.3%",
        "audio_used=false",
    ]:
        if required not in manuscript:
            errors.append(f"manuscript evidence is missing fixed claim: {required}")
    audit = (output_dir / "draft_replacement_audit.md").read_text(encoding="utf-8")
    if (
        "Status: **integrated and removed**" not in audit
        or "Legacy findings: **19**" not in audit
    ):
        errors.append("legacy draft integration audit is incomplete")

    for frame in [clip_models, response, delta]:
        required_numeric = frame[
            ["rmse", "rmse_ci_low", "rmse_ci_high", "mae", "r2", "n_train", "n_eval"]
        ]
        if not np.isfinite(required_numeric.to_numpy(dtype=float)).all():
            errors.append("a regression fixed table contains invalid core metrics")
        missing_correlations = frame[
            frame[["pearson_r", "spearman_rho"]].isna().any(axis=1)
        ]
        if not missing_correlations["model_id"].str.contains("target_mean").all():
            errors.append("only constant Target Mean rows may omit correlations")
    for frame in [delta_source, paired, multiseed, sensitivity, calibration]:
        numeric = frame.select_dtypes(include="number")
        if numeric.empty or not np.isfinite(numeric.to_numpy(dtype=float)).all():
            errors.append("a manuscript-facing numeric table contains non-finite values")

    if errors:
        print(f"Paper 2 fixed-output validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(
        f"Paper 2 fixed-output validation passed: {config['freeze_id']}, "
        "12 tables, 6 figures, 23 manifested files"
    )


if __name__ == "__main__":
    main()

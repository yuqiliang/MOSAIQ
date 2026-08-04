"""Build the frozen MOSAIQ v0.1 candidate manifests and validation report.

Usage:
  uv run python scripts/build_benchmark_report.py
  uv run python scripts/build_benchmark_report.py --check-only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = REPO_ROOT / "benchmark" / "release.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "benchmark" / "validation"
DEFAULT_MANIFEST_DIR = REPO_ROOT / "benchmark" / "manifests"

VALIDATION_OUTPUTS = [
    "validation_summary.csv",
    "row_counts.csv",
    "task_eligibility.csv",
    "split_summary.csv",
    "exclusions.csv",
    "asset_coverage.csv",
    "feature_coverage.csv",
    "license_audit.csv",
    "source_checksums.sha256",
    "validation_report.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build MOSAIQ frozen manifests and technical-validation outputs"
    )
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument(
        "--generated-at",
        default=None,
        help="UTC ISO timestamp; defaults to SOURCE_DATE_EPOCH or the current time",
    )
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def write_csv(rows: Iterable[dict[str, Any]], path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows), columns=columns)
    frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_row(row: pd.Series) -> str:
    payload = json.dumps(
        {str(key): str(value) for key, value in row.items()},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generated_at(value: str | None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        dt = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalise_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value).strip().lower()


def filter_mask(frame: pd.DataFrame, filters: list[dict[str, Any]]) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for rule in filters:
        actual = frame[rule["column"]].map(normalise_scalar)
        operator = rule["operator"]
        if operator == "not_null":
            current = actual.ne("")
        elif operator in {"equals", "not_equals"}:
            current = actual.eq(normalise_scalar(rule.get("value")))
            if operator == "not_equals":
                current = ~current
        else:
            expected = {normalise_scalar(item) for item in rule.get("values", [])}
            current = actual.isin(expected)
            if operator == "not_in":
                current = ~current
        mask &= current
    return mask


def read_exclusions(path: Path) -> list[dict[str, Any]]:
    data = load_yaml(path)
    values = data.get("exclusions", [])
    if not isinstance(values, list):
        raise ValueError(f"{path}: exclusions must be a list")
    return [item for item in values if isinstance(item, dict)]


def assignment_path(dataset_id: str) -> Path:
    names = {
        "ISD": "isd_split.csv",
        "ARAUS": "araus_split.csv",
        "SATP": "satp_folds.csv",
        "DeLTA": "delta_split.csv",
    }
    return REPO_ROOT / "benchmark" / "splits" / names[dataset_id]


def add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    scope: str,
    observed: Any,
    expected: Any,
    details: str,
    dataset_id: str = "",
    task_id: str = "",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": status,
            "scope": scope,
            "dataset_id": dataset_id,
            "task_id": task_id,
            "observed": observed,
            "expected": expected,
            "details": details,
        }
    )


def run_command_check(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = " ".join(result.stdout.strip().split())
    return result.returncode == 0, output[:1000]


def summarise_frictionless_output(output: str) -> str:
    """Return stable validation evidence without runtime-dependent timings."""
    payload = json.loads(output)
    tasks = []
    for task in payload.get("tasks", []):
        stats = task.get("stats", {})
        tasks.append(
            {
                "name": task.get("name"),
                "valid": task.get("valid"),
                "errors": stats.get("errors"),
                "warnings": stats.get("warnings"),
                "rows": stats.get("rows"),
                "fields": stats.get("fields"),
                "sha256": stats.get("sha256"),
            }
        )
    return json.dumps(
        {"valid": payload.get("valid"), "tasks": tasks},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def run_frictionless_check(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    try:
        detail = summarise_frictionless_output(result.stdout)
    except (json.JSONDecodeError, TypeError, AttributeError):
        detail = " ".join(result.stdout.strip().split())[:1000]
    return result.returncode == 0, detail


def frictionless_executable() -> str | None:
    adjacent = Path(sys.executable).parent / "frictionless"
    if adjacent.exists():
        return str(adjacent)
    return shutil.which("frictionless")


def partitioned_clips(dataset_id: str, clips: pd.DataFrame) -> pd.DataFrame:
    assignment = load_csv(assignment_path(dataset_id))
    if dataset_id == "SATP":
        assignment = assignment.copy()
        assignment["partition"] = "fold_" + assignment["fold"].astype(str)
    else:
        assignment = assignment.rename(columns={"split": "partition"})
        assignment["fold"] = ""
    return clips.merge(
        assignment[["clip_id", "partition", "fold", "split_version", "exclusion_reason"]],
        on="clip_id",
        how="left",
        validate="one_to_one",
    )


def package_resource_counts(
    dataset: dict[str, Any], checks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    package_path = repo_path(dataset["package"])
    package = load_yaml(package_path)
    rows: list[dict[str, Any]] = []
    for resource in package.get("resources", []):
        path = package_path.parent / resource["path"]
        if not path.exists():
            add_check(
                checks,
                "resource_exists",
                "FAIL",
                "resource",
                "missing",
                "exists",
                relative(path),
                dataset["dataset_id"],
            )
            continue
        frame = load_csv(path)
        rows.append(
            {
                "dataset_id": dataset["dataset_id"],
                "track": dataset["track"],
                "resource": resource["name"],
                "path": relative(path),
                "n_rows": len(frame),
                "n_columns": len(frame.columns),
                "sha256": sha256_file(path),
            }
        )
    return rows


def validate_dataset_integrity(
    dataset: dict[str, Any],
    exclusions: list[dict[str, Any]],
    checks: list[dict[str, Any]],
) -> None:
    dataset_id = dataset["dataset_id"]
    clips = load_csv(repo_path(dataset["clips"]))
    responses = load_csv(repo_path(dataset["responses"]))

    duplicate_ids = int(clips["clip_id"].duplicated().sum())
    blank_ids = int(clips["clip_id"].str.strip().eq("").sum())
    add_check(
        checks,
        "clip_id_integrity",
        "PASS" if duplicate_ids == 0 and blank_ids == 0 else "FAIL",
        "dataset",
        f"duplicates={duplicate_ids}; blanks={blank_ids}",
        "duplicates=0; blanks=0",
        "Exact clip identifiers must be unique and non-empty.",
        dataset_id,
    )

    normalised = clips["clip_id"].str.strip()
    collision_mask = normalised.duplicated(keep=False) & clips["clip_id"].ne(normalised)
    collision_ids = set(clips.loc[collision_mask, "clip_id"])
    declared = {
        str(item["clip_id"])
        for item in exclusions
        if item.get("dataset_id") == dataset_id
    }
    unresolved = collision_ids.difference(declared)
    status = "FAIL" if unresolved else "WARN" if collision_ids else "PASS"
    add_check(
        checks,
        "whitespace_normalised_id_collision",
        status,
        "dataset",
        len(collision_ids),
        0,
        (
            "All collision rows are explicitly excluded pending source review."
            if collision_ids and not unresolved
            else "No whitespace-normalised identifier collisions."
            if not collision_ids
            else f"Undeclared collisions: {sorted(unresolved)}"
        ),
        dataset_id,
    )

    clip_ids = set(clips["clip_id"])
    orphan_responses = int((~responses["clip_id"].isin(clip_ids)).sum())
    duplicate_responses = (
        int(responses["response_id"].duplicated().sum())
        if "response_id" in responses.columns
        else 0
    )
    add_check(
        checks,
        "response_linkage",
        "PASS" if orphan_responses == 0 and duplicate_responses == 0 else "FAIL",
        "dataset",
        f"orphans={orphan_responses}; duplicate_response_ids={duplicate_responses}",
        "orphans=0; duplicate_response_ids=0",
        "Every response must link to exactly one source clip.",
        dataset_id,
    )

    observed = clips["clip_id"].map(responses.groupby("clip_id").size()).fillna(0).astype(int)
    expected = pd.to_numeric(clips["n_responses"], errors="coerce")
    mismatches = int(observed.ne(expected).sum())
    add_check(
        checks,
        "response_count_consistency",
        "PASS" if mismatches == 0 else "FAIL",
        "dataset",
        mismatches,
        0,
        "clips.n_responses must equal the number of linked response rows.",
        dataset_id,
    )

    unexpected_dataset_ids = sorted(set(clips["dataset_id"]).difference({dataset_id}))
    add_check(
        checks,
        "dataset_namespace",
        "PASS" if not unexpected_dataset_ids else "FAIL",
        "dataset",
        ";".join(unexpected_dataset_ids),
        dataset_id,
        "All clip rows must use the declared dataset namespace.",
        dataset_id,
    )


def build_task_manifests(
    registry: dict[str, Any],
    exclusions: list[dict[str, Any]],
    freeze: dict[str, Any],
    manifest_dir: Path,
    checks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[Path]]:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for old in manifest_dir.glob("*.csv"):
        old.unlink()

    eligibility_rows: list[dict[str, Any]] = []
    manifest_paths: list[Path] = []
    exclusion_map: dict[str, set[str]] = {}
    for item in exclusions:
        exclusion_map.setdefault(str(item["dataset_id"]), set()).add(str(item["clip_id"]))

    for entry in registry["tasks"]:
        config = load_yaml(repo_path(entry["config"]))
        task = config["task"]
        unit_of_analysis = task["unit_of_analysis"]
        id_column = config["input"]["id_column"]
        split_link_column = config["input"].get("split_link_column", "clip_id")
        target_columns = config["target"]["columns"]
        scale = config["target"].get("scale", {})
        for dataset in config["input"]["datasets"]:
            dataset_id = dataset["dataset_id"]
            source_path = repo_path(dataset["path"])
            source = load_csv(source_path)
            filters = dataset.get("filters", [])
            filtered = filter_mask(source, filters)
            declared_excluded = source[split_link_column].isin(
                exclusion_map.get(dataset_id, set())
            )

            numeric = source[target_columns].apply(pd.to_numeric, errors="coerce")
            missing_target = source[target_columns].apply(
                lambda column: column.str.strip().eq("")
            ).any(axis=1)
            invalid_target = numeric.isna().any(axis=1) & ~missing_target
            if "minimum" in scale:
                invalid_target |= numeric.lt(float(scale["minimum"])).any(axis=1)
            if "maximum" in scale:
                invalid_target |= numeric.gt(float(scale["maximum"])).any(axis=1)

            eligible = filtered & ~declared_excluded & ~missing_target & ~invalid_target
            assignments = load_csv(assignment_path(dataset_id))
            if dataset_id == "SATP":
                assignments = assignments.copy()
                assignments["partition"] = "fold_" + assignments["fold"].astype(str)
            else:
                assignments = assignments.rename(columns={"split": "partition"})
                assignments["fold"] = ""

            merged = source.loc[eligible].merge(
                assignments[
                    ["clip_id", "partition", "fold", "split_version", "exclusion_reason"]
                ],
                left_on=split_link_column,
                right_on="clip_id",
                how="left",
                validate="one_to_one" if unit_of_analysis == "clip" else "many_to_one",
            )
            split_excluded = merged["partition"].eq("excluded")
            unassigned = merged["partition"].eq("")
            frozen = merged.loc[~split_excluded & ~unassigned].copy()

            source_hashes = source.apply(sha256_row, axis=1)
            hash_by_id = dict(zip(source[id_column], source_hashes, strict=True))
            manifest_rows = []
            for _, row in frozen.iterrows():
                record_id = row[id_column]
                manifest_rows.append(
                    {
                        "freeze_id": freeze["id"],
                        "benchmark_id": freeze["benchmark_id"],
                        "benchmark_version": freeze["benchmark_version"],
                        "task_id": task["id"],
                        "task_version": task["version"],
                        "dataset_id": dataset_id,
                        "unit_of_analysis": unit_of_analysis,
                        "record_id": record_id,
                        "clip_id": row[split_link_column],
                        "partition": row["partition"],
                        "fold": row["fold"],
                        "split_version": row["split_version"],
                        "source_path": relative(source_path),
                        "source_row_sha256": hash_by_id[record_id],
                    }
                )

            manifest_path = manifest_dir / f"{task['id']}__{dataset_id.lower()}.csv"
            columns = [
                "freeze_id",
                "benchmark_id",
                "benchmark_version",
                "task_id",
                "task_version",
                "dataset_id",
                "unit_of_analysis",
                "record_id",
                "clip_id",
                "partition",
                "fold",
                "split_version",
                "source_path",
                "source_row_sha256",
            ]
            write_csv(manifest_rows, manifest_path, columns)
            manifest_paths.append(manifest_path)

            frozen_count = len(manifest_rows)
            eligibility_rows.append(
                {
                    "task_id": task["id"],
                    "task_version": task["version"],
                    "dataset_id": dataset_id,
                    "unit_of_analysis": unit_of_analysis,
                    "source_rows": len(source),
                    "after_filters": int(filtered.sum()),
                    "declared_exclusions": int((filtered & declared_excluded).sum()),
                    "missing_targets": int((filtered & ~declared_excluded & missing_target).sum()),
                    "invalid_targets": int((filtered & ~declared_excluded & invalid_target).sum()),
                    "split_excluded_after_task_filters": int(split_excluded.sum()),
                    "unassigned": int(unassigned.sum()),
                    "frozen_rows": frozen_count,
                    "manifest": relative(manifest_path),
                }
            )
            add_check(
                checks,
                "task_manifest_freeze",
                "PASS" if frozen_count > 0 and not split_excluded.any() and not unassigned.any() else "FAIL",
                "task_dataset",
                frozen_count,
                ">0 with no excluded or unassigned rows",
                relative(manifest_path),
                dataset_id,
                task["id"],
            )

    return eligibility_rows, manifest_paths


def build_split_summary(release: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in release["datasets"]:
        dataset_id = dataset["dataset_id"]
        assignment = load_csv(assignment_path(dataset_id))
        if dataset_id == "SATP":
            assignment["partition"] = "fold_" + assignment["fold"].astype(str)
        else:
            assignment = assignment.rename(columns={"split": "partition"})
        for partition, group in assignment.groupby("partition", sort=True):
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "track": dataset["track"],
                    "partition": partition,
                    "n_clips": len(group),
                    "fraction": round(len(group) / len(assignment), 8),
                    "split_version": group["split_version"].iloc[0],
                    "n_with_exclusion_reason": int(group["exclusion_reason"].str.strip().ne("").sum()),
                }
            )
    return rows


def build_exclusion_rows(
    release: dict[str, Any], declared: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    declared_map = {(str(row["dataset_id"]), str(row["clip_id"])): row for row in declared}
    rows: list[dict[str, Any]] = []
    for dataset in release["datasets"]:
        dataset_id = dataset["dataset_id"]
        assignment = load_csv(assignment_path(dataset_id))
        if dataset_id == "SATP":
            continue
        excluded = assignment[assignment["split"].eq("excluded")]
        for _, row in excluded.iterrows():
            item = declared_map.get((dataset_id, row["clip_id"]), {})
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "clip_id": row["clip_id"],
                    "split_version": row["split_version"],
                    "exclusion_reason": row["exclusion_reason"],
                    "declaration_status": item.get("status", "derived_from_split_build"),
                    "details": item.get(
                        "reason",
                        "Excluded deterministically by the split builder from source target/fold state.",
                    ),
                }
            )
    return rows


def build_asset_coverage(
    release: dict[str, Any], checks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in release["datasets"]:
        dataset_id = dataset["dataset_id"]
        clips = partitioned_clips(dataset_id, load_csv(repo_path(dataset["clips"])))
        for modality, policy in dataset.get("assets", {}).items():
            if "column" in policy:
                column = policy["column"]
                available = clips[column].str.strip().ne("")
                basis = column
            else:
                columns = policy["derivation_columns"]
                available = clips[columns].apply(lambda col: col.str.strip().ne("")).all(axis=1)
                basis = "+".join(columns)

            broken_local = 0
            if policy["reference_type"] == "repository_path" and "column" in policy:
                for value in clips.loc[available, policy["column"]]:
                    if not repo_path(value).exists():
                        broken_local += 1
            add_check(
                checks,
                f"{modality}_asset_reference_integrity",
                "PASS" if broken_local == 0 else "FAIL",
                "dataset",
                broken_local,
                0,
                (
                    "External references are audited for presence; local existence is not expected."
                    if policy["reference_type"] != "repository_path"
                    else "Repository-relative asset paths must resolve."
                ),
                dataset_id,
            )

            groups = [("all", clips)] + list(clips.groupby("partition", sort=True))
            for partition, group in groups:
                count = int(available.loc[group.index].sum())
                rows.append(
                    {
                        "dataset_id": dataset_id,
                        "track": dataset["track"],
                        "partition": partition,
                        "modality": modality,
                        "n_clips": len(group),
                        "n_with_reference": count,
                        "coverage": round(count / len(group), 8) if len(group) else 0,
                        "availability_basis": basis,
                        "reference_type": policy["reference_type"],
                        "materialisation": policy["materialisation"],
                        "broken_local_references": broken_local,
                    }
                )
    return rows


def real_feature_clip_ids(path: Path, feature_type: str) -> set[str]:
    if not path.exists():
        return set()
    features = load_csv(path)
    if "feature_type" not in features.columns:
        return set()
    selected = features[features["feature_type"].eq(feature_type)].copy()
    placeholder = pd.Series(False, index=selected.index)
    for column in ["notes", "feature_value_json", "provenance_json", "model_version"]:
        if column in selected.columns:
            placeholder |= selected[column].str.lower().str.contains("placeholder", na=False)
    return set(selected.loc[~placeholder, "clip_id"])


def build_feature_coverage(release: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in release["datasets"]:
        dataset_id = dataset["dataset_id"]
        clips = partitioned_clips(dataset_id, load_csv(repo_path(dataset["clips"])))
        for feature_set in release["feature_sets"]:
            if feature_set["source"] == "clip_columns":
                required = feature_set["required_columns"]
                if all(column in clips.columns for column in required):
                    available = clips[required].apply(
                        lambda column: column.str.strip().ne("")
                    ).all(axis=1)
                    note = "+".join(required)
                else:
                    available = pd.Series(False, index=clips.index)
                    note = "missing_columns=" + "+".join(
                        column for column in required if column not in clips.columns
                    )
            else:
                feature_path = repo_path(dataset.get("features", "__missing__"))
                ids = real_feature_clip_ids(feature_path, feature_set["feature_type"])
                available = clips["clip_id"].isin(ids)
                note = "placeholder FeatureRecords excluded"

            groups = [("all", clips)] + list(clips.groupby("partition", sort=True))
            for partition, group in groups:
                count = int(available.loc[group.index].sum())
                rows.append(
                    {
                        "dataset_id": dataset_id,
                        "track": dataset["track"],
                        "partition": partition,
                        "feature_set_id": feature_set["feature_set_id"],
                        "n_clips": len(group),
                        "n_available": count,
                        "coverage": round(count / len(group), 8) if len(group) else 0,
                        "source": feature_set["source"],
                        "notes": note,
                    }
                )
    return rows


def build_license_audit(
    release: dict[str, Any], checks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in release["datasets"]:
        dataset_id = dataset["dataset_id"]
        clips = load_csv(repo_path(dataset["clips"]))
        observed = sorted(value for value in set(clips["licence_spdx"]) if value.strip())
        declared = str(dataset["declared_license"])
        matches = observed == [declared]
        review_required = "review_required" in dataset["raw_asset_redistribution_status"]
        add_check(
            checks,
            "declared_license_consistency",
            "WARN" if review_required and matches else "PASS" if matches else "FAIL",
            "dataset",
            ";".join(observed),
            declared,
            (
                "Per-file raw-asset review remains required before public release."
                if review_required
                else "Observed clip licence values match the release declaration."
            ),
            dataset_id,
        )
        rows.append(
            {
                "dataset_id": dataset_id,
                "track": dataset["track"],
                "declared_license": declared,
                "observed_clip_licenses": ";".join(observed),
                "metadata_redistribution_status": dataset["metadata_redistribution_status"],
                "raw_asset_redistribution_status": dataset["raw_asset_redistribution_status"],
                "audit_status": "review_required" if review_required else "recorded",
                "notes": release["release_policy_note"],
            }
        )

        source_files = dataset.get("source_files")
        if source_files:
            source = load_csv(repo_path(source_files))
            valid_urls = source["download_url"].map(
                lambda value: urlparse(value).scheme == "https" and bool(urlparse(value).netloc)
            )
            add_check(
                checks,
                "source_download_url_shape",
                "PASS" if valid_urls.all() else "FAIL",
                "dataset",
                int(valid_urls.sum()),
                len(source),
                "Source manifest download URLs must be absolute HTTPS URLs.",
                dataset_id,
            )
    return rows


def source_input_paths(
    release_path: Path,
    release: dict[str, Any],
    registry: dict[str, Any],
) -> list[Path]:
    paths = [
        release_path,
        REPO_ROOT / "benchmark" / "tasks.yaml",
        REPO_ROOT / "benchmark" / "exclusions.yaml",
        REPO_ROOT / "benchmark" / "schemas" / "task.schema.yaml",
        REPO_ROOT / "benchmark" / "splits" / "split_checksums.sha256",
        REPO_ROOT / "scripts" / "build_benchmark_report.py",
        REPO_ROOT / "scripts" / "build_benchmark_splits.py",
        REPO_ROOT / "scripts" / "validate_benchmark_splits.py",
        REPO_ROOT / "scripts" / "validate_benchmark_tasks.py",
    ]
    for entry in registry["tasks"]:
        paths.append(repo_path(entry["config"]))
    for dataset in release["datasets"]:
        for field in ["package", "clips", "responses", "features", "source_files"]:
            if dataset.get(field):
                paths.append(repo_path(dataset[field]))
        package_path = repo_path(dataset["package"])
        package = load_yaml(package_path)
        for resource in package.get("resources", []):
            schema = resource.get("schema")
            if isinstance(schema, str):
                paths.append((package_path.parent / schema).resolve())
        paths.append(assignment_path(dataset["dataset_id"]))
    return sorted(set(paths), key=relative)


def write_checksum_file(paths: list[Path], base: Path, output: Path) -> None:
    lines = []
    for path in sorted(paths, key=lambda item: str(item)):
        try:
            name = path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            name = str(path.resolve())
        lines.append(f"{sha256_file(path)}  {name}\n")
    output.write_text("".join(lines), encoding="ascii")


def verify_checksum_file(path: Path, base: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing checksum file: {relative(path)}"]
    for line in path.read_text(encoding="ascii").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            errors.append(f"malformed checksum line: {line}")
            continue
        expected, name = parts
        candidate = base / name
        if not candidate.exists():
            errors.append(f"missing checksummed file: {name}")
        elif sha256_file(candidate) != expected:
            errors.append(f"checksum mismatch: {name}")
    return errors


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def build_report(
    release: dict[str, Any],
    timestamp: str,
    checks: list[dict[str, Any]],
    row_counts: list[dict[str, Any]],
    eligibility: list[dict[str, Any]],
    splits: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    features: list[dict[str, Any]],
    licenses: list[dict[str, Any]],
) -> str:
    failures = sum(row["status"] == "FAIL" for row in checks)
    warnings = sum(row["status"] == "WARN" for row in checks)
    passes = sum(row["status"] == "PASS" for row in checks)
    overall = "FAIL" if failures else "PASS WITH WARNINGS" if warnings else "PASS"
    freeze = release["freeze"]

    resource_table = markdown_table(
        ["Dataset", "Track", "Resource", "Rows", "Columns"],
        [
            [row["dataset_id"], row["track"], row["resource"], row["n_rows"], row["n_columns"]]
            for row in row_counts
        ],
    )
    task_table = markdown_table(
        ["Task", "Dataset", "Source", "Frozen", "Manifest"],
        [
            [
                row["task_id"],
                row["dataset_id"],
                row["source_rows"],
                row["frozen_rows"],
                f"`{row['manifest']}`",
            ]
            for row in eligibility
        ],
    )
    split_table = markdown_table(
        ["Dataset", "Partition", "Clips", "Fraction", "Version"],
        [
            [
                row["dataset_id"],
                row["partition"],
                row["n_clips"],
                f"{float(row['fraction']):.3f}",
                row["split_version"],
            ]
            for row in splits
        ],
    )
    asset_all = [row for row in assets if row["partition"] == "all"]
    asset_table = markdown_table(
        ["Dataset", "Modality", "References", "Coverage", "Materialisation"],
        [
            [
                row["dataset_id"],
                row["modality"],
                f"{row['n_with_reference']}/{row['n_clips']}",
                f"{100 * float(row['coverage']):.1f}%",
                row["materialisation"],
            ]
            for row in asset_all
        ],
    )
    feature_all = [row for row in features if row["partition"] == "all"]
    feature_table = markdown_table(
        ["Dataset", "Feature set", "Available", "Coverage"],
        [
            [
                row["dataset_id"],
                row["feature_set_id"],
                f"{row['n_available']}/{row['n_clips']}",
                f"{100 * float(row['coverage']):.1f}%",
            ]
            for row in feature_all
        ],
    )
    license_table = markdown_table(
        ["Dataset", "Declared", "Metadata", "Raw assets", "Audit"],
        [
            [
                row["dataset_id"],
                row["declared_license"],
                row["metadata_redistribution_status"],
                row["raw_asset_redistribution_status"],
                row["audit_status"],
            ]
            for row in licenses
        ],
    )
    exclusion_table = markdown_table(
        ["Dataset", "Reason", "Count"],
        [
            [dataset_id, reason, len(group)]
            for (dataset_id, reason), group in pd.DataFrame(exclusions).groupby(
                ["dataset_id", "exclusion_reason"], sort=True
            )
        ],
    )

    warning_lines = [
        f"- `{row['check_id']}` ({row['dataset_id'] or row['scope']}): {row['details']}"
        for row in checks
        if row["status"] == "WARN"
    ] or ["- None."]
    failure_lines = [
        f"- `{row['check_id']}` ({row['dataset_id'] or row['scope']}): {row['details']}"
        for row in checks
        if row["status"] == "FAIL"
    ] or ["- None."]

    return f"""# MOSAIQ Benchmark Technical Validation Report

Generated: `{timestamp}`<br>
Freeze ID: `{freeze['id']}`<br>
Benchmark version: `{freeze['benchmark_version']}`<br>
Split version: `{freeze['split_version']}`<br>
Overall status: **{overall}**

This report is generated by `scripts/build_benchmark_report.py`. Counts and
release statements should be updated by rerunning the script, not by editing
this file manually.

## Validation Summary

- PASS: {passes}
- WARN: {warnings}
- FAIL: {failures}
- Core tracks: {', '.join(release['tracks']['core'])}
- Extension tracks: {', '.join(release['tracks']['extension'])}

## Frozen Resources

{resource_table}

## Task Eligibility and Manifests

{task_table}

Every manifest records the task and split versions plus a SHA-256 digest of
the complete source record row. `benchmark/manifests/manifest_checksums.sha256`
locks the generated manifest files.

## Split Coverage

{split_table}

Split validation checks exact source coverage and declared leakage constraints.
ISD locations remain within one partition; ARAUS preserves source folds; SATP
uses deterministic five-fold evaluation; DeLTA uses the shared stratified split.

## Exclusions

{exclusion_table}

The full record-level audit is in `benchmark/validation/exclusions.csv`.

## Asset Availability

{asset_table}

An asset reference is not the same as a file stored in this repository. ISD
audio/video fields are source identifiers; ARAUS augmented audio is
reconstructible from soundscape, masker, and SMR components; SATP and DeLTA
audio paths identify members of source archives that are not ingested locally.

## Feature Coverage

{feature_table}

Placeholder FeatureRecords are excluded from coverage. The current candidate
therefore has no released CLIP or CitySeg features. ARAUS has complete shared
psychoacoustic columns; ISD has partial coverage; SATP and DeLTA do not contain
the shared psychoacoustic feature set.

## Licence and Redistribution Audit

{license_table}

These statuses record current release planning and are not legal advice.
Per-file source licences remain authoritative, especially for ARAUS assets.

## Warnings

{chr(10).join(warning_lines)}

## Failures

{chr(10).join(failure_lines)}

## Reproduce

```bash
uv run python scripts/build_benchmark_report.py
uv run python scripts/build_benchmark_report.py --check-only
uv run python scripts/validate_benchmark_tasks.py
uv run python scripts/validate_benchmark_splits.py
```

The candidate can advance to baseline execution only when this report has no
FAIL checks. WARN items must remain visible in Paper 2 Technical Validation and
Usage Notes unless resolved before the final MOSAIQ-v1.0 freeze.
"""


def generate(args: argparse.Namespace) -> None:
    release_path = args.release.resolve()
    output_dir = args.output_dir.resolve()
    manifest_dir = args.manifest_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    release = load_yaml(release_path)
    registry = load_yaml(REPO_ROOT / "benchmark" / "tasks.yaml")
    exclusions = read_exclusions(REPO_ROOT / "benchmark" / "exclusions.yaml")
    freeze = release["freeze"]
    timestamp = generated_at(args.generated_at or freeze.get("generated_at"))
    checks: list[dict[str, Any]] = []

    for script in ["validate_benchmark_tasks.py", "validate_benchmark_splits.py"]:
        ok, detail = run_command_check([sys.executable, str(REPO_ROOT / "scripts" / script)])
        add_check(
            checks,
            script.removesuffix(".py"),
            "PASS" if ok else "FAIL",
            "benchmark",
            "exit=0" if ok else "exit!=0",
            "exit=0",
            detail,
        )

    frictionless = frictionless_executable()
    for dataset in release["datasets"]:
        dataset_id = dataset["dataset_id"]
        if frictionless:
            ok, detail = run_frictionless_check(
                [frictionless, "validate", str(repo_path(dataset["package"])), "--trusted", "--json"]
            )
        else:
            ok, detail = False, "frictionless executable not found"
        add_check(
            checks,
            "frictionless_package_validation",
            "PASS" if ok else "FAIL",
            "dataset",
            "valid" if ok else "invalid",
            "valid",
            detail,
            dataset_id,
        )

    row_counts: list[dict[str, Any]] = []
    for dataset in release["datasets"]:
        row_counts.extend(package_resource_counts(dataset, checks))
        validate_dataset_integrity(dataset, exclusions, checks)

    eligibility, manifest_paths = build_task_manifests(
        registry, exclusions, freeze, manifest_dir, checks
    )
    split_rows = build_split_summary(release)
    exclusion_rows = build_exclusion_rows(release, exclusions)
    asset_rows = build_asset_coverage(release, checks)
    feature_rows = build_feature_coverage(release)
    license_rows = build_license_audit(release, checks)

    write_csv(
        checks,
        output_dir / "validation_summary.csv",
        ["check_id", "status", "scope", "dataset_id", "task_id", "observed", "expected", "details"],
    )
    write_csv(
        row_counts,
        output_dir / "row_counts.csv",
        ["dataset_id", "track", "resource", "path", "n_rows", "n_columns", "sha256"],
    )
    write_csv(
        eligibility,
        output_dir / "task_eligibility.csv",
        [
            "task_id",
            "task_version",
            "dataset_id",
            "unit_of_analysis",
            "source_rows",
            "after_filters",
            "declared_exclusions",
            "missing_targets",
            "invalid_targets",
            "split_excluded_after_task_filters",
            "unassigned",
            "frozen_rows",
            "manifest",
        ],
    )
    write_csv(
        split_rows,
        output_dir / "split_summary.csv",
        ["dataset_id", "track", "partition", "n_clips", "fraction", "split_version", "n_with_exclusion_reason"],
    )
    write_csv(
        exclusion_rows,
        output_dir / "exclusions.csv",
        ["dataset_id", "clip_id", "split_version", "exclusion_reason", "declaration_status", "details"],
    )
    write_csv(
        asset_rows,
        output_dir / "asset_coverage.csv",
        [
            "dataset_id",
            "track",
            "partition",
            "modality",
            "n_clips",
            "n_with_reference",
            "coverage",
            "availability_basis",
            "reference_type",
            "materialisation",
            "broken_local_references",
        ],
    )
    write_csv(
        feature_rows,
        output_dir / "feature_coverage.csv",
        ["dataset_id", "track", "partition", "feature_set_id", "n_clips", "n_available", "coverage", "source", "notes"],
    )
    write_csv(
        license_rows,
        output_dir / "license_audit.csv",
        [
            "dataset_id",
            "track",
            "declared_license",
            "observed_clip_licenses",
            "metadata_redistribution_status",
            "raw_asset_redistribution_status",
            "audit_status",
            "notes",
        ],
    )

    write_checksum_file(
        source_input_paths(release_path, release, registry),
        REPO_ROOT,
        output_dir / "source_checksums.sha256",
    )
    write_checksum_file(
        manifest_paths,
        manifest_dir,
        manifest_dir / "manifest_checksums.sha256",
    )
    report = build_report(
        release,
        timestamp,
        checks,
        row_counts,
        eligibility,
        split_rows,
        exclusion_rows,
        asset_rows,
        feature_rows,
        license_rows,
    )
    (output_dir / "validation_report.md").write_text(report, encoding="utf-8")
    write_checksum_file(
        [output_dir / name for name in VALIDATION_OUTPUTS],
        output_dir,
        output_dir / "validation_checksums.sha256",
    )

    failures = [row for row in checks if row["status"] == "FAIL"]
    warnings = [row for row in checks if row["status"] == "WARN"]
    print(
        f"Built validation freeze {freeze['id']}: "
        f"{len(manifest_paths)} manifests, {len(checks)} checks, "
        f"{len(warnings)} warning(s), {len(failures)} failure(s)"
    )
    if failures:
        for row in failures:
            print(f"- {row['check_id']} [{row['dataset_id'] or row['scope']}]: {row['details']}")
        raise SystemExit(1)


def check_only(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    manifest_dir = args.manifest_dir.resolve()
    errors = []
    errors.extend(verify_checksum_file(output_dir / "source_checksums.sha256", REPO_ROOT))
    errors.extend(verify_checksum_file(output_dir / "validation_checksums.sha256", output_dir))
    errors.extend(verify_checksum_file(manifest_dir / "manifest_checksums.sha256", manifest_dir))

    summary_path = output_dir / "validation_summary.csv"
    if summary_path.exists():
        summary = load_csv(summary_path)
        failed = summary[summary["status"].eq("FAIL")]
        if not failed.empty:
            errors.append(f"validation summary contains {len(failed)} FAIL row(s)")
    else:
        errors.append("missing validation_summary.csv")

    if errors:
        print(f"Benchmark validation freeze check failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Benchmark validation freeze check passed")


def main() -> None:
    args = parse_args()
    if args.check_only:
        check_only(args)
    else:
        generate(args)


if __name__ == "__main__":
    main()

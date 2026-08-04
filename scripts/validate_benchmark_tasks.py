"""Validate the MOSAIQ benchmark registry and task configurations.

Usage:
  uv run python scripts/validate_benchmark_tasks.py
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FILTER_OPERATORS = {"equals", "not_equals", "in", "not_in", "not_null"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MOSAIQ benchmark task definitions against source tables"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("benchmark/tasks.yaml"),
        help="Task registry path relative to the repository root",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the document root")
    return value


def resolve_repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def normalise_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value).strip().lower()


def row_matches_filter(row: dict[str, str], rule: dict[str, Any]) -> bool:
    column = rule["column"]
    operator = rule["operator"]
    actual = normalise_scalar(row.get(column))

    if operator == "not_null":
        return actual != ""

    if operator in {"equals", "not_equals"}:
        expected = normalise_scalar(rule.get("value"))
        matches = actual == expected
        return matches if operator == "equals" else not matches

    expected_values = {normalise_scalar(item) for item in rule.get("values", [])}
    matches = actual in expected_values
    return matches if operator == "in" else not matches


def validate_filter_shape(
    task_id: str, dataset_id: str, rule: dict[str, Any], errors: list[str]
) -> None:
    operator = rule.get("operator")
    if operator not in ALLOWED_FILTER_OPERATORS:
        return
    if operator in {"equals", "not_equals"} and "value" not in rule:
        errors.append(
            f"{task_id}/{dataset_id}: filter operator '{operator}' requires 'value'"
        )
    if operator in {"in", "not_in"} and not rule.get("values"):
        errors.append(
            f"{task_id}/{dataset_id}: filter operator '{operator}' requires non-empty 'values'"
        )


def is_missing(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def validate_target_value(
    raw_value: str,
    minimum: float | None,
    maximum: float | None,
) -> bool:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(value):
        return False
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    return True


def validate_dataset(
    task: dict[str, Any],
    dataset: dict[str, Any],
    errors: list[str],
) -> tuple[int, int]:
    task_id = task["task"]["id"]
    dataset_id = dataset["dataset_id"]
    path = resolve_repo_path(dataset["path"])
    if not path.exists():
        errors.append(f"{task_id}/{dataset_id}: data file does not exist: {path}")
        return 0, 0

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)

    exclusion_ids: set[str] = set()
    exclusions_file = dataset.get("exclusions_file")
    if exclusions_file:
        exclusions_path = resolve_repo_path(exclusions_file)
        if not exclusions_path.exists():
            errors.append(
                f"{task_id}/{dataset_id}: exclusions file does not exist: {exclusions_path}"
            )
        else:
            exclusion_data = load_yaml(exclusions_path)
            exclusions = exclusion_data.get("exclusions", [])
            if exclusion_data.get("schema_version") != "0.1":
                errors.append(
                    f"{task_id}/{dataset_id}: unsupported exclusions schema version"
                )
            if not isinstance(exclusions, list):
                errors.append(
                    f"{task_id}/{dataset_id}: exclusions must be a list in {exclusions_file}"
                )
            else:
                required_exclusion_fields = {"dataset_id", "clip_id", "status", "reason"}
                for index, item in enumerate(exclusions, start=1):
                    if not isinstance(item, dict):
                        errors.append(
                            f"{task_id}/{dataset_id}: exclusion {index} must be a mapping"
                        )
                        continue
                    missing_fields = sorted(required_exclusion_fields.difference(item))
                    if missing_fields:
                        errors.append(
                            f"{task_id}/{dataset_id}: exclusion {index} missing "
                            + ", ".join(missing_fields)
                        )
                exclusion_ids = {
                    str(item.get("clip_id", ""))
                    for item in exclusions
                    if isinstance(item, dict) and item.get("dataset_id") == dataset_id
                }

    id_column = task["input"]["id_column"]
    split_link_column = task["input"].get("split_link_column", "clip_id")
    target_columns = task["target"]["columns"]
    filters = dataset.get("filters", [])
    split_rules = [
        rule
        for rule in task["split_protocol"]["rules"]
        if rule["dataset_id"] == dataset_id
    ]
    referenced_columns = {id_column, split_link_column, *target_columns}
    if task["input"]["record_type"] == "clips":
        referenced_columns.add("dataset_id")
    referenced_columns.update(rule["column"] for rule in filters)
    for split_rule in split_rules:
        referenced_columns.update(split_rule.get("group_columns", []))
        referenced_columns.update(split_rule.get("stratify_columns", []))

    missing_columns = sorted(referenced_columns.difference(headers))
    if missing_columns:
        errors.append(
            f"{task_id}/{dataset_id}: missing source columns: {', '.join(missing_columns)}"
        )
        return len(rows), 0

    for rule in filters:
        validate_filter_shape(task_id, dataset_id, rule, errors)

    raw_ids = [row[id_column] for row in rows]
    split_link_ids = [row[split_link_column] for row in rows]
    unknown_exclusions = sorted(exclusion_ids.difference(split_link_ids))
    if unknown_exclusions:
        errors.append(
            f"{task_id}/{dataset_id}: exclusions do not match source rows: "
            + ", ".join(repr(value) for value in unknown_exclusions)
        )

    blank_ids = sum(not value.strip() for value in raw_ids)
    duplicate_count = len(raw_ids) - len(set(raw_ids))
    if blank_ids:
        errors.append(f"{task_id}/{dataset_id}: {blank_ids} blank {id_column} values")
    if duplicate_count:
        errors.append(
            f"{task_id}/{dataset_id}: {duplicate_count} duplicate {id_column} values"
        )

    if "dataset_id" in headers:
        unexpected_dataset_ids = sorted(
            {
                row["dataset_id"].strip()
                for row in rows
                if row["dataset_id"].strip() != dataset_id
            }
        )
        if unexpected_dataset_ids:
            errors.append(
                f"{task_id}/{dataset_id}: unexpected dataset_id values: "
                + ", ".join(unexpected_dataset_ids)
            )

    scale = task["target"].get("scale", {})
    minimum = scale.get("minimum")
    maximum = scale.get("maximum")
    eligible_rows = []
    invalid_target_rows = 0
    for row in rows:
        if row[split_link_column] in exclusion_ids:
            continue
        if not all(row_matches_filter(row, rule) for rule in filters):
            continue
        if any(is_missing(row[column]) for column in target_columns):
            if task["target"]["missing_value_policy"] == "error":
                invalid_target_rows += 1
            continue
        if not all(
            validate_target_value(row[column], minimum, maximum) for column in target_columns
        ):
            invalid_target_rows += 1
            continue
        eligible_rows.append(row)

    eligible_ids = [row[id_column] for row in eligible_rows]
    noncanonical_ids = [value for value in eligible_ids if value != value.strip()]
    normalised_duplicate_count = len(eligible_ids) - len(
        {value.strip() for value in eligible_ids}
    )
    if noncanonical_ids:
        errors.append(
            f"{task_id}/{dataset_id}: {len(noncanonical_ids)} eligible ids contain surrounding whitespace"
        )
    if normalised_duplicate_count:
        errors.append(
            f"{task_id}/{dataset_id}: {normalised_duplicate_count} eligible ids collide after whitespace normalisation"
        )

    if invalid_target_rows:
        errors.append(
            f"{task_id}/{dataset_id}: {invalid_target_rows} rows have invalid or out-of-range targets"
        )
    if not eligible_rows:
        errors.append(f"{task_id}/{dataset_id}: no eligible rows remain after filtering")

    assignment_file = task["split_protocol"]["assignment_files"][dataset_id]
    with resolve_repo_path(assignment_file).open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        assignment_rows = list(csv.DictReader(handle))
    assignment_clip_ids = {row["clip_id"] for row in assignment_rows}
    unassigned_links = sorted(
        {row[split_link_column] for row in eligible_rows}.difference(assignment_clip_ids)
    )
    if unassigned_links:
        errors.append(
            f"{task_id}/{dataset_id}: {len(unassigned_links)} eligible records have no split assignment"
        )

    return len(rows), len(eligible_rows)


def validate_task(
    registry_entry: dict[str, Any],
    schema: dict[str, Any],
    errors: list[str],
) -> list[str]:
    config_path = resolve_repo_path(registry_entry["config"])
    if not config_path.exists():
        errors.append(f"{registry_entry['id']}: config does not exist: {config_path}")
        return []

    config = load_yaml(config_path)
    schema_errors = sorted(
        Draft202012Validator(schema).iter_errors(config), key=lambda item: list(item.path)
    )
    for error in schema_errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{config_path.relative_to(REPO_ROOT)}:{location}: {error.message}")
    if schema_errors:
        return []

    task_id = config["task"]["id"]
    if task_id != registry_entry["id"]:
        errors.append(
            f"{registry_entry['id']}: config task id is '{task_id}'"
        )
    if config["task"]["status"] != registry_entry["status"]:
        errors.append(
            f"{task_id}: registry status and config status do not match"
        )

    unit = config["task"]["unit_of_analysis"]
    record_type = config["input"]["record_type"]
    id_column = config["input"]["id_column"]
    if unit == "clip" and (record_type != "clips" or id_column != "clip_id"):
        errors.append(f"{task_id}: clip tasks must use clips records keyed by clip_id")
    if unit == "response" and (
        record_type != "responses"
        or id_column != "response_id"
        or config["input"].get("split_link_column") != "clip_id"
    ):
        errors.append(
            f"{task_id}: response tasks must use responses keyed by response_id and split_link_column clip_id"
        )

    config_datasets = [item["dataset_id"] for item in config["input"]["datasets"]]
    if config_datasets != registry_entry["datasets"]:
        errors.append(
            f"{task_id}: registry datasets {registry_entry['datasets']} do not match "
            f"config datasets {config_datasets}"
        )
    if len(config_datasets) != len(set(config_datasets)):
        errors.append(f"{task_id}: duplicate dataset entries in task config")

    split_dataset_ids = [rule["dataset_id"] for rule in config["split_protocol"]["rules"]]
    if sorted(split_dataset_ids) != sorted(config_datasets):
        errors.append(
            f"{task_id}: split rules must contain exactly one rule for each input dataset"
        )
    assignment_ids = sorted(config["split_protocol"]["assignment_files"])
    if assignment_ids != sorted(config_datasets):
        errors.append(
            f"{task_id}: split assignment files must cover every input dataset"
        )

    task_status = config["task"]["status"]
    split_status = config["split_protocol"]["status"]
    if task_status == "ready" and split_status != "released":
        errors.append(f"{task_id}: a ready task must have released splits")
    if split_status == "released":
        expected_split_version = config["split_protocol"]["version"]
        for dataset_id, assignment_path in config["split_protocol"][
            "assignment_files"
        ].items():
            resolved_assignment = resolve_repo_path(assignment_path)
            if not resolved_assignment.exists():
                errors.append(
                    f"{task_id}/{dataset_id}: released split file is missing: {assignment_path}"
                )
                continue
            with resolved_assignment.open("r", encoding="utf-8", newline="") as handle:
                assignment_rows = list(csv.DictReader(handle))
            required_columns = {"clip_id", "dataset_id", "split_version"}
            required_columns.add("fold" if dataset_id == "SATP" else "split")
            actual_columns = set(assignment_rows[0]) if assignment_rows else set()
            missing_columns = sorted(required_columns.difference(actual_columns))
            if missing_columns:
                errors.append(
                    f"{task_id}/{dataset_id}: split file missing columns: "
                    + ", ".join(missing_columns)
                )
                continue
            assignment_ids = [row["clip_id"] for row in assignment_rows]
            if len(assignment_ids) != len(set(assignment_ids)):
                errors.append(f"{task_id}/{dataset_id}: duplicate clip ids in split file")
            if {row["dataset_id"] for row in assignment_rows} != {dataset_id}:
                errors.append(f"{task_id}/{dataset_id}: invalid dataset ids in split file")
            if {row["split_version"] for row in assignment_rows} != {
                expected_split_version
            }:
                errors.append(f"{task_id}/{dataset_id}: split version mismatch")

    metric_names = [metric["name"] for metric in config["evaluation"]["metrics"]]
    if config["evaluation"]["primary_metric"] not in metric_names:
        errors.append(f"{task_id}: primary metric is not listed under evaluation.metrics")
    if len(metric_names) != len(set(metric_names)):
        errors.append(f"{task_id}: duplicate evaluation metric names")

    summaries = []
    for dataset in config["input"]["datasets"]:
        total, eligible = validate_dataset(config, dataset, errors)
        summaries.append(f"{dataset['dataset_id']} {eligible}/{total}")
    return summaries


def main() -> None:
    args = parse_args()
    registry_path = resolve_repo_path(args.registry)
    schema_path = REPO_ROOT / "benchmark" / "schemas" / "task.schema.yaml"
    registry = load_yaml(registry_path)
    schema = load_yaml(schema_path)
    errors: list[str] = []

    if registry.get("schema_version") != "0.1":
        errors.append("benchmark/tasks.yaml: unsupported or missing schema_version")
    entries = registry.get("tasks")
    if not isinstance(entries, list) or not entries:
        errors.append("benchmark/tasks.yaml: tasks must be a non-empty list")
        entries = []

    task_ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    if len(task_ids) != len(entries) or any(not task_id for task_id in task_ids):
        errors.append("benchmark/tasks.yaml: every task entry must have an id")
    if len(task_ids) != len(set(task_ids)):
        errors.append("benchmark/tasks.yaml: task ids must be unique")

    summaries: list[tuple[str, list[str]]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        required = {"id", "config", "status", "datasets", "summary"}
        missing = sorted(required.difference(entry))
        if missing:
            errors.append(
                f"benchmark/tasks.yaml: task entry missing: {', '.join(missing)}"
            )
            continue
        summaries.append((entry["id"], validate_task(entry, schema, errors)))

    if errors:
        print(f"Benchmark task validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(
        f"Benchmark task validation passed: {registry_path.relative_to(REPO_ROOT)} "
        f"({len(entries)} tasks)"
    )
    for task_id, dataset_summaries in summaries:
        print(f"- {task_id}: {', '.join(dataset_summaries)} eligible rows")


if __name__ == "__main__":
    main()

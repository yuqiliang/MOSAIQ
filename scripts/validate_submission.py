#!/usr/bin/env python3
"""Validate a tidy MOSAIQ prediction submission against frozen manifests."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = [
    "benchmark_version",
    "split_version",
    "task_id",
    "task_version",
    "dataset_id",
    "partition",
    "fold",
    "record_id",
    "target",
    "prediction",
    "uncertainty",
    "model_id",
    "run_id",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Require every frozen evaluation record/target exactly once.",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow a header-only file, for validating the shipped template.",
    )
    return parser.parse_args()


def load_task(task_id: str) -> dict:
    matches = []
    for path in (ROOT / "benchmark" / "configs").glob("task_*.yaml"):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        if config["task"]["id"] == task_id:
            matches.append(config)
    if len(matches) != 1:
        raise ValueError(f"expected one task config for {task_id!r}, found {len(matches)}")
    return matches[0]


def parse_number(value: str, field: str, row_number: int, optional: bool = False) -> float | None:
    if optional and value.strip() == "":
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {field} is not numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"row {row_number}: {field} must be finite")
    return number


def manifest_rows(task_id: str, dataset_id: str) -> list[dict[str, str]]:
    path = ROOT / "benchmark" / "manifests" / f"{task_id}__{dataset_id.lower()}.csv"
    if not path.exists():
        raise ValueError(f"no frozen manifest for task={task_id}, dataset={dataset_id}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def target_columns(config: dict) -> list[str]:
    target = config["target"]
    if "columns" in target:
        return list(target["columns"])
    if "column" in target:
        return [target["column"]]
    if "label_columns" in target:
        return list(target["label_columns"])
    raise ValueError(f"task {config['task']['id']} has no recognised target columns")


def main() -> int:
    args = parse_args()
    with args.submission.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            raise SystemExit(
                "submission columns must exactly match:\n" + ",".join(REQUIRED_COLUMNS)
            )
        rows = list(reader)

    if not rows:
        if args.allow_empty:
            print("PASS: header-only MOSAIQ submission template is valid")
            return 0
        raise SystemExit("submission contains no prediction rows")

    errors: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}

    for row_number, row in enumerate(rows, start=2):
        for field in REQUIRED_COLUMNS:
            if field not in {"partition", "fold", "uncertainty"} and not row[field].strip():
                errors.append(f"row {row_number}: {field} is required")
        try:
            parse_number(row["prediction"], "prediction", row_number)
            uncertainty = parse_number(
                row["uncertainty"], "uncertainty", row_number, optional=True
            )
            if uncertainty is not None and uncertainty < 0:
                errors.append(f"row {row_number}: uncertainty must be non-negative")
        except ValueError as exc:
            errors.append(str(exc))

        key = (row["task_id"], row["dataset_id"], row["record_id"], row["target"])
        if key in seen:
            errors.append(f"row {row_number}: duplicate prediction key {key}")
        seen.add(key)
        groups.setdefault((row["task_id"], row["dataset_id"]), []).append(row)

    for (task_id, dataset_id), group in groups.items():
        try:
            config = load_task(task_id)
            manifest = manifest_rows(task_id, dataset_id)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        allowed_targets = set(target_columns(config))
        by_id = {row["record_id"]: row for row in manifest}
        benchmark_versions = {row["benchmark_version"] for row in manifest}
        split_versions = {row["split_version"] for row in manifest}
        task_versions = {row["task_version"] for row in manifest}

        for row in group:
            record = by_id.get(row["record_id"])
            if record is None:
                errors.append(
                    f"{task_id}/{dataset_id}: unknown record_id {row['record_id']}"
                )
                continue
            if row["target"] not in allowed_targets:
                errors.append(
                    f"{task_id}/{dataset_id}: unknown target {row['target']}"
                )
            if row["benchmark_version"] not in benchmark_versions:
                errors.append(
                    f"{task_id}/{dataset_id}: benchmark_version mismatch"
                )
            if row["split_version"] not in split_versions:
                errors.append(f"{task_id}/{dataset_id}: split_version mismatch")
            if row["task_version"] not in task_versions:
                errors.append(f"{task_id}/{dataset_id}: task_version mismatch")
            if row["partition"] != record["partition"]:
                errors.append(
                    f"{task_id}/{dataset_id}/{row['record_id']}: partition mismatch"
                )
            if row["fold"] != record["fold"]:
                errors.append(
                    f"{task_id}/{dataset_id}/{row['record_id']}: fold mismatch"
                )

        if args.require_complete:
            fixed_test = [row for row in manifest if row["partition"] == "test"]
            evaluation = fixed_test or [row for row in manifest if row["fold"] != ""]
            expected = {
                (row["record_id"], target)
                for row in evaluation
                for target in allowed_targets
            }
            observed = {(row["record_id"], row["target"]) for row in group}
            missing = expected - observed
            extra = observed - expected
            if missing:
                errors.append(
                    f"{task_id}/{dataset_id}: missing {len(missing)} evaluation predictions"
                )
            if extra:
                errors.append(
                    f"{task_id}/{dataset_id}: {len(extra)} non-evaluation predictions present"
                )

    if errors:
        print("FAIL: MOSAIQ submission validation")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS: {len(rows)} prediction rows across {len(groups)} task/dataset groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

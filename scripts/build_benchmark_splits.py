"""Build deterministic MOSAIQ v0.1 benchmark split assignments.

Usage:
  uv run python scripts/build_benchmark_splits.py
  uv run python scripts/build_benchmark_splits.py --check-only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml
from iterstrat.ml_stratifiers import (
    MultilabelStratifiedKFold,
    MultilabelStratifiedShuffleSplit,
)
from sklearn.model_selection import StratifiedGroupKFold


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "benchmark" / "splits"
DEFAULT_SPLIT_VERSION = "0.1.0"
DEFAULT_SEED = 2026
CHECKSUM_FILENAMES = [
    "isd_split.csv",
    "araus_split.csv",
    "satp_folds.csv",
    "delta_split.csv",
    "split_summary.csv",
]

ISO_COLUMNS = ["mean_ISOPleasant", "mean_ISOEventful"]
PAQ_COLUMNS = [
    "mean_PAQ1_pleasant",
    "mean_PAQ2_vibrant",
    "mean_PAQ3_eventful",
    "mean_PAQ4_chaotic",
    "mean_PAQ5_annoying",
    "mean_PAQ6_monotonous",
    "mean_PAQ7_uneventful",
    "mean_PAQ8_calm",
]
DELTA_SOURCE_COLUMNS = [
    "source_aircraft",
    "source_bells",
    "source_bird_tweet",
    "source_bus",
    "source_car",
    "source_children",
    "source_construction",
    "source_dog_bark",
    "source_footsteps",
    "source_general_traffic",
    "source_horn",
    "source_laughter",
    "source_motorcycle",
    "source_music",
    "source_non_identifiable",
    "source_other",
    "source_rail",
    "source_rustling_leaves",
    "source_screeching_brakes",
    "source_shouting",
    "source_siren",
    "source_speech",
    "source_ventilation",
    "source_water",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MOSAIQ benchmark split files")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--split-version", default=DEFAULT_SPLIT_VERSION)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate existing split files without regenerating them",
    )
    return parser.parse_args()


def load_clips(dataset_id: str) -> pd.DataFrame:
    path = REPO_ROOT / "datasets" / dataset_id / "data" / "clips.csv"
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    return frame[list(columns)].apply(pd.to_numeric, errors="coerce")


def quantile_codes(series: pd.Series, q: int) -> pd.Series:
    return pd.qcut(series, q=q, labels=False, duplicates="drop").astype(int)


def load_exclusion_ids(dataset_id: str) -> set[str]:
    path = REPO_ROOT / "benchmark" / "exclusions.yaml"
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return {
        str(item["clip_id"])
        for item in data.get("exclusions", [])
        if item.get("dataset_id") == dataset_id
    }


def assignment_frame(
    clips: pd.DataFrame,
    assignments: pd.Series,
    split_version: str,
    exclusion_reasons: pd.Series | None = None,
) -> pd.DataFrame:
    result = clips[["clip_id", "dataset_id"]].copy()
    result["split"] = assignments
    result["split_version"] = split_version
    if exclusion_reasons is None:
        result["exclusion_reason"] = ""
    else:
        result["exclusion_reason"] = exclusion_reasons
    return result


def choose_isd_fold_mapping(
    folds: pd.Series,
    targets: pd.DataFrame,
    strata: pd.Series,
) -> dict[int, str]:
    """Select dev/test folds with the smallest deterministic distribution drift."""
    global_mean = targets[ISO_COLUMNS].mean()
    global_std = targets[ISO_COLUMNS].std().replace(0, 1)
    global_hist = strata.value_counts(normalize=True)
    target_fractions = {"train": 0.60, "dev": 0.20, "test": 0.20}
    best: tuple[float, int, int] | None = None

    for dev_fold in range(5):
        for test_fold in range(5):
            if dev_fold == test_fold:
                continue
            mapping = {
                fold_id: (
                    "dev" if fold_id == dev_fold else "test" if fold_id == test_fold else "train"
                )
                for fold_id in range(5)
            }
            partition = folds.map(mapping)
            score = 0.0
            for split_name in ["train", "dev", "test"]:
                index = partition[partition == split_name].index
                split_targets = targets.loc[index, ISO_COLUMNS]
                mean_drift = ((split_targets.mean() - global_mean).abs() / global_std).sum()
                split_hist = strata.loc[index].value_counts(normalize=True).reindex(
                    global_hist.index, fill_value=0
                )
                histogram_drift = 0.5 * (split_hist - global_hist).abs().sum()
                size_drift = abs(len(index) / len(targets) - target_fractions[split_name])
                score += float(mean_drift + histogram_drift + 2.0 * size_drift)
            candidate = (score, dev_fold, test_fold)
            if best is None or candidate < best:
                best = candidate

    if best is None:
        raise RuntimeError("Unable to select ISD dev/test folds")
    _, dev_fold, test_fold = best
    return {
        fold_id: (
            "dev" if fold_id == dev_fold else "test" if fold_id == test_fold else "train"
        )
        for fold_id in range(5)
    }


def build_isd(split_version: str, seed: int) -> pd.DataFrame:
    clips = load_clips("ISD")
    targets = numeric(clips, PAQ_COLUMNS + ISO_COLUMNS)
    source_exclusions = load_exclusion_ids("ISD")
    source_excluded = clips["clip_id"].isin(source_exclusions)
    missing_target = targets.isna().any(axis=1)
    eligible = ~(source_excluded | missing_target)

    eligible_clips = clips.loc[eligible].copy()
    eligible_targets = targets.loc[eligible]
    pleasant_bin = quantile_codes(eligible_targets["mean_ISOPleasant"], 4)
    eventful_bin = quantile_codes(eligible_targets["mean_ISOEventful"], 4)
    strata = pleasant_bin.astype(str) + "_" + eventful_bin.astype(str)

    splitter = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=seed,
    )
    fold = pd.Series(index=eligible_clips.index, dtype="int64")
    for fold_id, (_, test_positions) in enumerate(
        splitter.split(
            eligible_clips,
            y=strata,
            groups=eligible_clips["LocationID"],
        )
    ):
        fold.loc[eligible_clips.index[test_positions]] = fold_id

    fold_to_split = choose_isd_fold_mapping(fold, eligible_targets, strata)
    assignments = pd.Series("excluded", index=clips.index, dtype="object")
    assignments.loc[eligible] = fold.map(fold_to_split)
    reasons = pd.Series("", index=clips.index, dtype="object")
    reasons.loc[source_excluded] = "pending_source_review"
    reasons.loc[missing_target & ~source_excluded] = "missing_iso_target"
    return assignment_frame(clips, assignments, split_version, reasons)


def build_araus(split_version: str) -> pd.DataFrame:
    clips = load_clips("ARAUS")
    source_folds = pd.to_numeric(clips["fold_r"], errors="raise")
    fold_mapping = {
        -1: "excluded",
        0: "test",
        1: "train",
        2: "train",
        3: "train",
        4: "train",
        5: "dev",
        6: "excluded",
        7: "excluded",
    }
    assignments = source_folds.map(fold_mapping)
    if assignments.isna().any():
        unknown = sorted(source_folds.loc[assignments.isna()].unique())
        raise ValueError(f"ARAUS contains unmapped fold_r values: {unknown}")
    reasons = pd.Series("", index=clips.index, dtype="object")
    reasons.loc[assignments.eq("excluded") & source_folds.eq(-1)] = "auxiliary_common_stimulus"
    reasons.loc[assignments.eq("excluded") & source_folds.isin([6, 7])] = (
        "unmaterialised_v2_test_fold"
    )
    return assignment_frame(clips, assignments, split_version, reasons)


def build_satp(split_version: str, seed: int) -> pd.DataFrame:
    clips = load_clips("SATP")
    targets = numeric(clips, ISO_COLUMNS)
    if targets.isna().any(axis=None):
        raise ValueError("SATP split generation requires complete ISO coordinate targets")

    pleasant_bin = quantile_codes(targets["mean_ISOPleasant"], 3)
    eventful_bin = quantile_codes(targets["mean_ISOEventful"], 3)
    labels = pd.concat(
        [
            pd.get_dummies(pleasant_bin, prefix="pleasant"),
            pd.get_dummies(eventful_bin, prefix="eventful"),
        ],
        axis=1,
    ).to_numpy(dtype=int)

    splitter = MultilabelStratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=seed,
    )
    folds = pd.Series(index=clips.index, dtype="int64")
    for fold_id, (_, test_positions) in enumerate(splitter.split(clips, labels)):
        folds.iloc[test_positions] = fold_id

    result = clips[["clip_id", "dataset_id"]].copy()
    result["fold"] = folds.astype(int)
    result["split_version"] = split_version
    result["exclusion_reason"] = ""
    return result


def build_delta(split_version: str, seed: int) -> pd.DataFrame:
    clips = load_clips("DeLTA")
    sources = numeric(clips, DELTA_SOURCE_COLUMNS).astype(int)
    annoyance = pd.to_numeric(clips["mean_annoyance"], errors="raise")
    annoyance_bin = quantile_codes(annoyance, 5)
    labels = np.column_stack(
        [sources.to_numpy(dtype=int), pd.get_dummies(annoyance_bin).to_numpy(dtype=int)]
    )

    first_split = MultilabelStratifiedShuffleSplit(
        n_splits=1,
        test_size=0.30,
        random_state=seed,
    )
    train_positions, remainder_positions = next(first_split.split(clips, labels))
    remainder_labels = labels[remainder_positions]
    second_split = MultilabelStratifiedShuffleSplit(
        n_splits=1,
        test_size=0.50,
        random_state=seed + 1,
    )
    dev_relative, test_relative = next(
        second_split.split(np.zeros(len(remainder_positions)), remainder_labels)
    )

    assignments = pd.Series(index=clips.index, dtype="object")
    assignments.iloc[train_positions] = "train"
    assignments.iloc[remainder_positions[dev_relative]] = "dev"
    assignments.iloc[remainder_positions[test_relative]] = "test"
    return assignment_frame(clips, assignments, split_version)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")


def read_assignment(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(output_dir: Path) -> None:
    lines = [f"{file_sha256(output_dir / name)}  {name}\n" for name in CHECKSUM_FILENAMES]
    (output_dir / "split_checksums.sha256").write_text("".join(lines), encoding="ascii")


def validate_checksums(output_dir: Path, errors: list[str]) -> None:
    manifest = output_dir / "split_checksums.sha256"
    if not manifest.exists():
        errors.append(f"Missing split checksum manifest: {manifest}")
        return
    recorded: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            errors.append(f"Malformed checksum line: {line}")
            continue
        recorded[parts[1].strip()] = parts[0]
    for filename in CHECKSUM_FILENAMES:
        path = output_dir / filename
        if path.exists() and recorded.get(filename) != file_sha256(path):
            errors.append(f"Checksum mismatch: {filename}")


def validate_exact_coverage(
    dataset_id: str,
    assignment: pd.DataFrame,
    expected_version: str,
    errors: list[str],
) -> None:
    source = load_clips(dataset_id)
    required = {"clip_id", "dataset_id", "split_version", "exclusion_reason"}
    if dataset_id == "SATP":
        required.add("fold")
    else:
        required.add("split")
    missing = sorted(required.difference(assignment.columns))
    if missing:
        errors.append(f"{dataset_id}: missing assignment columns: {', '.join(missing)}")
        return

    source_ids = source["clip_id"].tolist()
    assigned_ids = assignment["clip_id"].tolist()
    if len(assigned_ids) != len(set(assigned_ids)):
        errors.append(f"{dataset_id}: duplicate clip_id values in assignment file")
    if set(source_ids) != set(assigned_ids) or len(source_ids) != len(assigned_ids):
        errors.append(f"{dataset_id}: assignment file does not exactly cover source clips")
    if set(assignment["dataset_id"]) != {dataset_id}:
        errors.append(f"{dataset_id}: invalid dataset_id in assignment file")
    if set(assignment["split_version"]) != {expected_version}:
        errors.append(f"{dataset_id}: split_version does not match {expected_version}")


def validate_outputs(output_dir: Path, split_version: str) -> None:
    paths = {
        "ISD": output_dir / "isd_split.csv",
        "ARAUS": output_dir / "araus_split.csv",
        "SATP": output_dir / "satp_folds.csv",
        "DeLTA": output_dir / "delta_split.csv",
    }
    errors: list[str] = []
    validate_checksums(output_dir, errors)
    assignments: dict[str, pd.DataFrame] = {}
    for dataset_id, path in paths.items():
        if not path.exists():
            errors.append(f"{dataset_id}: missing split file: {path}")
            continue
        assignments[dataset_id] = read_assignment(path)
        validate_exact_coverage(dataset_id, assignments[dataset_id], split_version, errors)

    for dataset_id in ["ISD", "ARAUS", "DeLTA"]:
        if dataset_id not in assignments:
            continue
        frame = assignments[dataset_id]
        allowed = {"train", "dev", "test", "excluded"}
        unknown = sorted(set(frame["split"]).difference(allowed))
        if unknown:
            errors.append(f"{dataset_id}: invalid split values: {unknown}")
        blank_reasons = frame["split"].eq("excluded") & frame["exclusion_reason"].eq("")
        if blank_reasons.any():
            errors.append(f"{dataset_id}: excluded rows require exclusion_reason")

    if "ISD" in assignments:
        source = load_clips("ISD").drop(columns=["split"], errors="ignore")
        merged = source.merge(
            assignments["ISD"][["clip_id", "split"]],
            on="clip_id",
            validate="one_to_one",
        )
        eligible = merged[merged["split"] != "excluded"]
        leakage = eligible.groupby("LocationID")["split"].nunique()
        if (leakage > 1).any():
            errors.append("ISD: LocationID values cross benchmark partitions")

    if "ARAUS" in assignments:
        source = load_clips("ARAUS").drop(columns=["split"], errors="ignore")
        merged = source.merge(
            assignments["ARAUS"][["clip_id", "split"]], on="clip_id", validate="one_to_one"
        )
        expected = pd.to_numeric(merged["fold_r"]).map(
            {-1: "excluded", 0: "test", 1: "train", 2: "train", 3: "train", 4: "train", 5: "dev", 6: "excluded", 7: "excluded"}
        )
        if not merged["split"].equals(expected):
            errors.append("ARAUS: assignments do not match the declared source-fold mapping")

    if "SATP" in assignments:
        folds = pd.to_numeric(assignments["SATP"]["fold"], errors="coerce")
        if folds.isna().any() or set(folds.astype(int)) != set(range(5)):
            errors.append("SATP: fold must contain integers 0 through 4")
        counts = folds.value_counts()
        if counts.max() - counts.min() > 1:
            errors.append("SATP: fold sizes differ by more than one clip")

    if "DeLTA" in assignments and assignments["DeLTA"]["split"].eq("").any():
        errors.append("DeLTA: every clip must have a split")

    if errors:
        print(f"Benchmark split validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"Benchmark split validation passed: version {split_version}")
    for dataset_id, frame in assignments.items():
        column = "fold" if dataset_id == "SATP" else "split"
        counts = frame[column].value_counts().sort_index()
        formatted = ", ".join(f"{key}={value}" for key, value in counts.items())
        print(f"- {dataset_id}: {formatted}")


def build_summary(output_dir: Path, split_version: str) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for dataset_id, filename in [
        ("ISD", "isd_split.csv"),
        ("ARAUS", "araus_split.csv"),
        ("SATP", "satp_folds.csv"),
        ("DeLTA", "delta_split.csv"),
    ]:
        clips = load_clips(dataset_id)
        assignment = read_assignment(output_dir / filename)
        clips = clips.drop(columns=["split"], errors="ignore")
        merged = clips.merge(assignment, on=["clip_id", "dataset_id"], validate="one_to_one")
        partition_column = "fold" if dataset_id == "SATP" else "split"
        for partition, group in merged.groupby(partition_column, sort=True):
            record: dict[str, object] = {
                "dataset_id": dataset_id,
                "partition": partition,
                "n_clips": len(group),
                "split_version": split_version,
                "mean_ISOPleasant": "",
                "mean_ISOEventful": "",
                "mean_annoyance": "",
                "mean_label_cardinality": "",
            }
            for column in ISO_COLUMNS:
                if column in group:
                    record[column] = round(pd.to_numeric(group[column]).mean(), 6)
            if "mean_annoyance" in group:
                record["mean_annoyance"] = round(
                    pd.to_numeric(group["mean_annoyance"]).mean(), 6
                )
            if all(column in group for column in DELTA_SOURCE_COLUMNS):
                record["mean_label_cardinality"] = round(
                    numeric(group, DELTA_SOURCE_COLUMNS).sum(axis=1).mean(), 6
                )
            records.append(record)
    return pd.DataFrame(records)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if args.check_only:
        validate_outputs(output_dir, args.split_version)
        return

    outputs = {
        "isd_split.csv": build_isd(args.split_version, args.seed),
        "araus_split.csv": build_araus(args.split_version),
        "satp_folds.csv": build_satp(args.split_version, args.seed),
        "delta_split.csv": build_delta(args.split_version, args.seed),
    }
    for filename, frame in outputs.items():
        write_csv(frame, output_dir / filename)
    write_csv(build_summary(output_dir, args.split_version), output_dir / "split_summary.csv")
    write_checksums(output_dir)
    validate_outputs(output_dir, args.split_version)


if __name__ == "__main__":
    main()

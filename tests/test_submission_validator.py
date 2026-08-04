from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_submission.py"


def run_validator(path: Path, *options: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path), *options],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_header_only_template_is_valid() -> None:
    result = run_validator(
        ROOT / "benchmark" / "submissions" / "submission_template.csv",
        "--allow-empty",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def araus_test_submission() -> pd.DataFrame:
    predictions = pd.read_csv(
        ROOT
        / "benchmark"
        / "results"
        / "predictions"
        / "araus_pleasantness_regression__araus__araus_target_mean__seed2026.csv"
    )
    predictions = predictions[predictions["partition"].eq("test")].copy()
    return pd.DataFrame(
        {
            "benchmark_version": "0.1.0-dev",
            "split_version": "0.1.0",
            "task_id": predictions["task_id"],
            "task_version": "0.1.0",
            "dataset_id": predictions["dataset_id"],
            "partition": predictions["partition"],
            "fold": "",
            "record_id": predictions["record_id"],
            "target": predictions["target"],
            "prediction": predictions["y_pred"],
            "uncertainty": predictions["y_std"],
            "model_id": "araus_target_mean",
            "run_id": predictions["run_id"],
        }
    )


def test_complete_frozen_submission_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "submission.csv"
    araus_test_submission().to_csv(path, index=False)
    result = run_validator(path, "--require-complete")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "48 prediction rows" in result.stdout


def test_duplicate_prediction_is_rejected(tmp_path: Path) -> None:
    frame = araus_test_submission()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    path = tmp_path / "duplicate.csv"
    frame.to_csv(path, index=False)
    result = run_validator(path)
    assert result.returncode == 1
    assert "duplicate prediction key" in result.stdout

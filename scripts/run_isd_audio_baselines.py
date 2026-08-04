#!/usr/bin/env python3
"""Run clip- and response-level reference baselines on ISD audio."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from extract_audio_descriptors import MODEL_FEATURE_COLUMNS


ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    "isd_audio_clip_iso_coordinates": {
        "records": ROOT / "datasets/ISD/data/clips.csv",
        "record_id": "clip_id",
        "targets": ["mean_ISOPleasant", "mean_ISOEventful"],
    },
    "isd_audio_response_iso_coordinates": {
        "records": ROOT / "datasets/ISD/data/responses.csv",
        "record_id": "response_id",
        "targets": ["ISOPleasant", "ISOEventful"],
    },
}


def metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rmse": float(np.sqrt(mean_squared_error(observed, predicted))),
        "mae": float(mean_absolute_error(observed, predicted)),
        "r2": float(r2_score(observed, predicted)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--descriptors", type=Path, required=True)
    parser.add_argument("--clips", type=Path, default=TASKS["isd_audio_clip_iso_coordinates"]["records"])
    parser.add_argument(
        "--responses",
        type=Path,
        default=TASKS["isd_audio_response_iso_coordinates"]["records"],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "benchmark/audio/results",
    )
    parser.add_argument("--alpha", type=float, default=1.0)
    args = parser.parse_args()

    descriptors = pd.read_csv(args.descriptors)
    models = {
        "audio_target_mean": None,
        "audio_descriptor_ridge": Pipeline(
            [
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=args.alpha)),
            ]
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metric_rows = []
    prediction_rows = []
    task_metadata = {}
    task_inputs = {
        "isd_audio_clip_iso_coordinates": pd.read_csv(args.clips),
        "isd_audio_response_iso_coordinates": pd.read_csv(args.responses),
    }
    for task_id, task in TASKS.items():
        targets = task["targets"]
        record_id = task["record_id"]
        records = task_inputs[task_id]
        validate = "one_to_one" if record_id == "clip_id" else "one_to_many"
        record_columns = list(dict.fromkeys([record_id, "clip_id", *targets]))
        frame = descriptors.merge(
            records[record_columns],
            on="clip_id",
            how="inner",
            validate=validate,
        ).dropna(subset=[*MODEL_FEATURE_COLUMNS, *targets])
        train = frame["split"].eq("train")
        if not train.any():
            raise SystemExit(f"No train assets are available for {task_id}.")
        x_train = frame.loc[train, MODEL_FEATURE_COLUMNS]
        y_train = frame.loc[train, targets].to_numpy()

        task_metadata[task_id] = {
            "record_id": record_id,
            "targets": targets,
            "train_rows": int(train.sum()),
            "dev_rows": int(frame["split"].eq("dev").sum()),
            "test_rows": int(frame["split"].eq("test").sum()),
            "train_clips": int(frame.loc[train, "clip_id"].nunique()),
            "dev_clips": int(frame.loc[frame["split"].eq("dev"), "clip_id"].nunique()),
            "test_clips": int(frame.loc[frame["split"].eq("test"), "clip_id"].nunique()),
        }

        for model_id, configured_model in models.items():
            model = configured_model
            if model is None:
                train_mean = y_train.mean(axis=0)
            else:
                model.fit(x_train, y_train)
            for partition in ("dev", "test"):
                mask = frame["split"].eq(partition)
                if not mask.any():
                    continue
                held_out = frame.loc[mask]
                observed = held_out[targets].to_numpy()
                predicted = (
                    np.tile(train_mean, (mask.sum(), 1))
                    if model is None
                    else model.predict(held_out[MODEL_FEATURE_COLUMNS])
                )
                for target_index, target in enumerate(targets):
                    values = metrics(observed[:, target_index], predicted[:, target_index])
                    for metric_name, value in values.items():
                        metric_rows.append(
                            {
                                "model_id": model_id,
                                "dataset_id": "ISD",
                                "task_id": task_id,
                                "partition": partition,
                                "target": target,
                                "metric": metric_name,
                                "value": value,
                                "n": int(mask.sum()),
                                "n_clips": int(held_out["clip_id"].nunique()),
                                "audio_used": True,
                            }
                        )
                for row_index, (_, record) in enumerate(held_out.iterrows()):
                    for target_index, target in enumerate(targets):
                        prediction_rows.append(
                            {
                                "model_id": model_id,
                                "task_id": task_id,
                                "record_id": record[record_id],
                                "clip_id": record["clip_id"],
                                "partition": partition,
                                "target": target,
                                "observed": observed[row_index, target_index],
                                "prediction": predicted[row_index, target_index],
                            }
                        )

    pd.DataFrame(metric_rows).to_csv(args.output_dir / "metrics.csv", index=False)
    pd.DataFrame(prediction_rows).to_csv(
        args.output_dir / "predictions.csv",
        index=False,
    )
    metadata = {
        "run_id": "isd_audio_descriptor_baselines_v0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": "ISD",
        "tasks": task_metadata,
        "split_version": "0.1.0",
        "models": list(models),
        "features": MODEL_FEATURE_COLUMNS,
        "audio_used": True,
        "calibration_status": "relative_descriptors_only_pending_source_review",
    }
    (args.output_dir / "run.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"WROTE {args.output_dir}: {len(metric_rows)} metrics, "
        f"{len(prediction_rows)} predictions"
    )


if __name__ == "__main__":
    main()

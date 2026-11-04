#!/usr/bin/env python3
"""Bootstrap uncertainty and paired comparisons for ISD audio baselines."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(observed - predicted))))


def mae(observed: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(observed - predicted)))


def interval(values: list[float]) -> tuple[float, float]:
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def cluster_positions(clip_ids: np.ndarray) -> list[np.ndarray]:
    """Precompute row positions for each clip-level sampling cluster."""
    return [
        np.flatnonzero(clip_ids == clip_id)
        for clip_id in pd.unique(clip_ids)
    ]


def cluster_sample_indices(
    positions: list[np.ndarray],
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample clips with replacement while retaining every response in a clip."""
    sampled = rng.integers(0, len(positions), size=len(positions))
    return np.concatenate([positions[index] for index in sampled])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    frame = pd.read_csv(args.predictions)
    rng = np.random.default_rng(args.seed)
    interval_rows = []
    for keys, group in frame.groupby(
        ["task_id", "model_id", "partition", "target"]
    ):
        group = group.reset_index(drop=True)
        observed = group["observed"].to_numpy(dtype=float)
        predicted = group["prediction"].to_numpy(dtype=float)
        positions = cluster_positions(group["clip_id"].to_numpy())
        draws = {"rmse": [], "mae": []}
        for _ in range(args.iterations):
            index = cluster_sample_indices(positions, rng)
            draws["rmse"].append(rmse(observed[index], predicted[index]))
            draws["mae"].append(mae(observed[index], predicted[index]))
        for metric, values in draws.items():
            low, high = interval(values)
            point = rmse(observed, predicted) if metric == "rmse" else mae(observed, predicted)
            interval_rows.append(
                {
                    "task_id": keys[0],
                    "model_id": keys[1],
                    "partition": keys[2],
                    "target": keys[3],
                    "metric": metric,
                    "estimate": point,
                    "ci_low": low,
                    "ci_high": high,
                    "confidence_level": 0.95,
                    "bootstrap_iterations": args.iterations,
                    "bootstrap_unit": "clip_id",
                    "n": len(group),
                    "n_clusters": group["clip_id"].nunique(),
                }
            )

    comparison_rows = []
    baseline_id = "audio_target_mean"
    candidate_id = "audio_descriptor_ridge"
    for keys, group in frame.groupby(["task_id", "partition", "target"]):
        wide = group.pivot(
            index=["record_id", "clip_id"],
            columns="model_id",
            values=["observed", "prediction"],
        )
        if baseline_id not in wide["prediction"] or candidate_id not in wide["prediction"]:
            continue
        observed = wide["observed"][baseline_id].to_numpy(dtype=float)
        baseline = wide["prediction"][baseline_id].to_numpy(dtype=float)
        candidate = wide["prediction"][candidate_id].to_numpy(dtype=float)
        point = rmse(observed, baseline) - rmse(observed, candidate)
        clip_ids = wide.index.get_level_values("clip_id").to_numpy()
        positions = cluster_positions(clip_ids)
        draws = []
        for _ in range(args.iterations):
            index = cluster_sample_indices(positions, rng)
            draws.append(
                rmse(observed[index], baseline[index])
                - rmse(observed[index], candidate[index])
            )
        low, high = interval(draws)
        comparison_rows.append(
            {
                "baseline_model": baseline_id,
                "candidate_model": candidate_id,
                "task_id": keys[0],
                "partition": keys[1],
                "target": keys[2],
                "metric": "rmse_improvement",
                "estimate": point,
                "ci_low": low,
                "ci_high": high,
                "candidate_better_probability": float(np.mean(np.asarray(draws) > 0)),
                "bootstrap_iterations": args.iterations,
                "bootstrap_unit": "clip_id",
                "n": len(wide),
                "n_clusters": len(positions),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(interval_rows).to_csv(
        args.output_dir / "bootstrap_intervals.csv",
        index=False,
    )
    pd.DataFrame(comparison_rows).to_csv(
        args.output_dir / "paired_comparisons.csv",
        index=False,
    )
    print(
        f"WROTE {len(interval_rows)} intervals and "
        f"{len(comparison_rows)} paired comparisons"
    )


if __name__ == "__main__":
    main()

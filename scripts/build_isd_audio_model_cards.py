#!/usr/bin/env python3
"""Generate model cards for the executed ISD audio reference baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


MODEL_DESCRIPTIONS = {
    "audio_target_mean": (
        "Input-free reference that predicts the training-set target mean.",
        "none",
    ),
    "audio_descriptor_ridge": (
        "Ridge regression over deterministic relative waveform descriptors.",
        "audio waveform descriptors",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    metrics = pd.read_csv(args.results_dir / "metrics.csv")
    run = json.loads((args.results_dir / "run.json").read_text())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for model_id, (description, inputs) in MODEL_DESCRIPTIONS.items():
        rows = metrics[metrics["model_id"].eq(model_id)]
        table = rows[
            ["task_id", "partition", "target", "metric", "value", "n", "n_clips"]
        ].to_markdown(index=False, floatfmt=".4f")
        limitations = (
            "- ISD-only audio coverage; no cross-dataset audio claim.\n"
            "- Relative waveform descriptors do not establish calibrated level.\n"
            "- Missing or ambiguous source assets are excluded before training.\n"
            "- Results are valid only for split version 0.1.0 and the frozen audio cohort."
        )
        card = f"""# {model_id}

## Summary

{description}

## Contract

- Dataset: ISD
- Tasks: `isd_audio_clip_iso_coordinates`, `isd_audio_response_iso_coordinates`
- Inputs: {inputs}
- Targets: clip-mean and individual-response ISO Pleasantness and Eventfulness
- Split version: `{run['split_version']}`
- Audio used: `true`
- Clip-task train/dev/test rows: {run['tasks']['isd_audio_clip_iso_coordinates']['train_rows']}/{run['tasks']['isd_audio_clip_iso_coordinates']['dev_rows']}/{run['tasks']['isd_audio_clip_iso_coordinates']['test_rows']}
- Response-task train/dev/test rows: {run['tasks']['isd_audio_response_iso_coordinates']['train_rows']}/{run['tasks']['isd_audio_response_iso_coordinates']['dev_rows']}/{run['tasks']['isd_audio_response_iso_coordinates']['test_rows']}
- Calibration status: `{run['calibration_status']}`

## Results

{table}

## Limitations

{limitations}
"""
        (args.output_dir / f"{model_id}.md").write_text(card, encoding="utf-8")
    print(f"WROTE {len(MODEL_DESCRIPTIONS)} audio model cards")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run deterministic technical QC over materialised MOSAIQ WAV assets."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.io import wavfile


FIELDS = [
    "asset_id",
    "clip_id",
    "split",
    "status",
    "issues",
    "sample_rate_hz",
    "channels",
    "frames",
    "duration_s",
    "expected_duration_s",
    "duration_delta_s",
    "sample_dtype",
    "finite_fraction",
    "peak_abs",
    "rms",
    "rms_relative_db",
    "zero_fraction",
    "float_scale_review",
]


def analyse(path: Path, expected_duration: float | None) -> dict:
    rate, data = wavfile.read(path, mmap=True)
    array = np.asarray(data)
    frames = int(array.shape[0])
    channels = 1 if array.ndim == 1 else int(array.shape[1])
    values = array.astype(np.float64, copy=False)
    if np.issubdtype(array.dtype, np.integer):
        limit = max(abs(np.iinfo(array.dtype).min), np.iinfo(array.dtype).max)
        values = values / float(limit)

    finite = np.isfinite(values)
    finite_fraction = float(finite.mean()) if values.size else 0.0
    finite_values = values[finite]
    peak = float(np.max(np.abs(finite_values))) if finite_values.size else float("nan")
    rms = (
        float(np.sqrt(np.mean(np.square(finite_values))))
        if finite_values.size
        else float("nan")
    )
    rms_db = float(20 * np.log10(rms)) if rms > 0 else float("-inf")
    zero_fraction = float(np.mean(values == 0)) if values.size else 1.0
    duration = frames / float(rate)
    duration_delta = (
        ""
        if expected_duration is None
        else duration - float(expected_duration)
    )

    issues: list[str] = []
    failures: list[str] = []
    if frames == 0:
        failures.append("empty")
    if finite_fraction < 1.0:
        failures.append("non_finite_samples")
    if not np.isfinite(rms) or rms == 0:
        failures.append("zero_signal")
    if rate not in {44100, 48000}:
        issues.append("unsupported_sample_rate")
    if channels != 2:
        issues.append("unexpected_channel_count")
    if str(array.dtype) != "float32":
        issues.append("source_description_sample_dtype_mismatch")
    if expected_duration is not None and abs(float(duration_delta)) > 0.25:
        issues.append("duration_mismatch")
    float_review = bool(np.issubdtype(array.dtype, np.floating) and peak >= 1.0)
    if float_review:
        issues.append("float_amplitude_scale_requires_review")
    issues.append("calibration_metadata_pending")

    all_issues = failures + issues
    status = "fail" if failures else ("warn" if issues else "pass")
    return {
        "status": status,
        "issues": ";".join(all_issues),
        "sample_rate_hz": rate,
        "channels": channels,
        "frames": frames,
        "duration_s": duration,
        "expected_duration_s": "" if expected_duration is None else expected_duration,
        "duration_delta_s": duration_delta,
        "sample_dtype": str(array.dtype),
        "finite_fraction": finite_fraction,
        "peak_abs": peak,
        "rms": rms,
        "rms_relative_db": rms_db,
        "zero_fraction": zero_fraction,
        "float_scale_review": float_review,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, dtype=str, keep_default_na=False)
    selected = manifest[
        manifest["use_for_benchmark"].str.lower().eq("true")
    ]
    rows = []
    for _, item in selected.iterrows():
        path = args.storage_root / item["local_relative_path"]
        expected = (
            None
            if not item["expected_duration_s"]
            else float(item["expected_duration_s"])
        )
        try:
            result = analyse(path, expected)
        except Exception as error:
            result = {
                "status": "fail",
                "issues": f"unreadable:{type(error).__name__}",
                **{field: "" for field in FIELDS[5:]},
            }
        rows.append(
            {
                "asset_id": item["asset_id"],
                "clip_id": item["clip_id"],
                "split": item["split"],
                **result,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    statuses = Counter(row["status"] for row in rows)
    issue_counts: Counter[str] = Counter()
    for row in rows:
        issue_counts.update(issue for issue in row["issues"].split(";") if issue)
    summary = {
        "schema_version": "0.1",
        "manifest": args.manifest.as_posix(),
        "assets_checked": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
        "technical_qc_passed": statuses.get("fail", 0) == 0,
        "calibration_review_complete": False,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(yaml.safe_dump(summary, sort_keys=False), encoding="utf-8")
    print(f"WROTE {args.output} ({len(rows)} assets)")
    print(f"WROTE {args.summary}")
    if statuses.get("fail", 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

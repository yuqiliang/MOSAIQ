#!/usr/bin/env python3
"""Extract deterministic, dependency-light waveform descriptors for ISD audio."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.io import wavfile
from scipy.signal import welch


FIELDS = [
    "asset_id",
    "clip_id",
    "split",
    "audio_sha256",
    "sample_rate_hz",
    "channels",
    "duration_s",
    "rms",
    "peak_abs",
    "crest_factor",
    "zero_crossing_rate",
    "stereo_correlation",
    "spectral_centroid_hz",
    "spectral_bandwidth_hz",
    "spectral_rolloff85_hz",
    "bandpower_low_20_250",
    "bandpower_mid_250_2000",
    "bandpower_high_2000_20000",
]
FEATURE_COLUMNS = FIELDS[7:]
AMPLITUDE_SCALE_DEPENDENT_COLUMNS = ["rms", "peak_abs"]
MODEL_FEATURE_COLUMNS = [
    column
    for column in FEATURE_COLUMNS
    if column not in AMPLITUDE_SCALE_DEPENDENT_COLUMNS
]


def normalized_audio(data: np.ndarray) -> np.ndarray:
    values = np.asarray(data).astype(np.float64, copy=False)
    if np.issubdtype(data.dtype, np.integer):
        limit = max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max)
        values = values / float(limit)
    return values


def compute_descriptors(data: np.ndarray, sample_rate: int) -> dict[str, float]:
    values = normalized_audio(data)
    if values.ndim == 1:
        channels = 1
        mono = values
    else:
        channels = int(values.shape[1])
        mono = values.mean(axis=1)
    mono = np.nan_to_num(mono, copy=False)

    rms = float(np.sqrt(np.mean(np.square(mono))))
    peak = float(np.max(np.abs(mono)))
    crest = peak / rms if rms > 0 else float("nan")
    zcr = float(np.mean(np.signbit(mono[1:]) != np.signbit(mono[:-1])))
    stereo_correlation = float("nan")
    if channels >= 2:
        left = values[:, 0]
        right = values[:, 1]
        if np.std(left) > 0 and np.std(right) > 0:
            stereo_correlation = float(np.corrcoef(left, right)[0, 1])

    frequencies, power = welch(
        mono,
        fs=sample_rate,
        nperseg=min(4096, len(mono)),
        noverlap=min(2048, max(0, len(mono) // 2)),
        scaling="spectrum",
    )
    total = float(power.sum())
    if total <= 0:
        centroid = bandwidth = rolloff = float("nan")
        low = mid = high = float("nan")
    else:
        centroid = float(np.sum(frequencies * power) / total)
        bandwidth = float(
            np.sqrt(np.sum(np.square(frequencies - centroid) * power) / total)
        )
        cumulative = np.cumsum(power)
        rolloff_index = min(
            int(np.searchsorted(cumulative, 0.85 * cumulative[-1])),
            len(frequencies) - 1,
        )
        rolloff = float(frequencies[rolloff_index])

        def band_ratio(low_hz: float, high_hz: float) -> float:
            mask = (frequencies >= low_hz) & (frequencies < high_hz)
            return float(power[mask].sum() / total)

        low = band_ratio(20, 250)
        mid = band_ratio(250, 2000)
        high = band_ratio(2000, min(20000, sample_rate / 2 + 1))

    return {
        "rms": rms,
        "peak_abs": peak,
        "crest_factor": crest,
        "zero_crossing_rate": zcr,
        "stereo_correlation": stereo_correlation,
        "spectral_centroid_hz": centroid,
        "spectral_bandwidth_hz": bandwidth,
        "spectral_rolloff85_hz": rolloff,
        "bandpower_low_20_250": low,
        "bandpower_mid_250_2000": mid,
        "bandpower_high_2000_20000": high,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, dtype=str, keep_default_na=False)
    selected = manifest[manifest["use_for_benchmark"].str.lower().eq("true")]
    rows = []
    for _, item in selected.iterrows():
        path = args.storage_root / item["local_relative_path"]
        rate, data = wavfile.read(path, mmap=True)
        channels = 1 if data.ndim == 1 else int(data.shape[1])
        rows.append(
            {
                "asset_id": item["asset_id"],
                "clip_id": item["clip_id"],
                "split": item["split"],
                "audio_sha256": item["audio_sha256"],
                "sample_rate_hz": int(rate),
                "channels": channels,
                "duration_s": data.shape[0] / float(rate),
                **compute_descriptors(data, int(rate)),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    frame = pd.DataFrame(rows)
    summary = {
        "schema_version": "0.1",
        "manifest": args.manifest.as_posix(),
        "assets_processed": len(rows),
        "feature_columns": FEATURE_COLUMNS,
        "split_counts": (
            frame["split"].value_counts().sort_index().to_dict() if len(frame) else {}
        ),
        "non_finite_feature_rows": (
            int((~np.isfinite(frame[FEATURE_COLUMNS].to_numpy(dtype=float))).any(axis=1).sum())
            if len(frame)
            else 0
        ),
        "audio_used": True,
        "amplitude_scale_dependent_features": AMPLITUDE_SCALE_DEPENDENT_COLUMNS,
        "scale_invariant_model_features": MODEL_FEATURE_COLUMNS,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(yaml.safe_dump(summary, sort_keys=False), encoding="utf-8")
    print(f"WROTE {args.output} ({len(rows)} rows)")
    print(f"WROTE {args.summary}")


if __name__ == "__main__":
    main()

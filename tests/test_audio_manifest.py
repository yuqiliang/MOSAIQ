from pathlib import Path

import pandas as pd
import numpy as np

from scripts.build_isd_audio_manifest import normalize_group_id
from scripts.extract_audio_descriptors import compute_descriptors
from scripts.validate_audio_manifest import validate


ROOT = Path(__file__).resolve().parents[1]


def test_isd_source_filename_aliases_normalize_to_group_id() -> None:
    assert normalize_group_id("NP125.hdf.wav") == "NP125"
    assert normalize_group_id("NP102.1.wav") == "NP102"
    assert normalize_group_id("NP101.wav") == "NP101"


def test_groningen_manifest_has_no_split_leakage_when_present() -> None:
    manifest = ROOT / "benchmark/audio/manifests/isd_groningen_audio_manifest.csv"
    if not manifest.exists():
        return
    errors, _warnings = validate(
        manifest,
        ROOT / "datasets/ISD/data/clips.csv",
        ROOT / "benchmark/splits/isd_split.csv",
        require_complete=False,
    )
    assert errors == []
    frame = pd.read_csv(manifest)
    usable = frame[frame["use_for_benchmark"]]
    assert not usable["clip_id"].duplicated().any()


def test_audio_descriptors_are_finite_for_stereo_sine_wave() -> None:
    rate = 48000
    time = np.arange(rate, dtype=float) / rate
    left = 0.1 * np.sin(2 * np.pi * 440 * time)
    right = 0.1 * np.sin(2 * np.pi * 880 * time)
    features = compute_descriptors(np.column_stack([left, right]), rate)
    assert all(np.isfinite(value) for value in features.values())
    assert features["spectral_centroid_hz"] > 0
    assert -1 <= features["stereo_correlation"] <= 1

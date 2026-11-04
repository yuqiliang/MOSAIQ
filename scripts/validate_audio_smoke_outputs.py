#!/usr/bin/env python3
"""Validate committed ISD audio smoke manifests, QC, and descriptors."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from extract_audio_descriptors import FEATURE_COLUMNS
from validate_audio_manifest import validate


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark/audio/manifests/isd_groningen_audio_manifest.csv"
MANIFEST_SUMMARY = (
    ROOT / "benchmark/audio/manifests/isd_groningen_audio_summary.yaml"
)
QC = ROOT / "benchmark/audio/qc/isd_groningen_audio_qc.csv"
QC_SUMMARY = ROOT / "benchmark/audio/qc/isd_groningen_audio_qc_summary.yaml"
FEATURES = ROOT / "benchmark/audio/features/isd_groningen_audio_descriptors.csv"
FEATURE_SUMMARY = (
    ROOT / "benchmark/audio/features/isd_groningen_audio_descriptors_summary.yaml"
)
REGISTRY = ROOT / "benchmark/governance/isd_zenodo_source_registry.csv"


def main() -> None:
    errors, warnings = validate(
        MANIFEST,
        ROOT / "datasets/ISD/data/clips.csv",
        ROOT / "benchmark/splits/isd_split.csv",
        require_complete=False,
    )
    if errors:
        raise SystemExit("\n".join(errors))

    manifest = pd.read_csv(MANIFEST)
    usable = manifest[manifest["use_for_benchmark"]]
    qc = pd.read_csv(QC)
    features = pd.read_csv(FEATURES)
    registry = pd.read_csv(REGISTRY)
    manifest_summary = yaml.safe_load(MANIFEST_SUMMARY.read_text())
    qc_summary = yaml.safe_load(QC_SUMMARY.read_text())
    feature_summary = yaml.safe_load(FEATURE_SUMMARY.read_text())

    checks = {
        "manifest usable count": len(usable) == manifest_summary["usable_assets"],
        "QC coverage": set(qc["asset_id"]) == set(usable["asset_id"]),
        "QC no failures": not qc["status"].eq("fail").any(),
        "descriptor coverage": set(features["asset_id"]) == set(usable["asset_id"]),
        "descriptor values finite": np.isfinite(
            features[FEATURE_COLUMNS].to_numpy(dtype=float)
        ).all(),
        "QC summary": qc_summary["technical_qc_passed"] is True,
        "feature summary": feature_summary["audio_used"] is True,
        "frozen split inheritance": set(usable["split"]) == {"test"},
        "source registry version": set(registry["source_version"]) == {"1.0.1-alpha.1"},
        "source registry licence": set(registry["licence_spdx"]) == {"CC-BY-4.0"},
        "Groningen source verified": registry.loc[
            registry["file_name"].eq("WAV_Groningen_1.zip"),
            "local_status",
        ].eq("downloaded_verified").all(),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit(f"Audio smoke validation failed: {', '.join(failed)}")
    for warning in warnings:
        print(f"WARN: {warning}")
    print(
        "Audio smoke validation passed: "
        f"{len(usable)} assets, {len(qc)} QC rows, {len(features)} descriptor rows"
    )


if __name__ == "__main__":
    main()

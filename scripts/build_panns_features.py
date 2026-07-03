"""Build optional PANNs audio embedding FeatureRecords linked to MOSAIQ clips.

This script writes rows to features.csv using the MOSAIQ FeatureRecord schema:
- feature_type=audio_embedding
- source_modality=audio
- model_name defaults to PANNs-Cnn14

It does not vendor PANNs or checkpoints. Install runtime dependencies and
provide any required checkpoint path outside the repository.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np

from feature_fields import FEATURE_FIELDS

AUDIO_EXTENSIONS = [".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac"]


@dataclass
class ClipRow:
    clip_id: str
    dataset_id: str
    audio_asset: str
    start_s: float
    end_s: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PANNs audio embedding FeatureRecords")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--clips-csv", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--audio-root", type=Path, default=None)
    parser.add_argument("--embeddings-dir", type=Path, default=None)
    parser.add_argument("--audio-field", type=str, default="audio_asset")
    parser.add_argument("--model-name", type=str, default="PANNs-Cnn14")
    parser.add_argument("--checkpoint-path", type=Path, default=None)
    parser.add_argument("--sample-rate", type=int, default=32000)
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--storage", type=str, default="npy", choices=["npy", "base64"])
    parser.add_argument("--dtype", type=str, default="float32", choices=["float16", "float32", "float64"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mode", type=str, default="append", choices=["append", "overwrite"])
    parser.add_argument("--skip-missing-audio", action="store_true")
    return parser.parse_args()


def package_version(pkg: str) -> str:
    try:
        return version(pkg)
    except PackageNotFoundError:
        return "not-installed"


def get_git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def parse_float(value: str, default: float) -> float:
    try:
        return float(value) if value != "" else default
    except Exception:
        return default


def choose_audio_asset(row: dict[str, str], audio_field: str) -> str:
    for field in [audio_field, "audio_asset", "soundscape", "source_audio_path", "clip_id"]:
        value = (row.get(field) or "").strip()
        if value:
            return value
    return ""


def load_clips(path: Path, audio_field: str) -> list[ClipRow]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        required = {"clip_id", "dataset_id"}
        missing = sorted(required.difference(set(reader.fieldnames)))
        if missing:
            raise ValueError(f"clips.csv missing required columns: {', '.join(missing)}")
        return [
            ClipRow(
                clip_id=row["clip_id"],
                dataset_id=row["dataset_id"],
                audio_asset=choose_audio_asset(row, audio_field),
                start_s=parse_float(row.get("start_s", row.get("binaural_start_s", "")), 0.0),
                end_s=parse_float(row.get("end_s", row.get("binaural_end_s", "")), 0.0),
            )
            for row in reader
        ]


def resolve_audio_path(clip: ClipRow, dataset_dir: Path, audio_root: Path | None) -> Path | None:
    raw = clip.audio_asset.strip()
    if not raw:
        return None
    p = Path(raw)
    candidates: list[Path] = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.extend([dataset_dir / "data" / p, dataset_dir / p])
        if audio_root is not None:
            candidates.append(audio_root / p)
        if p.suffix == "":
            for ext in AUDIO_EXTENSIONS:
                candidates.extend([dataset_dir / "data" / f"{raw}{ext}", dataset_dir / f"{raw}{ext}"])
                if audio_root is not None:
                    candidates.append(audio_root / f"{raw}{ext}")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def get_device(user_device: str, torch: Any) -> str:
    if user_device in {"cpu", "cuda"}:
        return user_device
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_audio_segment(audio_path: Path, sample_rate: int, start_s: float, end_s: float, librosa: Any) -> np.ndarray:
    duration = (end_s - start_s) if end_s > start_s else None
    audio, _ = librosa.load(audio_path, sr=sample_rate, mono=True, offset=max(start_s, 0.0), duration=duration)
    return np.asarray(audio, dtype=np.float32)


def existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in FEATURE_FIELDS})


def main() -> None:
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    clips_csv = (args.clips_csv or (dataset_dir / "data" / "clips.csv")).resolve()
    output_csv = (args.output_csv or (dataset_dir / "data" / "features.csv")).resolve()
    embeddings_dir = (args.embeddings_dir or (dataset_dir / "data" / "features" / "panns_audio_embedding")).resolve()
    audio_root = args.audio_root.resolve() if args.audio_root else None

    try:
        import librosa
        import torch
        from panns_inference import AudioTagging
    except Exception as exc:
        raise RuntimeError(
            "Missing runtime dependencies. Install: panns-inference librosa torch numpy"
        ) from exc

    clips = load_clips(clips_csv, args.audio_field)
    if args.limit is not None:
        clips = clips[: args.limit]

    device = get_device(args.device, torch)
    checkpoint = str(args.checkpoint_path) if args.checkpoint_path else None
    tagger = AudioTagging(checkpoint_path=checkpoint, device=device)
    out_dtype = np.dtype(args.dtype)

    if args.storage == "npy":
        embeddings_dir.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()
    lib_versions = {
        "python": platform.python_version(),
        "numpy": package_version("numpy"),
        "torch": package_version("torch"),
        "librosa": package_version("librosa"),
        "panns_inference": package_version("panns-inference"),
    }
    script_version = get_git_commit()

    generated: list[dict[str, Any]] = []
    skipped = 0
    for clip in clips:
        audio_path = resolve_audio_path(clip, dataset_dir, audio_root)
        if audio_path is None:
            msg = f"Unable to resolve audio for clip_id={clip.clip_id}"
            if args.skip_missing_audio:
                print(f"SKIP: {msg}")
                skipped += 1
                continue
            raise FileNotFoundError(msg)

        audio = load_audio_segment(audio_path, args.sample_rate, clip.start_s, clip.end_s, librosa)
        _, embedding = tagger.inference(audio[None, :])
        embedding = np.asarray(embedding).reshape(-1).astype(out_dtype, copy=False)

        feature_path = ""
        value_format = "vector"
        payload: dict[str, Any] = {
            "storage": "base64",
            "embedding_base64": base64.b64encode(embedding.tobytes()).decode("ascii"),
        }
        if args.storage == "npy":
            rel = Path("data") / "features" / "panns_audio_embedding" / f"{clip.clip_id}.npy"
            np.save(dataset_dir / rel, embedding)
            feature_path = rel.as_posix()
            value_format = "path"
            payload = {"storage": "npy"}

        payload.update(
            {
                "embedding_dim": int(embedding.shape[0]),
                "dtype": str(embedding.dtype),
                "pooling": "clipwise",
                "sample_rate_hz": args.sample_rate,
                "start_s": clip.start_s,
                "end_s": clip.end_s,
            }
        )

        provenance = {
            "tool": "PANNs",
            "tool_package": "panns-inference",
            "tool_version": package_version("panns-inference"),
            "model_name": args.model_name,
            "model_version": str(args.checkpoint_path) if args.checkpoint_path else "default",
            "input_asset_id": clip.audio_asset,
            "clip_id": clip.clip_id,
            "sample_rate_hz": args.sample_rate,
            "pooling": "clipwise",
            "preprocessing": "mono_resample_to_32000hz" if args.sample_rate == 32000 else f"mono_resample_to_{args.sample_rate}hz",
            "library_versions": lib_versions,
            "device": device,
            "script": "scripts/build_panns_features.py",
            "script_version": script_version,
            "created_by": "MOSAIQ",
            "created_date": now_iso,
        }

        generated.append(
            {
                "feature_id": f"panns_{clip.clip_id}",
                "dataset_id": clip.dataset_id,
                "clip_id": clip.clip_id,
                "asset_id": clip.audio_asset,
                "modality": "audio",
                "feature_type": "audio_embedding",
                "feature_name": "PANNs clipwise audio embedding",
                "source_modality": "audio",
                "value_format": value_format,
                "extractor_name": "PANNs",
                "extractor_version": package_version("panns-inference"),
                "provenance_json": json.dumps(provenance, ensure_ascii=True, separators=(",", ":")),
                "feature_storage_path": feature_path,
                "feature_path": feature_path,
                "feature_file_type": "npy" if value_format == "path" else "inline_base64",
                "feature_value_json": json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
                "feature_dimension": int(embedding.shape[0]),
                "feature_shape": f"[{int(embedding.shape[0])}]",
                "feature_format": value_format,
                "embedding_dim": int(embedding.shape[0]),
                "dtype": str(embedding.dtype),
                "model_name": args.model_name,
                "model_version": str(args.checkpoint_path) if args.checkpoint_path else "default",
                "model_checkpoint": str(args.checkpoint_path) if args.checkpoint_path else "default",
                "input_asset_id": clip.audio_asset,
                "input_asset": clip.audio_asset,
                "input_time_window": f"{clip.start_s:.6g}-{clip.end_s:.6g}s",
                "sampling_rate_or_fps": str(args.sample_rate),
                "code_reference": "scripts/build_panns_features.py",
                "created_by": "MOSAIQ",
                "date_created": now_iso,
                "frame_time_s": "",
                "frame_index": "",
                "pooling": "clipwise",
                "language": "",
                "provenance_notes": "",
                "notes": "",
            }
        )

    rows = existing_rows(output_csv) if args.mode == "append" else []
    generated_ids = {row["feature_id"] for row in generated}
    kept = [row for row in rows if row.get("feature_id") not in generated_ids]
    write_rows(output_csv, kept + generated)

    print(f"Wrote {len(generated)} audio_embedding rows to {output_csv}")
    if skipped:
        print(f"Skipped {skipped} clips with unresolved audio")


if __name__ == "__main__":
    main()

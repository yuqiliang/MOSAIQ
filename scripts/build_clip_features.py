"""Build optional CLIP embedding FeatureRecords linked to MOSAIQ clips.

This script writes clip-level records to features.csv using the generic MOSAIQ
feature schema, with:
- feature_type=clip_embedding
- feature_family=visual_embedding
- value_format in {path, base64}
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

VIDEO_EXTENSIONS = [".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"]
FEATURE_FIELDS = [
    "feature_id",
    "clip_id",
    "feature_type",
    "source_modality",
    "value_format",
    "provenance_json",
    "feature_path",
    "feature_value_json",
    "embedding_dim",
    "dtype",
    "model_name",
    "model_version",
    "input_asset_id",
    "frame_time_s",
    "frame_index",
    "pooling",
    "language",
    "notes",
]


@dataclass
class ClipRow:
    clip_id: str
    dataset_id: str
    video_asset: str
    video_asset_id: str
    start_s: float
    end_s: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build CLIP embedding features for MOSAIQ clips")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--clips-csv", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--embeddings-dir", type=Path, default=None)
    parser.add_argument("--video-root", type=Path, default=None)
    parser.add_argument("--model-name", type=str, default="ViT-B-32")
    parser.add_argument("--pretrained", type=str, default="openai")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--storage", type=str, default="npy", choices=["npy", "base64"])
    parser.add_argument("--dtype", type=str, default="float32", choices=["float16", "float32", "float64"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mode", type=str, default="append", choices=["append", "overwrite"])
    parser.add_argument("--skip-missing-video", action="store_true")
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


def normalize_model_name(model_name: str) -> str:
    return {"ViT-B/32": "ViT-B-32", "ViT-L/14": "ViT-L-14"}.get(model_name, model_name)


def parse_float(value: str, default: float) -> float:
    try:
        return float(value) if value != "" else default
    except Exception:
        return default


def load_clips(path: Path) -> list[ClipRow]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        required = {"clip_id", "dataset_id", "video_asset", "video_asset_id", "start_s", "end_s"}
        missing = sorted(required.difference(set(reader.fieldnames)))
        if missing:
            raise ValueError(f"clips.csv missing required columns: {', '.join(missing)}")
        return [
            ClipRow(
                clip_id=row["clip_id"],
                dataset_id=row["dataset_id"],
                video_asset=row.get("video_asset", ""),
                video_asset_id=row.get("video_asset_id", ""),
                start_s=parse_float(row.get("start_s", ""), 0.0),
                end_s=parse_float(row.get("end_s", ""), 0.0),
            )
            for row in reader
        ]


def resolve_video_path(clip: ClipRow, dataset_dir: Path, video_root: Path | None) -> Path | None:
    candidates: list[Path] = []
    for raw in [clip.video_asset, clip.video_asset_id]:
        raw = (raw or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates.extend([dataset_dir / "data" / p, dataset_dir / p])
            if video_root is not None:
                candidates.append(video_root / p)
            if p.suffix == "":
                for ext in VIDEO_EXTENSIONS:
                    candidates.extend([dataset_dir / "data" / f"{raw}{ext}", dataset_dir / f"{raw}{ext}"])
                    if video_root is not None:
                        candidates.append(video_root / f"{raw}{ext}")
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def get_device(user_device: str, torch: Any) -> str:
    if user_device in {"cpu", "cuda"}:
        return user_device
    return "cuda" if torch.cuda.is_available() else "cpu"


def extract_center_frame(video_path: Path, start_s: float, end_s: float, cv2: Any) -> tuple[np.ndarray, float, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    try:
        target_time = max((start_s + end_s) / 2.0, 0.0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps > 0 and frame_count > 0:
            frame_index = max(0, min(int(round(target_time * fps)), frame_count - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Failed to decode frame {frame_index} from {video_path}")
            frame_time_s = frame_index / fps
        else:
            cap.set(cv2.CAP_PROP_POS_MSEC, target_time * 1000.0)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Failed to decode center frame at {target_time:.3f}s from {video_path}")
            frame_time_s, frame_index = target_time, 0
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), frame_time_s, frame_index
    finally:
        cap.release()


def existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FEATURE_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FEATURE_FIELDS})


def main() -> None:
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    clips_csv = (args.clips_csv or (dataset_dir / "data" / "clips.csv")).resolve()
    output_csv = (args.output_csv or (dataset_dir / "data" / "features.csv")).resolve()
    embeddings_dir = (args.embeddings_dir or (dataset_dir / "data" / "features" / "clip_embedding")).resolve()
    video_root = args.video_root.resolve() if args.video_root else None

    try:
        import cv2
        import open_clip
        import torch
        from PIL import Image
    except Exception as exc:
        raise RuntimeError(
            "Missing runtime dependencies. Install: open-clip-torch torch torchvision pillow opencv-python-headless"
        ) from exc

    clips = load_clips(clips_csv)
    if args.limit is not None:
        clips = clips[: args.limit]

    model_name = normalize_model_name(args.model_name)
    device = get_device(args.device, torch)
    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=args.pretrained)
    model = model.to(device)
    model.eval()

    if args.storage == "npy":
        embeddings_dir.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()
    lib_versions = {
        "python": platform.python_version(),
        "numpy": package_version("numpy"),
        "torch": package_version("torch"),
        "open_clip_torch": package_version("open-clip-torch"),
        "opencv_python_headless": package_version("opencv-python-headless"),
        "pillow": package_version("pillow"),
    }
    script_version = get_git_commit()

    generated: list[dict[str, str]] = []
    skipped = 0
    out_dtype = np.dtype(args.dtype)

    for clip in clips:
        video_path = resolve_video_path(clip, dataset_dir, video_root)
        if video_path is None:
            msg = f"Unable to resolve video for clip_id={clip.clip_id}"
            if args.skip_missing_video:
                print(f"SKIP: {msg}")
                skipped += 1
                continue
            raise FileNotFoundError(msg)

        frame_rgb, frame_time_s, frame_index = extract_center_frame(video_path, clip.start_s, clip.end_s, cv2)
        image_tensor = preprocess(Image.fromarray(frame_rgb)).unsqueeze(0).to(device)
        with torch.no_grad():
            emb = model.encode_image(image_tensor).detach().cpu().numpy().reshape(-1)
        emb = emb.astype(out_dtype, copy=False)

        feature_path = ""
        value_format = "base64"
        feature_json_payload: dict[str, Any] = {
            "embedding_dim": int(emb.shape[0]),
            "dtype": str(emb.dtype),
            "pooling": "center_frame",
            "frame_time_s": round(float(frame_time_s), 6),
            "frame_index": int(frame_index),
            "video_asset_id": clip.video_asset_id,
        }
        if args.storage == "npy":
            rel = Path("data") / "features" / "clip_embedding" / f"{clip.clip_id}.npy"
            np.save(dataset_dir / rel, emb)
            feature_path = rel.as_posix()
            value_format = "path"
            feature_json_payload["storage"] = "npy"
        else:
            feature_json_payload["storage"] = "base64"
            feature_json_payload["embedding_base64"] = base64.b64encode(emb.tobytes()).decode("ascii")

        provenance = {
            "tool": "open_clip",
            "tool_version": package_version("open-clip-torch"),
            "model": model_name,
            "version": args.pretrained,
            "library_versions": lib_versions,
            "frame_sampling_rule": "center_frame_at_t=(start_s+end_s)/2",
            "preprocess": "open_clip.create_model_and_transforms eval preprocessing",
            "device": device,
            "input_video_asset_id": clip.video_asset_id,
            "clip_id": clip.clip_id,
            "generated_by_script": "scripts/build_clip_features.py",
            "generated_at": now_iso,
            "script_version": script_version,
        }

        generated.append(
            {
                "feature_id": f"clipemb_{clip.clip_id}",
                "clip_id": clip.clip_id,
                "feature_type": "visual_clip_embedding",
                "source_modality": "visual",
                "value_format": value_format,
                "provenance_json": json.dumps(provenance, ensure_ascii=True, separators=(",", ":")),
                "feature_path": feature_path,
                "feature_value_json": json.dumps(feature_json_payload, ensure_ascii=True, separators=(",", ":")),
                "embedding_dim": int(emb.shape[0]),
                "dtype": str(emb.dtype),
                "model_name": model_name,
                "model_version": args.pretrained,
                "input_asset_id": clip.video_asset_id,
                "frame_time_s": round(float(frame_time_s), 6),
                "frame_index": int(frame_index),
                "pooling": "center_frame",
                "language": "",
                "notes": "",
            }
        )

    if args.mode == "append":
        rows = existing_rows(output_csv)
    else:
        rows = []

    # Keep non-clip_embedding features; replace clip_embedding rows by clip_id.
    kept = [r for r in rows if not (r.get("feature_type") == "visual_clip_embedding" and r.get("clip_id"))]
    merged = kept + generated
    write_rows(output_csv, merged)

    print(f"Wrote {len(generated)} clip_embedding rows to {output_csv}")
    if skipped:
        print(f"Skipped {skipped} clips with unresolved videos")


if __name__ == "__main__":
    main()

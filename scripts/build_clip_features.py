"""Build optional CLIP visual embedding features linked to MOSAIQ clips.

This script reads clips.csv, samples one representative frame per clip
(default: center frame at t=(start_s + end_s)/2), computes a CLIP image
embedding, and writes a features.csv resource compatible with
datasets/*/schemas/features.schema.yaml.
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


@dataclass
class ClipRow:
    clip_id: str
    dataset_id: str
    video_asset: str
    video_asset_id: str
    start_s: float
    end_s: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build CLIP visual embedding features for MOSAIQ clips")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        required=True,
        help="Dataset root directory (e.g., datasets/ISD or datasets/ARAUS)",
    )
    parser.add_argument(
        "--clips-csv",
        type=Path,
        default=None,
        help="Override clips CSV path (defaults to <dataset-dir>/data/clips.csv)",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Output features CSV path (defaults to <dataset-dir>/data/features.csv)",
    )
    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default=None,
        help="Directory for .npy embeddings (default: <dataset-dir>/data/features/visual_clip_embedding)",
    )
    parser.add_argument(
        "--video-root",
        type=Path,
        default=None,
        help="Optional root directory to resolve video paths from ids",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="ViT-B-32",
        help="OpenCLIP model name (e.g., ViT-B-32 or ViT-L-14)",
    )
    parser.add_argument(
        "--pretrained",
        type=str,
        default="openai",
        help="OpenCLIP pretrained checkpoint key (e.g., openai)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Inference device",
    )
    parser.add_argument(
        "--storage",
        type=str,
        default="npy",
        choices=["npy", "base64"],
        help="How to store embedding payload in embedding_path_or_value",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="float32",
        choices=["float16", "float32", "float64"],
        help="Output embedding dtype",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of clips to process",
    )
    parser.add_argument(
        "--frame-sampling-rule",
        type=str,
        default="center",
        choices=["center"],
        help="Frame sampling rule",
    )
    parser.add_argument(
        "--skip-missing-video",
        action="store_true",
        help="Skip clips with unresolved video assets instead of failing",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing features.csv if present",
    )
    return parser.parse_args()


def package_version(pkg: str) -> str:
    try:
        return version(pkg)
    except PackageNotFoundError:
        return "not-installed"


def get_git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def normalize_model_name(model_name: str) -> str:
    # Accept CLIP-style aliases in the task spec.
    aliases = {
        "ViT-B/32": "ViT-B-32",
        "ViT-L/14": "ViT-L-14",
    }
    return aliases.get(model_name, model_name)


def require_columns(header: list[str], required: list[str]) -> None:
    missing = [col for col in required if col not in header]
    if missing:
        raise ValueError(f"clips.csv missing required columns: {', '.join(missing)}")


def parse_float(value: str, default: float) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except Exception:
        return default


def load_clips(path: Path) -> list[ClipRow]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        require_columns(
            reader.fieldnames,
            ["clip_id", "dataset_id", "video_asset", "video_asset_id", "start_s", "end_s"],
        )
        rows: list[ClipRow] = []
        for row in reader:
            rows.append(
                ClipRow(
                    clip_id=row["clip_id"],
                    dataset_id=row["dataset_id"],
                    video_asset=row.get("video_asset", ""),
                    video_asset_id=row.get("video_asset_id", ""),
                    start_s=parse_float(row.get("start_s", ""), 0.0),
                    end_s=parse_float(row.get("end_s", ""), 0.0),
                )
            )
        return rows


def resolve_video_path(
    clip: ClipRow,
    dataset_dir: Path,
    video_root: Path | None,
) -> Path | None:
    candidates: list[Path] = []
    for raw in [clip.video_asset, clip.video_asset_id]:
        raw = (raw or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates.append(dataset_dir / "data" / p)
            candidates.append(dataset_dir / p)
            if video_root is not None:
                candidates.append(video_root / p)

            # If the value looks like an ID without extension, try common video extensions.
            if p.suffix == "":
                for ext in VIDEO_EXTENSIONS:
                    candidates.append(dataset_dir / "data" / f"{raw}{ext}")
                    candidates.append(dataset_dir / f"{raw}{ext}")
                    if video_root is not None:
                        candidates.append(video_root / f"{raw}{ext}")

    for cand in candidates:
        if cand.exists() and cand.is_file():
            return cand
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
            frame_index = int(round(target_time * fps))
            frame_index = max(0, min(frame_index, frame_count - 1))
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
            frame_time_s = target_time
            frame_index = 0

        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame_rgb, frame_time_s, frame_index
    finally:
        cap.release()


def build_provenance(
    args: argparse.Namespace,
    script_version: str,
    lib_versions: dict[str, str],
    device: str,
    model_name: str,
) -> str:
    payload = {
        "model": model_name,
        "version": args.pretrained,
        "library_versions": lib_versions,
        "frame_sampling_rule": "center_frame_at_t=(start_s+end_s)/2",
        "preprocess": "open_clip.create_model_and_transforms eval preprocessing",
        "device": device,
        "date": datetime.now(timezone.utc).isoformat(),
        "script_version": script_version,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def main() -> None:
    args = parse_args()

    dataset_dir = args.dataset_dir.resolve()
    clips_csv = (args.clips_csv or (dataset_dir / "data" / "clips.csv")).resolve()
    output_csv = (args.output_csv or (dataset_dir / "data" / "features.csv")).resolve()
    embeddings_dir = (
        (args.embeddings_dir or (dataset_dir / "data" / "features" / "visual_clip_embedding"))
        .resolve()
    )
    video_root = args.video_root.resolve() if args.video_root else None

    if output_csv.exists() and not args.overwrite:
        raise FileExistsError(f"{output_csv} already exists. Use --overwrite to replace it.")

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

    device = get_device(args.device, torch)
    model_name = normalize_model_name(args.model_name)
    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=args.pretrained)
    model = model.to(device)
    model.eval()

    np_dtype = np.dtype(args.dtype)
    lib_versions = {
        "python": platform.python_version(),
        "numpy": package_version("numpy"),
        "torch": package_version("torch"),
        "open_clip_torch": package_version("open-clip-torch"),
        "opencv_python_headless": package_version("opencv-python-headless"),
        "pillow": package_version("pillow"),
    }
    script_version = get_git_commit()

    if args.storage == "npy":
        embeddings_dir.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows_out: list[dict[str, Any]] = []
    skipped = 0
    for idx, clip in enumerate(clips, start=1):
        video_path = resolve_video_path(clip, dataset_dir, video_root)
        if video_path is None:
            msg = f"Unable to resolve video for clip_id={clip.clip_id} (video_asset={clip.video_asset}, video_asset_id={clip.video_asset_id})"
            if args.skip_missing_video:
                print(f"SKIP: {msg}")
                skipped += 1
                continue
            raise FileNotFoundError(msg)

        frame_rgb, frame_time_s, frame_index = extract_center_frame(video_path, clip.start_s, clip.end_s, cv2)
        image = Image.fromarray(frame_rgb)
        image_tensor = preprocess(image).unsqueeze(0).to(device)

        with torch.no_grad():
            embedding = model.encode_image(image_tensor).detach().cpu().numpy().reshape(-1)
        embedding = embedding.astype(np_dtype, copy=False)

        if args.storage == "npy":
            emb_rel = Path("data") / "features" / "visual_clip_embedding" / f"{clip.clip_id}.npy"
            emb_abs = dataset_dir / emb_rel
            emb_abs.parent.mkdir(parents=True, exist_ok=True)
            np.save(emb_abs, embedding)
            embedding_payload = emb_rel.as_posix()
        else:
            embedding_payload = base64.b64encode(embedding.tobytes()).decode("ascii")

        rows_out.append(
            {
                "feature_id": f"{clip.dataset_id}_FEAT_{idx:06d}",
                "clip_id": clip.clip_id,
                "feature_type": "visual_clip_embedding",
                "embedding_path_or_value": embedding_payload,
                "embedding_dim": int(embedding.shape[0]),
                "dtype": str(embedding.dtype),
                "pooling": "center_frame",
                "frame_time_s": f"{frame_time_s:.6f}",
                "frame_index": int(frame_index),
                "video_asset_id": clip.video_asset_id,
                "provenance_json": build_provenance(args, script_version, lib_versions, device, model_name),
            }
        )

    fieldnames = [
        "feature_id",
        "clip_id",
        "feature_type",
        "embedding_path_or_value",
        "embedding_dim",
        "dtype",
        "pooling",
        "frame_time_s",
        "frame_index",
        "video_asset_id",
        "provenance_json",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} feature rows to {output_csv}")
    if skipped:
        print(f"Skipped {skipped} clips with unresolved videos (--skip-missing-video enabled)")


if __name__ == "__main__":
    main()

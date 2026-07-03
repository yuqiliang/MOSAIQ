"""Build CitySeg-derived semantic summary FeatureRecords for MOSAIQ clips.

Minimal implementation scope:
- Supports precomputed summary JSON/CSV inputs.
- Includes TODO notes for full HDF5 mask aggregation.
- Writes generic clip-level feature rows to features.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feature_fields import FEATURE_FIELDS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build CitySeg semantic summary features")
    parser.add_argument("--clips", type=Path, required=True, help="Path to clips.csv")
    parser.add_argument("--cityseg-dir", type=Path, required=True, help="Path to CitySeg outputs")
    parser.add_argument("--output", type=Path, required=True, help="Path to features.csv")
    parser.add_argument("--dataset-id", type=str, required=True, help="Dataset id (e.g., ISD, ARAUS)")
    parser.add_argument("--class-map", type=Path, default=Path("config/cityseg_class_map.yaml"))
    parser.add_argument("--mode", type=str, default="append", choices=["append", "overwrite"])
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--skip-missing", action="store_true", help="Skip clips with no CitySeg summary")
    return parser.parse_args()


def load_json_or_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                f"Could not parse {path}. Expected JSON-compatible YAML or install pyyaml."
            ) from exc
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError(f"Expected mapping in {path}")
        return data


def canonical_class(name: str, aliases: dict[str, str]) -> str:
    key = name.strip().lower().replace("-", " ")
    key = " ".join(key.split())
    return aliases.get(key, key.replace(" ", "_"))


def to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def merge_class_ratio(raw: dict[str, Any], aliases: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in raw.items():
        cname = canonical_class(str(k), aliases)
        out[cname] = out.get(cname, 0.0) + to_float(v)
    return out


def aggregate_frame_stats(frame_stats: list[dict[str, Any]], aliases: dict[str, str]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    if not frame_stats:
        return {}, {}
    per_class_values: dict[str, list[float]] = {}
    for frame in frame_stats:
        frame_ratio = frame.get("class_ratio", {})
        if isinstance(frame_ratio, dict):
            merged = merge_class_ratio(frame_ratio, aliases)
            for cname, val in merged.items():
                per_class_values.setdefault(cname, []).append(val)

    class_ratio: dict[str, float] = {}
    temporal: dict[str, dict[str, float]] = {}
    for cname, vals in per_class_values.items():
        if not vals:
            continue
        n = len(vals)
        mean_v = sum(vals) / n
        class_ratio[cname] = mean_v
        var = sum((v - mean_v) ** 2 for v in vals) / n
        temporal[cname] = {
            "mean": mean_v,
            "std": var ** 0.5,
            "min": min(vals),
            "max": max(vals),
        }
    return class_ratio, temporal


def compute_grouped_categories(class_ratio: dict[str, float], groups: dict[str, list[str]], aliases: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for gname, members in groups.items():
        total = 0.0
        for m in members:
            cname = canonical_class(m, aliases)
            total += class_ratio.get(cname, 0.0)
        out[gname] = total
    return out


def top_k_classes(class_ratio: dict[str, float], k: int) -> list[str]:
    return [k_ for k_, _ in sorted(class_ratio.items(), key=lambda kv: kv[1], reverse=True)[:k]]


def load_clips(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_precomputed_index(cityseg_dir: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    packed = cityseg_dir / "clip_summaries.json"
    if packed.exists():
        payload = json.loads(packed.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "summaries" in payload and isinstance(payload["summaries"], list):
            for rec in payload["summaries"]:
                if isinstance(rec, dict) and rec.get("clip_id"):
                    index[str(rec["clip_id"])] = rec
        elif isinstance(payload, dict):
            for k, v in payload.items():
                if isinstance(v, dict):
                    rec = dict(v)
                    rec.setdefault("clip_id", k)
                    index[str(k)] = rec
        elif isinstance(payload, list):
            for rec in payload:
                if isinstance(rec, dict) and rec.get("clip_id"):
                    index[str(rec["clip_id"])] = rec
    return index


def load_csv_summary(path: Path, clip_id: str) -> dict[str, Any] | None:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return None

    # Pattern 1: aggregated rows, one class per row.
    if {"class_name", "ratio"}.issubset(set(rows[0].keys())):
        class_ratio: dict[str, float] = {}
        for r in rows:
            if "clip_id" in r and r.get("clip_id") and r["clip_id"] != clip_id:
                continue
            class_ratio[r["class_name"]] = to_float(r["ratio"])
        if class_ratio:
            return {"clip_id": clip_id, "class_ratio": class_ratio, "frame_sampling_rule": "unknown"}

    # Pattern 2: frame-wise rows with frame_id,class_name,ratio.
    if {"frame_id", "class_name", "ratio"}.issubset(set(rows[0].keys())):
        by_frame: dict[str, dict[str, float]] = {}
        for r in rows:
            if "clip_id" in r and r.get("clip_id") and r["clip_id"] != clip_id:
                continue
            fid = str(r["frame_id"])
            by_frame.setdefault(fid, {})[r["class_name"]] = to_float(r["ratio"])
        if by_frame:
            frame_stats = [{"class_ratio": cr} for cr in by_frame.values()]
            return {
                "clip_id": clip_id,
                "frame_stats": frame_stats,
                "sampled_frame_count": len(frame_stats),
                "frame_sampling_rule": "unknown",
            }

    return None


def find_summary_for_clip(cityseg_dir: Path, clip_id: str, index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if clip_id in index:
        return dict(index[clip_id])

    json_candidates = [
        cityseg_dir / f"{clip_id}.summary.json",
        cityseg_dir / f"{clip_id}_summary.json",
        cityseg_dir / f"{clip_id}.json",
    ]
    for p in json_candidates:
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                obj.setdefault("clip_id", clip_id)
                return obj

    csv_candidates = [
        cityseg_dir / f"{clip_id}.summary.csv",
        cityseg_dir / f"{clip_id}_summary.csv",
        cityseg_dir / f"{clip_id}.csv",
    ]
    for p in csv_candidates:
        if p.exists():
            obj = load_csv_summary(p, clip_id)
            if obj is not None:
                return obj

    # TODO: Support direct HDF5 parsing and aggregation from frame masks.
    h5_candidates = [cityseg_dir / f"{clip_id}.h5", cityseg_dir / f"{clip_id}.hdf5"]
    for p in h5_candidates:
        if p.exists():
            print(f"TODO: HDF5 aggregation not implemented yet for {p}")
            return None

    return None


def existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FEATURE_FIELDS})


def clip_video_info(clip_row: dict[str, str]) -> tuple[str | None, str | None]:
    video_asset_id = clip_row.get("video_asset_id") or None
    video_asset = clip_row.get("video_asset") or None
    return video_asset_id, video_asset


def main() -> None:
    args = parse_args()
    clips = load_clips(args.clips)
    class_map = load_json_or_yaml(args.class_map)

    aliases = {str(k).strip().lower(): str(v).strip().lower() for k, v in class_map.get("aliases", {}).items()}
    groups_raw = class_map.get("groups", {})
    groups: dict[str, list[str]] = {}
    if isinstance(groups_raw, dict):
        for k, v in groups_raw.items():
            if isinstance(v, list):
                groups[str(k)] = [str(x) for x in v]

    class_map_version = str(class_map.get("version", "v1"))
    taxonomy = str(class_map.get("dataset_taxonomy", "Cityscapes"))

    cityseg_index = load_precomputed_index(args.cityseg_dir)
    now_iso = datetime.now(timezone.utc).isoformat()

    generated_rows: list[dict[str, str]] = []
    missing_count = 0

    for clip in clips:
        clip_id = clip.get("clip_id", "")
        if not clip_id:
            continue

        summary = find_summary_for_clip(args.cityseg_dir, clip_id, cityseg_index)
        if summary is None:
            missing_count += 1
            msg = f"No CitySeg summary found for clip_id={clip_id}"
            if args.skip_missing:
                continue
            raise FileNotFoundError(msg)

        # Accept either direct class_ratio or per-frame summaries.
        frame_stats = summary.get("frame_stats") if isinstance(summary.get("frame_stats"), list) else []
        temporal_stats: dict[str, dict[str, float]] = {}

        class_ratio_raw = summary.get("class_ratio")
        if isinstance(class_ratio_raw, dict):
            class_ratio = merge_class_ratio(class_ratio_raw, aliases)
        else:
            class_ratio, temporal_stats = aggregate_frame_stats(frame_stats, aliases)

        if not class_ratio:
            raise ValueError(f"CitySeg summary for {clip_id} missing usable class_ratio/frame_stats")

        grouped = summary.get("grouped_categories")
        if not isinstance(grouped, dict):
            grouped = compute_grouped_categories(class_ratio, groups, aliases)

        sampled_frame_count = int(summary.get("sampled_frame_count") or max(len(frame_stats), 1))
        frame_sampling_rule = str(summary.get("frame_sampling_rule") or "unknown")
        dominant = summary.get("dominant_classes")
        if not isinstance(dominant, list):
            dominant = top_k_classes(class_ratio, args.top_k)

        feature_payload: dict[str, Any] = {
            "class_ratio": class_ratio,
            "grouped_categories": grouped,
            "sampled_frame_count": sampled_frame_count,
            "frame_sampling_rule": frame_sampling_rule,
            "dominant_classes": [str(x) for x in dominant],
        }
        if temporal_stats:
            feature_payload["temporal_stats"] = temporal_stats

        video_asset_id, video_asset = clip_video_info(clip)

        provenance = {
            "tool": "CitySeg",
            "tool_repository": "https://github.com/MitchellAcoustics/cityseg",
            "tool_version": summary.get("tool_version", "unknown"),
            "segmentation_model": summary.get("segmentation_model", "OneFormer"),
            "model_checkpoint": summary.get("model_checkpoint"),
            "dataset_id": args.dataset_id,
            "dataset_taxonomy": summary.get("dataset_taxonomy", taxonomy),
            "class_map_version": summary.get("class_map_version", class_map_version),
            "input_video_asset_id": video_asset_id,
            "input_video_path": video_asset,
            "clip_id": clip_id,
            "frame_sampling_rule": frame_sampling_rule,
            "preprocessing": summary.get(
                "preprocessing",
                {"resize": None, "fps_used": None, "projection": None},
            ),
            "generated_by_script": "scripts/build_cityseg_features.py",
            "generated_at": now_iso,
            "notes": summary.get("notes", ""),
        }

        feature_id = str(summary.get("feature_id") or f"cityseg_{clip_id}_{class_map_version}")
        feature_path = str(summary.get("feature_path") or "")

        generated_rows.append(
            {
                "feature_id": feature_id,
                "dataset_id": args.dataset_id,
                "clip_id": clip_id,
                "asset_id": video_asset_id or "",
                "modality": "visual",
                "feature_type": "visual_semantic_summary",
                "feature_name": "CitySeg semantic class summary",
                "source_modality": "visual",
                "value_format": "json" if not feature_path else "path",
                "extractor_name": "CitySeg",
                "extractor_version": str(provenance.get("tool_version", "unknown")),
                "provenance_json": json.dumps(provenance, ensure_ascii=True, separators=(",", ":")),
                "feature_storage_path": feature_path,
                "feature_path": feature_path,
                "feature_file_type": Path(feature_path).suffix.lstrip(".") if feature_path else "json",
                "feature_value_json": json.dumps(feature_payload, ensure_ascii=True, separators=(",", ":")),
                "feature_dimension": "",
                "feature_shape": "object",
                "feature_format": "json" if not feature_path else "path",
                "embedding_dim": "",
                "dtype": "",
                "model_name": str(provenance.get("segmentation_model", "OneFormer")),
                "model_version": str(provenance.get("tool_version", "unknown")),
                "model_checkpoint": str(provenance.get("model_checkpoint") or ""),
                "input_asset_id": video_asset_id or "",
                "input_asset": video_asset or "",
                "input_time_window": "",
                "sampling_rate_or_fps": frame_sampling_rule,
                "code_reference": "scripts/build_cityseg_features.py",
                "created_by": "MOSAIQ",
                "date_created": now_iso,
                "frame_time_s": "",
                "frame_index": "",
                "pooling": "",
                "language": "",
                "provenance_notes": str(summary.get("notes", "")),
                "notes": str(summary.get("notes", "")),
            }
        )

    base_rows = existing_rows(args.output) if args.mode == "append" else []
    kept = [r for r in base_rows if r.get("feature_type") != "visual_semantic_summary"]

    # Replace by feature_id if already present among kept.
    existing_ids = {r.get("feature_id") for r in kept}
    for r in generated_rows:
        if r["feature_id"] in existing_ids:
            kept = [x for x in kept if x.get("feature_id") != r["feature_id"]]
        kept.append(r)

    write_rows(args.output, kept)
    print(f"Wrote {len(generated_rows)} visual_semantic_summary rows to {args.output}")
    if missing_count:
        print(f"Missing summaries for {missing_count} clips")


if __name__ == "__main__":
    main()

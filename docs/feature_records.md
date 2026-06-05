# FeatureRecords in MOSAIQ

## What is a FeatureRecord
A FeatureRecord is an optional derived-feature row linked to a benchmark clip by `clip_id`.
Each row describes one derived descriptor (or descriptor bundle) together with provenance metadata.

## Why FeatureRecords are separate from `clips.csv`
`clips.csv` stores core clip metadata and benchmark targets.
Derived features are stored in `features.csv` so MOSAIQ can:
- add new feature families without changing clip-level core tables;
- keep extraction pipelines modular and reproducible;
- compare audio-only, visual-only, and multimodal baselines consistently.

## How `feature_id` and `clip_id` work
- `feature_id` uniquely identifies a single FeatureRecord row.
- `clip_id` points to the clip unit of analysis in `clips.csv`.
- Multiple FeatureRecords can reference the same `clip_id` (e.g., CLIP + CitySeg).
- Psychoacoustic indicators are currently kept in clip-level/acoustic metadata when available, rather than represented as FeatureRecords.

## Representing CLIP embeddings
Use:
- `feature_type=visual_clip_embedding`
- `source_modality=visual`
- `value_format=path` (recommended) or `vector/array`
- `feature_path` for external embedding files
- `embedding_dim`, `dtype`, `model_name`, `model_version`, `frame_time_s`, `frame_index`, `pooling` when applicable.

## Representing CitySeg semantic summaries
Use:
- `feature_type=visual_semantic_summary`
- `source_modality=visual`
- `value_format=json`
- `feature_value_json` for clip-level summary stats such as class ratios and grouped category ratios.

Store only clip-level summaries in `features.csv`.
Do not store full segmentation masks directly in `features.csv`; keep large assets external and reference by `feature_path` and provenance.

## Provenance JSON guidance
`provenance_json` should capture enough information to reproduce feature extraction.
Typical fields include tool/model identifiers, input asset IDs, sampling/aggregation rules, preprocessing, script path/version, and creation date.

CLIP example:

```json
{
  "tool": "open_clip",
  "model_name": "ViT-B-32",
  "model_version": "laion2b_s34b_b79k",
  "input_asset_id": "example_video_asset",
  "frame_sampling_rule": "center_frame",
  "preprocessing": "resize_and_normalize_default_clip_preprocess",
  "script": "scripts/extract_clip_embeddings.py",
  "script_version": "placeholder",
  "created_by": "MOSAIQ",
  "created_date": "YYYY-MM-DD"
}
```

CitySeg example:

```json
{
  "tool": "CitySeg",
  "model_name": "placeholder",
  "model_version": "placeholder",
  "input_asset_id": "example_video_asset",
  "frame_sampling_rule": "all_frames_or_sampled_frames",
  "aggregation_rule": "mean_class_ratio_over_clip",
  "class_map": "cityseg_default_classes",
  "script": "placeholder",
  "created_date": "YYYY-MM-DD"
}
```

## Current status in this release
Currently provided:
- shared FeatureRecord schema;
- dataset placeholder `features.csv` resources with visual example rows;
- lightweight validation helper script.

Placeholder/future extension areas:
- full CLIP embedding extraction assets;
- full CitySeg HDF5 aggregation pipelines;
- generated soundscape caption baselines, after the caption task is formally included;
- behavioural/eye-tracking derived descriptors.

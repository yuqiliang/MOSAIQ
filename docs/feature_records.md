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

## How identifiers work
- `feature_id` uniquely identifies a single FeatureRecord row.
- `dataset_id` identifies the source dataset.
- `clip_id` points to the clip unit of analysis in `clips.csv`.
- `asset_id` / `input_asset_id` identify the media asset used to create the feature when available.
- `preprocessing_id` can point to a preprocessing record that explains how the feature input was created.
- Multiple FeatureRecords can reference the same `clip_id` (e.g., PANNs + CLIP + CitySeg).
- Psychoacoustic indicators are currently kept in clip-level/acoustic metadata when available, rather than represented as FeatureRecords.

## Core fields
FeatureRecords use a flexible schema in `shared_schemas/features.schema.yaml`.
The important fields are:

- identity: `feature_id`, `dataset_id`, `clip_id`, `asset_id`
- feature description: `modality`, `feature_type`, `feature_name`
- extractor provenance: `extractor_name`, `extractor_version`, `model_name`, `model_checkpoint`
- input reference: `input_asset`, `input_time_window`, `sampling_rate_or_fps`
- storage reference: `feature_format`, `feature_storage_path`, `feature_file_type`, `feature_value_json`
- reproducibility: `preprocessing_id`, `code_reference`, `created_by`, `date_created`, `provenance_json`

The older fields `source_modality`, `value_format`, `feature_path`,
`embedding_dim`, and `dtype` remain for compatibility with existing scripts.

## Representing PANNs audio embeddings
Use:
- `feature_type=audio_embedding`
- `modality=audio`
- `source_modality=audio`
- `feature_format=path` / `value_format=path` when embeddings are stored externally
- `feature_storage_path` / `feature_path` for external embedding files
- `feature_dimension`, `feature_shape`, `embedding_dim`, `dtype`, `model_name`, `model_version`, `input_asset_id`, and `pooling` when applicable.

For PANNs, `model_name` should identify the model family and architecture, for example `PANNs-Cnn14`.
Store generated arrays outside `features.csv`; use `feature_value_json` only for compact metadata such as `sample_rate_hz`, pooling rule, and placeholder status.

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

PANNs example:

```json
{
  "tool": "PANNs",
  "tool_package": "panns-inference",
  "model_name": "PANNs-Cnn14",
  "model_version": "placeholder_or_checkpoint_path",
  "input_asset_id": "example_audio_asset",
  "sample_rate_hz": 32000,
  "pooling": "clipwise",
  "preprocessing": "mono_resample_to_32000hz",
  "script": "scripts/build_panns_features.py",
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
- dataset placeholder `features.csv` resources with audio and visual example rows;
- lightweight validation helper script.
- an ISD placeholder behavioural-attention row showing how future gaze-on-class
  descriptors can be documented without claiming that eye-tracking data have
  already been extracted.

Placeholder/future extension areas:
- full PANNs audio embedding extraction assets;
- full CLIP embedding extraction assets;
- full CitySeg HDF5 aggregation pipelines;
- generated soundscape caption baselines, after the caption task is formally included;
- behavioural/eye-tracking derived descriptors.

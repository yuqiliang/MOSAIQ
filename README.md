# MOSAIQ — Multimodal Open Soundscape AI Quality-benchmark

MOSAIQ is a standardised multimodal benchmark for soundscape AI research,
integrating audio, visual, and perceptual rating data from multiple source
datasets (ISD, ARAUS, …) under a unified schema. This repository hosts the
MOSAIQ data schema, validation tooling, build scripts, and (in later
phases) baseline models and evaluation pipelines.

## Current contributions

The current MOSAIQ implementation contributes a schema-level foundation for
future multimodal soundscape benchmark construction. It should be understood as
a validated data and harmonisation reference implementation, not yet as a
completed model benchmark with fixed splits and baseline results.

1. **Dataset-level catalogue for heterogeneous soundscape datasets**
   `catalogue/datasets.csv` indexes 20 soundscape and affective
   audio/visual datasets with comparable metadata about scenario, scale,
   modality availability, perceptual framework, access, licence, rating scale
   information, known limitations, and provenance.

2. **Executable Frictionless Data Package implementation**
   MOSAIQ represents the catalogue and dataset packages using Frictionless
   schemas, so field types, required values, enumerations, value ranges, and
   foreign-key relationships can be checked automatically rather than described
   only in prose.

3. **Dataset-specific MOSAIQ packages**
   The repository currently includes package implementations for ISD, ARAUS,
   SATP, and DeLTA. These packages organise source datasets into validated
   clip-level, response-level, source-file, feature, rating, and preprocessing
   resources where available.

4. **Conservative schema-level harmonisation**
   MOSAIQ maps heterogeneous source records into a shared representation with
   stable identifiers, canonical ISO 12913 PAQ semantics, explicit missingness,
   provenance, and reviewable mapping tables. This is structural and semantic
   harmonisation; it does not claim statistical equivalence across datasets.

5. **Original-versus-harmonised rating representation**
   Source ratings are not overwritten. MOSAIQ can preserve original rating
   values and scales while documenting derived harmonised values through
   `ratings.csv` and `preprocessing.csv`. For SATP, for example, original
   0-100 PAQ values are retained and MOSAIQ-compatible 1-5 values are derived
   with documented transformations.

6. **Extensible FeatureRecord layer**
   Derived descriptors such as PANNs audio embeddings, CLIP visual embeddings,
   CitySeg semantic summaries, and future gaze/attention descriptors are
   represented as optional FeatureRecords linked to clips, assets,
   preprocessing records, extractor metadata, storage paths, and provenance.

7. **Validation and reproducibility tooling**
   The repository provides Frictionless validation commands, MOSAIQ-specific
   linkage checks, FeatureRecord checks, schema-harmonisation validation, and
   build scripts for regenerating curated tables from source data.

### Current scope boundaries

MOSAIQ currently prepares datasets for benchmark construction, but it does not
yet provide a full MOSAIQ-v1 benchmark release. The current implementation does
not perform statistical harmonisation, distribution matching, domain
adaptation, z-normalisation with train-only statistics, imputation,
cross-framework label mapping, fixed train/validation/test split generation,
or baseline model evaluation. Those steps belong to later
benchmark/model-training workflows.


## Repository structure

```
MOSAIQ/
├── README.md
├── pyproject.toml
├── uv.lock
├── datacatalog.yaml             
│
├── catalogue/                   
│   ├── datapackage.yaml
│   ├── datasets.csv
│   └── datasets_catalogue.json   
│
├── datasets/                    
│   ├── ISD/
│   │   ├── datapackage.yaml
│   │   ├── schemas/
│   │   │   ├── clips.schema.yaml
│   │   │   ├── features.schema.yaml
│   │   │   └── responses.schema.yaml
│   │   └── data/
│   │       ├── clips.csv
│   │       ├── features.csv
│   │       └── responses.csv
│   ├── ARAUS/
│   │   ├── datapackage.yaml
│   │   ├── SCHEMA_NOTES.md
│   │   ├── schemas/
│   │   │   ├── clips.schema.yaml
│   │   │   └── responses.schema.yaml
│   │   └── data/
│   │       ├── clips.csv
│   │       └── responses.csv
│   ├── SATP/
│   │   ├── datapackage.yaml
│   │   ├── SCHEMA_NOTES.md
│   │   ├── schemas/
│   │   └── data/
│   │       ├── clips.csv
│   │       ├── responses.csv
│   │       ├── ratings.csv
│   │       ├── preprocessing.csv
│   │       └── features.csv
│   └── DeLTA/
│       ├── datapackage.yaml
│       ├── SCHEMA_NOTES.md
│       ├── schemas/
│       └── data/
│
├── shared_schemas/               
│   ├── datasets.schema.yaml
│   ├── features.schema.yaml
│   ├── preprocessing.schema.yaml
│   └── ratings.schema.yaml
│
├── config/
│   └── cityseg_class_map.yaml
│
├── scripts/
│   ├── build_isd.py
│   ├── build_araus.py
│   ├── build_satp.py
│   ├── build_delta.py
│   ├── build_panns_features.py
│   ├── build_clip_features.py
│   ├── build_cityseg_features.py
│   ├── check_feature_records.py
│   ├── feature_fields.py
│   ├── validate_in_python.py
│   ├── validate_mosaiq.py
│   └── validate_schema_harmonisation.py
│
└── notebooks/
    └── 01_explore_isd.ipynb
```

## Quick start

This project uses [uv](https://github.com/astral-sh/uv) for environment and
dependency management.

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Sync the environment

From the repository root:

```bash
uv sync
```

This creates a `.venv/` in the project directory and installs all
dependencies pinned in `uv.lock`.

### 3. Validate the data package

```bash
uv run frictionless validate catalogue/datapackage.yaml
uv run frictionless validate datasets/ISD/datapackage.yaml --trusted
uv run frictionless validate datasets/ARAUS/datapackage.yaml --trusted
uv run frictionless validate datasets/SATP/datapackage.yaml --trusted
uv run frictionless validate datasets/DeLTA/datapackage.yaml
```

Expected output: catalogue resources (`datasets`) and dataset package
resources (`clips`, `responses`, optional `ratings`, `preprocessing`,
`features`) all reporting `VALID`. (`--trusted` is used when a dataset package
references shared schemas through parent-relative paths.)

For MOSAIQ-specific linkage checks:

```bash
uv run python scripts/validate_mosaiq.py --dataset-dir datasets/ISD --skip-file-check
uv run python scripts/validate_mosaiq.py --dataset-dir datasets/ARAUS --skip-file-check
uv run python scripts/validate_mosaiq.py --dataset-dir datasets/SATP --skip-file-check
```

### Original and harmonised ratings

MOSAIQ does not destructively transform source ratings. Original values remain
available, and harmonised values are stored as derived fields or documented
through preprocessing records.

For SATP:
- the original PAQ values are preserved as `*_raw_0_100` columns in
  `datasets/SATP/data/responses.csv`;
- MOSAIQ-compatible 1-5 PAQ values are derived with `1 + 4 * raw / 100`;
- the transformation is documented in `datasets/SATP/data/preprocessing.csv`;
- `datasets/SATP/data/ratings.csv` provides a small long-form rating example
  with `rating_value_original`, original scale metadata, and
  `rating_value_harmonised`.

Z-normalisation is not applied in this schema revision. It is deferred to
future benchmark/model-training workflows where train-only statistics can be
used without leakage.

### Derived FeatureRecords

MOSAIQ supports optional derived FeatureRecords linked by `clip_id` in
`datasets/<dataset>/data/features.csv`.

Supported examples include:
- PANNs audio embeddings
- CLIP visual embeddings
- CitySeg semantic summaries
- gaze-on-class / behavioural attention descriptors as a future extension

In this release, MOSAIQ defines the shared FeatureRecord schema for visual
and audio-derived features, semantic summaries, and placeholder behavioural
attention records. Psychoacoustic indicators remain in clip-level/acoustic
metadata when available, but the schema can represent future psychoacoustic
FeatureRecords if needed. Caption features are a future extension and are not
included in the current schema.

### 4. Build PANNs audio embedding features (optional)

PANNs audio embeddings are stored as FeatureRecords with:
- `feature_type=audio_embedding`
- `source_modality=audio`
- `model_name=PANNs-Cnn14`
- `value_format=path` when embeddings are stored externally

The repository includes placeholder PANNs FeatureRecords only. It does not
generate real embeddings or add large `.npy` files by default.

Example command:

```bash
uv run python scripts/build_panns_features.py \
  --dataset-dir datasets/ISD \
  --audio-root /path/to/audio \
  --model-name PANNs-Cnn14 \
  --storage npy \
  --mode append \
  --skip-missing-audio
```

### 5. Build CLIP visual embedding features (optional)

Input (`clips.csv` must contain these columns):
- `clip_id`: unique clip identifier used to link feature records.
- `dataset_id`: dataset namespace used in `feature_id`.
- `video_asset` and `video_asset_id`: source video linkage; script will resolve to real video files.
- `start_s`, `end_s`: temporal segment boundaries used for frame sampling.

Output:
- `datasets/<dataset>/data/features.csv` with columns:
  `feature_id, dataset_id, clip_id, asset_id, modality, feature_type,
  feature_name, source_modality, value_format, extractor_name,
  extractor_version, model_name, model_version, model_checkpoint,
  input_asset_id, input_asset, input_time_window, sampling_rate_or_fps,
  feature_dimension, feature_shape, feature_format, feature_storage_path,
  feature_path, feature_file_type, feature_value_json, provenance_json,
  checksum, preprocessing_id, code_reference, created_by, date_created,
  frame_time_s, frame_index, pooling, embedding_dim, dtype, language,
  provenance_notes, notes`
- If `--storage npy` (default): one `.npy` file per clip under:
  `datasets/<dataset>/data/features/clip_embedding/`
- If `--storage base64`: embedding payload is stored in `feature_value_json`.

Sampling and feature definition:
- `feature_type` is always `visual_clip_embedding`.
- `source_modality` is `visual`.
- Default frame rule is center frame:
  `t = (start_s + end_s) / 2`.
- Pooling/frame metadata are stored in `feature_value_json`.

Mandatory provenance fields written to `provenance_json`:
- `model`, `version`, `library_versions`, `frame_sampling_rule`,
  `preprocess`, `device`, `generated_at`, `script_version`.

How to use:

1. Install runtime dependencies (one-time):

```bash
uv add open-clip-torch torch torchvision pillow opencv-python-headless
```

2. Build features for one dataset (recommended `.npy` storage):

```bash
uv run python scripts/build_clip_features.py \
  --dataset-dir datasets/ISD \
  --video-root /path/to/videos \
  --model-name ViT-B/32 \
  --pretrained openai \
  --storage npy \
  --mode append
```

3. Validate package integrity after extraction:

```bash
uv run frictionless validate datasets/ISD/datapackage.yaml
```

Useful options:
- `--dataset-dir`: target dataset root (`datasets/ISD` or `datasets/ARAUS`).
- `--video-root`: root directory to resolve `video_asset`/`video_asset_id`.
- `--storage`: `npy` or `base64`.
- `--dtype`: `float16`, `float32`, or `float64`.
- `--device`: `auto`, `cpu`, or `cuda`.
- `--limit`: process only first N clips for smoke tests.
- `--skip-missing-video`: skip unresolved clips instead of failing.
- `--mode`: `append` or `overwrite`.

### 6. CitySeg semantic summaries (optional)

CitySeg summaries are optional visual semantic FeatureRecords linked by
`clip_id`.

- CLIP embeddings provide scalable visual baseline features.
- CitySeg summaries provide interpretable semantic descriptors such as
  road, vegetation, sky, building, vehicle, and person proportions.
- These features support PAQ item prediction, ISO-coordinate prediction,
  and future gaze-on-class analysis.

Feature conventions for CitySeg:
- `feature_type=visual_semantic_summary`
- `source_modality=visual`
- `value_format=json` (or `path` for external large summaries)
- Full segmentation masks/HDF5 are not stored in `features.csv`; only clip
  summaries are stored directly, with raw assets referenced by path/provenance.

Example command:

```bash
uv run python scripts/build_cityseg_features.py \
  --clips datasets/ISD/data/clips.csv \
  --cityseg-dir /path/to/cityseg_outputs \
  --output datasets/ISD/data/features.csv \
  --dataset-id ISD \
  --mode append
```

Validation for features:

```bash
uv run python scripts/validate_mosaiq.py --dataset-dir datasets/ISD
```

### 7. Regenerate data from source

If you have access to the original ISD `ISD_v1_0_Data.csv`, you can
regenerate the derived CSVs from scratch:

```bash
uv run python scripts/build_datasets_csv.py     # rebuilds data/catalogue/datasets.csv
uv run python scripts/build_isd.py              # rebuilds data/ISD/clips.csv + responses.csv
uv run python scripts/build_satp.py             # rebuilds SATP clips, responses, ratings examples, preprocessing
uv run python scripts/build_delta.py            # rebuilds data/DeLTA/clips.csv + responses.csv
```

## Schema design philosophy

MOSAIQ separates the data into three layers, each with its own schema:

1. **Dataset-level catalogue** (`catalogue/datasets.csv`) — one row per
   source dataset, capturing scale, modalities, recording specifications,
   perceptual framework, rating scale information, access conditions,
   limitations, schema version, and provenance.

2. **Clip-level metadata** (`datasets/<dataset>/data/clips.csv`) — one row per clip
   with aggregated PAQ ratings, derived ISO Pleasant / Eventful coordinates,
   and available acoustic or psychoacoustic measurements.

3. **Response-level metadata** (`datasets/<dataset>/data/responses.csv`) — one row
   per individual participant assessment, linked to clips via `clip_id`.

4. **Rating and preprocessing records** (`ratings.csv`, `preprocessing.csv`) —
   optional long-form examples and transformation records that explain how
   harmonised fields were derived while preserving original values.

5. **FeatureRecords** (`features.csv`) — optional derived descriptors and
   embeddings linked to clips/assets through stable IDs and provenance.

Schemas are formally specified using the [Frictionless Data Package](https://specs.frictionlessdata.io/)
standard, which supports type checks, value-range constraints, enumerations,
and foreign-key relationships across resources.

An additional schema-level harmonisation layer is documented in
[`docs/schema_level_harmonisation.md`](docs/schema_level_harmonisation.md).
This layer prepares ISD, ARAUS, and SATP examples for later benchmark
construction using a shared structure and conservative ISO 12913 semantics; it
does not claim that the datasets are statistically or fully harmonised. RDSS or
similar working storage can later hold large media and feature arrays, while
the archived data repository release can preserve validated metadata,
checksums, and resolvable asset references.

## Development

### Add a dependency

```bash
uv add <package-name>
uv add --dev <package-name>     # development-only (e.g. jupyter, pytest)
```

### Run a Python script

```bash
uv run python <script.py>
```

### Open Jupyter

```bash
uv add --dev jupyter ipykernel
uv run jupyter lab
```

## Citation

If you use MOSAIQ in your research, please cite:

```bibtex
@misc{mosaiq2026,
  author    = {Liang, Yuqi and Mitchell, Andrew and Kang, Jian and Aletta, Francesco},
  title     = {MOSAIQ: Multimodal Open Soundscape AI Quality-benchmark},
  year      = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/yuqiliang/MOSAIQ}}
}
```

## Team

- **Yuqi Liang**  — UCL Institute for Environmental Design and Engineering
- **Francesco Aletta**  — UCL Institute for Environmental Design and Engineering
- **Jian Kang** — UCL Institute for Environmental Design and Engineering
- **Andrew Mitchell** — UCL Bartlett School of Sustainable Construction

## Licence

- Schemas, code, and documentation: MIT
- Data: per-source-dataset licences (see `licence_spdx` field in each `datasets.csv` row)

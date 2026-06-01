# MOSAIQ — Multimodal Open Soundscape AI Quality-benchmark

MOSAIQ is a standardised multimodal benchmark for soundscape AI research,
integrating audio, visual, and perceptual rating data from multiple source
datasets (ISD, ARAUS, …) under a unified schema. This repository hosts the
MOSAIQ data schema, validation tooling, build scripts, and (in later
phases) baseline models and evaluation pipelines.


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
│   └── ARAUS/
│       ├── datapackage.yaml
│       ├── SCHEMA_NOTES.md
│       ├── schemas/
│       │   ├── clips.schema.yaml
│       │   ├── features.schema.yaml
│       │   └── responses.schema.yaml
│       └── data/
│           ├── clips.csv
│           ├── features.csv
│           └── responses.csv
│
├── shared_schemas/               
│   ├── datasets.schema.yaml
│   └── features.schema.yaml
│
├── config/
│   └── cityseg_class_map.yaml
│
├── scripts/
│   ├── build_isd.py
│   ├── build_clip_features.py
│   ├── build_cityseg_features.py
│   ├── validate_in_python.py
│   └── validate_mosaiq.py
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
```

Expected output: catalogue resources (`datasets`) and dataset package
resources (`clips`, `responses`, optional `features`) all reporting `VALID`.
(`--trusted` is used for dataset packages because the shared feature schema is
referenced via a parent-relative path.)

### Derived FeatureRecords

MOSAIQ supports optional derived FeatureRecords linked by `clip_id` in
`datasets/<dataset>/data/features.csv`.

Supported examples include:
- CLIP visual embeddings
- CitySeg semantic summaries
- soundscape captions

In this release, MOSAIQ defines the shared FeatureRecord schema and placeholder
resources. Full extraction pipelines and benchmark baselines for these derived
features will be provided in later MOSAIQ releases.

### 4. Build CLIP visual embedding features (optional)

Input (`clips.csv` must contain these columns):
- `clip_id`: unique clip identifier used to link feature records.
- `dataset_id`: dataset namespace used in `feature_id`.
- `video_asset` and `video_asset_id`: source video linkage; script will resolve to real video files.
- `start_s`, `end_s`: temporal segment boundaries used for frame sampling.

Output:
- `datasets/<dataset>/data/features.csv` with columns:
  `feature_id, clip_id, dataset_id, feature_type, feature_family, value_format, feature_path, feature_json, provenance_json, created_at, notes`
- If `--storage npy` (default): one `.npy` file per clip under:
  `datasets/<dataset>/data/features/clip_embedding/`
- If `--storage base64`: embedding payload is stored in `feature_json`.

Sampling and feature definition:
- `feature_type` is always `visual_clip_embedding`.
- `source_modality` is `visual`.
- Default frame rule is center frame:
  `t = (start_s + end_s) / 2`.
- Pooling/frame metadata are stored in `feature_json`.

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

### 5. CitySeg semantic summaries (optional)

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

### 6. Regenerate data from source

If you have access to the original ISD `ISD_v1_0_Data.csv`, you can
regenerate the derived CSVs from scratch:

```bash
uv run python scripts/build_datasets_csv.py     # rebuilds data/catalogue/datasets.csv
uv run python scripts/regen_and_flatten.py      # rebuilds data/ISD/clips.csv + responses.csv
```

## Schema design philosophy

MOSAIQ separates the data into three layers, each with its own schema:

1. **Dataset-level catalogue** (`data/catalogue/datasets.csv`) — one row per
   source dataset, capturing scale, modalities, recording specifications,
   perceptual framework, and access conditions.

2. **Clip-level metadata** (`data/<dataset>/clips.csv`) — one row per clip
   with aggregated PAQ ratings, derived ISO Pleasant / Eventful coordinates,
   and primary psychoacoustic features.

3. **Response-level metadata** (`data/<dataset>/responses.csv`) — one row
   per individual participant assessment, linked to clips via `clip_id`.

Schemas are formally specified using the [Frictionless Data Package](https://specs.frictionlessdata.io/)
standard, which supports type checks, value-range constraints, enumerations,
and foreign-key relationships across resources.

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

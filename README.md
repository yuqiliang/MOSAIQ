# MOSAIQ — Multimodal Open Soundscape AI Quality-benchmark

Frictionless data package for the MOSAIQ benchmark, integrating multiple
soundscape datasets (ISD, ARAUS, …) under a unified schema.

## Repository structure

```
mosaiq/
├── datapackage.yaml              # Frictionless package manifest
├── schemas/                      # Schema definitions (rules)
│   ├── datasets.schema.yaml
│   ├── clips.schema.yaml
│   └── responses.schema.yaml
├── data/                         # Schema-conformant data (instances)
│   ├── _dataset_level/datasets.csv
│   └── ISD/
│       ├── clips.csv
│       └── responses.csv
├── build_datasets_csv.py         # Builds datasets.csv from nested JSON
├── regen_and_flatten.py          # Builds clips.csv + responses.csv from ISD CSV
├── validate_in_python.py         # Python API validation example
├── pyproject.toml                # Project config + dependencies (uv-managed)
├── uv.lock                       # Locked dependency versions
└── .python-version               # Pinned Python version
```

## Quick start

This project uses [uv](https://github.com/astral-sh/uv) for environment and
dependency management.

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Sync the environment

From the repo root:

```bash
uv sync
```

This creates a `.venv/` in the project directory and installs all
dependencies pinned in `uv.lock`.

### 3. Validate the data package

```bash
uv run frictionless validate datapackage.yaml
```

Expected output: three resources (`datasets`, `clips`, `responses`) all
reporting `VALID`.

### 4. Regenerate data from source

If you want to regenerate the CSVs from the original ISD data:

```bash
# Requires ISD_v1_0_Data.csv locally — update path inside the script
uv run python regen_and_flatten.py
uv run python build_datasets_csv.py
```

## Development

### Add a new dependency

```bash
uv add <package-name>
```

### Run a Python script in the environment

```bash
uv run python <script.py>
```

### Open a Jupyter notebook

```bash
uv run jupyter lab
```

## Schema design philosophy

MOSAIQ separates three layers:

1. **Dataset-level catalogue** (`datasets.csv`) — one row per source dataset,
   with scale, modalities, and access conditions.
2. **Clip-level metadata** (`clips.csv`) — one row per clip with aggregated
   PAQ ratings and primary psychoacoustic features.
3. **Response-level data** (`responses.csv`) — one row per individual
   participant assessment.

Schemas are formally specified using the [Frictionless Data Package](https://specs.frictionlessdata.io/)
standard, which supports type checks, value constraints, enumerations, and
foreign-key relationships across resources.

## License

- Schemas, code, and documentation: MIT
- Data: per-source-dataset licences (see `licence_spdx` field in `datasets.csv`)

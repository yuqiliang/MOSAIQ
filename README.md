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
│   └── ISD/
│       ├── datapackage.yaml
│       ├── schemas/
│       │   ├── clips.schema.yaml
│       │   └── responses.schema.yaml
│       └── data/
│           ├── clips.csv
│           └── responses.csv
│
├── shared_schemas/               
│   └── datasets.schema.yaml
│
├── scripts/
│   ├── build_isd.py
│   └── validate_in_python.py
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
uv run frictionless validate datapackage.yaml
```

Expected output: three resources (`datasets`, `clips`, `responses`) all
reporting `VALID`.

### 4. Regenerate data from source

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

# MOSAIQ Benchmark

This directory defines the experimental contract for MOSAIQ Benchmark v0.1.
It is deliberately separate from the dataset schemas: the schemas describe
what the source records contain, while the benchmark configuration specifies
which records, targets, splits, and metrics form a reproducible task.

## Current status

MOSAIQ Benchmark v0.1 is a **draft benchmark specification**. Seven clip- and
response-level tasks are materialised against the current ISD, ARAUS, SATP,
and DeLTA tables, split assignments version `0.1.0` have been released, and
the candidate freeze has a generated technical-validation report. The first
audio-free tabular baseline suite has also been executed with 17 experiments,
498 metric rows, and generated model cards. Step 7 adds five-seed stability,
2,000-sample cluster-bootstrap intervals, paired comparisons, ISD feature-
coverage sensitivity, and GPR interval calibration. Internal release
documentation, data cards, governance records, and a result-submission
contract are present. Tasks remain `draft` until external rights, usability,
archival DOI, and public-release gates are complete.

An experimental ISD audio track under `audio/` adds an official Zenodo source
registry, an audio manifest schema, full candidate-archive mapping/QC evidence,
an 820-clip frozen cohort, deterministic waveform descriptors, and executed
clip- and response-level Target Mean/Ridge references. Raw media remain outside
Git. Learned CNN, pretrained-encoder, fusion, missing-modality, and added-noise
comparisons remain pending.

## Layout

```text
benchmark/
├── README.md
├── tasks.yaml                  # benchmark and task registry
├── exclusions.yaml             # versioned record-level exclusions and reasons
├── release.yaml                # candidate freeze, tracks, assets, and licence policy
├── release_checklist.md        # internal and external publication gates
├── data_cards/                 # benchmark and source-track data cards
├── governance/                 # licence/consent registry and attribution
├── submissions/                # prediction format, schema, and template
├── schemas/
│   └── task.schema.yaml        # machine-readable task-config contract
├── configs/
│   ├── task_iso_paq.yaml
│   ├── task_iso_coordinates.yaml
│   ├── task_araus_appropriateness.yaml
│   ├── task_araus_pleasantness.yaml
│   ├── task_isd_individual_iso.yaml
│   ├── task_delta_annoyance.yaml
│   └── task_delta_sources.yaml
├── splits/
│   ├── isd_split.csv
│   ├── araus_split.csv
│   ├── satp_folds.csv
│   ├── delta_split.csv
│   ├── split_summary.csv
│   ├── split_checksums.sha256
│   └── README.md
├── manifests/
│   ├── *.csv                   # frozen eligible clip IDs per task and dataset
│   ├── manifest_checksums.sha256
│   └── README.md
├── validation/
│   ├── validation_report.md    # generated Step 4 report
│   ├── validation_summary.csv
│   ├── row_counts.csv
│   ├── task_eligibility.csv
│   ├── split_summary.csv
│   ├── exclusions.csv
│   ├── asset_coverage.csv
│   ├── feature_coverage.csv
│   ├── license_audit.csv
│   ├── source_checksums.sha256
│   ├── validation_checksums.sha256
│   └── README.md
├── baselines/
│   ├── README.md
│   └── baseline_config.yaml
├── audio/
│   ├── audio_manifest.schema.yaml
│   ├── configs/
│   ├── manifests/
│   ├── qc/
│   ├── cohort/
│   ├── features/
│   ├── results/
│   └── model_cards/
├── model_cards/
│   ├── README.md
│   └── *.md
├── robustness/
│   ├── robustness_config.yaml
│   ├── robustness_report.md
│   ├── *.csv
│   └── multiseed/
└── results/
    ├── baseline_results.csv
    ├── distribution_curves.csv
    ├── predictions/
    └── runs/
```

## v0.1 task scope

| Task | Datasets | Target | Type |
| --- | --- | --- | --- |
| `iso_paq_regression` | ISD, ARAUS, SATP | Eight mean ISO PAQ items | Multi-output regression |
| `iso_coordinate_regression` | ISD, ARAUS, SATP | Mean ISO Pleasantness and Eventfulness | Multi-output regression |
| `araus_appropriateness` | ARAUS | Mean appropriateness | Regression |
| `araus_pleasantness_regression` | ARAUS | Mean ISO Pleasantness | Regression |
| `isd_individual_iso_prediction` | ISD | Individual ISO Pleasantness and Eventfulness | Multi-output regression |
| `delta_annoyance` | DeLTA | Mean annoyance | Regression |
| `delta_source_multilabel` | DeLTA | 24 sound-source indicators | Multi-label classification |

The ISD response task inherits the released clip partition through `clip_id`.
Consequently, assessments of the same soundscape cannot cross train, dev, and
test boundaries. The v0.1 baseline suite is tabular and does not load audio.
The separate experimental audio track applies the same inheritance rule and
also prohibits one waveform SHA-256 from crossing partitions.

## Validate the specification

From the repository root:

```bash
uv run python scripts/validate_benchmark_tasks.py
```

The validator checks the registry and task files against
`schemas/task.schema.yaml`, verifies referenced data files and columns, applies
the declared eligibility filters, and reports the number of usable rows per
dataset. Released split files must match the version declared in each task
config.

Regenerate or validate the released assignments:

```bash
uv run python scripts/build_benchmark_splits.py
uv run python scripts/validate_benchmark_splits.py
```

Regenerate or verify the candidate dataset freeze and technical-validation
outputs:

```bash
uv run python scripts/build_benchmark_report.py
uv run python scripts/build_benchmark_report.py --check-only
uv run python scripts/run_tabular_baselines.py
uv run python scripts/build_model_cards.py
uv run python scripts/validate_tabular_baselines.py
uv run python scripts/run_robustness_evaluation.py
uv run python scripts/validate_robustness_evaluation.py
uv run python scripts/validate_submission.py benchmark/submissions/submission_template.csv --allow-empty
```

The report generator validates all four Frictionless packages, checks clip and
response integrity, freezes one manifest per task/dataset pair, audits target
eligibility, split coverage, exclusions, assets, features, and declared
licences, and writes checksums for both source inputs and generated outputs.

ISD and ARAUS are the v0.1 core tracks. SATP and DeLTA are extension tracks.
External source identifiers and archive members count as asset references, not
as locally materialised files. See `validation/validation_report.md` for the
current limitations and warnings.

The robustness evaluation resamples `clip_id` clusters, so repeated ISD
assessments of the same soundscape remain together. Its confidence intervals
describe the current test partitions and must not be interpreted as external
validation. See `robustness/robustness_report.md` for methods and findings.

## Status progression

1. `draft`: targets and protocols are defined, but released split assignments
   and/or baseline evidence are incomplete.
2. `ready`: split assignments exist, validate, and are versioned for public
   evaluation.
3. `deprecated`: retained for provenance but replaced by a newer task version.

The registry in `tasks.yaml` is the entry point for software and documentation.
Detailed methodological decisions belong in the individual files under
`configs/`.

The public submission contract is documented in `submissions/README.md`.
Official results must validate with `--require-complete` and must be accompanied
by a model card. Results from different cohorts or benchmark versions must not
be placed in one undifferentiated ranking.

## Known source-data exclusions

Two ISD rows contain `clip_id` values that differ from other rows only by a
trailing space, but their associated metadata are not consistent enough to
justify silently merging them. They are listed in `exclusions.yaml` and
excluded from the ISO tasks pending source review. The task validator checks
that every declared exclusion still refers to a real source row.

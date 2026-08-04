# Reproducing the MOSAIQ v0.1 benchmark candidate

## Scope

These instructions reproduce the checked no-audio tabular benchmark from the
files committed to this repository. They do not download or reconstruct raw
audio or video.

## Environment

Requirements:

- Python 3.12 or later;
- `uv`;
- a checkout at the release commit recorded in the eventual DOI deposit.

From the repository root:

```bash
uv sync --frozen
```

## Validate the source packages

```bash
uv run frictionless validate catalogue/datapackage.yaml
uv run frictionless validate datasets/ISD/datapackage.yaml --trusted
uv run frictionless validate datasets/ARAUS/datapackage.yaml --trusted
uv run frictionless validate datasets/SATP/datapackage.yaml
uv run frictionless validate datasets/DeLTA/datapackage.yaml
```

## Rebuild splits and the candidate freeze

```bash
uv run python scripts/build_benchmark_splits.py
uv run python scripts/validate_benchmark_splits.py
uv run python scripts/build_benchmark_report.py
uv run python scripts/build_benchmark_report.py --check-only
```

The rebuild must preserve `benchmark/splits/split_checksums.sha256`,
`benchmark/manifests/manifest_checksums.sha256`, and the generated validation
checksums.

## Reproduce models and robustness outputs

```bash
uv run python scripts/run_tabular_baselines.py
uv run python scripts/build_model_cards.py
uv run python scripts/validate_tabular_baselines.py
uv run python scripts/run_robustness_evaluation.py
uv run python scripts/validate_robustness_evaluation.py
```

Every run must record the task, feature cohort, split version, random seed,
dependency versions, predictions, and `audio_used=false`.

## Reproduce Paper 2 outputs

```bash
uv run python scripts/build_paper2_fixed_outputs.py
uv run python scripts/validate_paper2_fixed_outputs.py
```

Do not manually edit generated tables or figures. Numerical changes require a
new output version and regenerated checksums.

## Validate a benchmark submission

```bash
uv run python scripts/validate_submission.py path/to/predictions.csv
```

Use `--require-complete` for an official result. The validator checks the
submission schema, task/dataset manifest membership, target names, duplicate
predictions, and version consistency.

## Reconstructing from original source deposits

The current repository contains harmonised tables. A public archival release
must also include immutable citations and retrieval instructions for the exact
source deposits:

1. Download the cited source version from its DOI record.
2. Verify the source archive checksum recorded in the public RDR manifest.
3. Run the relevant `scripts/build_<dataset>.py` command with the source paths
   documented in that release's provenance record.
4. Compare the generated table checksums with the archived MOSAIQ checksums.

Source archives are intentionally not downloaded automatically because their
licences and access terms differ. The public release must provide exact
commands and checksums after the final rights review.

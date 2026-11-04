---
model_id: isd_clip_target_mean
task_id: iso_coordinate_regression
dataset_id: ISD
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# isd_clip_target_mean

## Model Summary

- **Task:** `iso_coordinate_regression` (multi_output_regression)
- **Dataset:** `ISD`
- **Estimator family:** `target_mean`
- **Feature set:** `none`
- **Predictors:** None
- **Targets:** `mean_ISOPleasant`, `mean_ISOEventful`
- **Parameters:** `{}`
- **Random seed:** `2026`
- **Audio used:** `false`

## Intended Use

This model establishes reproducible reference performance for MOSAIQ Paper 2
and validates the corresponding task, split, feature, prediction, and metric
interfaces. It is not intended for consequential decisions about individuals
or places.

## Data and Evaluation

- Training records: 1599
- Development records: 524
- Test records: 581
- Split protocol: `dataset_specific` version `0.1.0`
- Preprocessing is fitted on training records only.
- No classification threshold is used.

### Test Point Metrics

| Target | RMSE | MAE | R2 | Pearson r | Spearman rho |
| --- | --- | --- | --- | --- | --- |
| mean_ISOEventful | 0.2383 | 0.1828 | -0.0077 | NA | NA |
| mean_ISOPleasant | 0.2974 | 0.2385 | -0.0023 | NA | NA |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- The model ignores all predictors and represents an intentionally weak reference point.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment isd_clip_target_mean
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `iso_coordinate_regression__isd__isd_clip_target_mean__seed2026`
- Experiment SHA-256: `4c26b60f9cbef2eb41b8ac59a457462c7c7054cbbaa65a6f264a971571c604a7`
- Task config: `benchmark/configs/task_iso_coordinates.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/iso_coordinate_regression__isd__isd_clip_target_mean__seed2026.csv`

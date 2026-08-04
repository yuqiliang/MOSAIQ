---
model_id: delta_annoyance_target_mean
task_id: delta_annoyance
dataset_id: DeLTA
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# delta_annoyance_target_mean

## Model Summary

- **Task:** `delta_annoyance` (regression)
- **Dataset:** `DeLTA`
- **Estimator family:** `target_mean`
- **Feature set:** `none`
- **Predictors:** None
- **Targets:** `mean_annoyance`
- **Parameters:** `{}`
- **Random seed:** `2026`
- **Audio used:** `false`

## Intended Use

This model establishes reproducible reference performance for MOSAIQ Paper 2
and validates the corresponding task, split, feature, prediction, and metric
interfaces. It is not intended for consequential decisions about individuals
or places.

## Data and Evaluation

- Training records: 2012
- Development records: 441
- Test records: 437
- Split protocol: `fixed_train_dev_test` version `0.1.0`
- Preprocessing is fitted on training records only.
- No classification threshold is used.

### Test Point Metrics

| Target | RMSE | MAE | R2 | Pearson r | Spearman rho |
| --- | --- | --- | --- | --- | --- |
| mean_annoyance | 1.3516 | 1.1244 | -0.0006 | NA | NA |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- The model ignores all predictors and represents an intentionally weak reference point.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment delta_annoyance_target_mean
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `delta_annoyance__delta__delta_annoyance_target_mean__seed2026`
- Experiment SHA-256: `9303182fb978d9bce8648d9970eb1d7e574df03dc1c5bd84307afb9ad09916bb`
- Task config: `benchmark/configs/task_delta_annoyance.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/delta_annoyance__delta__delta_annoyance_target_mean__seed2026.csv`

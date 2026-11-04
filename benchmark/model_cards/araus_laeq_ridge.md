---
model_id: araus_laeq_ridge
task_id: araus_pleasantness_regression
dataset_id: ARAUS
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# araus_laeq_ridge

## Model Summary

- **Task:** `araus_pleasantness_regression` (regression)
- **Dataset:** `ARAUS`
- **Estimator family:** `ridge`
- **Feature set:** `laeq`
- **Predictors:** `LAeq_dBA`
- **Targets:** `mean_ISOPleasant`
- **Parameters:** `{"alpha": 1.0}`
- **Random seed:** `2026`
- **Audio used:** `false`

## Intended Use

This model establishes reproducible reference performance for MOSAIQ Paper 2
and validates the corresponding task, split, feature, prediction, and metric
interfaces. It is not intended for consequential decisions about individuals
or places.

## Data and Evaluation

- Training records: 17730
- Development records: 4440
- Test records: 48
- Split protocol: `fixed_train_dev_test` version `0.1.0`
- Preprocessing is fitted on training records only.
- No classification threshold is used.

### Test Point Metrics

| Target | RMSE | MAE | R2 | Pearson r | Spearman rho |
| --- | --- | --- | --- | --- | --- |
| mean_ISOPleasant | 0.2701 | 0.2224 | 0.2298 | 0.8139 | 0.7897 |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- The independent ARAUS test partition contains only 48 eligible clips.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment araus_laeq_ridge
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `araus_pleasantness_regression__araus__araus_laeq_ridge__seed2026`
- Experiment SHA-256: `90ff2c04ecfec0729dbc35486b6b5efee0793d6db32c6e357b35a8931148637d`
- Task config: `benchmark/configs/task_araus_pleasantness.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/araus_pleasantness_regression__araus__araus_laeq_ridge__seed2026.csv`

---
model_id: araus_psychoacoustic_ridge
task_id: araus_pleasantness_regression
dataset_id: ARAUS
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# araus_psychoacoustic_ridge

## Model Summary

- **Task:** `araus_pleasantness_regression` (regression)
- **Dataset:** `ARAUS`
- **Estimator family:** `ridge`
- **Feature set:** `shared6`
- **Predictors:** `LAeq_dBA`, `loudness_N_sone`, `sharpness_S_acum`, `roughness_R_asper`, `fluctuation_strength_F_vacil`, `tonality_T_tu`
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
| mean_ISOPleasant | 0.2762 | 0.2356 | 0.1952 | 0.7893 | 0.8101 |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- The independent ARAUS test partition contains only 48 eligible clips.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment araus_psychoacoustic_ridge
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `araus_pleasantness_regression__araus__araus_psychoacoustic_ridge__seed2026`
- Experiment SHA-256: `c938130800de8c90098925c06077174b41170c6c0159698f2723ae86820e5bad`
- Task config: `benchmark/configs/task_araus_pleasantness.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/araus_pleasantness_regression__araus__araus_psychoacoustic_ridge__seed2026.csv`

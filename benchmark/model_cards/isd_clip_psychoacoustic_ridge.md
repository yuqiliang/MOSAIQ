---
model_id: isd_clip_psychoacoustic_ridge
task_id: iso_coordinate_regression
dataset_id: ISD
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# isd_clip_psychoacoustic_ridge

## Model Summary

- **Task:** `iso_coordinate_regression` (multi_output_regression)
- **Dataset:** `ISD`
- **Estimator family:** `ridge`
- **Feature set:** `shared6`
- **Predictors:** `LAeq_dBA`, `loudness_N_sone`, `sharpness_S_acum`, `roughness_R_asper`, `fluctuation_strength_F_vacil`, `tonality_T_tu`
- **Targets:** `mean_ISOPleasant`, `mean_ISOEventful`
- **Parameters:** `{"alpha": 1.0}`
- **Random seed:** `2026`
- **Audio used:** `false`

## Intended Use

This model establishes reproducible reference performance for MOSAIQ Paper 2
and validates the corresponding task, split, feature, prediction, and metric
interfaces. It is not intended for consequential decisions about individuals
or places.

## Data and Evaluation

- Training records: 784
- Development records: 204
- Test records: 184
- Split protocol: `dataset_specific` version `0.1.0`
- Preprocessing is fitted on training records only.
- No classification threshold is used.

### Test Point Metrics

| Target | RMSE | MAE | R2 | Pearson r | Spearman rho |
| --- | --- | --- | --- | --- | --- |
| mean_ISOEventful | 0.2850 | 0.2234 | -0.1090 | 0.0462 | 0.1042 |
| mean_ISOPleasant | 0.2764 | 0.2250 | 0.0417 | 0.2741 | 0.2835 |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- The shared-six complete-case cohort covers 43.3% of ISD clips.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment isd_clip_psychoacoustic_ridge
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `iso_coordinate_regression__isd__isd_clip_psychoacoustic_ridge__seed2026`
- Experiment SHA-256: `593fecb9c1ba5cf9c11ed5aa7dabee90786845b718fa2863a7eed313a6e47fa5`
- Task config: `benchmark/configs/task_iso_coordinates.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/iso_coordinate_regression__isd__isd_clip_psychoacoustic_ridge__seed2026.csv`

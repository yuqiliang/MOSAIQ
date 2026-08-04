---
model_id: tong_style_reduced_rf
task_id: isd_individual_iso_prediction
dataset_id: ISD
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# tong_style_reduced_rf

## Model Summary

- **Task:** `isd_individual_iso_prediction` (multi_output_regression)
- **Dataset:** `ISD`
- **Estimator family:** `random_forest`
- **Feature set:** `tong_style_reduced`
- **Predictors:** `LAeq_dBA`, `loudness_N_sone`, `sharpness_S_acum`, `roughness_R_asper`, `fluctuation_strength_F_vacil`, `tonality_T_tu`, `age`, `latitude`, `longitude`, `gender`, `language`
- **Targets:** `ISOPleasant`, `ISOEventful`
- **Parameters:** `{"min_samples_leaf": 3, "n_estimators": 300, "n_jobs": 1}`
- **Random seed:** `2026`
- **Audio used:** `false`

## Intended Use

This model establishes reproducible reference performance for MOSAIQ Paper 2
and validates the corresponding task, split, feature, prediction, and metric
interfaces. It is not intended for consequential decisions about individuals
or places.

## Data and Evaluation

- Training records: 1324
- Development records: 308
- Test records: 279
- Split protocol: `fixed_train_dev_test` version `0.1.0`
- Preprocessing is fitted on training records only.
- No classification threshold is used.

### Test Point Metrics

| Target | RMSE | MAE | R2 | Pearson r | Spearman rho |
| --- | --- | --- | --- | --- | --- |
| ISOEventful | 0.3203 | 0.2540 | -0.0652 | 0.2624 | 0.2013 |
| ISOPleasant | 0.3572 | 0.2971 | -0.3257 | -0.0200 | -0.0405 |

### Test Distribution Metrics

| Target | KL | JS | DME |
| --- | --- | --- | --- |
| ISOEventful | 2.4860 | 0.1423 | 0.4317 |
| ISOPleasant | 1.6865 | 0.1350 | 0.4003 |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- The feature set omits unavailable CitySeg, OSM, THD, and other Tong et al. predictors.
- ISD evaluation holds out locations rather than randomly splitting individual responses.
- The shared-six complete-case cohort covers 43.3% of ISD clips.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment tong_style_reduced_rf
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `isd_individual_iso_prediction__isd__tong_style_reduced_rf__seed2026`
- Experiment SHA-256: `443ef00495d838be8416e13377ac86803a2dcaed3e1e4af73be5a095b804e9a4`
- Task config: `benchmark/configs/task_isd_individual_iso.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/isd_individual_iso_prediction__isd__tong_style_reduced_rf__seed2026.csv`

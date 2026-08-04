---
model_id: delta_annoyance_from_observed_sources_rf
task_id: delta_annoyance
dataset_id: DeLTA
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# delta_annoyance_from_observed_sources_rf

## Model Summary

- **Task:** `delta_annoyance` (regression)
- **Dataset:** `DeLTA`
- **Estimator family:** `random_forest`
- **Feature set:** `delta_source_indicators`
- **Predictors:** `source_aircraft`, `source_bells`, `source_bird_tweet`, `source_bus`, `source_car`, `source_children`, `source_construction`, `source_dog_bark`, `source_footsteps`, `source_general_traffic`, `source_horn`, `source_laughter`, `source_motorcycle`, `source_music`, `source_non_identifiable`, `source_other`, `source_rail`, `source_rustling_leaves`, `source_screeching_brakes`, `source_shouting`, `source_siren`, `source_speech`, `source_ventilation`, `source_water`
- **Targets:** `mean_annoyance`
- **Parameters:** `{"min_samples_leaf": 3, "n_estimators": 300, "n_jobs": 1}`
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
| mean_annoyance | 1.2484 | 1.0223 | 0.1463 | 0.4064 | 0.4030 |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- Inference assumes that the 24 source annotations are already observed; predicted-source propagation is not evaluated here.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment delta_annoyance_from_observed_sources_rf
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `delta_annoyance__delta__delta_annoyance_from_observed_sources_rf__seed2026`
- Experiment SHA-256: `c5487b6cb1f8f172dbbe58967b32a40031cdd4217edd1bba667e351c003741a2`
- Task config: `benchmark/configs/task_delta_annoyance.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/delta_annoyance__delta__delta_annoyance_from_observed_sources_rf__seed2026.csv`

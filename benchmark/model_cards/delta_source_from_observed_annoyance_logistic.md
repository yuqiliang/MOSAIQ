---
model_id: delta_source_from_observed_annoyance_logistic
task_id: delta_source_multilabel
dataset_id: DeLTA
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# delta_source_from_observed_annoyance_logistic

## Model Summary

- **Task:** `delta_source_multilabel` (multilabel_classification)
- **Dataset:** `DeLTA`
- **Estimator family:** `one_vs_rest_logistic`
- **Feature set:** `delta_annoyance_only`
- **Predictors:** `mean_annoyance`
- **Targets:** `source_aircraft`, `source_bells`, `source_bird_tweet`, `source_bus`, `source_car`, `source_children`, `source_construction`, `source_dog_bark`, `source_footsteps`, `source_general_traffic`, `source_horn`, `source_laughter`, `source_motorcycle`, `source_music`, `source_non_identifiable`, `source_other`, `source_rail`, `source_rustling_leaves`, `source_screeching_brakes`, `source_shouting`, `source_siren`, `source_speech`, `source_ventilation`, `source_water`
- **Parameters:** `{"C": 1.0, "class_weight": "balanced"}`
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
- Decision thresholds were selected per label on the development partition only.

### Test Aggregate Metrics

| Scope | Macro AP | Micro AP | Macro F1 | Micro F1 |
| --- | --- | --- | --- | --- |
| All 24 labels | 0.1615 | 0.1594 | 0.2099 | 0.2963 |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- This diagnostic model conditions on observed mean annoyance and is not an automatic audio source-recognition model.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment delta_source_from_observed_annoyance_logistic
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `delta_source_multilabel__delta__delta_source_from_observed_annoyance_logistic__seed2026`
- Experiment SHA-256: `fbd0d8c56122955308a76fd1041479cd4a7e0ebd249ae01828497292aaabeca3`
- Task config: `benchmark/configs/task_delta_sources.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/delta_source_multilabel__delta__delta_source_from_observed_annoyance_logistic__seed2026.csv`

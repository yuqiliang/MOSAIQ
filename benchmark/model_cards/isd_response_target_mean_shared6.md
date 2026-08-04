---
model_id: isd_response_target_mean_shared6
task_id: isd_individual_iso_prediction
dataset_id: ISD
benchmark_version: 0.1.0-dev
split_version: 0.1.0
status: reference-baseline
audio_used: false
---

# isd_response_target_mean_shared6

## Model Summary

- **Task:** `isd_individual_iso_prediction` (multi_output_regression)
- **Dataset:** `ISD`
- **Estimator family:** `target_mean`
- **Feature set:** `shared6_cohort_only`
- **Predictors:** None
- **Targets:** `ISOPleasant`, `ISOEventful`
- **Parameters:** `{}`
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
| ISOEventful | 0.3383 | 0.2690 | -0.1883 | NA | NA |
| ISOPleasant | 0.3103 | 0.2601 | -0.0001 | NA | NA |

### Test Distribution Metrics

| Target | KL | JS | DME |
| --- | --- | --- | --- |
| ISOEventful | 11.7603 | 0.3627 | 0.7201 |
| ISOPleasant | 11.9138 | 0.3916 | 0.7535 |

## Limitations

- This is a reference baseline, not a proposed state-of-the-art architecture.
- No audio waveform is consumed; the run metadata records `audio_used=false`.
- Performance is specific to MOSAIQ split version `0.1.0` and must not be compared to results using a different cohort without qualification.
- The shared-six complete-case cohort covers 43.3% of ISD clips.
- The model ignores all predictors and represents an intentionally weak reference point.

## Reproduction and Provenance

```bash
uv run python scripts/run_tabular_baselines.py --experiment isd_response_target_mean_shared6
uv run python scripts/validate_tabular_baselines.py
```

- Run ID: `isd_individual_iso_prediction__isd__isd_response_target_mean_shared6__seed2026`
- Experiment SHA-256: `382e24a08e25596346a64d7d1466ec99d2854f28b68631abb5f5f512e4371148`
- Task config: `benchmark/configs/task_isd_individual_iso.yaml`
- Baseline config: `benchmark/baselines/baseline_config.yaml`
- Result table: `benchmark/results/baseline_results.csv`
- Predictions: `benchmark/results/predictions/isd_individual_iso_prediction__isd__isd_response_target_mean_shared6__seed2026.csv`

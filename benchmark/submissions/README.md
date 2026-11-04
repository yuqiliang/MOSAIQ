# MOSAIQ result submissions

Submissions use tidy long-form predictions so regression, multi-output, and
multilabel tasks share one contract. One row represents one record/target
prediction.

Required columns:

- `benchmark_version`
- `split_version`
- `task_id`
- `task_version`
- `dataset_id`
- `partition`
- `fold`
- `record_id`
- `target`
- `prediction`
- `uncertainty`
- `model_id`
- `run_id`

Use a blank `partition` for fold-based SATP submissions and a blank `fold` for
fixed train/dev/test tasks. `uncertainty` may be blank when the model does not
produce predictive uncertainty.

Validate:

```bash
uv run python scripts/validate_submission.py predictions.csv
uv run python scripts/validate_submission.py predictions.csv --require-complete
```

Official results must pass `--require-complete`, include every expected
evaluation record/target exactly once, and be accompanied by a model card.
The public leaderboard must display benchmark, task, split, and cohort versions
and must not rank results from incompatible cohorts as if they were comparable.

# Generated baseline results

Run `uv run python scripts/run_tabular_baselines.py` to regenerate this
directory. The primary files are:

- `baseline_results.csv`: tidy point and distribution metric rows;
- `distribution_curves.csv`: KDE values on the fixed ISO interval [-1, 1];
- `predictions/`: held-out observed values, predictions, and GPR standard deviations;
- `artifacts/`: fitted preprocessors and per-target estimators;
- `runs/`: experiment parameters, row counts, package versions, and `audio_used=false`.

Do not compare model rows with different `feature_set`, `n_train`, or `n_eval`
as if they used the same evaluation cohort.

Step 7 does not overwrite these Step 6 outputs. Its configuration, per-seed
runs, confidence intervals, paired comparisons, sensitivity analysis, and
generated report are under `benchmark/robustness/`.

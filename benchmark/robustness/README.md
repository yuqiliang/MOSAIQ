# Step 7 robustness evaluation

`robustness_config.yaml` is the executable contract for MOSAIQ Step 7. Run:

```bash
uv run python scripts/run_robustness_evaluation.py
uv run python scripts/validate_robustness_evaluation.py
```

The pipeline produces:

- `multiseed_results.csv`: held-out metrics from five seeds for RF/XGBoost;
- `multiseed_summary.csv`: mean, standard deviation, minimum, and maximum;
- `bootstrap_intervals.csv`: cluster-bootstrap 95% confidence intervals;
- `paired_comparisons.csv`: paired bootstrap improvement over declared references;
- `feature_coverage_sensitivity.csv`: ISD all-eligible versus shared6 cohorts;
- `gpr_calibration.csv`: empirical coverage and width of GPR prediction intervals;
- `robustness_report.md`: generated methods, findings, and interpretation limits;
- `multiseed/`: per-seed predictions, metadata, and fitted artifacts.

Responses from the same soundscape are resampled together by `clip_id`. This
preserves the dependence created when one clip has multiple assessments.
Positive values in `paired_comparisons.csv` always mean that the candidate is
better, regardless of whether the original metric is minimized or maximized.

The evaluation remains audio-free and uses the fixed MOSAIQ split release
`0.1.0`. Bootstrap intervals describe uncertainty for the current held-out
sample. They are not evidence that performance transfers to a new dataset.

# Benchmark baselines

`baseline_config.yaml` is the executable contract for the MOSAIQ tabular
benchmark v0.1. It defines feature cohorts, model families, parameters, task
configs, split version, and random seed. Run it from the repository root:

```bash
uv run python scripts/run_tabular_baselines.py
```

Generated metrics are written to `benchmark/results/baseline_results.csv`.
The same directory contains per-record predictions, fitted artefacts, run
metadata, package versions, and KDE curves. Preprocessing is fitted on the
training partition only; development and test records are transformed without
refitting.

The current suite contains 17 experiments and 498 tidy metric rows. It includes
LAeq-only and shared-psychoacoustic regression, ARAUS shared6 transfer models,
ISD reduced-feature response models, DeLTA label prevalence and
annoyance-conditioned source classification, and DeLTA annoyance regression
conditioned on observed source indicators.

Regenerate the accompanying model cards after every full run:

```bash
uv run python scripts/build_model_cards.py
```

This release is intentionally audio-free. `araus_elastic_net_shared6` is a
six-feature transfer baseline rather than the published 264-candidate ARAUS
replication. The `tong_style_reduced_*` models omit unavailable CitySeg, OSM,
THD, and other published factors. The response target-mean model uses the same
six-feature complete-case cohort as the four Tong-style models so their metrics
are directly comparable. DeLTA cross-target models assume that the conditioning
human response or source annotations are observed and are diagnostic rather
than deployable audio models.

Step 7 robustness analyses are deliberately stored separately under
`benchmark/robustness/`. This preserves the Step 6 point-estimate freeze while
adding multi-seed summaries, cluster-bootstrap confidence intervals, paired
comparisons, feature-coverage sensitivity, and GPR interval calibration.

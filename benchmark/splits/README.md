# Benchmark split assignments

This directory contains MOSAIQ split release `0.1.0`, generated with seed
`2026`. Assignment files contain no target values and are immutable within this
split version. `split_checksums.sha256` records the released file hashes.

## Methods

- ISD: ISO coordinates are quantile-binned and passed to five-fold
  `StratifiedGroupKFold`, grouping all clips by `LocationID`. A deterministic
  distribution-drift objective selects one fold for development and one for
  test; the remaining three form training.
- ARAUS: source folds 1-4 are training, fold 5 is development, fold 0 is test,
  and fold -1 common stimuli are excluded.
- SATP: deterministic five-fold cross-validation uses iterative multilabel
  stratification over three quantile bins for each ISO coordinate.
- DeLTA: iterative multilabel stratified shuffling creates approximately
  70/15/15 train/development/test partitions while balancing 24 source labels
  and five annoyance quantile bins.

| Dataset | Train | Dev | Test | Excluded / folds |
| --- | ---: | ---: | ---: | --- |
| ISD | 1,599 | 524 | 581 | 5 excluded |
| ARAUS | 17,730 | 4,440 | 48 | 6 excluded |
| SATP | - | - | - | folds: 5, 5, 5, 6, 6 |
| DeLTA | 2,012 | 441 | 437 | 0 excluded |

Five ISD clips are excluded: two unresolved whitespace-normalised identifier
collisions and three clips with incomplete ISO targets. Six ARAUS auxiliary
common stimuli are also excluded.

Required fixed-split columns:

```text
clip_id,dataset_id,split,split_version,exclusion_reason
```

`split` must be one of `train`, `dev`, `test`, or `excluded`.

SATP uses deterministic five-fold cross-validation because it has only 27
recordings. Its assignment file instead uses:

```text
clip_id,dataset_id,fold,split_version,exclusion_reason
```

where `fold` is an integer from 0 to 4. All assignment files cover every source
clip exactly once, including explicit `excluded` rows where applicable. They do
not modify the source `datasets/*/data/clips.csv` files.

## Commands

```bash
uv run python scripts/build_benchmark_splits.py
uv run python scripts/validate_benchmark_splits.py
```

`split_summary.csv` reports partition counts and selected target-distribution
diagnostics. Rebuilding with the same data, seed, dependencies, and split
version must reproduce the checksums.

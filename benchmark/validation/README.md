# Benchmark validation outputs

This directory contains the generated, versioned Step 4 audit for the candidate
dataset freeze declared in `benchmark/release.yaml`.

- `validation_summary.csv`: check-level PASS/WARN/FAIL evidence.
- `row_counts.csv`: resource dimensions and source hashes.
- `task_eligibility.csv`: source, filter, exclusion, target, and frozen counts.
- `split_summary.csv`: partition sizes and fractions.
- `exclusions.csv`: record-level exclusions and reasons.
- `asset_coverage.csv`: asset-reference coverage by dataset and partition.
- `feature_coverage.csv`: usable feature coverage by dataset and partition.
- `license_audit.csv`: declared metadata and raw-asset release status.
- `source_checksums.sha256`: checksums of every freeze input.
- `validation_checksums.sha256`: checksums of generated validation outputs.
- `validation_report.md`: paper-ready technical-validation narrative and tables.

Regenerate and verify from the repository root:

```bash
uv run python scripts/build_benchmark_report.py
uv run python scripts/build_benchmark_report.py --check-only
```

The generator also writes frozen task manifests under `benchmark/manifests/`.
Counts in papers and release notes should be sourced from these outputs rather
than maintained manually.

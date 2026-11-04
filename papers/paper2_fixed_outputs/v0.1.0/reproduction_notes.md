# Fixed-output reproduction notes

This package is generated from saved benchmark validation, baseline and
robustness outputs. It does not depend on a manuscript draft, meeting notes,
personal recaps or internal work audits.

Run from the repository root:

```bash
uv run python scripts/build_paper2_fixed_outputs.py
uv run python scripts/validate_paper2_fixed_outputs.py
```

The twelve CSV tables and six figures represent the frozen no-audio benchmark.
The output manifest records the SHA-256 of each generated file. The separate
ISD audio reference track is not included in these numerical results.

Interpret results using the same dataset, task, feature cohort and split.
Retain the documented validation warnings, small ARAUS test-set caveat and
conditional interpretation of DeLTA cross-target models.

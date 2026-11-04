# MOSAIQ manuscript-facing evidence

The repository contains reproducible numerical evidence used by the MOSAIQ
benchmark manuscript. Manuscript drafts, editorial correspondence and personal
revision histories are maintained outside the repository.

The versioned output package is generated from benchmark validation, baseline
and robustness results:

```bash
uv run python scripts/build_paper2_fixed_outputs.py
uv run python scripts/validate_paper2_fixed_outputs.py
```

The current package is `paper2_fixed_outputs/v0.1.0/`. Use its key-number file,
fixed tables, figures, reproduction notes and checksum manifest when citing
results. The separate ISD audio results retain their own versioned scope.

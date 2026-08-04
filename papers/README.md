# MOSAIQ papers

The former Markdown working draft was removed after its 19 stale statements
were integrated into a versioned Word manuscript. The repository retains only
generated numerical evidence and an integration audit; the Word draft is
maintained with the thesis materials outside this repository.

The versioned Paper 2 evidence package is generated from benchmark validation,
baseline, and robustness outputs:

```bash
uv run python scripts/build_paper2_fixed_outputs.py
uv run python scripts/validate_paper2_fixed_outputs.py
```

The current package is `paper2_fixed_outputs/v0.1.0/`. Numerical claims should
be copied from its key-number file, fixed tables, or generated manuscript
insert. `draft_replacement_audit.md` records the completed legacy-draft
replacement.

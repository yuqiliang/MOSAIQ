# MOSAIQ v0.1 candidate data card

## Summary

MOSAIQ v0.1 is a secondary, ISO 12913-aware benchmark candidate constructed
from ISD and ARAUS core tracks plus SATP and DeLTA extension tracks. It
materialises 27,850 clip/stimulus rows and 59,935 response rows. It provides
versioned tasks, splits, manifests, validation reports, tabular baselines,
robustness evidence, and model cards.

## Intended use

- Reproducible evaluation of tabular soundscape-perception tasks.
- Testing split, validation, uncertainty, and reporting procedures.
- Development of models that respect source-dataset context and task grain.
- Preparing a later audio, visual, and multimodal benchmark release.

## Out-of-scope use

- Claims about raw-audio, visual, or multimodal model performance.
- Safety-critical, clinical, legal, or individual-level decision making.
- Inferring causal effects from observational or aggregated responses.
- Treating source datasets as exchangeable without reporting dataset identity.
- Redistributing source media without checking source and per-file terms.

## Composition

Core tracks are ISD and ARAUS. SATP contributes multilingual ISO responses and
uses five-fold evaluation because it has 27 recordings. DeLTA contributes
annoyance and 24 sound-source labels. Participant counts are summed by dataset
and are not de-duplicated across sources.

## Splits and leakage controls

ISD is grouped by location, ARAUS preserves published folds, SATP uses
deterministic recording-level five-fold evaluation, and DeLTA uses iterative
stratification over annoyance bins and source labels. Response-level ISD
records inherit their clip partition.

## Validation

The candidate has 49 checks: 47 PASS, 2 WARN, and 0 FAIL. The warnings concern
excluded ISD identifier collisions and the ARAUS raw-asset rights review.

## Known limitations

- No waveform or video file is materialised.
- Shared psychoacoustic features cover 43.3% of ISD clips and select a shifted
  complete-case cohort.
- The ARAUS independent test fold contains 48 eligible clips.
- Current DeLTA cross-target models consume observed human labels.
- Current evaluations are within-dataset and do not establish external
  generalisation.
- GPR intervals under-cover on the held-out ISD response cohort.

## Governance

See `DATA_LICENSE.md`, `benchmark/governance/`, and
`benchmark/release_checklist.md`. Source-specific terms are authoritative.

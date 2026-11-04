# DeLTA track data card

## Role

DeLTA is an extension track for annoyance regression and 24-label sound-source
classification.

## Candidate materialisation

- 2,890 clip rows.
- 11,650 response rows.
- Split: 2,012 train, 441 dev, and 437 test.
- Stratification uses annoyance bins and the multilabel source matrix.

## Baseline interpretation

Label prevalence is the unconditional classification reference. The logistic
source baseline consumes observed mean annoyance. Ridge and random-forest
annoyance baselines consume observed source labels. These are diagnostic
conditional models, not automatic audio recognisers.

## Risks and limitations

- No waveform is included, so the source-classification task is not yet an
  audio event detection benchmark.
- Rare labels require per-class reporting; pooled micro metrics can conceal
  poor minority-label performance.
- DeLTA is derived from ISD material and its provenance obligations must be
  retained.

## Source

Deep Learning Techniques for noise Annoyance detection, Zenodo,
doi:10.5281/zenodo.7158057; Hou et al., Journal of the Acoustical Society of
America, doi:10.1121/10.0022408.

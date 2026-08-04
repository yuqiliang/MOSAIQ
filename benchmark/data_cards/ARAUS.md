# ARAUS track data card

## Role

ARAUS is a MOSAIQ core track for ISO PAQ, ISO coordinate, appropriateness, and
published pleasantness-reference tasks.

## Candidate materialisation

- 22,224 clip/stimulus rows.
- 27,255 response rows.
- 22,218 eligible clips after six common/auxiliary exclusions.
- Split: 17,730 train, 4,440 dev, 48 test, and 6 excluded.
- Split policy: preserve the published fold structure.

## Features and baselines

Shared acoustic/psychoacoustic coverage is complete for the tabular shared-six
set. The MOSAIQ Elastic Net is a shared-six transfer baseline, not a replication
of the published 264-candidate model. The published CNN is not included because
v0.1 contains no waveforms.

## Risks and limitations

- The independent test set is small and uncertainty must be reported.
- Augmented stimuli are reconstructed from soundscape, masker, and level-ratio
  components; related stimuli must not be split casually.
- Raw media have mixed or per-file terms and remain blocked from MOSAIQ
  redistribution until the rights inventory is complete.

## Source

Affective Responses to Augmented Urban Soundscapes, NTU Research Data,
doi:10.21979/N9/9OTEVX; Ooi et al., IEEE Transactions on Affective Computing,
doi:10.1109/TAFFC.2023.3247914.

# SATP track data card

## Role

SATP is an extension track for multilingual ISO PAQ and coordinate evaluation.

## Candidate materialisation

- 27 recording-level clips.
- 17,441 response rows.
- Five deterministic recording-level folds containing 5, 5, 5, 6, and 6 clips.

## Processing

Source PAQ values on 0-100 are retained and converted to 1-5 by
`1 + 4 * value / 100` for the common benchmark representation. ISO coordinates
are derived from the eight PAQ items.

## Risks and limitations

- Twenty-seven recordings are insufficient for a stable fixed holdout.
- Responses are numerous but do not create additional independent stimuli.
- Language and translation effects should not be interpreted as recording-level
  generalisation without participant- and language-aware analysis.
- No shared-six psychoacoustic feature set is available in v0.1.

## Source

Soundscape Attributes Translation Project, doi:10.5281/zenodo.7143599.

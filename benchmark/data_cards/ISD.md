# ISD track data card

## Role

ISD is a MOSAIQ core track for clip-level ISO PAQ/coordinate tasks and an
individual response-level ISO task.

## Candidate materialisation

- 2,709 clip rows.
- 3,589 response rows.
- 2,704 clips eligible after five explicit exclusions.
- Split: 1,599 train, 524 dev, 581 test, and 5 excluded.
- Grouping unit: location.

## Features

LAeq and psychoacoustic fields are available for a subset. The shared-six
complete-case set covers 1,174 of 2,709 clips (43.3%). Missingness is associated
with soundscape/group coverage, not with multiple assessments per soundscape.

## Risks and limitations

- Two whitespace-normalised identifier collisions are unresolved and excluded.
- Complete-case response models describe a selected cohort; test Eventfulness
  differs from the full cohort.
- Source media are referenced but not redistributed in v0.1.
- Participant-level and site-context effects require careful interpretation.

## Source

International Soundscape Database, doi:10.5281/zenodo.10672568. Confirm the
exact source version and current terms before public deposition.

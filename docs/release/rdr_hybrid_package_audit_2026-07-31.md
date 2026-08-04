# MOSAIQ RDR consolidated private-draft package audit

Audit date: 31 July 2026<br>
RDR item: `33130373`<br>
Status: private draft; not submitted; not public; no DOI

## Consolidated structure

- One MOSAIQ v0.2.0-rc1 benchmark-kit ZIP containing four tabular dataset
  packages, schemas, seven tasks, split 0.1.0, manifests, 17 tabular baseline
  experiments, robustness outputs, model/data cards, validators, tests, and
  Paper 2 fixed outputs.
- One ZIP64 ISD audio extension containing the accepted files from the official
  Granada, Groningen, London 1-4, and Venice source archives, organised into
  train, development, and test directories.
- Five small top-level support files: one entry README, one consolidated
  licence/attribution statement, one audio manifest, one deposit manifest, and
  one checksum inventory. Detailed dictionaries, cohort, exclusions, QC,
  reports, citation metadata, and model/data cards remain in the benchmark kit.

## Validation result

- Seven top-level files in the replacement RDR draft package set.
- One ZIP64 audio package of approximately 9.6 GiB.
- 820 accepted and unique WAV files: 546 train, 154 development, 120 test.
- Audio payload size: 10,266,162,886 bytes before ZIP container overhead.
- Audio ZIP size: 10,266,488,035 bytes; SHA-256
  `b7e8eedf7a433cb4abd1b244b6e07c8e52a678d91e13c4fc6d4d20d1d0bde8af`.
- Benchmark-kit SHA-256:
  `0c4134553a1cb1cb36c4fc3b81a6fde1128e78a151d6cbe879f1ac2b8d01100d`.
- Package set size: approximately 9.7 GiB.
- Every source WAV byte size and SHA-256 matched the frozen full manifest.
- Every ZIP passed central-directory and member-read validation.
- The audio package contains a filtered manifest, README, and internal checksum
  inventory covering its metadata and all 820 WAV members.
- The core ZIP contains no WAV payloads.
- The previous 24 July no-audio ZIP and the superseded 21-file package layout
  are removed from the RDR draft.
- Duplicate private draft `32982863`, titled `MOSAIQ Core Schema and Harmonised
  Metadata`, was permanently deleted; `33130373` is the sole remaining item.

## Remaining gates

The provisional record-level licence is CC BY 4.0. Before submission for
review, confirm participant-identifier treatment with UCL RDM; final author
order, ORCIDs, funding, and related identifiers; source and owner rights; the
record-level licence; and whether the ISD audio extension belongs in the first
public benchmark release. External usability and co-author review remain
intentionally paused.

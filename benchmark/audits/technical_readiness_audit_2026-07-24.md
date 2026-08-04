# MOSAIQ technical-readiness audit

Audit date: 24 July 2026<br>
Review pass: 2 of 3<br>
Scope: repository, data packages, splits, freeze, baselines, robustness, release interface

## Overall judgement

The repository is technically runnable and internally consistent for the
declared no-audio tabular v0.1 candidate. All current validators and unit tests
pass. The candidate is not yet a legally or externally validated public v1.0.

Status: **PASS for internal candidate; CONDITIONAL for public release**

## Executed checks

| Area | Result |
| --- | --- |
| Catalogue Frictionless package | VALID |
| ISD package | clips, responses, features VALID |
| ARAUS package | clips, responses, features VALID |
| SATP package | clips, responses, source_files VALID |
| DeLTA package | clips, responses, source_files VALID |
| Task contracts | 7 tasks PASS |
| Split validation | version 0.1.0 PASS |
| Candidate freeze | check-only PASS |
| Freeze checks | 47 PASS, 2 WARN, 0 FAIL |
| Baselines | 17 experiments, 498 metric rows, audio_used=false PASS |
| Robustness | 3 stochastic models x 5 seeds; 123 intervals; 34 comparisons; 24 coverage rows; 6 calibration rows PASS |
| Fixed Paper 2 outputs | 12 tables, 6 figures, 23 manifested files PASS |
| Result submission validator | Header template and complete 48-row ARAUS submission PASS |
| Unit tests | 9 PASS |
| Python syntax | scripts compile PASS |
| Locked environment | `uv lock --locked` PASS |

## Leakage and evaluation controls

- ISD LocationID groups do not cross train/dev/test.
- ISD responses inherit clip partitions.
- ARAUS source folds are preserved and auxiliary/unmaterialised folds excluded.
- SATP recordings occupy one deterministic fold each.
- DeLTA recordings occupy one partition and preserve multilabel/annoyance
  marginals through iterative stratification.
- Preprocessing is fitted on training data only.
- Paired comparisons require matched record cohorts.
- Bootstrap resampling uses clip_id clusters.

## Reproducibility controls

- Random seed 2026 is fixed; stochastic robustness uses 2026-2030.
- Task, benchmark, split, feature, model, and run identifiers are saved.
- Source rows and frozen manifests have SHA-256 hashes.
- Generated Paper 2 files have a manifest and checksums.
- The old Markdown manuscript is absent and no longer a generator dependency.
- `CITATION.cff`, MIT code licence, data-licensing policy, data cards,
  attribution registry, release notes, reproduce guide, and submission
  contract are present.

## Documented warnings and blockers

1. Two whitespace-normalised ISD identifier conflicts remain excluded.
2. ARAUS raw-media rights require per-file review.
3. No raw audio/video is materialised.
4. ISD shared-six coverage is 43.3% and selects a shifted test cohort.
5. ARAUS has 48 eligible independent test records.
6. Current evaluations are within-dataset and do not establish external
   transfer.
7. The UCL RDR/Zenodo DOI and immutable release tag do not exist.
8. Independent usability review has not been run.

## Technical risks before public release

- Exact source-archive versions and checksums must accompany the RDR deposit.
- The current task status remains `draft` and benchmark version `0.1.0-dev`.
- Media ingestion will change feature coverage, model scope, storage, rights,
  and robustness obligations and therefore requires a new version.
- CI has not yet been observed on GitHub for this uncommitted working tree.

## Pass-2 conclusion

No failing internal technical check remains. Public release must stay blocked
until the rights, source-archive, external usability, media-scope, and DOI gates
in `benchmark/release_checklist.md` are resolved.

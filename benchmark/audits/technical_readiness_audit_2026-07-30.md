# MOSAIQ technical-readiness audit

Audit date: 30 July 2026<br>
Review pass: 2 of 3<br>
Scope: repository, data packages, splits, freezes, baselines, audio extension,
robustness, and release interfaces

## Overall judgement

The repository is runnable and internally consistent for the declared
no-audio tabular candidate and the separate ISD audio reference track. It is
not yet a legally cleared or externally validated public MOSAIQ-v1.0.

Status: **PASS for internal candidate; CONDITIONAL for public release**

## Executed checks

| Area | Result |
| --- | --- |
| Unit tests | 15 passed |
| Python syntax | `scripts` and `tests` compile |
| Four dataset packages | All Frictionless resources VALID |
| Task contracts and splits | 7 tasks PASS; split 0.1.0 PASS |
| Candidate validation freeze | 49 checks, 2 documented WARN, 0 FAIL |
| Tabular baselines | 17 experiments, 498 metric rows, `audio_used=false` PASS |
| Tabular robustness | 5 seeds; 123 intervals; 34 comparisons; 24 coverage and 6 calibration rows PASS |
| Paper 2 no-audio fixed outputs | 12 tables, 6 figures, 23 files PASS |
| Full ISD audio manifest | 1,021 rows; Frictionless VALID |
| Frozen audio cohort | 820 assets; 546 train, 154 dev, 120 test; no cross-split SHA-256 |
| Audio QC and descriptors | 820/820 technical PASS; 11 finite descriptors |
| Audio references | 2 tasks, 2 models, 48 metric and 2,988 held-out prediction rows PASS |
| Audio uncertainty | 2,000 clip-clustered resamples; 32 intervals; 8 paired comparisons |
| Repository formatting | `git diff --check` PASS |

## Controls and interpretation

- Responses inherit their parent `clip_id` partition.
- No waveform SHA-256 crosses train, development, and test.
- Descriptor preprocessing is fitted on training clips only.
- Response-level bootstrap samples `clip_id` clusters rather than treating
  repeated assessments as independent.
- Absolute amplitude descriptors are excluded from Ridge because calibration
  and amplitude scale remain unresolved.
- Descriptor Ridge improves held-out Eventfulness but not Pleasantness; these
  are interface-validation references, not state-of-the-art claims.

## Documented warnings and blockers

1. The full audio manifest retains 201 explicit exclusions: 143 missing source
   assets, 52 unmatched assets, three ambiguous matches, one duplicate, and
   two split exclusions.
2. All 820 accepted files retain a calibration warning; 247 float files need
   amplitude-scale review.
3. Learned CNN, pretrained encoder, fusion, missing-modality, and added-noise
   evaluations are not yet implemented.
4. ARAUS media rights still require per-file review.
5. The public tag, archival DOI, anonymous reviewer access, and UCL RDR upload
   do not exist.
6. CI has not yet been observed on GitHub for this working tree.

## Pass-2 conclusion

No failing local technical check remains. Public release remains blocked by
rights, release-scope, DOI/access, external-review, and learned multimodal
obligations rather than by an undisclosed implementation failure.

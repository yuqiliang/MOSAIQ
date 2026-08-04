# MOSAIQ release notes

## Repository audit - 4 August 2026

- Added a current architecture diagram and component-level repository audit.
- Revalidated all dataset packages, task contracts, splits, baseline outputs,
  robustness outputs, Paper 2 evidence, and experimental ISD audio outputs.
- Fixed the Frictionless Python API example and stale source-rebuild commands.
- Made validation freezes reproducible by recording a fixed generation time and
  removing runtime-duration fields from frozen validation evidence.
- Made tabular and robustness estimators byte-reproducible by explicitly using
  one worker for frozen model generation.
- Expanded the regression suite to 24 tests and removed unused code detected by
  correctness linting.

The audit does not change the public-release status: MOSAIQ remains an
internally validated candidate with the external gates listed below.

## v0.1.0-dev candidate - 24 July 2026

This is a citable-release candidate for the no-audio tabular scope. It is not
the final multimodal MOSAIQ-v1.0 promised in the OMAIB work plan.

### Included

- Four materialised datasets: ISD, ARAUS, SATP, and DeLTA.
- 27,850 clip or stimulus rows and 59,935 response rows.
- Seven versioned tasks and eleven task/dataset manifests.
- Deterministic split version `0.1.0` with dataset-specific leakage controls.
- Forty-nine technical checks: 47 PASS, 2 WARN, and 0 FAIL.
- Seventeen baseline experiments and generated model cards.
- Five-seed stability, cluster-bootstrap uncertainty, paired comparisons,
  feature-coverage sensitivity, and GPR interval calibration.
- Twelve fixed manuscript tables and six checksum-locked figures.
- A results submission contract and validator.

### Known release blockers

1. ARAUS raw-asset redistribution requires a per-file rights review.
2. Two whitespace-normalised ISD identifier collisions remain excluded pending
   source-owner review.
3. Raw audio and video are not included, so audio, visual, multimodal,
   missing-modality, and added-noise claims are out of scope.
4. The UCL RDR/Zenodo record, public DOI, anonymous reviewer link, and public
   GitHub release do not yet exist.
5. The release has not yet completed the planned independent usability review
   with Connected Places Catapult or the soundscape community.

### Compatibility

The candidate uses benchmark version `0.1.0-dev`, split version `0.1.0`, and
Paper 2 fixed-output freeze `mosaiq-paper2-fixed-v0.1.0-20260721`. Any public
release must either retain these exact artefacts or increment the relevant
version and regenerate all manifests, checksums, results, figures, and paper
numbers.

## Experimental ISD audio track - 30 July 2026

This is not a new public benchmark release and does not alter the fixed
no-audio Paper 2 evidence.

- Added the official Zenodo source/version/licence/checksum registry.
- Added resumable acquisition and safe WAV extraction outside Git.
- Added a Frictionless audio manifest schema and split-leakage validator.
- Materialised and verified the Groningen archive as a smoke test.
- Mapped 51 of 59 scoped clips; reported eight missing assets and one
  byte-identical duplicate explicitly.
- Passed technical QC for all 51 accepted assets.
- Recorded that observed Groningen encoding is `int16`, while the source prose
  describes 32-bit floating-point WAV.
- Added deterministic waveform descriptors and an audio baseline interface.
- Preregistered audio, fusion, missing-modality, and added-noise comparisons
  before full audio results.
- Verified all seven benchmark-candidate archives and froze 820 accepted clips
  (546 train, 154 development, 120 test) with 201 explicit exclusions.
- Executed clip- and response-level Target Mean and descriptor Ridge baselines,
  producing 2,988 held-out prediction rows.
- Added 2,000-sample clip-clustered uncertainty, paired comparisons, model
  cards, a full audio report, and CI validation.

Learned CNN, pretrained-encoder, fusion, missing-modality, and added-noise runs
remain pending. External usability and Paper 2 co-author review are deferred
by the user.

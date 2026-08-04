# MOSAIQ work that does not require audio

Status date: 30 July 2026

User-deferred items: external usability review and Paper 2 co-author review.

## Ready or already completed

- [x] Shared two-level schemas and four harmonised dataset packages.
- [x] Seven task contracts, deterministic splits, manifests, and checksums.
- [x] Unified no-audio training, prediction, and evaluation interfaces.
- [x] Target-mean, Ridge, ARAUS-style Elastic Net, response-level ISD,
      Tong-style tabular, DeLTA, and distributional baselines.
- [x] Model cards, data cards, robustness evaluation, and Paper 2 fixed outputs.
- [x] Result-submission schema, example, validator, and reproduction guide.
- [x] No-audio RDR candidate metadata and deterministic packaging workflow.

## Can be completed before waveform ingestion

- [ ] Obtain co-author confirmation of author order, affiliations, ORCIDs,
      funding, ownership, and the proposed licence for MOSAIQ-generated content.
- [ ] Complete the ARAUS source-terms inventory and record a decision for every
      media component before redistributing reconstructed stimuli.
- [ ] Confirm participant-data, ethics, and consent wording with UCL research
      data support.
- [ ] Run the independent usability protocol from a clean machine and resolve
      every critical or major issue — deferred by user.
- [ ] Ask one external researcher to produce a valid benchmark submission using
      only the archive documentation.
- [x] Freeze the ISD source-acquisition registry with URL, source version,
      archive checksum, retrieval date, licence, and attribution. Other source
      datasets remain separate rights tracks.
- [ ] Expand the column-level data dictionary for every public table and link
      each transformed field to its source field and mapping rule.
- [ ] Add release CI that builds the RDR archive, verifies its checksum, extracts
      it, and reruns the smoke-test suite.
- [x] Pre-register the audio asset manifest contract: canonical asset ID,
      dataset, source URI, licence, checksum, format, sample rate, channels,
      duration, calibration state, and access class.
- [x] Define audio quality-control thresholds and machine-readable failure
      reasons for missing, corrupt, clipped, silent, uncalibrated, or
      channel-inconsistent files.
- [x] Freeze the intended audio-feature and waveform-model configurations,
      including resampling, channel handling, segment policy, augmentation,
      random seeds, and compute budget.
- [x] Define audio-only, tabular-only, multimodal, missing-modality, and
      added-noise comparison tables before seeing final model results.
- [ ] Prepare the Scientific Data repository, Data Records, Technical
      Validation, Usage Notes, Code Availability, and Data Availability text
      around the fixed no-audio evidence.
- [ ] Create the clean release branch/tag only after the private archive and
      external usability review agree.

## Work unlocked by the ISD audio acquisition

- [x] Materialise the rights-cleared ISD files and verify source checksums.
- [x] Run full ISD audio QC and freeze the 820-clip availability cohort with
      201 explicit exclusions.
- [x] Extract deterministic waveform descriptors.
- [x] Run clip- and response-level Target Mean and descriptor Ridge references.
- [x] Run clip-clustered bootstrap uncertainty and paired comparisons.
- [x] Generate audio model cards, a versioned report, and CI validation.
- [ ] Extract log-mel features and train an ISD-adapted ARAUS-style CNN.
- [ ] Train audio-only and multimodal models on the frozen splits.
- [ ] Run missing-modality and added-noise robustness experiments.
- [ ] Update model cards, fixed outputs, manuscript claims, and the public RDR
      package with measured audio results.

The private no-audio record is useful for preservation and reviewer dry runs,
but it should remain labelled as `0.1.0-dev`, not MOSAIQ-v1.0.

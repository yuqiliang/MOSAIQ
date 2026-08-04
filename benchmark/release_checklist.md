# MOSAIQ public-release checklist

Status date: 30 July 2026

## Internal candidate gates

- [x] Dataset packages validate.
- [x] Task contracts validate.
- [x] Splits are deterministic and leakage-aware.
- [x] Task manifests and checksums are frozen.
- [x] Baseline runs and model cards are reproducible.
- [x] Robustness and uncertainty outputs validate.
- [x] Paper 2 fixed outputs validate.
- [x] Data cards, licensing policy, attribution registry, reproduction guide,
      submission format, and release notes exist.
- [x] Code licence is present.
- [x] ISD source licence, Zenodo version, source checksums, audio manifest
      contract, Groningen mapping smoke test, QC, and descriptor interface are
      recorded.
- [x] Full ISD candidate archives are verified; an 820-clip cohort, 201-row
      exclusion log, two reference baselines, uncertainty outputs, and model
      cards validate in CI.
- [x] Build and independently validate the consolidated v0.2.0-rc1 package set:
      one benchmark-kit ZIP, one ZIP64 ISD audio extension, five support files,
      and 820 unique WAV files.
- [x] Replace the superseded 21-file layout in UCL RDR private draft `33130373`
      and delete any confirmed duplicate MOSAIQ draft without submitting for
      review, publishing, or reserving a DOI.
- [x] Freeze the ARAUS v4.2 and USotW record 10106181 source metadata, classify
      the ARAUS v1 audio inputs, and prepare a source-register-only RDR draft
      extension with no copied ARAUS media.
- [x] Upload the four-file ARAUS v1 source-register extension to UCL RDR private
      draft `33130373`; update the title and description, retain Draft status,
      and do not create a DOI, private link, or review submission.

## External gates required before calling the release MOSAIQ-v1.0

- [ ] Resolve or formally accept the two excluded ISD identifier collisions.
- [ ] Convert the reported ARAUS permission discussion into written approval
      defining public redistribution scope; complete the masker-level licence
      and citation inventory before any ARAUS media deposit.
- [ ] Confirm owner approval for the proposed CC BY 4.0 licence on original
      MOSAIQ documentation and benchmark metadata.
- [ ] Confirm ethics/consent wording and managed-access requirements with the
      source owners and UCL.
- [ ] Run the independent usability review and resolve critical findings —
      deferred by user.
- [ ] Decide whether the public release remains tabular or adds the separate
      ISD-only audio track; do not imply four-dataset audio coverage.
- [ ] If media are added, run audio, visual, multimodal, missing-modality, and
      added-noise benchmarks promised in the OMAIB plan.
- [ ] Create a clean GitHub release tag and immutable source archive.
- [ ] Deposit the permitted package in UCL RDR/Zenodo and obtain a DOI.
- [ ] Replace all pending DOI and release-commit fields.
- [ ] Provide an anonymous reviewer-access link at first submission.
- [ ] Complete co-author scientific, language, and authorship review —
      deferred by user.

The benchmark is an internally validated v0.1 candidate until every applicable
external gate is checked. Passing internal CI alone is not a public-release or
journal-acceptance claim.

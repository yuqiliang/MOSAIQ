# MOSAIQ RDR private-draft core benchmark package

## Deposit status

This archive is the MOSAIQ v0.2.0-rc1 benchmark kit, rebuilt on 31 July 2026
for UCL RDR private draft `33130373`. The kit remains free of waveform
payloads, while 820 permitted ISD WAV files are stored in one separately
checksummed ZIP64 audio extension. The draft is not authorised for public
release and is not the final four-dataset multimodal MOSAIQ-v1.0 benchmark.

The candidate freeze is
`mosaiq-benchmark-v0.1-candidate-20260716`; split version `0.1.0`; Paper 2
fixed-output freeze `mosaiq-paper2-fixed-v0.1.0-20260721`.

## Contents

The archive contains:

- harmonised tabular records for ISD, ARAUS, SATP, and DeLTA;
- schemas, catalogue entries, task definitions, splits, and frozen manifests;
- no-audio tabular baseline configurations, predictions, metrics, and models;
- robustness, uncertainty, calibration, and distribution-evaluation outputs;
- model cards, data cards, validation reports, and result-submission tools;
- Paper 2 fixed tables and figures;
- source code, tests, a locked Python environment, and release documentation;
- `file_manifest.csv` and `checksums.sha256` generated at packaging time.

The package also includes the ISD audio manifests, QC, descriptors, reference
results, and model cards, but not the WAV payloads themselves. The Word
manuscript is maintained separately and is not part of this deposit.

## Explicit exclusions

No raw or reconstructed audio, video, images, source archives, credentials,
local virtual environments, caches, Git history, or private working files are
included in this benchmark-kit ZIP. The separate audio package contains only
the 820 accepted ISD WAV files; it excludes 201 unresolved/excluded mappings,
lockdown audit-only files, duplicate source archives, and all non-ISD media.

## Participant data

Response tables contain pseudonymous source-study participant identifiers and
analysis variables such as age, gender, language, and institution where
available in the cited source datasets. They contain no names, email addresses,
telephone numbers, postal addresses, or IP addresses. Source-study terms,
ethical approvals, and consent conditions remain authoritative. The private
draft must be reviewed with UCL research data support before any public access
setting is selected.

## Licensing

`LICENSE` applies to MOSAIQ source code. Source-derived records retain their
source-specific terms. `DATA_LICENSE.md` and
`benchmark/governance/license_consent_registry.csv` define the current
licensing boundary and unresolved actions. In particular, ARAUS remains subject
to its source terms and per-file media review. The ISD audio extension retains
the source DOI, version, CC BY 4.0 attribution, per-asset manifest, and
checksums. Do not publish the package set until the public-release checklist is
complete.

The private draft also has a separately labelled ARAUS v1 source register. It
freezes the official ARAUS v4.2 and USotW sources, source checksums, scope
decisions, and acquisition code. It is not an ARAUS media archive and does not
change the ISD-only audio coverage of this release candidate.

## Integrity and reproduction

From the extracted archive root:

```bash
sha256sum -c checksums.sha256
uv sync --locked
uv run pytest -q
uv run python scripts/validate_benchmark_tasks.py
uv run python scripts/validate_benchmark_splits.py
uv run python scripts/build_benchmark_report.py --check-only
uv run python scripts/validate_tabular_baselines.py
uv run python scripts/validate_robustness_evaluation.py
uv run python scripts/validate_paper2_fixed_outputs.py
```

See `docs/reproduce_benchmark.md` for the complete workflow.

## Before public release

The authoritative outstanding gates are in
`benchmark/release_checklist.md`. They include source-rights and consent review,
owner approval, independent usability testing, a clean GitHub release, final
author/funder metadata, and an explicit decision about the media release.

# UCL RDR package plan

## Preparation status

The no-audio `0.1.0-dev` private-draft archive, repository metadata, licensing
notice, file-level checksum manifest, and pre-audio work plan were prepared and
independently validated on 24 July 2026. No RDR record has been created and no
file has been uploaded. Public release and DOI creation remain unauthorised.

The archive is generated with:

```bash
uv run python scripts/build_rdr_package.py \
  --output-dir "/path/to/rdr"
```

This writes a ZIP and a sibling `.zip.sha256` checksum file. The validation
evidence is recorded in `docs/release/rdr_package_audit_2026-07-24.md`.

## Deposit identity

- Working title: MOSAIQ soundscape benchmark v0.1.
- Candidate freeze: `mosaiq-benchmark-v0.1-candidate-20260716`.
- Split version: `0.1.0`.
- Paper-output freeze: `mosaiq-paper2-fixed-v0.1.0-20260721`.
- Public DOI: pending UCL RDR or Zenodo deposition.

## Package A - always shareable code and documentation

- Source code and locked environment.
- Task configurations, schemas, splits, manifests, and checksums.
- Validation reports, model cards, data cards, and release documentation.
- Result submission template and validator.
- Paper-facing generated tables and figures.

## Package B - harmonised tabular data

- `catalogue/` and permitted resources under `datasets/`.
- Per-file source attribution and licence registry.
- Provenance and source-version checksums.
- A README describing every resource and column family.

Package B can be deposited only after the final owner/licence review recorded
in `benchmark/release_checklist.md`.

## Package C - raw or reconstructed media

Raw audio and video must be partitioned by rights status:

- redistribute with attribution;
- reconstruct/download from source;
- managed access;
- do not redistribute.

ARAUS raw media are blocked pending per-file review. No raw media are included
in the current candidate.

## Repository metadata

The RDR record should include authors, affiliations, ORCIDs, abstract, keywords,
funding, related source DOIs, related paper DOI, software repository URL,
licences, version, temporal coverage, and a clear statement that participant
counts are not de-duplicated across source datasets.

## Pre-deposit checks

1. Build from a clean release tag.
2. Run every CI validation command.
3. Generate a recursive SHA-256 manifest for the deposit.
4. Open the archive on a second machine and complete the usability protocol.
5. Confirm that no local paths, credentials, direct identifiers, or
   unlicensed media are present.
6. Deposit Package A and the permitted parts of Package B.
7. Record the DOI in `CITATION.cff`, the manuscript, and release metadata.

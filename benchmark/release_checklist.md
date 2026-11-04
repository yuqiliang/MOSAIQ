# MOSAIQ public-release requirements

These requirements describe the evidence needed for a public benchmark release.
They are separate from personal progress records and administrative deposit logs.

## Reproducibility

- Dataset packages and declared source schemas validate.
- Task contracts, eligibility rules and exclusions are versioned.
- Splits satisfy their grouping, leakage and determinism constraints.
- Frozen manifests and input/output checksums reproduce.
- Baseline predictions, model cards and uncertainty analyses validate.
- Data cards, attribution, submission format and reproduction instructions exist.
- Public archives exclude personal notes, meeting records and work audits.

## Data and scientific scope

- Resolve or explicitly document excluded identifier conflicts.
- Confirm source-specific redistribution rights, including ARAUS per-file terms.
- Confirm consent, participant-data handling and access requirements.
- Confirm the licence for MOSAIQ-authored metadata and documentation.
- Report audio and visual coverage by dataset and version.
- Describe the ISD audio reference separately from the tabular candidate.
- Do not claim learned audio, fusion or noise experiments that have no results.
- Complete independent reproduction and scientific review before final release.

## Archival publication

- Confirm author, affiliation, funding and citation metadata.
- Create a release tag and an immutable permitted source archive.
- Deposit the permitted files in an archival repository and record its DOI.
- Replace pending identifiers with the actual release commit and archive.
- Provide appropriate reviewer access for manuscript submission.

Passing internal CI demonstrates consistency of the tested artefacts. Public
release status must be established separately from those technical checks.

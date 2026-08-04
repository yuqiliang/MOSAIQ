# MOSAIQ RDR package audit

Audit date: 24 July 2026

Scope: private-draft, no-audio MOSAIQ `0.1.0-dev` archive. This audit does not
authorise public release, assign a public data licence, or resolve the external
gates in `benchmark/release_checklist.md`.

## Package controls

- Archive built from an explicit allow-list of release files and directories.
- `.git`, `.venv`, caches, credentials, private environment files, symbolic
  links, Word manuscripts, and common audio/video payload extensions excluded.
- Root `RDR_README.md`, `file_manifest.csv`, and `checksums.sha256` added.
- ZIP timestamps normalised and files ordered deterministically.
- Sibling `.zip.sha256` generated for repository-side upload verification.

## Content audit

- 319 content files listed in the internal checksum manifest.
- 321 total archive files after adding the two root manifests.
- Zero `.wav`, `.mp3`, `.flac`, `.mp4`, `.mov`, or `.avi` payloads.
- Zero personal absolute paths.
- Zero contact email addresses in structured data.
- Zero `.env`, private-key, Git-history, virtual-environment, or cache paths.
- Direct identifiers such as names, email addresses, telephone numbers, postal
  addresses, and IP addresses are not present.
- Response tables retain pseudonymous participant identifiers and source-study
  analysis variables. Source terms and consent conditions remain authoritative.

## Clean-extraction verification

A fresh extraction was used for every check:

- Internal SHA-256 manifest: all files `OK`.
- Locked environment installation: passed.
- Unit tests: 9 passed.
- Frictionless catalogue and ISD, ARAUS, SATP, DeLTA packages: all `VALID`.
- Task registry: 7 tasks passed.
- Split version `0.1.0`: passed.
- Benchmark freeze check: passed.
- Tabular baselines: 17 experiments and 498 metric rows passed,
  `audio_used=false`.
- Robustness outputs: 3 stochastic models x 5 seeds, 123 bootstrap intervals,
  34 paired comparisons, 24 coverage rows, and 6 GPR calibration rows passed.
- Paper 2 fixed outputs: 12 tables, 6 figures, and 23 manifested files passed.

## Remaining release blockers

- ARAUS source-term and per-file rights review.
- Owner confirmation for the proposed licence on MOSAIQ-generated content.
- UCL confirmation of participant-data, ethics, consent, and access wording.
- Independent external usability review.
- Final author, ORCID, funding, and co-author approval.
- Clean GitHub release and final decision on tabular-only versus media-bearing
  public scope.

The ZIP is suitable for a private RDR draft and controlled review. It is not
suitable for public publication until the applicable blockers are closed.

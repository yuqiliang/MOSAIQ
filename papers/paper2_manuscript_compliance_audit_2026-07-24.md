# Paper 2 manuscript and journal-compliance audit

Audit date: 24 July 2026<br>
Review pass: 3 of 3<br>
Target: Scientific Data Data Descriptor

## Audited manuscript

`MOSAIQ_Paper2_ScientificData_Draft_v0.1.0.docx` (maintained outside the
repository in the project manuscript directory)

SHA-256: `de5a0deeba91019ab79daccd3997ca27121a9a652824888cb95b536694208474`

The checksum must be recomputed if the Word file changes.

## Scientific Data structure

| Requirement | Result |
| --- | --- |
| Objective title under 110 characters | PASS: 78 characters |
| No self-constructed acronym in title | PASS |
| Abstract approximately <=170 words | PASS: 147 words |
| Background & Summary | PASS |
| Methods | PASS |
| Data Records | PASS |
| Data Overview | PASS, limited to resource and split orientation |
| Technical Validation | PASS |
| Usage Notes | PASS |
| Data Availability | CONDITIONAL: candidate URL present, DOI pending |
| Code Availability | CONDITIONAL: repository present, immutable tag/DOI pending |
| References and formal data citations | PASS for draft; final metadata check required |
| Author Contributions | Draft present; author confirmation pending |
| Competing Interests | Draft present; author confirmation pending |
| Acknowledgements and Funding | Administrative confirmation pending |
| Ethics statement | Secondary-data statement present in Methods |

## Content boundary

- Paper 1 remains the schema/interoperability contribution.
- Paper 2 documents construction, splits, validation, baselines, and reusable
  benchmark evidence.
- Baselines are presented as technical validation, not architecture novelty.
- The manuscript does not claim that source datasets are statistically
  interchangeable.
- The manuscript repeatedly states the no-audio scope and model limitations.
- No numerical TODO from the deleted Markdown draft remains.

## Numerical consistency

The manuscript uses:

- 27,850 clips/stimuli;
- 59,935 responses;
- 5,078 summed participants;
- seven tasks and eleven manifests;
- split version 0.1.0;
- 47 PASS, 2 WARN, 0 FAIL;
- 17 experiments and 498 metric rows;
- five stochastic seeds and 2,000 cluster-bootstrap resamples;
- 43.3% ISD shared-six clip coverage;
- 48 ARAUS test records.

These agree with the validated fixed-output package.

## Word quality assurance

- One portrait US Letter section with 0.75-inch margins.
- Times New Roman throughout.
- 14 Heading 1 and 21 Heading 2 paragraphs.
- Six machine-readable Word tables.
- Seven inline figures with captions and alt text.
- Twelve rendered pages inspected at full size.
- No clipped table, overlapping text, blank page, or inaccessible image found.
- Accessibility audit: 0 high, 0 medium, 0 low findings.

## Submission blockers

1. Scientific Data requires data to be downloadable for first review and in a
   formal repository by later review. The archival deposit and DOI are absent.
2. Final corresponding-author email, ORCID, affiliations, funding, contributor
   roles, acknowledgements, and competing-interest confirmations are absent.
3. Source rights and exact source-version checksums are not final.
4. Independent usability and co-author reviews are not complete.
5. The journal may ask whether the secondary compilation adds sufficient value
   beyond its inputs; the submission should foreground fixed task manifests,
   leakage-aware splits, validation evidence, and reusable evaluation records.
6. If the intended submission is called multimodal MOSAIQ-v1.0, audio/visual
   assets and models must be added first. The current manuscript is suitable
   only for the explicitly tabular candidate scope.

## Pass-3 conclusion

The Word manuscript is a complete, evidence-backed draft with journal-aligned
structure and no unresolved numerical placeholders. It is not submission-ready
until the DOI/data-access, rights, author, funding, and external-review gates
are completed.

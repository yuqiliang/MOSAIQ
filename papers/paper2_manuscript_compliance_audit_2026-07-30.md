# Paper 2 manuscript and journal-compliance audit

Audit date: 30 July 2026<br>
Review pass: 3 of 3<br>
Target: Scientific Data Data Descriptor

## Audited manuscript

`MOSAIQ_Paper2_ScientificData_Draft_v0.2.0_audio_reference.docx`, maintained
outside the repository in the project manuscript directory.

SHA-256:
`1f34c54acf4b063af4ded44aa80967d44030dad83260186953fa20729421a787`

## Scientific Data structure

| Requirement | Result |
| --- | --- |
| Background & Summary | PASS |
| Methods | PASS; separate ISD audio extension documented |
| Data Records | PASS; audio cohort, exclusions, and storage boundary documented |
| Technical Validation | PASS; QC, reference results, and uncertainty included |
| Usage Notes | PASS; calibration, scope, and generalisation limits explicit |
| Data Availability | CONDITIONAL; Zenodo source cited, MOSAIQ DOI pending |
| Code Availability | CONDITIONAL; repository present, immutable tag/DOI pending |
| References and data citations | PASS for working draft; final metadata check pending |
| Author and administrative statements | Drafted; confirmation pending |

## Numerical and version consistency

- The no-audio `mosaiq-paper2-fixed-v0.1.0-20260721` output freeze remains
  unchanged.
- The audio extension is separately identified as `0.1.0-audio`.
- The manuscript reports 1,021 mappings, 820 accepted clips, 201 exclusions,
  48 audio metric rows, and 2,988 held-out audio predictions.
- Clip-level Eventfulness RMSE changes from 0.3198 to 0.2924; the paired
  improvement is 0.0274 with 95% CI 0.0138 to 0.0421.
- Pleasantness is explicitly reported as not improved by descriptor Ridge.

## Word quality assurance

- Twelve pages rendered and inspected.
- Tables, figures, headings, captions, pagination, and all references are
  visible without clipping or overlap.
- Accessibility audit: 0 high, 0 medium, and 0 low findings.
- The versioned v0.1.0 source draft is preserved.

## Submission blockers

1. A formal MOSAIQ archival deposit, DOI, immutable code tag, and anonymous
   reviewer access are absent.
2. Final rights, author metadata, funding, contributions, acknowledgements, and
   competing-interest confirmation are pending.
3. External usability and co-author reviews are intentionally paused.
4. The release boundary must decide whether audio evidence enters a new Paper 2
   fixed-output version.
5. The current audio references do not establish multimodal or state-of-the-art
   performance.

## Pass-3 conclusion

The Word file is a coherent journal-aligned working draft and accurately
describes both the no-audio freeze and the separate ISD audio reference
extension. It is not submission-ready until the DOI/access, rights, release
boundary, author, and review gates are complete.

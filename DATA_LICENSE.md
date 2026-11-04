# MOSAIQ data licensing

The MIT licence in `LICENSE` applies to MOSAIQ source code. It does not replace
the licences, consent conditions, or terms attached to source datasets and
media assets.

MOSAIQ v0.1 is a secondary tabular benchmark candidate. A separately
versioned private-draft extension contains 820 accepted ISD WAV files under
the source record's declared CC BY 4.0 licence. The core contains harmonised
metadata, identifiers, perceptual responses, derived tabular features, split
assignments, manifests, predictions, and validation outputs. Source-specific
terms remain authoritative for every redistributed record and media asset.

## Release rule

- ISD, SATP, and DeLTA records are distributed only to the extent allowed by
  their cited source records and declared licences.
- The ARAUS v4.2 record declares CC BY-NC 4.0. The depositor reports that use
  has been discussed with the responsible ARAUS contact, but written public
  redistribution scope and participant-data wording remain pending. Raw ARAUS
  audio, masker, and visual files must not be publicly redistributed from
  MOSAIQ until the per-file review in
  `benchmark/governance/license_consent_registry.csv` is complete.
- Raw audio and video are not included in the v0.1 core repository package.
  The RDR private-draft upload stores the permitted ISD-only audio extension in
  one ZIP64 archive with attribution, a per-file manifest, and checksums. It
  does not redistribute ARAUS, SATP, or DeLTA raw media. A separate private
  draft ARAUS v1 source register freezes official URLs, scope decisions, source
  checksums, and an acquisition script; it contains no ARAUS or USotW media.
- MOSAIQ-generated split files, task definitions, validation reports, and
  original documentation are intended for release under CC BY 4.0, subject to
  confirmation by the copyright holders before the public DOI freeze.
- Where a source licence and the proposed MOSAIQ documentation licence differ,
  the more restrictive source terms control the source-derived content.

This file records release policy, not legal advice. The machine-readable
registry and the source repository records must be reviewed again immediately
before a public deposit.

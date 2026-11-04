# MOSAIQ audio data dictionary

## Source acquisition registry

`benchmark/governance/isd_zenodo_source_registry.csv` records one row per file
in the official Zenodo record.

| Column | Meaning |
|---|---|
| `dataset_id` | MOSAIQ source dataset namespace. |
| `source_record` | Persistent DOI URL for the source record. |
| `source_version` | Source release version used for the freeze. |
| `file_name` | Exact Zenodo file key. |
| `file_role` | Audio, metadata, survey, sound-level, or source-code role. |
| `benchmark_scope_status` | Candidate, supporting, or source-audit-only role. |
| `size_bytes` | Byte size declared by the Zenodo API. |
| `checksum_algorithm` | Source checksum algorithm, currently MD5. |
| `checksum` | Checksum declared by Zenodo. |
| `download_url` | Official Zenodo API content URL. |
| `licence_spdx` | Licence declared by the source record. |
| `redistribution_status` | MOSAIQ release interpretation of the source terms. |
| `metadata_checked_at` | Date the API metadata was checked. |
| `local_status` | Not downloaded, verified, or invalid. |
| `local_relative_path` | Relative working-storage path; never an absolute path. |

## Audio asset manifest

The schema is `benchmark/audio/audio_manifest.schema.yaml`. One row represents
one source WAV candidate or one expected clip for which no source asset was
found.

| Column | Meaning |
|---|---|
| `asset_id` | Stable MOSAIQ identifier derived from archive and member path. |
| `dataset_id` | Source dataset, currently `ISD`. |
| `clip_id` | Linked MOSAIQ clip when mapping succeeds. |
| `split` | Frozen split inherited from the linked clip. |
| `source_record` | Source DOI. |
| `source_version` | Exact source version. |
| `archive_name` | Zenodo archive containing the source member. |
| `member_path` | Exact path recorded in the ZIP central directory. |
| `local_relative_path` | Path relative to external audio working storage. |
| `source_uri` | DOI or archive download URL. |
| `licence_spdx` | Source licence identifier. |
| `redistribution_status` | Whether and how the asset can be redistributed. |
| `access_class` | Open, embargoed, managed, or unavailable. |
| `group_id_normalized` | Filename-derived GroupID after documented alias cleanup. |
| `location_hint` | Source member parent directory used as a mapping hint. |
| `audio_sha256` | Byte-level checksum of the extracted WAV. |
| `bytes` | Extracted WAV size. |
| `format` | Container format. |
| `sample_rate_hz` | Sample rate read from the WAV header. |
| `channels` | Channel count read from the WAV. |
| `frames` | Number of audio frames. |
| `duration_s` | `frames / sample_rate_hz`. |
| `expected_duration_s` | Duration recorded in the harmonised ISD clip table. |
| `sample_dtype` | Actual decoded sample dtype. |
| `calibration_status` | Current calibration metadata state. |
| `materialization_status` | Whether the waveform is locally available. |
| `mapping_status` | Matched, missing, ambiguous, duplicate, or conflicting. |
| `use_for_benchmark` | True only for a unique, materialised, accepted mapping. |
| `mapping_notes` | Human-readable explanation of mapping decisions. |

## Mapping statuses

- `matched`: unique accepted source-to-clip link.
- `missing_source_asset`: a clip is in archive scope but no WAV candidate exists.
- `unmatched_source_asset`: a WAV has no corresponding MOSAIQ clip.
- `ambiguous_clip_match`: more than one clip could match.
- `exact_duplicate_excluded`: byte-identical duplicate; one canonical copy kept.
- `duplicate_conflict`: non-identical WAVs map to the same clip.

## Quality-control output

`benchmark/audio/qc/*.csv` contains one row per usable asset. `status=fail`
means the file must not enter a benchmark. `warn` keeps the file eligible while
recording an unresolved non-fatal condition.

Technical checks cover readability, non-empty data, finite samples, non-zero
signal, sample rate, channels, duration agreement, actual encoding, peak,
RMS, zero fraction, and float amplitude scale. Calibration is reported
separately and is not inferred from waveform amplitude.

## Waveform descriptors

`benchmark/audio/features/*.csv` contains deterministic relative descriptors:
RMS, peak, crest factor, zero-crossing rate, stereo correlation, spectral
centroid, bandwidth, 85% rolloff, and three normalized band-power ratios.

These descriptors validate the audio training interface without claiming
calibrated sound-level prediction. They are suitable for the
`audio_descriptor_ridge` reference baseline. RMS and peak are retained for QC
but excluded from that model until calibration metadata are confirmed.
Calibration-dependent claims must use source-validated calibration metadata.

## Frozen cohort

`benchmark/audio/cohort/v0.1.0/isd_audio_cohort.csv` contains one row per
accepted waveform. `isd_audio_exclusions.csv` records every rejected manifest
row and its reason. `isd_audio_cohort_summary.yaml` records split counts,
cross-split SHA checks, and exclusion counts. `checksums.sha256` locks the
manifest, QC, cohort, exclusions, and summary used for the freeze.

## Baseline outputs

`benchmark/audio/results/v0.1.0/metrics.csv` contains one row per model, task,
partition, target, and metric. `predictions.csv` contains one held-out
prediction per record and target, with both `record_id` and the parent
`clip_id`. Response-level predictions inherit the clip split.

`evaluation/bootstrap_intervals.csv` reports 95% intervals for RMSE and MAE.
`evaluation/paired_comparisons.csv` reports the paired RMSE difference between
Target Mean and Ridge. Both resample `clip_id`, retaining all responses from a
sampled clip together.

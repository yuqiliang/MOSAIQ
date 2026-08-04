# ISD audio smoke report

Status date: 30 July 2026

## Source acquisition

The official ISD Zenodo record `10.5281/zenodo.10672568`, version
`1.0.1-alpha.1`, was queried through the Zenodo API. The record declares
CC BY 4.0. The following files were downloaded and verified against source MD5:

- `ISD v1.0 Data.csv`;
- `ISD v1.0 Metadata.xlsx`;
- `WAV_Groningen_1.zip`.

The remaining ISD WAV archives are being acquired separately from Git.

The verified `WAV_Lockdown_Venice.zip` contains 94 WAV files but none of their
GroupIDs link to a current MOSAIQ ISD clip. It is therefore source-audit-only,
not an eligible supervised benchmark archive. The lockdown archives are kept
separate from the seven normal-session candidate archives.

## Mapping

`WAV_Groningen_1.zip` contains 52 WAV members representing 51 unique normalized
GroupIDs. The MOSAIQ location scope contains 59 clips.

- 51 clips have one accepted audio mapping.
- 8 expected clips have no WAV candidate in the source archive.
- `NP102.wav` and `NP102.1.wav` are byte-identical; one is explicitly excluded.
- `NP125.hdf.wav` is mapped through the documented `.hdf` filename alias.
- All 51 accepted clips inherit the frozen `test` split.

Because no Groningen asset belongs to train or development, the subset is a
pipeline smoke test only and cannot support an official trained baseline.

## Technical QC

All 51 accepted WAV files:

- are readable and non-empty;
- contain finite, non-zero samples;
- are 48 kHz and stereo;
- agree with tabular expected duration within 0.005 seconds.

No technical failures were observed. Every file retains warnings for pending
calibration review and for a source-description encoding discrepancy: the
record prose describes 32-bit floating-point WAV, while the inspected
Groningen files decode as `int16`.

An interim Granada/Groningen/London 1 dry run also observed both 44.1 kHz and
48 kHz source files. Both are accepted source rates; learned waveform models
will resample to 48 kHz under the frozen preprocessing configuration.

## Descriptor interface

Eleven deterministic relative waveform descriptors were extracted for every
accepted file with no non-finite feature rows. These validate the
`audio_descriptor_ridge` interface without making calibrated sound-level
claims.

## Release interpretation

The smoke result establishes acquisition, integrity, mapping, split inheritance,
QC, and feature extraction. It does not establish full ISD audio coverage,
model performance, ARAUS CNN reproduction, multimodal improvement, or final
MOSAIQ-v1.0 readiness.

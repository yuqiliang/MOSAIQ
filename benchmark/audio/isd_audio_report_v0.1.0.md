# ISD audio track report v0.1.0

Status date: 30 July 2026

## Scope

This report freezes the first trainable MOSAIQ audio track. It links
rights-cleared WAV files from ISD Zenodo record
<https://doi.org/10.5281/zenodo.10672568>, source version
`1.0.1-alpha.1`, to the existing MOSAIQ ISD clips and split version `0.1.0`.
It does not change the no-audio Paper 2 fixed-output freeze and does not imply
that ARAUS, SATP, or DeLTA audio is available.

## Source and cohort

All seven benchmark-candidate WAV archives were downloaded, verified against
the source MD5 values, and safely extracted outside Git. The two lockdown
archives were also verified but remain source-audit-only because their
recordings do not have a reliable MOSAIQ label linkage.

The complete manifest contains 1,021 rows. The frozen cohort accepts 820 unique
audio-to-clip mappings:

| Split | Accepted clips |
|---|---:|
| Train | 546 |
| Development | 154 |
| Test | 120 |

The exclusion table records 201 rows: 143 expected clips without a source WAV,
52 source WAVs without a MOSAIQ clip, three ambiguous mappings, one
byte-identical duplicate, and two rows already excluded by the frozen split.
No accepted waveform SHA-256 occurs in more than one split.

## Technical validation

All 820 accepted WAV files are readable, finite, non-empty, non-silent,
stereo, and within 0.005 seconds of the harmonised clip duration. There are
341 files at 44.1 kHz and 479 at 48 kHz. The actual encodings are 769
`float32` files and 51 `int16` Groningen files.

Every asset retains a warning because calibrated sound-pressure metadata have
not been confirmed. In addition, 247 float files have an absolute peak of at
least one and require amplitude-scale interpretation, while the 51 Groningen
files differ from the source prose that describes 32-bit floating-point WAV.
These are provenance and calibration warnings, not decoding failures.

## Reference baselines

The executed baselines are an input-free training target mean and Ridge
regression over nine deterministic relative waveform descriptors. RMS and peak
are retained for QC but excluded from Ridge until calibration metadata are
confirmed. Both models use the frozen train partition and are evaluated on dev
and test only.

At clip level, Ridge improves test Eventfulness RMSE from 0.3198 to 0.2924
(paired improvement 0.0274; 95% cluster-bootstrap CI 0.0138 to 0.0421), but
worsens test Pleasantness RMSE from 0.2812 to 0.3043 (improvement -0.0231;
95% CI -0.0485 to 0.0033).

At response level, all assessments inherit their clip split. The complete
cohort contains 967 train, 258 dev, and 215 test responses. Ridge improves test
Eventfulness RMSE by 0.0271 (95% CI 0.0137 to 0.0399), while its test
Pleasantness difference is inconclusive (improvement -0.0053; 95% CI -0.0286
to 0.0179). Bootstrap sampling is clustered by `clip_id`.

## Interpretation boundary

These results establish a reproducible audio ingestion, validation, training,
prediction, and uncertainty interface. They do not establish state-of-the-art
soundscape prediction. The descriptor Ridge is deliberately low capacity and
its mixed held-out performance makes that limitation visible.

The preregistered learned log-mel CNN, frozen pretrained encoder, tabular-audio
fusion, missing-modality, and added-noise experiments remain separate future
runs. An ISD-adapted CNN must not be described as a reproduction of the ARAUS
model. External usability review and Paper 2 co-author review remain deferred
by the user.

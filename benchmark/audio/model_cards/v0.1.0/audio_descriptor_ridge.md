# audio_descriptor_ridge

## Summary

Ridge regression over deterministic relative waveform descriptors.

## Contract

- Dataset: ISD
- Tasks: `isd_audio_clip_iso_coordinates`, `isd_audio_response_iso_coordinates`
- Inputs: audio waveform descriptors
- Targets: clip-mean and individual-response ISO Pleasantness and Eventfulness
- Split version: `0.1.0`
- Audio used: `true`
- Clip-task train/dev/test rows: 546/154/120
- Response-task train/dev/test rows: 967/258/215
- Calibration status: `relative_descriptors_only_pending_source_review`

## Results

| task_id                            | partition   | target           | metric   |   value |   n |   n_clips |
|:-----------------------------------|:------------|:-----------------|:---------|--------:|----:|----------:|
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOPleasant | rmse     |  0.4559 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOPleasant | mae      |  0.3766 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOPleasant | r2       | -0.2267 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOEventful | rmse     |  0.2856 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOEventful | mae      |  0.2345 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOEventful | r2       | -0.0425 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOPleasant | rmse     |  0.3043 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOPleasant | mae      |  0.2468 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOPleasant | r2       | -0.1788 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOEventful | rmse     |  0.2924 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOEventful | mae      |  0.2390 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOEventful | r2       | -0.0882 | 120 |       120 |
| isd_audio_response_iso_coordinates | dev         | ISOPleasant      | rmse     |  0.4790 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOPleasant      | mae      |  0.3973 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOPleasant      | r2       | -0.2712 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOEventful      | rmse     |  0.3061 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOEventful      | mae      |  0.2495 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOEventful      | r2       | -0.0117 | 258 |       154 |
| isd_audio_response_iso_coordinates | test        | ISOPleasant      | rmse     |  0.3230 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOPleasant      | mae      |  0.2683 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOPleasant      | r2       | -0.0351 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOEventful      | rmse     |  0.3428 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOEventful      | mae      |  0.2798 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOEventful      | r2       | -0.1567 | 215 |       120 |

## Limitations

- ISD-only audio coverage; no cross-dataset audio claim.
- Relative waveform descriptors do not establish calibrated level.
- Missing or ambiguous source assets are excluded before training.
- Results are valid only for split version 0.1.0 and the frozen audio cohort.

# audio_target_mean

## Summary

Input-free reference that predicts the training-set target mean.

## Contract

- Dataset: ISD
- Tasks: `isd_audio_clip_iso_coordinates`, `isd_audio_response_iso_coordinates`
- Inputs: none
- Targets: clip-mean and individual-response ISO Pleasantness and Eventfulness
- Split version: `0.1.0`
- Audio used: `true`
- Clip-task train/dev/test rows: 546/154/120
- Response-task train/dev/test rows: 967/258/215
- Calibration status: `relative_descriptors_only_pending_source_review`

## Results

| task_id                            | partition   | target           | metric   |   value |   n |   n_clips |
|:-----------------------------------|:------------|:-----------------|:---------|--------:|----:|----------:|
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOPleasant | rmse     |  0.4692 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOPleasant | mae      |  0.3908 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOPleasant | r2       | -0.2996 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOEventful | rmse     |  0.2862 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOEventful | mae      |  0.2370 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | dev         | mean_ISOEventful | r2       | -0.0468 | 154 |       154 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOPleasant | rmse     |  0.2812 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOPleasant | mae      |  0.2353 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOPleasant | r2       | -0.0066 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOEventful | rmse     |  0.3198 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOEventful | mae      |  0.2620 | 120 |       120 |
| isd_audio_clip_iso_coordinates     | test        | mean_ISOEventful | r2       | -0.3019 | 120 |       120 |
| isd_audio_response_iso_coordinates | dev         | ISOPleasant      | rmse     |  0.5081 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOPleasant      | mae      |  0.4244 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOPleasant      | r2       | -0.4303 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOEventful      | rmse     |  0.3050 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOEventful      | mae      |  0.2461 | 258 |       154 |
| isd_audio_response_iso_coordinates | dev         | ISOEventful      | r2       | -0.0049 | 258 |       154 |
| isd_audio_response_iso_coordinates | test        | ISOPleasant      | rmse     |  0.3177 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOPleasant      | mae      |  0.2656 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOPleasant      | r2       | -0.0017 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOEventful      | rmse     |  0.3699 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOEventful      | mae      |  0.3058 | 215 |       120 |
| isd_audio_response_iso_coordinates | test        | ISOEventful      | r2       | -0.3466 | 215 |       120 |

## Limitations

- ISD-only audio coverage; no cross-dataset audio claim.
- Relative waveform descriptors do not establish calibrated level.
- Missing or ambiguous source assets are excluded before training.
- Results are valid only for split version 0.1.0 and the frozen audio cohort.

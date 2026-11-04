# MOSAIQ Paper 2 generated evidence insert

Freeze ID: `mosaiq-paper2-fixed-v0.1.0-20260721`<br>
Output version: `0.1.0`<br>
Benchmark version: `0.1.0-dev`<br>
Split version: `0.1.0`<br>
Scope: no-audio tabular benchmark v0.1

This file contains generated evidence blocks for the Scientific Data manuscript.
The prose may be integrated editorially, but numerical values must be updated by
rerunning the generator rather than manual editing.

## Data Records

The current MOSAIQ candidate materialises four source datasets as validated
clip- and response-level resources. Together they contain 27,850 clip or
stimulus rows and 59,935 response rows. The summed participant count is 5,078;
participants are not de-duplicated across source datasets.

| Dataset | Target family | Clips | Responses | Participants |
| --- | --- | --- | --- | --- |
| ISD | ISO PAQ and ISO coordinates | 2709 | 3589 | 2664 |
| ARAUS | ISO PAQ, ISO coordinates, appropriateness | 22224 | 27255 | 605 |
| SATP | Multilingual ISO PAQ and ISO coordinates | 27 | 17441 | 645 |
| DeLTA | Annoyance and 24 sound-source labels | 2890 | 11650 | 1164 |
| Total | dataset-specific | 27850 | 59935 | 5078 |

## Released splits

MOSAIQ split version `0.1.0` uses dataset-specific leakage controls. ISD is
grouped by location; ARAUS preserves source folds; SATP uses deterministic
five-fold evaluation because it has 27 recordings; and DeLTA uses iterative
multilabel stratification over source labels and annoyance bins. Response-level
ISD assessments inherit their clip partition through `clip_id`.

| Dataset | Partition | Clips |
| --- | --- | --- |
| ISD | dev | 524 |
| ISD | excluded | 5 |
| ISD | test | 581 |
| ISD | train | 1599 |
| ARAUS | dev | 4440 |
| ARAUS | excluded | 6 |
| ARAUS | test | 48 |
| ARAUS | train | 17730 |
| SATP | 0 | 5 |
| SATP | 1 | 5 |
| SATP | 2 | 5 |
| SATP | 3 | 6 |
| SATP | 4 | 6 |
| DeLTA | dev | 441 |
| DeLTA | test | 437 |
| DeLTA | train | 2012 |

## Technical Validation

The candidate freeze passes 47 checks, retains two documented warnings, and has
no failures. The warnings concern two excluded ISD identifier collisions and
the need for per-file ARAUS raw-asset licence review. Eleven task/dataset
manifests lock eligible record IDs and source-row hashes. Asset references are
complete, but waveform and video files are not materialised in this no-audio
release. Shared psychoacoustic features are complete for ARAUS and available
for 43.3% of ISD clips; SATP and DeLTA do not contain the shared6 set.

## Baseline methods

The 17 experiments were executed through a unified train, predict, and
evaluate interface. Numeric preprocessing and categorical encoding were fitted
on the training partition only. The suite includes Target Mean, LAeq Ridge,
shared6 Ridge, an ARAUS shared6 Elastic Net transfer, reduced-feature linear,
RF, XGBoost and GPR models, DeLTA label prevalence and annoyance-conditioned
source classification, and source-conditioned annoyance regression. The ARAUS
Elastic Net is not the full published 264-feature replication, and the reduced
Tong-style models omit unavailable CitySeg, OSM, THD, and related variables.
No model consumes audio; every run records `audio_used=false`.

## ISD response-level results

All models below use the same shared6 complete-case cohort: 1,324 train and 279
test responses. Test responses represent 184 unique clips. No reduced
Tong-style model stably improves both ISO targets over the matched Target Mean
reference on held-out locations.

| model_id | target | n_train | n_eval | rmse | rmse_ci_low | rmse_ci_high | mae | r2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| isd_response_target_mean_shared6 | ISOEventful | 1324.000 | 279.000 | 0.338 | 0.309 | 0.367 | 0.269 | -0.188 |
| isd_response_target_mean_shared6 | ISOPleasant | 1324.000 | 279.000 | 0.310 | 0.290 | 0.332 | 0.260 | -0.000 |
| tong_style_reduced_gpr | ISOEventful | 1324.000 | 279.000 | 0.374 | 0.343 | 0.403 | 0.305 | -0.455 |
| tong_style_reduced_gpr | ISOPleasant | 1324.000 | 279.000 | 0.330 | 0.306 | 0.354 | 0.272 | -0.133 |
| tong_style_reduced_lr | ISOEventful | 1324.000 | 279.000 | 0.350 | 0.315 | 0.383 | 0.278 | -0.274 |
| tong_style_reduced_lr | ISOPleasant | 1324.000 | 279.000 | 0.301 | 0.277 | 0.325 | 0.247 | 0.061 |
| tong_style_reduced_rf | ISOEventful | 1324.000 | 279.000 | 0.320 | 0.292 | 0.349 | 0.254 | -0.065 |
| tong_style_reduced_rf | ISOPleasant | 1324.000 | 279.000 | 0.357 | 0.331 | 0.384 | 0.297 | -0.326 |
| tong_style_reduced_xgboost | ISOEventful | 1324.000 | 279.000 | 0.319 | 0.289 | 0.348 | 0.252 | -0.059 |
| tong_style_reduced_xgboost | ISOPleasant | 1324.000 | 279.000 | 0.343 | 0.320 | 0.367 | 0.287 | -0.221 |

## DeLTA annoyance results

Observed-source Ridge and RF both improve over Target Mean. Paired RMSE
improvement is 0.106 [0.054, 0.160] for Ridge and 0.103 [0.038, 0.165] for RF.
These are conditional models requiring observed source labels and are not
audio-to-annoyance systems.

| model_id | n_train | n_eval | rmse | rmse_ci_low | rmse_ci_high | mae | r2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delta_annoyance_from_observed_sources_rf | 2012.000 | 437.000 | 1.248 | 1.171 | 1.325 | 1.022 | 0.146 |
| delta_annoyance_from_observed_sources_ridge | 2012.000 | 437.000 | 1.245 | 1.167 | 1.326 | 1.013 | 0.150 |
| delta_annoyance_target_mean | 2012.000 | 437.000 | 1.352 | 1.273 | 1.430 | 1.124 | -0.001 |

## DeLTA source-label results

The annoyance-conditioned logistic classifier improves macro average precision,
macro F1, and micro F1, but reduces pooled micro average precision relative to
label prevalence. Macro, micro, and per-label results must therefore remain
visible together. The classifier uses observed mean annoyance and is not an
automatic audio source recogniser.

| model_id | metric | estimate | ci_low | ci_high |
| --- | --- | --- | --- | --- |
| delta_source_from_observed_annoyance_logistic | macro_average_precision | 0.161 | 0.159 | 0.181 |
| delta_source_from_observed_annoyance_logistic | macro_f1 | 0.210 | 0.198 | 0.221 |
| delta_source_from_observed_annoyance_logistic | micro_average_precision | 0.159 | 0.150 | 0.171 |
| delta_source_from_observed_annoyance_logistic | micro_f1 | 0.296 | 0.283 | 0.309 |
| delta_source_label_prevalence | macro_average_precision | 0.126 | 0.121 | 0.131 |
| delta_source_label_prevalence | macro_f1 | 0.197 | 0.191 | 0.203 |
| delta_source_label_prevalence | micro_average_precision | 0.428 | 0.402 | 0.454 |
| delta_source_label_prevalence | micro_f1 | 0.224 | 0.217 | 0.231 |

## Robustness methods and findings

RF and XGBoost were rerun with seeds 2026-2030. The largest test-RMSE standard
deviation was 0.0034. Test uncertainty was estimated with 2,000 cluster
bootstrap resamples; all responses linked to the same `clip_id` were sampled
together. Candidate-reference comparisons used paired resamples and were
direction-normalised so positive improvement favours the candidate.

Shared6 retains 31.7% of ISD test clips and 40.7% of test responses. Its test
Eventfulness mean is shifted by 0.61 SD at clip level and 0.53 SD at response
level, showing that complete-case results describe a selected subset. GPR
intervals under-cover at all tested levels; the nominal 80% Eventfulness
interval covers 57.3% of held-out responses.

## Usage and interpretation limits

- ARAUS test results contain 48 records and require explicit small-test caveats.
- Results from different `cohort_id`, `n_train`, or `n_eval` values are not a fair ranking.
- Bootstrap intervals quantify uncertainty in the current test sample, not external transfer.
- ISD shared6 complete cases are not representative of the full test cohort.
- DeLTA cross-target models require observed human labels at inference time.
- Audio, visual, multimodal, missing-modality, and added-noise evaluation remain future work.

## Figure index

| figure_id | filename | caption |
| --- | --- | --- |
| Figure_1 | figure_01_isd_response_rmse.png | Test RMSE for matched-cohort ISD response-level baselines. |
| Figure_2 | figure_02_isd_response_distributions.png | Observed and predicted ISD response distributions on the fixed ISO interval. |
| Figure_3 | figure_03_gpr_observed_predicted.png | Observed versus predicted ISD responses for the reduced-feature GPR baseline. |
| Figure_4 | figure_04_multiseed_stability.png | Test-RMSE standard deviation across five fixed seeds for stochastic baselines. |
| Figure_5 | figure_05_paired_rmse_improvement.png | Direction-normalised paired RMSE improvement with 95% cluster-bootstrap intervals. |
| Figure_6 | figure_06_coverage_and_calibration.png | ISD shared6 test coverage and GPR prediction-interval calibration. |

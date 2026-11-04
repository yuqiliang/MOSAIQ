# MOSAIQ Step 7 robustness report

Robustness version: `0.1.0`<br>
Benchmark version: `0.1.0-dev`<br>
Split version: `0.1.0`

## What each analysis does

1. **Multi-seed stability.** RF and XGBoost are trained five times with seeds
   2026, 2027, 2028, 2029, 2030. The mean shows typical performance and the standard deviation shows how much the answer changes because of estimator randomness.
2. **Cluster bootstrap confidence intervals.** Test `clip_id` values are sampled
   with replacement 2000 times. All responses attached to a sampled clip stay together. Percentile intervals therefore describe held-out sample uncertainty without treating repeated assessments as independent.
3. **Paired model comparison.** Reference and candidate predictions are aligned
   on exactly the same records and resampled together. Improvement is direction-normalized, so a positive value always favours the candidate. An interval crossing zero means the current test sample does not establish a stable advantage.
4. **Feature-coverage sensitivity.** ISD all-eligible and shared6-complete cohorts
   are compared within every partition at both clip and response level. Retention, target shifts, and target-mean errors reveal whether complete-case filtering changes the population being evaluated.
5. **GPR interval calibration.** Gaussian prediction intervals at 50%, 80%, and
   95% nominal coverage are compared with their empirical coverage. Negative calibration error means intervals are too narrow; positive error means they are conservative.

## Multi-seed test RMSE

| model_id | target | mean | std | minimum | maximum | n_seeds |
| --- | --- | --- | --- | --- | --- | --- |
| delta_annoyance_from_observed_sources_rf | mean_annoyance | 1.2467 | 0.0012 | 1.2455 | 1.2484 | 5.0000 |
| tong_style_reduced_rf | ISOEventful | 0.3204 | 0.0008 | 0.3196 | 0.3215 | 5.0000 |
| tong_style_reduced_rf | ISOPleasant | 0.3567 | 0.0013 | 0.3554 | 0.3586 | 5.0000 |
| tong_style_reduced_xgboost | ISOEventful | 0.3211 | 0.0015 | 0.3193 | 0.3226 | 5.0000 |
| tong_style_reduced_xgboost | ISOPleasant | 0.3442 | 0.0034 | 0.3403 | 0.3494 | 5.0000 |

## Paired improvements

| candidate_model | target | metric | improvement | ci_low | ci_high | probability_improvement_gt_zero |
| --- | --- | --- | --- | --- | --- | --- |
| delta_annoyance_from_observed_sources_rf | mean_annoyance | rmse | 0.1032 | 0.0378 | 0.1648 | 1.0000 |
| delta_annoyance_from_observed_sources_ridge | mean_annoyance | rmse | 0.1061 | 0.0544 | 0.1596 | 1.0000 |
| delta_source_from_observed_annoyance_logistic | __all__ | macro_average_precision | 0.0352 | 0.0334 | 0.0540 | 1.0000 |
| delta_source_from_observed_annoyance_logistic | __all__ | macro_f1 | 0.0127 | 0.0017 | 0.0231 | 0.9895 |
| delta_source_from_observed_annoyance_logistic | __all__ | micro_average_precision | -0.2686 | -0.2944 | -0.2435 | 0.0000 |
| delta_source_from_observed_annoyance_logistic | __all__ | micro_f1 | 0.0722 | 0.0624 | 0.0817 | 1.0000 |
| tong_style_reduced_gpr | ISOEventful | rmse | -0.0361 | -0.0529 | -0.0205 | 0.0000 |
| tong_style_reduced_gpr | ISOPleasant | rmse | -0.0199 | -0.0332 | -0.0073 | 0.0005 |
| tong_style_reduced_lr | ISOEventful | rmse | -0.0120 | -0.0376 | 0.0127 | 0.1765 |
| tong_style_reduced_lr | ISOPleasant | rmse | 0.0096 | -0.0080 | 0.0272 | 0.8690 |
| tong_style_reduced_rf | ISOEventful | rmse | 0.0180 | -0.0027 | 0.0377 | 0.9545 |
| tong_style_reduced_rf | ISOPleasant | rmse | -0.0469 | -0.0686 | -0.0260 | 0.0000 |
| tong_style_reduced_xgboost | ISOEventful | rmse | 0.0190 | -0.0014 | 0.0402 | 0.9655 |
| tong_style_reduced_xgboost | ISOPleasant | rmse | -0.0326 | -0.0508 | -0.0144 | 0.0005 |

## ISD shared6 test-cohort sensitivity

| task_id | target | n_records | n_all_eligible | coverage_fraction | shared6_minus_all_mean | standardized_mean_shift |
| --- | --- | --- | --- | --- | --- | --- |
| isd_individual_iso_prediction | ISOEventful | 279.0000 | 685.0000 | 0.4073 | 0.1467 | 0.5260 |
| isd_individual_iso_prediction | ISOPleasant | 279.0000 | 685.0000 | 0.4073 | 0.0545 | 0.1767 |
| iso_coordinate_regression | mean_ISOEventful | 184.0000 | 581.0000 | 0.3167 | 0.1447 | 0.6091 |
| iso_coordinate_regression | mean_ISOPleasant | 184.0000 | 581.0000 | 0.3167 | 0.0581 | 0.1955 |

## GPR prediction-interval calibration

| target | nominal_coverage | empirical_coverage | calibration_error | mean_interval_width |
| --- | --- | --- | --- | --- |
| ISOEventful | 0.5000 | 0.3154 | -0.1846 | 0.3421 |
| ISOEventful | 0.8000 | 0.5735 | -0.2265 | 0.6500 |
| ISOEventful | 0.9500 | 0.8100 | -0.1400 | 0.9940 |
| ISOPleasant | 0.5000 | 0.4373 | -0.0627 | 0.4243 |
| ISOPleasant | 0.8000 | 0.7599 | -0.0401 | 0.8062 |
| ISOPleasant | 0.9500 | 0.9104 | -0.0396 | 1.2330 |

## Main findings

- Estimator randomness is small relative to the observed model differences: the largest test RMSE standard deviation across the stochastic models is 0.0034.
- Both DeLTA source-conditioned annoyance models have positive paired RMSE, MAE, and R2 improvement intervals against Target Mean. This supports conditional predictability when source labels are observed; it does not establish audio-to-annoyance prediction.
- No reduced Tong-style model stably improves both ISD targets on held-out locations. RF and XGBoost have better Eventfulness point estimates, but their paired 95% intervals cross zero, while both significantly worsen Pleasantness. GPR is worse than Target Mean for both RMSE targets.
- The DeLTA annoyance-conditioned source classifier improves macro average precision, macro F1, and micro F1, but worsens pooled micro average precision. The prevalence baseline receives a high micro AP because its label-specific constant scores rank frequent labels above rare labels when every label-record decision is pooled. Macro and per-label results must therefore remain visible.
- Shared6 retains only 31.7% of ISD test clips and 40.7% of ISD test responses. Eventfulness is shifted by 0.61 SD at clip level and 0.53 SD at response level, so shared6 results describe a selected subset rather than the full ISD test population.
- GPR intervals under-cover at every tested level. For Eventfulness, the nominal 80% interval covers only 57.3%, indicating overconfident uncertainty estimates under the current held-out-location split.

## Validation scope and limits

- 111 bootstrap intervals were estimable; constant predictors have undefined correlation intervals and are retained as `not_estimable` rather than silently removed.
- Confidence intervals condition on the released test partitions and the current datasets. They do not prove external or cross-dataset generalisation.
- Multiple assessments from one soundscape remain a key dependence structure; cluster resampling is used wherever those assessments occur.
- The feature sensitivity analysis describes complete-case selection. It does not infer or impute missing psychoacoustic features.
- GPR coverage assesses the current Gaussian uncertainty output. It does not establish that the model is probabilistically calibrated in a new city or dataset.
- All Step 7 runs remain tabular and record `audio_used=false`; audio evaluation is outside v0.1.

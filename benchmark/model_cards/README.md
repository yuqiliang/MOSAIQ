# MOSAIQ Baseline Model Cards

These cards are generated from the executable baseline config, run metadata,
and validated result table by `scripts/build_model_cards.py`. Do not edit an
individual card manually; regenerate after changing a model or result.

| Model | Task | Dataset | Audio |
| --- | --- | --- | --- |
| [`isd_clip_target_mean`](isd_clip_target_mean.md) | iso_coordinate_regression | ISD | No |
| [`isd_clip_laeq_ridge`](isd_clip_laeq_ridge.md) | iso_coordinate_regression | ISD | No |
| [`isd_clip_psychoacoustic_ridge`](isd_clip_psychoacoustic_ridge.md) | iso_coordinate_regression | ISD | No |
| [`araus_target_mean`](araus_target_mean.md) | araus_pleasantness_regression | ARAUS | No |
| [`araus_laeq_ridge`](araus_laeq_ridge.md) | araus_pleasantness_regression | ARAUS | No |
| [`araus_psychoacoustic_ridge`](araus_psychoacoustic_ridge.md) | araus_pleasantness_regression | ARAUS | No |
| [`araus_elastic_net_shared6`](araus_elastic_net_shared6.md) | araus_pleasantness_regression | ARAUS | No |
| [`isd_response_target_mean_shared6`](isd_response_target_mean_shared6.md) | isd_individual_iso_prediction | ISD | No |
| [`tong_style_reduced_lr`](tong_style_reduced_lr.md) | isd_individual_iso_prediction | ISD | No |
| [`tong_style_reduced_rf`](tong_style_reduced_rf.md) | isd_individual_iso_prediction | ISD | No |
| [`tong_style_reduced_xgboost`](tong_style_reduced_xgboost.md) | isd_individual_iso_prediction | ISD | No |
| [`tong_style_reduced_gpr`](tong_style_reduced_gpr.md) | isd_individual_iso_prediction | ISD | No |
| [`delta_source_label_prevalence`](delta_source_label_prevalence.md) | delta_source_multilabel | DeLTA | No |
| [`delta_source_from_observed_annoyance_logistic`](delta_source_from_observed_annoyance_logistic.md) | delta_source_multilabel | DeLTA | No |
| [`delta_annoyance_target_mean`](delta_annoyance_target_mean.md) | delta_annoyance | DeLTA | No |
| [`delta_annoyance_from_observed_sources_ridge`](delta_annoyance_from_observed_sources_ridge.md) | delta_annoyance | DeLTA | No |
| [`delta_annoyance_from_observed_sources_rf`](delta_annoyance_from_observed_sources_rf.md) | delta_annoyance | DeLTA | No |

"""Generate the executable Paper 2 baseline-results notebook."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "notebooks" / "paper2_baseline_figures.ipynb"


def main() -> None:
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.12"},
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            """# MOSAIQ Paper 2: tabular baseline and robustness results

This notebook generates Paper 2 tables and figures from the versioned MOSAIQ
tabular benchmark outputs. It does not load audio. ARAUS results use the shared
six-feature transfer baseline; Tong-style results use the reduced feature set
available in the current ISD package.

## tl;dr

The stochastic baselines are stable across five seeds, but test-sample and
cohort uncertainty materially affect interpretation. DeLTA source-conditioned
annoyance regression improves reliably over Target Mean. No reduced Tong-style
model reliably improves both ISD targets on held-out locations. ISD shared6
complete cases are a selected subset, and the current GPR intervals under-cover."""
        ),
        nbf.v4.new_code_cell(
            """from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path.cwd()
if not (ROOT / "benchmark").exists():
    ROOT = ROOT.parent
RESULTS = ROOT / "benchmark" / "results"
ROBUSTNESS = ROOT / "benchmark" / "robustness"
FIGURES = ROOT / "papers" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

metrics = pd.read_csv(RESULTS / "baseline_results.csv")
curves = pd.read_csv(RESULTS / "distribution_curves.csv")
multiseed = pd.read_csv(ROBUSTNESS / "multiseed_summary.csv")
bootstrap_ci = pd.read_csv(ROBUSTNESS / "bootstrap_intervals.csv")
paired = pd.read_csv(ROBUSTNESS / "paired_comparisons.csv")
coverage = pd.read_csv(ROBUSTNESS / "feature_coverage_sensitivity.csv")
calibration = pd.read_csv(ROBUSTNESS / "gpr_calibration.csv")
metrics.shape, curves.shape, bootstrap_ci.shape, paired.shape"""
        ),
        nbf.v4.new_markdown_cell(
            """## Response-level deterministic performance

All models in this table use the same ISD six-feature complete-case cohort:
1,324 training, 308 development, and 279 test responses."""
        ),
        nbf.v4.new_code_cell(
            """response_test = metrics[
    (metrics["task_id"] == "isd_individual_iso_prediction")
    & (metrics["partition"] == "test")
    & (metrics["scope"] == "individual")
]
response_table = response_test.pivot_table(
    index=["model_id", "target", "n_train", "n_eval"],
    columns="metric",
    values="value",
).reset_index()
response_table.round(4)"""
        ),
        nbf.v4.new_code_cell(
            """model_order = [
    "isd_response_target_mean_shared6",
    "tong_style_reduced_lr",
    "tong_style_reduced_rf",
    "tong_style_reduced_xgboost",
    "tong_style_reduced_gpr",
]
labels = ["Target mean", "LR", "RF", "XGBoost", "GPR"]
targets = ["ISOPleasant", "ISOEventful"]
colors = ["#287271", "#D88C32"]
x = np.arange(len(model_order))
width = 0.36

fig, ax = plt.subplots(figsize=(9, 4.8))
for index, target in enumerate(targets):
    values = [
        response_test[
            (response_test.model_id == model) &
            (response_test.target == target) &
            (response_test.metric == "rmse")
        ].value.iloc[0]
        for model in model_order
    ]
    ax.bar(x + (index - 0.5) * width, values, width, label=target, color=colors[index])
ax.set_xticks(x, labels)
ax.set_ylabel("Test RMSE")
ax.set_xlabel("Baseline model")
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.2)
fig.tight_layout()
fig.savefig(FIGURES / "paper2_response_rmse.png", dpi=300, bbox_inches="tight")
plt.show()"""
        ),
        nbf.v4.new_markdown_cell("## Group-level distribution comparison"),
        nbf.v4.new_code_cell(
            """distribution_table = metrics[
    (metrics["task_id"] == "isd_individual_iso_prediction")
    & (metrics["partition"] == "test")
    & (metrics["scope"] == "group_kde")
].pivot_table(index=["model_id", "target"], columns="metric", values="value")
distribution_table.round(4)"""
        ),
        nbf.v4.new_code_cell(
            """line_colors = ["#666666", "#287271", "#6C8EBF", "#D88C32", "#9C5A73"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, target in zip(axes, targets):
    target_curves = curves[(curves.partition == "test") & (curves.target == target)]
    observed = target_curves[target_curves.model_id == model_order[0]]
    ax.plot(observed.grid, observed.observed_density, color="black", lw=2.5, label="Observed")
    for model, label, color in zip(model_order, labels, line_colors):
        model_curve = target_curves[target_curves.model_id == model]
        ax.plot(model_curve.grid, model_curve.predicted_density, lw=1.6, color=color, label=label)
    ax.set_title(target)
    ax.set_xlabel("ISO coordinate")
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("Probability density")
axes[1].legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIGURES / "paper2_response_distributions.png", dpi=300, bbox_inches="tight")
plt.show()"""
        ),
        nbf.v4.new_markdown_cell("## GPR observed versus predicted responses"),
        nbf.v4.new_code_cell(
            """gpr_run = metrics[metrics.model_id == "tong_style_reduced_gpr"].run_id.iloc[0]
gpr = pd.read_csv(RESULTS / "predictions" / f"{gpr_run}.csv")
gpr = gpr[gpr.partition == "test"]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2), sharex=True, sharey=True)
for ax, target, color in zip(axes, targets, colors):
    values = gpr[gpr.target == target]
    ax.scatter(values.y_true, values.y_pred, s=17, alpha=0.55, color=color, edgecolor="none")
    ax.plot([-1, 1], [-1, 1], color="black", lw=1, linestyle="--")
    ax.set_title(target)
    ax.set_xlabel("Observed")
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("Predicted")
fig.tight_layout()
fig.savefig(FIGURES / "paper2_gpr_observed_predicted.png", dpi=300, bbox_inches="tight")
plt.show()"""
        ),
        nbf.v4.new_markdown_cell("## Clip-level reference baselines"),
        nbf.v4.new_code_cell(
            """clip_table = metrics[
    (metrics.partition == "test")
    & (metrics.scope == "record")
    & (metrics.metric.isin(["rmse", "mae", "r2"]))
].pivot_table(
    index=["task_id", "dataset_id", "feature_set", "model_id", "target", "n_train", "n_eval"],
    columns="metric",
    values="value",
).reset_index()
clip_table.round(4)"""
        ),
        nbf.v4.new_markdown_cell(
            """## Step 7 methods

1. **Multi-seed stability:** retrain RF and XGBoost with five fixed seeds to
   measure estimator randomness.
2. **Cluster bootstrap:** resample test `clip_id` values 2,000 times and keep all
   responses from the same soundscape together to obtain 95% percentile CIs.
3. **Paired comparison:** align candidate and reference predictions on identical
   records, then bootstrap their metric difference. Positive improvement always
   favours the candidate.
4. **Coverage sensitivity:** compare all eligible ISD records with shared6
   complete cases within each released partition.
5. **GPR calibration:** compare nominal 50%, 80%, and 95% Gaussian prediction
   intervals with empirical test coverage."""
        ),
        nbf.v4.new_markdown_cell("## Multi-seed stability"),
        nbf.v4.new_code_cell(
            """seed_rmse = multiseed[
    (multiseed.partition == "test")
    & (multiseed.metric == "rmse")
    & (multiseed.scope.isin(["individual", "record"]))
].copy()
seed_rmse["label"] = seed_rmse["model_id"].str.replace("tong_style_reduced_", "", regex=False)
seed_rmse["label"] = seed_rmse["label"].str.replace("delta_annoyance_from_observed_sources_", "delta ", regex=False)
seed_rmse["label"] = seed_rmse["label"] + " / " + seed_rmse["target"]
seed_rmse[["model_id", "target", "mean", "std", "minimum", "maximum", "n_seeds"]].round(4)"""
        ),
        nbf.v4.new_code_cell(
            """seed_plot = seed_rmse.sort_values("std", ascending=True).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 4.8))
y = np.arange(len(seed_plot))
ax.barh(y, seed_plot["std"], color="#287271")
ax.set_yticks(y, seed_plot["label"])
ax.set_xlabel("Standard deviation of test RMSE across five seeds")
ax.set_ylabel("")
ax.set_title("Stochastic baseline stability")
ax.grid(axis="x", alpha=0.2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(FIGURES / "paper2_multiseed_stability.png", dpi=300, bbox_inches="tight")
plt.show()"""
        ),
        nbf.v4.new_markdown_cell("## Cluster-bootstrap confidence intervals"),
        nbf.v4.new_code_cell(
            """selected_ci = bootstrap_ci[
    (bootstrap_ci.metric == "rmse")
    & (bootstrap_ci.model_id.isin(model_order + [
        "delta_annoyance_target_mean",
        "delta_annoyance_from_observed_sources_ridge",
        "delta_annoyance_from_observed_sources_rf",
    ]))
][["task_id", "model_id", "target", "estimate", "ci_low", "ci_high", "n_eval", "n_clusters"]]
selected_ci.round(4)"""
        ),
        nbf.v4.new_markdown_cell("## Paired improvement over the declared reference"),
        nbf.v4.new_code_cell(
            """paired_rmse = paired[paired.metric == "rmse"].copy()
paired_rmse["label"] = paired_rmse["candidate_model"].str.replace("tong_style_reduced_", "", regex=False)
paired_rmse["label"] = paired_rmse["label"].str.replace("delta_annoyance_from_observed_sources_", "delta ", regex=False)
paired_rmse["label"] = paired_rmse["label"] + " / " + paired_rmse["target"]
paired_rmse[["candidate_model", "target", "improvement", "ci_low", "ci_high", "probability_improvement_gt_zero"]].round(4)"""
        ),
        nbf.v4.new_code_cell(
            """paired_plot = paired_rmse.sort_values("improvement").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 5.6))
y = np.arange(len(paired_plot))
xerr = np.vstack([
    paired_plot["improvement"] - paired_plot["ci_low"],
    paired_plot["ci_high"] - paired_plot["improvement"],
])
colors_ci = np.where(paired_plot["ci_low"] > 0, "#287271", np.where(paired_plot["ci_high"] < 0, "#C65D3A", "#6B7280"))
for index in range(len(paired_plot)):
    ax.errorbar(paired_plot.loc[index, "improvement"], y[index], xerr=xerr[:, index:index+1], fmt="o", color=colors_ci[index], capsize=3)
ax.axvline(0, color="black", lw=1, linestyle="--")
ax.set_yticks(y, paired_plot["label"])
ax.set_xlabel("Paired RMSE improvement (positive favours candidate)")
ax.set_ylabel("")
ax.set_title("Paired test-set comparison with 95% cluster-bootstrap CI")
ax.grid(axis="x", alpha=0.2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(FIGURES / "paper2_paired_rmse_improvement.png", dpi=300, bbox_inches="tight")
plt.show()"""
        ),
        nbf.v4.new_markdown_cell("## ISD feature coverage and GPR calibration"),
        nbf.v4.new_code_cell(
            """coverage_test = coverage[
    (coverage.partition == "test") & (coverage.cohort == "shared6_complete")
].drop_duplicates("task_id")
coverage_test[["task_id", "unit_of_analysis", "n_records", "n_all_eligible", "coverage_fraction"]].round(4), calibration.round(4)"""
        ),
        nbf.v4.new_code_cell(
            """fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.4))
coverage_labels = ["Clip level", "Response level"]
coverage_values = [
    coverage_test.loc[coverage_test.unit_of_analysis == "clip", "coverage_fraction"].iloc[0],
    coverage_test.loc[coverage_test.unit_of_analysis == "response", "coverage_fraction"].iloc[0],
]
axes[0].bar(coverage_labels, coverage_values, color=["#287271", "#D88C32"])
axes[0].set_ylim(0, 1)
axes[0].set_ylabel("Retained fraction")
axes[0].set_title("ISD shared6 test coverage")
for index, value in enumerate(coverage_values):
    axes[0].text(index, value + 0.025, f"{value:.1%}", ha="center")

for target, color in zip(targets, colors):
    values = calibration[calibration.target == target]
    axes[1].plot(values.nominal_coverage, values.empirical_coverage, marker="o", color=color, label=target)
axes[1].plot([0.45, 1.0], [0.45, 1.0], color="black", lw=1, linestyle="--", label="Ideal")
axes[1].set_xlim(0.45, 1.0)
axes[1].set_ylim(0.25, 1.0)
axes[1].set_xlabel("Nominal coverage")
axes[1].set_ylabel("Empirical coverage")
axes[1].set_title("GPR prediction-interval calibration")
axes[1].legend(frameon=False, fontsize=8)
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)
fig.tight_layout()
fig.savefig(FIGURES / "paper2_coverage_and_calibration.png", dpi=300, bbox_inches="tight")
plt.show()"""
        ),
        nbf.v4.new_markdown_cell(
            """## Interpretation boundary

These outputs establish reproducible no-audio reference performance. They do
not constitute an exact replication of the ARAUS 264-candidate Elastic Net or
the full Tong et al. feature set. Negative or weak held-out-location results
must be reported as benchmark evidence rather than hidden by random response
splitting. Bootstrap intervals quantify uncertainty in the released test sample,
not transfer to a new dataset. The strong ISD complete-case shifts and GPR
under-coverage are technical-validation findings, not defects to conceal."""
        ),
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, OUTPUT)
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

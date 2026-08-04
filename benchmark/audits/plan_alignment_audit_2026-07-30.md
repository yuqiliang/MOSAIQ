# MOSAIQ plan-alignment audit

Audit date: 30 July 2026<br>
Review pass: 1 of 3<br>
Sources: OMAIB full application, Upgrade Report Chapter 5, benchmark roadmap,
and the implemented repository

## Overall judgement

The repository follows the data-centric sequence committed in the Upgrade
Report: schema and harmonisation, task contracts, leakage-aware splits,
technical validation, reusable baseline interfaces, robustness analysis, and
release preparation. The four-dataset no-audio candidate is complete for its
declared scope. A separately versioned ISD audio reference track now verifies
that the same split and evaluation contracts can support waveform-linked
models without retroactively changing the no-audio v0.1 freeze.

Status: **aligned internal benchmark candidate; final multimodal and public
release obligations remain**

## Objective alignment

| Objective | Implemented evidence | Status |
| --- | --- | --- |
| O1 Landscape and selection | Published review; ISD/ARAUS core and SATP/DeLTA extensions | Complete |
| O2 Standard evaluation protocol | Seven tasks, split 0.1.0, fixed metrics, submission contract, uncertainty rules | Complete for current tasks |
| O3 Multimodal alignment schema | Dataset, clip, response, feature, provenance, and missingness schemas | Complete as Paper 1/repo foundation |
| O4 Compile the benchmark | Four tabular packages plus a frozen 820-clip ISD audio cohort | Complete for current candidate; wider media pending |
| O5 Baselines and pipeline | 17 tabular experiments; two audio references; model cards; robustness outputs | Complete reference tier; learned audio/multimodal tier pending |
| O6 Open platform and outreach | CI, reproduce guide, release checklist, validated private-draft package | DOI, public deposit, and outreach pending |

## Upgrade Report boundary

The Upgrade Report requires compatible subsets, common preprocessing, fixed
splits and metrics, and predictive baselines through a unified interface. The
current implementation satisfies those requirements. Chapter 6 MMAudio
fine-tuning and Chapter 7 generative augmentation remain later thesis phases
and are not prerequisites for Paper 2.

## OMAIB obligations still open

1. Train the preregistered ISD log-mel CNN and pretrained encoder reference.
2. Add tabular-audio fusion, missing-modality, and added-noise tests.
3. Resolve whether the first public DOI is the tabular v0.1 candidate or a new
   media-bearing version.
4. Complete the source/per-file rights review and archival deposit.
5. Conduct external usability and co-author review when those paused gates
   resume.

## Pass-1 conclusion

No contradiction was found between the implemented benchmark and the project
plans. The 820-clip audio track is correctly labelled as an ISD-only extension,
not as the completed four-dataset multimodal MOSAIQ-v1.0.

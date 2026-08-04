# MOSAIQ plan-alignment audit

Audit date: 24 July 2026<br>
Review pass: 1 of 3<br>
Sources: OMAIB full application, Upgrade Report Chapter 5, and benchmark roadmap

## Overall judgement

The no-audio tabular v0.1 candidate is aligned with the sequence and data-
centric logic of the PhD Upgrade plan. It also completes the internal,
tabular parts of OMAIB O1-O5. It does not yet satisfy the OMAIB definition of
the final multimodal MOSAIQ-v1.0 because media, full audio/visual baselines,
missing-modality/noise tests, external usability review, and public archival
release remain incomplete.

Status: **internally coherent candidate; public v1.0 gates remain**

## OMAIB objectives

| Objective | Evidence | Status |
| --- | --- | --- |
| O1 Landscape review and selection | Twenty-dataset catalogue; ISD/ARAUS core; SATP/DeLTA extensions; published review | Complete |
| O2 Standardised evaluation protocol | Seven task contracts, fixed metrics, split 0.1.0, submission contract | Complete for tabular v0.1 |
| O3 Multimodal alignment schema | Dataset and clip/response/feature schemas, provenance and missingness | Complete as Paper 1/repo foundation |
| O4 Compile the benchmark | Four materialised tabular packages, 27,850 clips, 59,935 responses | Complete for tabular candidate; media pending |
| O5 Baselines and pipeline | Seventeen runs, unified interface, model cards, robustness evidence | Complete for tabular candidate; SOTA media models pending |
| O6 Open platform and outreach | GitHub-ready docs, RDR plan, release checklist | External release and outreach pending |

## OMAIB work packages

| Work package | Candidate evidence | Remaining obligation |
| --- | --- | --- |
| WP1 Evaluation protocol | Tasks, KPIs, split rules, uncertainty, calibration, submission schema | Run missing-media and added-noise checks after media ingestion; complete external plain-language usability review |
| WP2 Schema design | Compact schemas, validators, model/data cards, governance registry | Confirm final licence/consent statements with owners/UCL |
| WP3 Integration | Harmonised tables, psychoacoustic fields, balanced/grouped splits, provenance | Add exact source-archive checksums and permitted media |
| WP4 Baseline models | Target Mean, Ridge, Elastic Net transfer, reduced Tong-style models, DeLTA baselines | Add published ARAUS CNN/full feature replication and audio/visual/multimodal models to the media release |
| WP5 Release and platform | CI, reproduce guide, submission format, RDR package plan | Conduct community review, create release tag, DOI, RDR/Zenodo deposit, and results page |

## Upgrade Report Chapter 5

The Upgrade report requires a clip-level schema, compatible subsets from open
datasets such as ISD and ARAUS, a standardised evaluation protocol,
preprocessing, splits, common metrics, and baseline predictive models through a
unified training/evaluation pipeline. All are implemented for the tabular v0.1
scope. The report does not require Chapter 6 MMAudio fine-tuning or Chapter 7
generative augmentation to be part of Paper 2; those remain separate thesis
phases and should not be folded into the benchmark manuscript.

## Scope decisions that must remain explicit

1. v0.1 is no-audio and tabular. It is not the final multimodal v1.0.
2. ARAUS Elastic Net is a shared-six transfer, not the 264-feature replication.
3. Tong-style models are reduced implementations, not full reproductions.
4. DeLTA cross-target models consume observed labels and are diagnostic.
5. The ISD response task has 3,552 target-complete rows before split-linked
   exclusions and 3,549 rows in the frozen manifest.
6. MMAudio and generative augmentation belong to later thesis chapters.

## Pass-1 conclusion

No contradiction was found between the implemented tabular candidate and the
Upgrade plan. OMAIB multimodal and public-release promises are tracked as
external/future gates rather than misreported as completed.

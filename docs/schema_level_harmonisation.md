# MOSAIQ schema-level harmonisation

This document describes the first MOSAIQ harmonisation layer for ISD and
ARAUS. The scope is deliberately narrow: it prepares a common schema and
conservative ISO 12913 semantic representation for later benchmark work.

## What schema-level harmonisation means

Schema-level harmonisation means representing heterogeneous source datasets
with a shared record structure. In this repository, that structure covers:

- dataset identity
- data source and citation
- access and licence
- study type
- acoustic environment
- people or participants
- context
- sound sources
- audio modality
- visual modality
- perceptual annotation framework
- ISO 12913 perceived affective quality fields
- acoustic and psychoacoustic indicators
- derived feature records
- missingness
- provenance
- validation status

The shared schema is stored at:

```text
shared_schemas/schema_level_harmonisation.schema.json
```

## What this implementation does

This implementation adds a minimal schema-level layer:

- a shared JSON schema for dataset-level and sample-level harmonisation records
- controlled vocabularies for access, study, audio, visual, missingness, and
  provenance fields
- explicit harmonisation-level status fields for structural, semantic, feature,
  statistical, and benchmark-split harmonisation
- a checklist file for documenting what is aligned, partially aligned,
  documented only, or not performed:
  `mappings/harmonisation_checklist.json`
- a lightweight graph model for explainable schema-level information fusion:
  `mappings/mosaiq_harmonisation_graph.json`
- a multi-view alignment block for audio, visual, context, perception, and
  feature views
- a harmonisation potential score that reports structural readiness without
  claiming statistical equivalence
- canonical ISO 12913 PAQ item names:
  `pleasant`, `vibrant`, `eventful`, `chaotic`, `annoying`, `monotonous`,
  `uneventful`, and `calm`
- separate derived ISO coordinate fields:
  `pleasantness` and `eventfulness`
- long-form rating-scale examples that preserve `rating_value_original` and
  document `rating_value_harmonised` separately
- preprocessing records that describe transformations such as SATP 0-100 to
  MOSAIQ 1-5 PAQ conversion
- an expanded FeatureRecord schema for audio embeddings, visual embeddings,
  semantic visual summaries, gaze/attention descriptors, and future multimodal
  features
- mapping tables for ISD and ARAUS:
  `mappings/isd_to_mosaiq_schema.json`
  `mappings/araus_to_mosaiq_schema.json`
- two demonstration JSONL records:
  `examples/harmonised_samples/isd_sample.jsonl`
  `examples/harmonised_samples/araus_sample.jsonl`
- a lightweight validator:
  `scripts/validate_schema_harmonisation.py`
- a small ISO helper module:
  `scripts/iso12913.py`

The example records use existing values from the current MOSAIQ CSV files where
available. Fields that are unavailable in those rows are represented through
explicit `missingness` records rather than fabricated values.

Each mapping record now also includes `mapping_confidence`, `evidence_type`,
`review_status`, `ambiguity_note`, and `source_column_examples`. These fields
make the harmonisation auditable: a direct ISO PAQ mapping can be marked as
high-confidence, while modality or feature metadata can remain medium-confidence
until source documentation and extraction provenance are reviewed.

## What this implementation does not do

This layer does not create a fully harmonised benchmark dataset.

It also does not perform:

- statistical harmonisation
- domain adaptation
- distribution matching
- label rescaling
- imputation of missing labels
- train/validation/test split creation
- cross-framework mapping to SAM, EmojiGrid, valence/arousal, annoyance, or
  other non-ISO frameworks

Existing split columns in the current ARAUS/ISD tables may still be documented
as source metadata, but this task does not introduce new benchmark splits.

## ISO 12913 semantic boundary

ISD and ARAUS both use ISO 12913 soundscape constructs, so the semantic layer
is ISO-only. MOSAIQ canonical PAQ fields preserve the eight ISO perceived
affective quality items and keep original field names in each mapping record.

Item-level ratings are stored under:

```text
perception.iso_12913.paq
```

Derived Method A coordinates are stored separately under:

```text
perception.iso_12913.derived_coordinates
```

This separation avoids mixing raw PAQ ratings with derived pleasantness and
eventfulness coordinates.

MOSAIQ also separates value layers:

- `raw_response`: participant-level item ratings, when represented
- `aggregated_sample_annotation`: clip/sample-level PAQ summaries such as means
- `derived_coordinate`: pleasantness/eventfulness coordinates computed or
  copied as ISO Method A derived values

## Original and harmonised rating values

MOSAIQ does not overwrite source ratings. When a source dataset uses a different
response scale, the original value remains available and any harmonised value is
documented as a derived field.

For SATP, the source PAQ values are retained as `*_raw_0_100` columns in
`datasets/SATP/data/responses.csv`. The MOSAIQ 1-5 PAQ columns are derived with:

```text
1 + 4 * raw_0_100 / 100
```

The transformation is documented in:

```text
datasets/SATP/data/preprocessing.csv
```

and a small long-form rating example is stored in:

```text
datasets/SATP/data/ratings.csv
```

This is still schema-level harmonisation. It is not z-normalisation,
distribution matching, or full statistical harmonisation.

## FeatureRecord extensibility

Derived descriptors are represented through `FeatureRecord` rows rather than
being mixed into raw response tables. The shared schema is stored in:

```text
shared_schemas/features.schema.yaml
```

FeatureRecords link derived data to `dataset_id`, `clip_id`, optional
`asset_id`, extractor metadata, input time windows, storage paths, checksums,
preprocessing IDs, and provenance notes. The current examples cover PANNs audio
embeddings, CLIP visual embeddings, CitySeg semantic summaries, and a
placeholder gaze-on-class descriptor.

## Structural, semantic, and statistical harmonisation

Structural harmonisation defines the shared record layout: where dataset,
sample, modality, feature, missingness, provenance, and validation information
should be stored.

Semantic harmonisation defines the meaning of fields. For this task, semantic
harmonisation is limited to ISO 12913 concepts already used by ISD and ARAUS.

Statistical harmonisation would address differences in label distributions,
collection settings, domains, participant populations, or sampling strategy.
That work is intentionally out of scope here and should be documented as a
future benchmark-construction step.

## Multi-view alignment and graph representation

Inspired by information-fusion and multimodal entity-alignment literature, the
sample examples now include a lightweight `alignment` block:

```json
{
  "audio_view": "available",
  "visual_view": "available",
  "context_view": "available",
  "perception_view": "available",
  "feature_view": "partial",
  "alignment_status": "partially_schema_aligned",
  "unresolved_issues": ["sound source taxonomy not reported"]
}
```

This is a schema-level alignment statement only. It records whether each
modality/view can be represented, not whether distributions or labels are
statistically aligned.

The `knowledge_graph` block records simple relationships such as:

- Dataset `has_sample` Sample
- Sample `has_audio` AudioAsset
- Sample `has_visual` VisualAsset
- Sample `has_annotation` PAQAnnotation
- PAQAnnotation `uses_framework_item` ISO12913Item
- Sample `has_feature` FeatureRecord

This graph-style representation supports traceability and explanation, but it
does not implement knowledge-graph learning or automatic entity matching.

## Harmonisation potential

`harmonisation_potential` is a structural readiness score in the range `[0, 1]`.
It is useful for reporting whether a sample or dataset is ready for later
benchmark construction. It is not a performance metric and not a statistical
harmonisation score.

Example components include:

- PAQ completeness
- audio metadata completeness
- visual metadata availability
- context completeness
- provenance completeness

## Missingness

Missingness is represented explicitly as a list of records:

```json
{
  "field": "visual",
  "status": "not_reported",
  "reason": "The source row has no populated video asset field."
}
```

Allowed statuses are:

- `available`
- `not_collected`
- `not_reported`
- `not_accessible`
- `not_applicable`
- `unknown`

The examples use missingness records for unavailable source citation fields,
unreported sound-source details, and unavailable visual/audio assets.

## Provenance

Provenance is also represented explicitly as a list of records:

```json
{
  "source_type": "metadata_file",
  "note": "Values copied from datasets/ISD/data/clips.csv."
}
```

Allowed source types are:

- `paper`
- `dataset_documentation`
- `metadata_file`
- `manual_inspection`
- `code_extraction`
- `author_communication`
- `unknown`

Acoustic and psychoacoustic indicators should include either a method or a
provenance note when present.

## ISO Method A utility

The helper function in `scripts/iso12913.py` can compute ISO Method A
pleasantness and eventfulness when all eight PAQ items are available:

```python
from iso12913 import compute_method_a_coordinates

coords = compute_method_a_coordinates({
    "pleasant": 3,
    "vibrant": 4,
    "eventful": 3,
    "chaotic": 2,
    "annoying": 2,
    "monotonous": 1,
    "uneventful": 2,
    "calm": 4,
})
```

The utility raises an error if required PAQ items are missing. It does not
overwrite existing pleasantness or eventfulness values; callers must decide how
to store any computed result and should record the computation in provenance.

## Validation

Run the schema-level harmonisation validator from the repository root:

```bash
uv run python scripts/validate_schema_harmonisation.py
```

The validator checks:

- required top-level fields
- controlled vocabulary values
- harmonisation-level statuses
- multi-view alignment statuses
- `dataset_id` and `sample_id`
- `perception.framework == ISO_12913` for ISD and ARAUS examples
- missingness statuses
- provenance records
- canonical ISO PAQ field names
- separation of raw PAQ items and derived ISO coordinates
- lightweight graph node/edge consistency
- harmonisation potential scores
- mapping confidence/evidence/review fields
- explicit visual missingness when no visual asset is available
- method or provenance for acoustic and psychoacoustic indicators

Expected current summary:

```text
files checked: 2
records checked: 2
mapping files checked: 2
checklist files checked: 1
graph model files checked: 1
warnings: 0
errors: 0
```

## Literature-informed design notes

This MOSAIQ layer adapts three ideas from the referenced information-fusion
literature while keeping the implementation conservative:

- Nan et al. (2022), DOI `10.1016/j.inffus.2022.01.001`: harmonisation should
  be reported with explicit dataset properties, missingness, provenance,
  reproducibility, and non-goals.
- Holzinger et al. (2022), DOI `10.1016/j.inffus.2021.10.007`: information
  fusion benefits from explainable, verifiable, graph-style representations.
- Zhu et al. (2023), DOI `10.1016/j.inffus.2023.101935`: multimodal alignment
  is better treated as multiple views rather than a single flattened feature
  table.

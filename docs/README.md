# MOSAIQ documentation

This directory contains public documentation for using, reproducing and
extending MOSAIQ.

- [Reproduce the benchmark](reproduce_benchmark.md): inputs, fixed evaluation
  and verification commands.
- [Schema-level harmonisation](schema_level_harmonisation.md): representation,
  semantic scope and limitations.
- [Feature records](feature_records.md): feature types and provenance.
- [Audio data dictionary](audio_data_dictionary.md): audio manifests, QC and
  descriptor fields.
- [RDR package README](release/RDR_README.md): archival package usage.
- [Usability review protocol](release/usability_review_protocol.md):
  independent reproduction procedure.

Task contracts and public results live under [benchmark/](../benchmark/README.md).
Generated manuscript-facing evidence lives under [papers/](../papers/README.md).

## Documentation scope

Keep reusable descriptions of schemas, data provenance, evaluation methods,
known limitations and reproduction procedures in the repository. Machine-readable
source receipts, manifests, technical-validation outputs and model/data cards
remain part of the reproducible research artefact.

Store meeting records, personal recaps, supervisor updates, manuscript-editing
histories, administrative release plans and private work audits outside the
checkout. Their absence must not prevent builds, validation or archive creation.
The repository and release-package checks enforce this boundary.

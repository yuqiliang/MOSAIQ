"""Validate MOSAIQ schema-level harmonisation example records.

This validator is intentionally lightweight and uses only the Python standard
library. It checks the repository's demonstration JSONL records against the
schema-level expectations documented for ISD and ARAUS. It is not a statistical
harmonisation or dataset completeness validator.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from iso12913 import CANONICAL_PAQ_FIELDS


REPO_ROOT = Path(__file__).resolve().parents[1]

VISUAL_TYPES = {
    "none",
    "image",
    "video",
    "vr",
    "eye_tracking",
    "derived_visual_feature",
    "unknown",
}
AUDIO_CHANNEL_TYPES = {"mono", "stereo", "binaural", "ambisonic", "unknown"}
ENVIRONMENT_TYPES = {"real", "recorded", "virtual", "unknown"}
SETTINGS = {"field", "laboratory", "mixed", "unknown"}
ACCESS_STATUSES = {"open", "restricted", "request_required", "closed", "unknown"}
MISSINGNESS_STATUSES = {
    "available",
    "not_collected",
    "not_reported",
    "not_accessible",
    "not_applicable",
    "unknown",
}
PROVENANCE_SOURCE_TYPES = {
    "paper",
    "dataset_documentation",
    "metadata_file",
    "manual_inspection",
    "code_extraction",
    "author_communication",
    "unknown",
}
VALIDATION_STATUSES = {"unchecked", "valid", "valid_with_warnings", "invalid"}
HARMONISATION_STATUSES = {
    "aligned",
    "partially_aligned",
    "documented_only",
    "not_performed",
    "not_applicable",
    "unknown",
}
VIEW_STATUSES = {
    "available",
    "partial",
    "not_reported",
    "not_accessible",
    "not_applicable",
    "unknown",
}
ALIGNMENT_STATUSES = {
    "schema_aligned",
    "partially_schema_aligned",
    "not_aligned",
    "unknown",
}
MAPPING_CONFIDENCES = {"high", "medium", "low", "unknown"}
MAPPING_EVIDENCE_TYPES = {
    "source_schema",
    "paper",
    "metadata_file",
    "manual_inspection",
    "code_extraction",
    "author_communication",
    "unknown",
}
MAPPING_REVIEW_STATUSES = {"proposed", "reviewed", "accepted"}
REQUIRED_HARMONISATION_LEVELS = {
    "structural_harmonisation",
    "semantic_harmonisation",
    "feature_harmonisation",
    "statistical_harmonisation",
    "benchmark_split_harmonisation",
}
REQUIRED_ALIGNMENT_VIEWS = {
    "audio_view",
    "visual_view",
    "context_view",
    "perception_view",
    "feature_view",
}

SAMPLE_REQUIRED_TOP_LEVEL = {
    "record_type",
    "dataset_id",
    "dataset_identity",
    "sample_id",
    "source_clip_id",
    "source",
    "harmonisation",
    "access",
    "study",
    "acoustic_environment",
    "people",
    "context",
    "sound_sources",
    "audio",
    "visual",
    "alignment",
    "perception",
    "features",
    "knowledge_graph",
    "harmonisation_potential",
    "missingness",
    "provenance",
    "validation",
}

MAPPING_REQUIRED_FIELDS = {
    "original_field",
    "mosaiq_field",
    "semantic_basis",
    "transformation",
    "required",
    "missingness_rule",
    "provenance_note",
    "mapping_confidence",
    "evidence_type",
    "review_status",
    "ambiguity_note",
    "source_column_examples",
}


@dataclass
class Finding:
    path: Path
    record_id: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MOSAIQ schema-level harmonisation examples"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[REPO_ROOT / "examples" / "harmonised_samples"],
        help="JSONL file(s) or directories to validate",
    )
    parser.add_argument(
        "--mappings-dir",
        type=Path,
        default=REPO_ROOT / "mappings",
        help="Directory containing *_to_mosaiq_schema.json mapping files",
    )
    return parser.parse_args()


def iter_jsonl_paths(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.jsonl")))
        else:
            files.append(path)
    return files


def load_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            rows.append((line_number, json.loads(line)))
    return rows


def record_id(record: dict[str, Any]) -> str:
    return str(record.get("sample_id") or record.get("dataset_id") or "<unknown>")


def add_error(errors: list[Finding], path: Path, record: dict[str, Any], message: str) -> None:
    errors.append(Finding(path=path, record_id=record_id(record), message=message))


def add_warning(
    warnings: list[Finding], path: Path, record: dict[str, Any], message: str
) -> None:
    warnings.append(Finding(path=path, record_id=record_id(record), message=message))


def missingness_fields(record: dict[str, Any]) -> set[str]:
    return {
        str(item.get("field"))
        for item in record.get("missingness", [])
        if isinstance(item, dict)
    }


def validate_sample_record(
    path: Path,
    record: dict[str, Any],
    errors: list[Finding],
    warnings: list[Finding],
) -> None:
    missing_top = sorted(SAMPLE_REQUIRED_TOP_LEVEL - set(record))
    if missing_top:
        add_error(errors, path, record, f"missing top-level fields: {missing_top}")

    if not record.get("dataset_id"):
        add_error(errors, path, record, "dataset_id is required")
    if not record.get("sample_id"):
        add_error(errors, path, record, "sample_id is required")

    harmonisation = record.get("harmonisation", {})
    if harmonisation.get("scope") != "schema_level":
        add_error(errors, path, record, "harmonisation.scope must be schema_level")
    levels = harmonisation.get("levels", {})
    missing_levels = sorted(REQUIRED_HARMONISATION_LEVELS - set(levels))
    if missing_levels:
        add_error(errors, path, record, f"missing harmonisation levels: {missing_levels}")
    for level_name, level in levels.items():
        if not isinstance(level, dict):
            add_error(errors, path, record, f"harmonisation level {level_name} must be an object")
            continue
        if level.get("status") not in HARMONISATION_STATUSES:
            add_error(errors, path, record, f"harmonisation level {level_name} has invalid status")
        if not level.get("note"):
            add_error(errors, path, record, f"harmonisation level {level_name} requires note")
    for item in harmonisation.get("checklist", []):
        if not isinstance(item, dict):
            add_error(errors, path, record, "harmonisation.checklist entries must be objects")
            continue
        if item.get("status") not in HARMONISATION_STATUSES:
            add_error(errors, path, record, f"checklist item {item.get('item')} has invalid status")
        if not item.get("note"):
            add_error(errors, path, record, f"checklist item {item.get('item')} requires note")

    access = record.get("access", {})
    if access.get("status") not in ACCESS_STATUSES:
        add_error(errors, path, record, "access.status is not a controlled value")

    study = record.get("study", {})
    if study.get("environment_type") not in ENVIRONMENT_TYPES:
        add_error(errors, path, record, "study.environment_type is not a controlled value")
    if study.get("setting") not in SETTINGS:
        add_error(errors, path, record, "study.setting is not a controlled value")

    audio = record.get("audio", {})
    if audio.get("channel_type") not in AUDIO_CHANNEL_TYPES:
        add_error(errors, path, record, "audio.channel_type is not a controlled value")

    visual = record.get("visual", {})
    if visual.get("type") not in VISUAL_TYPES:
        add_error(errors, path, record, "visual.type is not a controlled value")

    alignment = record.get("alignment", {})
    missing_views = sorted(REQUIRED_ALIGNMENT_VIEWS - set(alignment))
    if missing_views:
        add_error(errors, path, record, f"missing alignment views: {missing_views}")
    for view_name in REQUIRED_ALIGNMENT_VIEWS:
        if alignment.get(view_name) not in VIEW_STATUSES:
            add_error(errors, path, record, f"alignment.{view_name} is not a controlled value")
    if alignment.get("alignment_status") not in ALIGNMENT_STATUSES:
        add_error(errors, path, record, "alignment.alignment_status is not controlled")
    if not isinstance(alignment.get("unresolved_issues"), list):
        add_error(errors, path, record, "alignment.unresolved_issues must be a list")

    perception = record.get("perception", {})
    if record.get("dataset_id") in {"ISD", "ARAUS"}:
        if perception.get("framework") != "ISO_12913":
            add_error(errors, path, record, "perception.framework must be ISO_12913")

    iso = perception.get("iso_12913", {})
    paq = iso.get("paq", {})
    paq_keys = set(paq)
    canonical_keys = set(CANONICAL_PAQ_FIELDS)
    extra_paq_keys = sorted(paq_keys - canonical_keys)
    missing_paq_keys = sorted(canonical_keys - paq_keys)
    if extra_paq_keys:
        add_error(errors, path, record, f"non-canonical ISO PAQ fields: {extra_paq_keys}")
    if missing_paq_keys:
        add_warning(warnings, path, record, f"missing ISO PAQ fields: {missing_paq_keys}")

    miss_fields = missingness_fields(record)
    for field, item in paq.items():
        if not isinstance(item, dict):
            add_error(errors, path, record, f"PAQ field {field} must be an object")
            continue
        if "value" not in item:
            add_error(errors, path, record, f"PAQ field {field} missing value")
        if "original_field" not in item:
            add_error(errors, path, record, f"PAQ field {field} missing original_field")
        if item.get("value_type") not in {"raw_response", "aggregated_sample_annotation"}:
            add_error(errors, path, record, f"PAQ field {field} has invalid value_type")
        if item.get("value") is None and f"perception.iso_12913.paq.{field}" not in miss_fields:
            add_warning(
                warnings,
                path,
                record,
                f"PAQ field {field} is null without explicit missingness record",
            )

    if {"pleasantness", "eventfulness"} & paq_keys:
        add_error(
            errors,
            path,
            record,
            "derived pleasantness/eventfulness must not be stored inside paq",
        )

    derived = iso.get("derived_coordinates", {})
    for raw_item in CANONICAL_PAQ_FIELDS:
        if raw_item in derived:
            add_error(
                errors,
                path,
                record,
                "raw PAQ item ratings must not be stored inside derived_coordinates",
            )
    for coord in ("pleasantness", "eventfulness"):
        if coord in derived:
            item = derived[coord]
            if not isinstance(item, dict):
                add_error(errors, path, record, f"derived coordinate {coord} must be an object")
            elif not item.get("method") or not item.get("source"):
                add_error(
                    errors,
                    path,
                    record,
                    f"derived coordinate {coord} requires method and source",
                )
            elif item.get("value_type") != "derived_coordinate":
                add_error(
                    errors,
                    path,
                    record,
                    f"derived coordinate {coord} must declare value_type=derived_coordinate",
                )

    for item in record.get("missingness", []):
        if not isinstance(item, dict):
            add_error(errors, path, record, "missingness entries must be objects")
            continue
        if item.get("status") not in MISSINGNESS_STATUSES:
            add_error(
                errors,
                path,
                record,
                f"missingness status for {item.get('field')} is not controlled",
            )

    for item in record.get("provenance", []):
        if not isinstance(item, dict):
            add_error(errors, path, record, "provenance entries must be objects")
            continue
        if item.get("source_type") not in PROVENANCE_SOURCE_TYPES:
            add_error(errors, path, record, "provenance.source_type is not controlled")
        if not item.get("note"):
            add_error(errors, path, record, "provenance.note is required")
    if not record.get("provenance"):
        add_error(errors, path, record, "provenance is required")

    validation = record.get("validation", {})
    if validation.get("status") not in VALIDATION_STATUSES:
        add_error(errors, path, record, "validation.status is not controlled")

    visual_missing = visual.get("type") in {"none", "unknown"} or not visual.get("asset")
    if visual_missing and "visual" not in miss_fields and "visual.asset" not in miss_fields:
        add_error(
            errors,
            path,
            record,
            "visual missingness must be explicitly reported when no visual asset is available",
        )

    features = record.get("features", {})
    for group in ("acoustic_indicators", "psychoacoustic_indicators", "derived_features"):
        for feature in features.get(group, []):
            if not isinstance(feature, dict):
                add_error(errors, path, record, f"{group} entries must be objects")
                continue
            if not feature.get("method") and not feature.get("provenance"):
                add_error(
                    errors,
                    path,
                    record,
                    f"{group}.{feature.get('name', '<unknown>')} needs method or provenance",
                )

    graph = record.get("knowledge_graph", {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list) or not nodes:
        add_error(errors, path, record, "knowledge_graph.nodes must be a non-empty list")
        node_ids: set[str] = set()
    else:
        node_ids = set()
        for node in nodes:
            if not isinstance(node, dict):
                add_error(errors, path, record, "knowledge_graph nodes must be objects")
                continue
            if not node.get("id") or not node.get("type") or not node.get("label"):
                add_error(errors, path, record, "knowledge_graph node requires id, type, and label")
            node_ids.add(str(node.get("id")))
    if not isinstance(edges, list) or not edges:
        add_error(errors, path, record, "knowledge_graph.edges must be a non-empty list")
    else:
        for edge in edges:
            if not isinstance(edge, dict):
                add_error(errors, path, record, "knowledge_graph edges must be objects")
                continue
            source = str(edge.get("source"))
            target = str(edge.get("target"))
            if source not in node_ids or target not in node_ids:
                add_error(
                    errors,
                    path,
                    record,
                    f"knowledge_graph edge references unknown node: {source} -> {target}",
                )
            if not edge.get("relation"):
                add_error(errors, path, record, "knowledge_graph edge requires relation")

    potential = record.get("harmonisation_potential", {})
    score = potential.get("score")
    if not isinstance(score, (int, float)) or not 0 <= score <= 1:
        add_error(errors, path, record, "harmonisation_potential.score must be in [0, 1]")
    components = potential.get("components", [])
    if not isinstance(components, list) or not components:
        add_error(errors, path, record, "harmonisation_potential.components must be non-empty")
    else:
        for component in components:
            if not isinstance(component, dict):
                add_error(errors, path, record, "harmonisation_potential components must be objects")
                continue
            comp_score = component.get("score")
            if not isinstance(comp_score, (int, float)) or not 0 <= comp_score <= 1:
                add_error(
                    errors,
                    path,
                    record,
                    f"harmonisation_potential component {component.get('name')} score must be in [0, 1]",
                )
            if component.get("status") not in HARMONISATION_STATUSES:
                add_error(
                    errors,
                    path,
                    record,
                    f"harmonisation_potential component {component.get('name')} has invalid status",
                )


def validate_mapping_files(
    mappings_dir: Path, errors: list[Finding], warnings: list[Finding]
) -> int:
    mapping_paths = sorted(mappings_dir.glob("*_to_mosaiq_schema.json"))
    for path in mapping_paths:
        with path.open("r", encoding="utf-8") as handle:
            mapping_doc = json.load(handle)
        pseudo_record = {"sample_id": mapping_doc.get("dataset_id", path.name)}
        if mapping_doc.get("semantic_framework") != "ISO_12913":
            add_error(errors, path, pseudo_record, "semantic_framework must be ISO_12913")
        if mapping_doc.get("harmonisation_scope") != "schema_level":
            add_error(errors, path, pseudo_record, "harmonisation_scope must be schema_level")
        mappings = mapping_doc.get("mappings")
        if not isinstance(mappings, list) or not mappings:
            add_error(errors, path, pseudo_record, "mappings must be a non-empty list")
            continue
        for index, mapping in enumerate(mappings, start=1):
            missing = sorted(MAPPING_REQUIRED_FIELDS - set(mapping))
            if missing:
                add_error(
                    errors,
                    path,
                    pseudo_record,
                    f"mapping {index} missing fields: {missing}",
                )
            if mapping.get("mapping_confidence") not in MAPPING_CONFIDENCES:
                add_error(
                    errors,
                    path,
                    pseudo_record,
                    f"mapping {index} has invalid mapping_confidence",
                )
            if mapping.get("evidence_type") not in MAPPING_EVIDENCE_TYPES:
                add_error(
                    errors,
                    path,
                    pseudo_record,
                    f"mapping {index} has invalid evidence_type",
                )
            if mapping.get("review_status") not in MAPPING_REVIEW_STATUSES:
                add_error(
                    errors,
                    path,
                    pseudo_record,
                    f"mapping {index} has invalid review_status",
                )
            if not isinstance(mapping.get("source_column_examples"), list):
                add_error(
                    errors,
                    path,
                    pseudo_record,
                    f"mapping {index} source_column_examples must be a list",
                )
        paq_targets = {
            mapping.get("mosaiq_field")
            for mapping in mappings
            if str(mapping.get("mosaiq_field", "")).startswith("perception.iso_12913.paq.")
        }
        for field in CANONICAL_PAQ_FIELDS:
            target = f"perception.iso_12913.paq.{field}"
            if target not in paq_targets:
                add_warning(warnings, path, pseudo_record, f"missing mapping target {target}")
    return len(mapping_paths)


def validate_checklist_file(
    path: Path, errors: list[Finding], warnings: list[Finding]
) -> int:
    with path.open("r", encoding="utf-8") as handle:
        checklist = json.load(handle)
    pseudo_record = {"sample_id": path.name}
    datasets = checklist.get("datasets", [])
    if not isinstance(datasets, list) or not datasets:
        add_error(errors, path, pseudo_record, "datasets must be a non-empty list")
        return 0
    for dataset in datasets:
        dataset_id = dataset.get("dataset_id", "<unknown>")
        items = dataset.get("items", [])
        if not items:
            add_error(errors, path, {"sample_id": dataset_id}, "checklist items are required")
        statuses = {item.get("status") for item in items if isinstance(item, dict)}
        if "not_performed" not in statuses:
            add_warning(
                warnings,
                path,
                {"sample_id": dataset_id},
                "checklist should explicitly mark non-performed harmonisation work",
            )
        for item in items:
            if item.get("status") not in HARMONISATION_STATUSES:
                add_error(
                    errors,
                    path,
                    {"sample_id": dataset_id},
                    f"checklist item {item.get('item')} has invalid status",
                )
    return 1


def validate_graph_model_file(path: Path, errors: list[Finding]) -> int:
    with path.open("r", encoding="utf-8") as handle:
        graph = json.load(handle)
    pseudo_record = {"sample_id": path.name}
    for field in ("node_types", "relation_types", "alignment_views", "scope_note"):
        if not graph.get(field):
            add_error(errors, path, pseudo_record, f"{field} is required")
    return 1


def main() -> int:
    args = parse_args()
    errors: list[Finding] = []
    warnings: list[Finding] = []

    schema_path = REPO_ROOT / "shared_schemas" / "schema_level_harmonisation.schema.json"
    with schema_path.open("r", encoding="utf-8") as handle:
        json.load(handle)

    files = iter_jsonl_paths(args.paths)
    records_checked = 0
    for path in files:
        for _, record in load_jsonl(path):
            records_checked += 1
            if record.get("record_type") == "sample":
                validate_sample_record(path, record, errors, warnings)
            else:
                add_error(errors, path, record, "only sample records are validated currently")

    mappings_checked = validate_mapping_files(args.mappings_dir, errors, warnings)
    checklist_checked = validate_checklist_file(
        args.mappings_dir / "harmonisation_checklist.json", errors, warnings
    )
    graph_models_checked = validate_graph_model_file(
        args.mappings_dir / "mosaiq_harmonisation_graph.json", errors
    )

    print("MOSAIQ schema-level harmonisation validation")
    print(f"files checked: {len(files)}")
    print(f"records checked: {records_checked}")
    print(f"mapping files checked: {mappings_checked}")
    print(f"checklist files checked: {checklist_checked}")
    print(f"graph model files checked: {graph_models_checked}")
    print(f"warnings: {len(warnings)}")
    print(f"errors: {len(errors)}")

    if warnings:
        print("\nWarnings:")
        for finding in warnings:
            print(f"- {finding.path}: {finding.record_id}: {finding.message}")

    if errors:
        print("\nErrors:")
        for finding in errors:
            print(f"- {finding.path}: {finding.record_id}: {finding.message}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build MOSAIQ SATP tables from the Zenodo workbook.

Expected source:
https://zenodo.org/records/7143599/files/SATP%20Dataset%20v1.2.xlsx?download=1
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

from iso12913 import compute_method_a_coordinates
from xlsx_xml import read_xlsx_rows


REVISION_DATE = "2026-06-15"
PAQ_FIELDS = {
    "PAQ1": "PAQ1_pleasant",
    "PAQ2": "PAQ2_vibrant",
    "PAQ3": "PAQ3_eventful",
    "PAQ4": "PAQ4_chaotic",
    "PAQ5": "PAQ5_annoying",
    "PAQ6": "PAQ6_monotonous",
    "PAQ7": "PAQ7_uneventful",
    "PAQ8": "PAQ8_calm",
}

PAQ_DIMENSIONS = {
    "PAQ1_pleasant": "pleasant",
    "PAQ2_vibrant": "vibrant",
    "PAQ3_eventful": "eventful",
    "PAQ4_chaotic": "chaotic",
    "PAQ5_annoying": "annoying",
    "PAQ6_monotonous": "monotonous",
    "PAQ7_uneventful": "uneventful",
    "PAQ8_calm": "calm",
}


def _blank_to_none(value: str) -> str | None:
    value = value.strip()
    return value or None


def _number(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    return float(value)


def _paq_number(value: str) -> float | None:
    number = _number(value)
    if number is None or not 0 <= number <= 100:
        return None
    return number


def _format(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return value


def _clip_id(recording: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", recording).strip("_")
    return f"SATP_{safe}"


def _to_likert(raw: float | None) -> float | None:
    if raw is None:
        return None
    return 1.0 + (4.0 * raw / 100.0)


def _coordinates_or_blank(values: dict[str, float | None]) -> dict[str, float | None]:
    try:
        coordinates = compute_method_a_coordinates(values)
    except ValueError:
        return {"pleasantness": None, "eventfulness": None}
    return coordinates


def _write_ratings(outdir: Path, records: list[dict[str, object]], ratings_limit: int | None) -> None:
    rating_fields = [
        "rating_id",
        "dataset_id",
        "clip_id",
        "response_id",
        "participant_id",
        "rating_item_original",
        "rating_dimension",
        "rating_framework",
        "rating_value_original",
        "rating_scale_min_original",
        "rating_scale_max_original",
        "rating_scale_step_original",
        "rating_scale_label_original",
        "rating_value_harmonised",
        "rating_scale_min_harmonised",
        "rating_scale_max_harmonised",
        "harmonisation_method",
        "harmonisation_notes",
        "preprocessing_id",
        "provenance",
    ]
    selected_records = records if ratings_limit is None else records[:ratings_limit]
    with (outdir / "ratings.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rating_fields)
        writer.writeheader()
        for record in selected_records:
            for field, dimension in PAQ_DIMENSIONS.items():
                raw_field = f"{field}_raw_0_100"
                writer.writerow(
                    {
                        "rating_id": f"{record['response_id']}_{field}",
                        "dataset_id": "SATP",
                        "clip_id": record["clip_id"],
                        "response_id": record["response_id"],
                        "participant_id": record["participant_id"],
                        "rating_item_original": raw_field,
                        "rating_dimension": dimension,
                        "rating_framework": "ISO_12913_Method_A_PAQ",
                        "rating_value_original": _format(record.get(raw_field)),
                        "rating_scale_min_original": 0,
                        "rating_scale_max_original": 100,
                        "rating_scale_step_original": "",
                        "rating_scale_label_original": "0=not at all; 100=extremely",
                        "rating_value_harmonised": _format(record.get(field)),
                        "rating_scale_min_harmonised": 1,
                        "rating_scale_max_harmonised": 5,
                        "harmonisation_method": "linear_0_100_to_1_5",
                        "harmonisation_notes": (
                            "Original SATP value is retained in responses.csv; "
                            "1-5 value is derived for MOSAIQ/ISO PAQ comparability."
                        ),
                        "preprocessing_id": f"SATP_PREPROCESS_{field}_SCALE",
                        "provenance": (
                            "Generated from SATP source workbook; full wide response "
                            "table preserves raw and derived columns."
                        ),
                    }
                )


def _write_preprocessing(outdir: Path) -> None:
    preprocessing_fields = [
        "preprocessing_id",
        "dataset_id",
        "clip_id",
        "input_field",
        "output_field",
        "transformation_type",
        "transformation_formula",
        "normalisation_range",
        "software_or_script",
        "code_version",
        "date_created",
        "notes",
    ]
    rows = []
    for field in PAQ_DIMENSIONS:
        rows.append(
            {
                "preprocessing_id": f"SATP_PREPROCESS_{field}_SCALE",
                "dataset_id": "SATP",
                "clip_id": "",
                "input_field": f"{field}_raw_0_100",
                "output_field": field,
                "transformation_type": "scale_conversion",
                "transformation_formula": "1 + 4 * input / 100",
                "normalisation_range": "0-100_to_1-5",
                "software_or_script": "scripts/build_satp.py",
                "code_version": "repository_worktree",
                "date_created": REVISION_DATE,
                "notes": (
                    "SATP source values remain available; the 1-5 value is a "
                    "derived harmonised field, not a replacement."
                ),
            }
        )
    rows.extend(
        [
            {
                "preprocessing_id": "SATP_PREPROCESS_ISO_COORDINATES_RESPONSE",
                "dataset_id": "SATP",
                "clip_id": "",
                "input_field": ";".join(PAQ_DIMENSIONS),
                "output_field": "ISOPleasant;ISOEventful",
                "transformation_type": "iso_coordinate_derivation",
                "transformation_formula": (
                    "ISO 12913 Method A pleasantness/eventfulness formula "
                    "implemented in scripts/iso12913.py"
                ),
                "normalisation_range": "-1_to_1",
                "software_or_script": "scripts/build_satp.py;scripts/iso12913.py",
                "code_version": "repository_worktree",
                "date_created": REVISION_DATE,
                "notes": (
                    "Derived from harmonised 1-5 PAQ item values after preserving "
                    "original SATP ratings."
                ),
            },
            {
                "preprocessing_id": "SATP_PREPROCESS_CLIP_MEANS",
                "dataset_id": "SATP",
                "clip_id": "",
                "input_field": "responses.csv PAQ and loudness fields grouped by clip_id",
                "output_field": "clips.csv mean_* fields",
                "transformation_type": "aggregation",
                "transformation_formula": (
                    "arithmetic mean over non-missing response-level values for each clip_id"
                ),
                "normalisation_range": "",
                "software_or_script": "scripts/build_satp.py",
                "code_version": "repository_worktree",
                "date_created": REVISION_DATE,
                "notes": (
                    "Clip-level summaries are derived aggregates; response-level "
                    "original values remain in responses.csv."
                ),
            },
        ]
    )
    with (outdir / "preprocessing.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=preprocessing_fields)
        writer.writeheader()
        writer.writerows(rows)


def build(source: Path, outdir: Path, ratings_limit: int | None = 2) -> None:
    rows = read_xlsx_rows(source, sheet_name="Main Merge")
    header = rows[0][:16]
    records = []
    for values in rows[1:]:
        values = values + [""] * (len(header) - len(values))
        source_row = dict(zip(header, values[: len(header)], strict=False))
        recording = source_row["Recording"].strip()
        if not recording:
            continue

        raw_values = {field: _paq_number(source_row[field]) for field in PAQ_FIELDS}
        converted = {PAQ_FIELDS[field]: _to_likert(raw_values[field]) for field in PAQ_FIELDS}
        raw = {f"{PAQ_FIELDS[field]}_raw_0_100": raw_values[field] for field in PAQ_FIELDS}
        coordinates = _coordinates_or_blank(converted)

        records.append(
            {
                "clip_id": _clip_id(recording),
                "recording": recording,
                "participant_id": source_row["Participant"].strip(),
                "language": source_row["Language"].strip(),
                "institution": source_row["Institution"].strip(),
                "age": _number(source_row["Age"]),
                "gender": _blank_to_none(source_row["Gender"]),
                "sequence_id": _blank_to_none(source_row["sequence_id"]),
                **converted,
                **raw,
                "loud_raw_0_100": _number(source_row["loud"]),
                "ISOPleasant": coordinates["pleasantness"],
                "ISOEventful": coordinates["eventfulness"],
            }
        )

    outdir.mkdir(parents=True, exist_ok=True)
    for index, record in enumerate(records, start=1):
        record["response_id"] = f"SATP_{index:06d}"

    response_fields = [
        "response_id",
        "clip_id",
        "participant_id",
        "language",
        "institution",
        "age",
        "gender",
        "sequence_id",
        *PAQ_FIELDS.values(),
        *(f"{field}_raw_0_100" for field in PAQ_FIELDS.values()),
        "loud_raw_0_100",
        "ISOPleasant",
        "ISOEventful",
    ]
    with (outdir / "responses.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=response_fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: _format(record.get(field)) for field in response_fields})

    _write_ratings(outdir, records, ratings_limit)
    _write_preprocessing(outdir)

    grouped = defaultdict(list)
    for record in records:
        grouped[record["clip_id"]].append(record)

    clip_fields = [
        "clip_id",
        "dataset_id",
        "recording",
        "audio_asset",
        "licence_spdx",
        "n_responses",
        "n_participants",
        "n_languages",
        *(f"mean_{field}" for field in PAQ_FIELDS.values()),
        "mean_loud_raw_0_100",
        "mean_ISOPleasant",
        "mean_ISOEventful",
    ]
    with (outdir / "clips.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=clip_fields)
        writer.writeheader()
        for clip_id, clip_records in sorted(grouped.items()):
            paq_means = {
                f"mean_{field}": mean(row[field] for row in clip_records if row[field] is not None)
                for field in PAQ_FIELDS.values()
            }
            loud_values = [
                row["loud_raw_0_100"] for row in clip_records if row["loud_raw_0_100"] is not None
            ]
            coordinates = _coordinates_or_blank(paq_means)
            recording = clip_records[0]["recording"]
            row = {
                "clip_id": clip_id,
                "dataset_id": "SATP",
                "recording": recording,
                "audio_asset": f"SATP WAV/{recording}.wav",
                "licence_spdx": "CC-BY-4.0",
                "n_responses": len(clip_records),
                "n_participants": len({record["participant_id"] for record in clip_records}),
                "n_languages": len({record["language"] for record in clip_records}),
                **paq_means,
                "mean_loud_raw_0_100": mean(loud_values) if loud_values else None,
                "mean_ISOPleasant": coordinates["pleasantness"],
                "mean_ISOEventful": coordinates["eventfulness"],
            }
            writer.writerow({field: _format(row.get(field)) for field in clip_fields})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/private/tmp/SATP_Dataset_v1.2.xlsx"))
    parser.add_argument("--outdir", type=Path, default=Path("datasets/SATP/data"))
    parser.add_argument(
        "--ratings-limit",
        type=int,
        default=2,
        help="Number of response rows to expand into long-form ratings examples; use 0 for all rows.",
    )
    args = parser.parse_args()
    ratings_limit = None if args.ratings_limit == 0 else args.ratings_limit
    build(args.source, args.outdir, ratings_limit=ratings_limit)


if __name__ == "__main__":
    main()

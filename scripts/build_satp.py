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


def build(source: Path, outdir: Path) -> None:
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
        for index, record in enumerate(records, start=1):
            writer.writerow(
                {field: _format(record.get(field)) for field in response_fields}
                | {"response_id": f"SATP_{index:06d}"}
            )

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
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the SATP source workbook.",
    )
    parser.add_argument("--outdir", type=Path, default=Path("datasets/SATP/data"))
    args = parser.parse_args()
    build(args.source, args.outdir)


if __name__ == "__main__":
    main()

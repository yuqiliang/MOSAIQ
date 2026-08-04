"""Build MOSAIQ DeLTA tables from the Zenodo workbooks."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from xlsx_xml import read_xlsx_rows


SOURCE_LABELS = [
    "Aircraft",
    "Bells",
    "Bird tweet",
    "Bus",
    "Car",
    "Children",
    "Construction",
    "Dog bark",
    "Footsteps",
    "General traffic",
    "Horn",
    "Laughter",
    "Motorcycle",
    "Music",
    "Non-identifiable",
    "Other",
    "Rail",
    "Rustling leaves",
    "Screeching brakes",
    "Shouting",
    "Siren",
    "Speech",
    "Ventilation",
    "Water",
]


def _field(label: str) -> str:
    return "source_" + re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _clip_id(recording: str) -> str:
    stem = recording.rsplit(".", 1)[0]
    safe = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    return f"DeLTA_{safe}"


def _number(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    return float(value)


def _integer(value: str) -> int | str:
    number = _number(value)
    return "" if number is None else int(number)


def _format(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return value


def _dicts(rows: list[list[str]], header_override: list[str] | None = None) -> list[dict[str, str]]:
    header = header_override or rows[0]
    out = []
    for values in rows[1:]:
        values = values + [""] * (len(header) - len(values))
        row = dict(zip(header, values[: len(header)], strict=False))
        out.append(row)
    return out


def build(responses_source: Path, collapsed_source: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    response_rows = _dicts(read_xlsx_rows(responses_source))
    source_fields = [_field(label) for label in SOURCE_LABELS]
    response_fields = [
        "response_id",
        "clip_id",
        "participant_id",
        "recording",
        "start_time_excel",
        "end_time_excel",
        "gender",
        "age",
        "experiment_id",
        "version",
        "tree_node_key",
        "annoyance",
        *source_fields,
    ]
    with (outdir / "responses.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=response_fields)
        writer.writeheader()
        for index, row in enumerate(response_rows, start=1):
            recording = row["recording"].strip()
            out = {
                "response_id": f"DeLTA_{index:06d}",
                "clip_id": _clip_id(recording),
                "participant_id": row["participant_id"].strip(),
                "recording": recording,
                "start_time_excel": _number(row["start_time"]),
                "end_time_excel": _number(row["end_time"]),
                "gender": row["gender"].strip(),
                "age": _integer(row["age"]),
                "experiment_id": row["experiment_id"].strip(),
                "version": row["version"].strip(),
                "tree_node_key": row["tree_node_key"].strip(),
                "annoyance": _integer(row["annoyance"]),
            }
            out.update({_field(label): _integer(row[label]) for label in SOURCE_LABELS})
            writer.writerow({field: _format(out.get(field)) for field in response_fields})

    collapsed_rows = read_xlsx_rows(collapsed_source)
    header = ["recording", *collapsed_rows[0][1:]]
    clip_rows = _dicts(collapsed_rows, header_override=header)
    clip_fields = [
        "clip_id",
        "dataset_id",
        "recording",
        "audio_asset",
        "licence_spdx",
        "n_responses",
        "n_sources",
        "mean_annoyance",
        *source_fields,
    ]
    with (outdir / "clips.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=clip_fields)
        writer.writeheader()
        for row in clip_rows:
            recording = row["recording"].strip()
            out = {
                "clip_id": _clip_id(recording),
                "dataset_id": "DeLTA",
                "recording": recording,
                "audio_asset": f"DeLTA_mp3_boost_8dB/{recording}",
                "licence_spdx": "CC-BY-4.0",
                "n_responses": _integer(row["no_participants"]),
                "n_sources": _integer(row["no_sources"]),
                "mean_annoyance": _number(row["annoyance"]),
            }
            out.update({_field(label): _integer(row[label]) for label in SOURCE_LABELS})
            writer.writerow({field: _format(out.get(field)) for field in clip_fields})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--responses-source",
        type=Path,
        required=True,
        help="Path to the DeLTA survey-response workbook.",
    )
    parser.add_argument(
        "--collapsed-source",
        type=Path,
        required=True,
        help="Path to the DeLTA collapsed-majority workbook.",
    )
    parser.add_argument("--outdir", type=Path, default=Path("datasets/DeLTA/data"))
    args = parser.parse_args()
    build(args.responses_source, args.collapsed_source, args.outdir)


if __name__ == "__main__":
    main()

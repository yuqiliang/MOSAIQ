"""Minimal XLSX reader for source metadata workbooks.

The project intentionally avoids adding an Excel dependency just to ingest a
small number of source tables. This helper reads plain worksheet cells from
the XLSX zip/XML structure and returns rows as strings.
"""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


SPREADSHEET_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
PACKAGE_REL_NS = {
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _column_index(cell_ref: str) -> int:
    match = re.match(r"[A-Z]+", cell_ref)
    if not match:
        return 0
    value = 0
    for char in match.group(0):
        value = value * 26 + ord(char) - 64
    return value - 1


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(text.text or "" for text in item.findall(".//a:t", SPREADSHEET_NS))
        for item in root.findall("a:si", SPREADSHEET_NS)
    ]


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", SPREADSHEET_NS))

    value_node = cell.find("a:v", SPREADSHEET_NS)
    raw = "" if value_node is None else value_node.text or ""
    if cell_type == "s" and raw:
        return shared[int(raw)]
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw


def read_xlsx_rows(path: str | Path, sheet_name: str | None = None) -> list[list[str]]:
    """Read a worksheet from an XLSX file as a list of string rows."""

    path = Path(path)
    with ZipFile(path) as archive:
        shared = _shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pr:Relationship", PACKAGE_REL_NS)
        }

        sheets = workbook.findall("a:sheets/a:sheet", SPREADSHEET_NS)
        if sheet_name is None:
            sheet = sheets[0]
        else:
            matches = [sheet for sheet in sheets if sheet.attrib["name"] == sheet_name]
            if not matches:
                raise ValueError(f"Sheet {sheet_name!r} not found in {path}")
            sheet = matches[0]

        rel_id = sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        target = relmap[rel_id]
        worksheet_path = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
        root = ET.fromstring(archive.read(worksheet_path))

        rows: list[list[str]] = []
        for row in root.findall("a:sheetData/a:row", SPREADSHEET_NS):
            values: list[str] = []
            for cell in row.findall("a:c", SPREADSHEET_NS):
                index = _column_index(cell.attrib["r"])
                while len(values) < index:
                    values.append("")
                values.append(_cell_value(cell, shared))
            rows.append(values)
        return rows

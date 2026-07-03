# SATP MOSAIQ Notes

Source record: <https://zenodo.org/records/7143599>.

- `responses.csv` is generated from `SATP Dataset v1.2.xlsx`, sheet `Main Merge`.
- SATP PAQ items are supplied on a 0-100 response scale. MOSAIQ stores both the raw
  `*_raw_0_100` values and derived 1-5 PAQ values using `1 + 4 * raw / 100`.
- The derived 1-5 PAQ values are harmonised fields, not replacements for the
  original measurements.
- `ratings.csv` provides a small long-form example of the original-value /
  harmonised-value representation for SATP PAQ items.
- `preprocessing.csv` records the scale-conversion formula, ISO coordinate
  derivation, and clip-level aggregation provenance.
- Source PAQ values outside 0-100 are treated as missing before conversion and
  aggregation.
- `clips.csv` aggregates the converted PAQ values by recording and computes ISO
  12913 Method A `mean_ISOPleasant` / `mean_ISOEventful`.
- The 198.1 MB WAV archive is listed in `source_files.csv` but not committed.

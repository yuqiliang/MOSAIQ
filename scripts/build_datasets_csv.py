"""
Flatten the nested dataset-level JSON into a schema-conformant CSV.

The source JSON has nested objects (Recording.Audio.Ambisonics, etc.)
that don't fit Frictionless's flat-table model. This script flattens
them with underscore-joined keys, normalises units (durations to
seconds), and sets boolean availability flags.
"""
import json
import re
import pandas as pd
from pathlib import Path

SRC = "/mnt/user-data/uploads/dataset-level.json"
OUT = "/home/claude/mosaiq_v2/datasets.csv"


def parse_duration_to_s(value):
    """Convert various duration encodings to seconds.

    Handles strings like '30s', '15 mins', '1 hour', plain numbers, etc.
    Returns None if value is None or unparseable.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    m = re.search(r"([\d.]+)", s)
    if not m:
        return None
    n = float(m.group(1))
    if "hour" in s:
        return n * 3600
    if "min" in s:
        return n * 60
    return n  # assume seconds


def parse_resolution(value):
    """Keep resolution as a string descriptor, normalise where possible."""
    if value is None:
        return ""
    s = str(value).strip()
    return s


def first_int(value):
    """Extract the first integer from a value. Handles '24 or 32' → 24."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    m = re.search(r"\d+", str(value))
    return int(m.group()) if m else None


def safe_get(d, *keys, default=None):
    """Walk nested dict, return default if any key missing or None."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def licence_from_description(description):
    """Heuristic SPDX from description text. Fallback to Unknown."""
    if not description:
        return "Unknown"
    d = description.lower()
    if "cc by-nc-sa" in d:
        return "CC-BY-NC-SA-4.0"
    if "cc by-nc" in d:
        return "CC-BY-NC-4.0"
    if "cc by-sa" in d:
        return "CC-BY-SA-4.0"
    if "cc by" in d:
        return "CC-BY-4.0"
    return "Unknown"


def normalise_visual_format(value):
    """Map free-text visual format to enum."""
    if not value:
        return ""
    v = str(value).lower()
    if "360" in v:
        return "360 Video"
    if "image" in v:
        return "Images"
    if "video" in v:
        return "Video"
    if "mixed" in v:
        return "Mixed"
    return ""


def normalise_setting(value):
    """Map free-text experimental settings to enum."""
    if not value:
        return "Other"
    v = str(value).lower()
    if "site" in v:
        return "On-site"
    if "lab" in v or "vr" in v:
        return "Lab-based"
    if v == "online":
        return "Online"
    if "mixed" in v:
        return "Mixed"
    return "Other"


with open(SRC) as f:
    data = json.load(f)

rows = []
for name, d in data.items():
    rec_audio = safe_get(d, "Recording", "Audio", default={})
    raw_visual = safe_get(d, "Recording", "Visual", default=None)
    # Some datasets store Visual as a string (e.g., "360 video") instead of a dict.
    # Normalise to dict here.
    if isinstance(raw_visual, str):
        rec_visual = {"Format": raw_visual}
    elif isinstance(raw_visual, dict):
        rec_visual = raw_visual
    else:
        rec_visual = {}

    # Sample size has both "Audio Samples" and "Audio Recording" keys
    n_audio = (safe_get(d, "Sample Size", "Audio Samples")
               or safe_get(d, "Sample Size", "Audio Recording"))

    row = {
        # 1. Identification
        "dataset_name":  name,
        "description":   d.get("Description"),
        "year":          d.get("Year"),
        "scenario":      d.get("Scenario"),
        "link":          d.get("Link") if d.get("Link") not in (None, "no available link") else "",

        # 2. Access & licensing
        "access":        d.get("Access") if d.get("Access") != "Partilally" else "Partially",
        "licence_spdx":  licence_from_description(d.get("Description")),

        # 3. Scale
        "n_audio_samples":     n_audio,
        "n_participants":      safe_get(d, "Sample Size", "Participants"),
        "n_assessments":       safe_get(d, "Sample Size", "Assessments"),
        "total_duration_min":  safe_get(d, "Sample Size", "Duration(mins)"),

        # 4a. Ambisonics
        "audio_ambisonics_available":         "Ambisonics" in rec_audio if rec_audio else False,
        "audio_ambisonics_bit_depth":         first_int(safe_get(rec_audio, "Ambisonics", "Bit Depth")),
        "audio_ambisonics_sampling_rate_hz":  safe_get(rec_audio, "Ambisonics", "Sampling Rate"),
        "audio_ambisonics_order":             safe_get(rec_audio, "Ambisonics", "Order"),
        "audio_ambisonics_clip_duration_s":   parse_duration_to_s(
            safe_get(rec_audio, "Ambisonics", "Duration")),

        # 4b. Binaural
        "audio_binaural_available":         "Binaural" in rec_audio if rec_audio else False,
        "audio_binaural_bit_depth":         first_int(safe_get(rec_audio, "Binaural", "Bit Depth")),
        "audio_binaural_sampling_rate_hz":  safe_get(rec_audio, "Binaural", "Sampling Rate"),
        "audio_binaural_clip_duration_s":   parse_duration_to_s(
            safe_get(rec_audio, "Binaural", "Duration") or
            safe_get(rec_audio, "Binaural", "Duration(s)")),

        # 4c. Monaural
        "audio_monaural_available":        "Monaural" in rec_audio if rec_audio else False,
        "audio_monaural_clip_duration_s":  parse_duration_to_s(
            safe_get(rec_audio, "Monaural", "Duration")),

        # 5. Visual
        "visual_available":         len(rec_visual) > 0,
        "visual_format":            normalise_visual_format(rec_visual.get("Format")),
        "visual_resolution":        parse_resolution(rec_visual.get("Resolution")),
        "visual_frame_rate_fps":    rec_visual.get("Frame Rate"),
        "visual_clip_duration_s":   parse_duration_to_s(rec_visual.get("Duration")),

        # 6. Annotation
        "annotation_framework":  safe_get(d, "Emotional Annotation", "Assessment Framework"),
        "experimental_setting":  normalise_setting(
            safe_get(d, "Emotional Annotation", "Experimental Setting")),

        # 7. Acoustic / environmental
        "acoustic_data_available":      d.get("Acoustic Data") is not None,
        "acoustic_measuring_instrument": safe_get(d, "Acoustic Data", "Measuring Instrument"),
        "environmental_data_available": d.get("Environmental Data") is not None,
    }
    rows.append(row)

df = pd.DataFrame(rows)

# Cast nullable integer columns
for col in ["year", "n_audio_samples", "n_participants", "n_assessments",
            "audio_ambisonics_bit_depth", "audio_ambisonics_sampling_rate_hz",
            "audio_ambisonics_order",
            "audio_binaural_bit_depth", "audio_binaural_sampling_rate_hz",
            "visual_frame_rate_fps"]:
    df[col] = df[col].astype("Int64")

df.to_csv(OUT, index=False)
print(f"Wrote {len(df)} dataset rows to {OUT}")
print(f"Columns ({len(df.columns)}):")
for c in df.columns:
    print(f"  - {c}")

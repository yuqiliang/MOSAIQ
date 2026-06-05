"""Small ISO 12913 helpers for MOSAIQ schema-level harmonisation.

This module intentionally stays narrow: it maps ISO perceived affective
quality (PAQ) item names to MOSAIQ canonical names and can compute Method A
pleasantness/eventfulness coordinates when all eight PAQ items are present.
It does not infer missing labels or convert non-ISO annotation frameworks.
"""

from __future__ import annotations

from math import cos, pi, sqrt
from typing import Mapping


CANONICAL_PAQ_FIELDS = (
    "pleasant",
    "vibrant",
    "eventful",
    "chaotic",
    "annoying",
    "monotonous",
    "uneventful",
    "calm",
)

ISO_METHOD_A_ORIGINAL_FIELDS = {
    "PAQ1_pleasant": "pleasant",
    "PAQ2_vibrant": "vibrant",
    "PAQ3_eventful": "eventful",
    "PAQ4_chaotic": "chaotic",
    "PAQ5_annoying": "annoying",
    "PAQ6_monotonous": "monotonous",
    "PAQ7_uneventful": "uneventful",
    "PAQ8_calm": "calm",
    "mean_PAQ1_pleasant": "pleasant",
    "mean_PAQ2_vibrant": "vibrant",
    "mean_PAQ3_eventful": "eventful",
    "mean_PAQ4_chaotic": "chaotic",
    "mean_PAQ5_annoying": "annoying",
    "mean_PAQ6_monotonous": "monotonous",
    "mean_PAQ7_uneventful": "uneventful",
    "mean_PAQ8_calm": "calm",
}


def canonicalize_paq_fields(
    ratings: Mapping[str, float | int | None],
) -> dict[str, float | None]:
    """Return PAQ ratings under canonical MOSAIQ ISO 12913 item names.

    Missing values remain ``None``. Unknown input fields are ignored so callers
    can pass wider source rows without pre-filtering.
    """

    canonical = {field: None for field in CANONICAL_PAQ_FIELDS}
    for original_field, value in ratings.items():
        canonical_field = ISO_METHOD_A_ORIGINAL_FIELDS.get(original_field, original_field)
        if canonical_field in canonical:
            canonical[canonical_field] = None if value is None else float(value)
    return canonical


def compute_method_a_coordinates(
    paq: Mapping[str, float | int | None],
) -> dict[str, float]:
    """Compute ISO 12913 Method A pleasantness and eventfulness coordinates.

    The input must contain all eight canonical PAQ fields. The function raises
    ``ValueError`` when any item is missing, keeping missingness explicit for
    the caller instead of guessing or imputing labels.
    """

    ratings = canonicalize_paq_fields(paq)
    missing = [field for field, value in ratings.items() if value is None]
    if missing:
        raise ValueError(f"Cannot compute ISO Method A coordinates; missing: {missing}")

    c = cos(pi / 4.0)
    denominator = 4.0 + sqrt(32.0)

    pleasantness = (
        (ratings["pleasant"] - ratings["annoying"])
        + c
        * (
            (ratings["calm"] - ratings["chaotic"])
            + (ratings["vibrant"] - ratings["monotonous"])
        )
    ) / denominator
    eventfulness = (
        (ratings["eventful"] - ratings["uneventful"])
        + c
        * (
            (ratings["chaotic"] - ratings["calm"])
            + (ratings["vibrant"] - ratings["monotonous"])
        )
    ) / denominator

    return {
        "pleasantness": pleasantness,
        "eventfulness": eventfulness,
    }

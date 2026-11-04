from math import cos, pi, sqrt

import pytest

from scripts.iso12913 import compute_method_a_coordinates


def test_method_a_neutral_profile_is_origin() -> None:
    values = {
        "pleasant": 3,
        "vibrant": 3,
        "eventful": 3,
        "chaotic": 3,
        "annoying": 3,
        "monotonous": 3,
        "uneventful": 3,
        "calm": 3,
    }
    assert compute_method_a_coordinates(values) == {
        "pleasantness": 0.0,
        "eventfulness": 0.0,
    }


def test_method_a_matches_declared_formula() -> None:
    values = {
        "pleasant": 5,
        "vibrant": 4,
        "eventful": 4,
        "chaotic": 2,
        "annoying": 1,
        "monotonous": 2,
        "uneventful": 2,
        "calm": 4,
    }
    result = compute_method_a_coordinates(values)
    coefficient = cos(pi / 4)
    denominator = 4 + sqrt(32)
    expected_pleasant = ((5 - 1) + coefficient * ((4 - 2) + (4 - 2))) / denominator
    expected_eventful = ((4 - 2) + coefficient * ((2 - 4) + (4 - 2))) / denominator
    assert result["pleasantness"] == pytest.approx(expected_pleasant)
    assert result["eventfulness"] == pytest.approx(expected_eventful)
    assert -1 <= result["pleasantness"] <= 1
    assert -1 <= result["eventfulness"] <= 1


def test_method_a_rejects_missing_items() -> None:
    with pytest.raises(ValueError, match="missing"):
        compute_method_a_coordinates({"pleasant": 3})

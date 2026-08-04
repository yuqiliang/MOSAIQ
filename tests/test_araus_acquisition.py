from scripts.acquire_araus import classify_file


def test_araus_restricted_usotw_archive_is_reference_only() -> None:
    status, note = classify_file("soundscapes_raw.zip", restricted=True)
    assert status == "reference_only"
    assert "USotW" in note


def test_araus_v1_archives_are_private_draft_candidates() -> None:
    status, note = classify_file("data.zip", restricted=False)
    assert status == "private_draft_candidate"
    assert "rights remain under review" in note


def test_araus_v2_and_visual_archives_are_deferred() -> None:
    assert classify_file("datav2.zip", restricted=False)[0] == "deferred_araus_v2"
    assert classify_file("videos.zip", restricted=False)[0] == "deferred_visual"


def test_araus_figures_are_not_benchmark_inputs() -> None:
    assert classify_file("figures.zip", restricted=False)[0] == "excluded_nonbenchmark"


def test_araus_unknown_files_are_excluded() -> None:
    status, _ = classify_file("unexpected.zip", restricted=False)
    assert status == "excluded_unexpected"

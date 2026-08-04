from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.acquire_isd_audio import benchmark_scope_status, safe_extract_wavs


def test_audio_archive_scope_separates_lockdown_sources() -> None:
    assert benchmark_scope_status("WAV_London_1.zip") == "benchmark_candidate"
    assert (
        benchmark_scope_status("WAV_Lockdown_London.zip")
        == "source_audit_only_pending_label_linkage"
    )


def test_safe_extract_namespaces_nonstandard_archive_root(tmp_path: Path) -> None:
    archive = tmp_path / "WAV_Example_1.zip"
    with ZipFile(archive, "w") as package:
        package.writestr("Supplier WAV Files/Location/X1.wav", b"wav")
        package.writestr("__MACOSX/._X1.wav", b"metadata")
        package.writestr("Supplier WAV Files/Location/X1.txt", b"sidecar")
    extraction = tmp_path / "extracted"
    assert safe_extract_wavs(archive, extraction) == 1
    assert (
        extraction
        / "WAV_Example_1"
        / "Supplier WAV Files"
        / "Location"
        / "X1.wav"
    ).read_bytes() == b"wav"


def test_safe_extract_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "WAV_Unsafe.zip"
    with ZipFile(archive, "w") as package:
        package.writestr("../escape.wav", b"wav")
    with pytest.raises(RuntimeError, match="Unsafe archive member"):
        safe_extract_wavs(archive, tmp_path / "extracted")

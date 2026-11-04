from pathlib import Path

import pytest

from scripts.documentation_scope import is_private_document
from scripts.build_rdr_package import is_included


@pytest.mark.parametrize("path", [
    "docs/recap/2026-11-03/README.md",
    "docs/meeting-notes.md",
    "docs/release/pre_audio_work_plan.md",
    "docs/repository_audit.md",
    "benchmark/audits/readiness_status.yaml",
    "papers/paper2_manuscript_compliance_audit_2026-07-30.md",
    "papers/paper2_fixed_outputs/v0.1.0/draft_replacement_audit.md",
    "outputs/schema07-audit/review.xlsx",
    "scripts/build_project_recap.py",
])
def test_personal_documents_are_classified(path: str) -> None:
    assert is_private_document(path)


@pytest.mark.parametrize("path", [
    "docs/reproduce_benchmark.md",
    "docs/release/RDR_README.md",
    "benchmark/validation/license_audit.csv",
    "benchmark/robustness/robustness_report.md",
    "papers/paper2_fixed_outputs/v0.1.0/reproduction_notes.md",
])
def test_public_reproduction_documents_are_retained(path: str) -> None:
    assert not is_private_document(path)


def test_release_packager_excludes_personal_note_even_when_present(tmp_path: Path) -> None:
    note = tmp_path / "docs" / "recap" / "notes.md"
    note.parent.mkdir(parents=True)
    note.write_text("Personal working note")
    assert not is_included(note, tmp_path)


def test_release_packager_keeps_public_document(tmp_path: Path) -> None:
    document = tmp_path / "docs" / "reproduce_benchmark.md"
    document.parent.mkdir(parents=True)
    document.write_text("Public reproduction instructions")
    assert is_included(document, tmp_path)


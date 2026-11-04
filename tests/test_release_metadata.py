from pathlib import Path

import pandas as pd
import yaml

from scripts.build_benchmark_report import summarise_frictionless_output


ROOT = Path(__file__).resolve().parents[1]


def test_citation_metadata_is_parseable_and_candidate_scoped() -> None:
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    assert citation["cff-version"] == "1.2.0"
    assert citation["version"] == "0.1.0-dev"
    assert citation["license"] == "MIT"
    assert len(citation["authors"]) == 5


def test_governance_registry_covers_every_materialised_dataset() -> None:
    registry = pd.read_csv(
        ROOT / "benchmark" / "governance" / "license_consent_registry.csv"
    )
    assert {"ISD", "ARAUS", "SATP", "DeLTA"}.issubset(set(registry["dataset_id"]))
    araus_media = registry[
        registry["dataset_id"].eq("ARAUS")
        & registry["component"].str.contains("raw", case=False)
    ]
    assert araus_media["release_blocker"].all()
    assert araus_media["redistribution_status"].eq("per_file_review_required").all()


def test_fixed_output_build_has_no_legacy_markdown_dependency() -> None:
    config = yaml.safe_load(
        (ROOT / "papers" / "paper2_output_config.yaml").read_text(encoding="utf-8")
    )
    assert "draft_path" not in config
    assert config["legacy_draft_status"] == "integrated_and_removed"
    assert not (ROOT / "papers" / "paper2_benchmark_draft.md").exists()


def test_benchmark_freeze_has_stable_generation_metadata() -> None:
    release = yaml.safe_load(
        (ROOT / "benchmark" / "release.yaml").read_text(encoding="utf-8")
    )
    assert release["freeze"]["generated_at"] == "2026-07-17T16:00:00Z"


def test_frictionless_summary_ignores_runtime_duration() -> None:
    first = (
        '{"valid":true,"tasks":[{"name":"clips","valid":true,'
        '"stats":{"errors":0,"warnings":0,"seconds":0.1,"rows":3,'
        '"fields":2,"sha256":"abc"}}]}'
    )
    second = first.replace('"seconds":0.1', '"seconds":9.9')
    assert summarise_frictionless_output(first) == summarise_frictionless_output(second)

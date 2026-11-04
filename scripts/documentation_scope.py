"""Keep personal research documents out of the public repository and archives."""

from fnmatch import fnmatchcase
from pathlib import Path
import sys


PRIVATE_DOCUMENT_PATTERNS = (
    "docs/recap/*",
    "docs/meeting*",
    "docs/*/meeting*",
    "docs/*three_pass_audit*",
    "docs/*change_ledger*",
    "docs/repository_audit.md",
    "docs/public_dataset_import_ledger_*.md",
    "docs/release/pre_audio_work_plan.md",
    "docs/release/ucl_rdr_package_plan.md",
    "docs/release/*_audit_*.md",
    "benchmark/audits/*",
    "papers/paper2_manuscript_compliance_audit_*.md",
    "papers/paper2_fixed_outputs/*/draft_replacement_audit.md",
    "outputs/*",
    "scripts/build_project_recap.py",
    "scripts/update_paper2_audio_draft.py",
)


def is_private_document(relative_path: str | Path) -> bool:
    path = Path(relative_path).as_posix()
    return any(fnmatchcase(path, pattern) for pattern in PRIVATE_DOCUMENT_PATTERNS)


def find_private_documents(root: Path) -> list[str]:
    found = []
    for name in ("docs", "benchmark", "papers", "outputs", "scripts"):
        directory = root / name
        if directory.is_dir():
            found.extend(
                path.relative_to(root).as_posix()
                for path in directory.rglob("*")
                if path.is_file() and is_private_document(path.relative_to(root))
            )
    return sorted(found)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = find_private_documents(root)
    if paths:
        print("Personal research documents must be stored outside the repository:")
        print("\n".join(paths))
        sys.exit(1)
    print("Documentation scope passed: no personal recaps, meeting notes or work audits")


if __name__ == "__main__":
    main()


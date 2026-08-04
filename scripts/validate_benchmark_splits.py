"""Validate released MOSAIQ benchmark split assignments."""

from build_benchmark_splits import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SPLIT_VERSION,
    validate_outputs,
)


if __name__ == "__main__":
    validate_outputs(DEFAULT_OUTPUT_DIR, DEFAULT_SPLIT_VERSION)

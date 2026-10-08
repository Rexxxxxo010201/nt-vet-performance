"""
Privacy guard for app/data/. The app may only ever read aggregate CSVs:
no USI, no date of birth, no internal student identifier, and nothing
that looks like one. This test fails loudly if any file in app/data/
carries such a column, and if app/data/ is empty (so the check can't be
silently skipped by having nothing to scan).
"""

from pathlib import Path

import pandas as pd
import pytest

from lib.privacy import find_forbidden_columns

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "data"


def _csv_files():
    files = sorted(APP_DATA_DIR.glob("*.csv"))
    assert files, f"No CSV files found in {APP_DATA_DIR}; the privacy check has nothing to scan."
    return files


def test_app_data_directory_exists():
    assert APP_DATA_DIR.is_dir(), f"{APP_DATA_DIR} does not exist."


@pytest.mark.parametrize("csv_path", _csv_files(), ids=lambda p: p.name)
def test_no_identifier_columns(csv_path):
    df = pd.read_csv(csv_path, nrows=0)  # header only - never materialise row data for this check
    offending = find_forbidden_columns(df.columns)
    assert not offending, f"{csv_path.name} has forbidden identifier-like column(s): {offending}"


def test_no_raw_or_clean_files_leaked_into_app_data():
    """app/data/ must only contain files this build step is known to have
    copied from outputs/analysis_tables/ (plus the three doc files), never
    anything copied directly from data/raw or data/clean."""
    allowed_extra = {"cleaning_log.csv", "recovered_funding_source.csv", "data_quality_summary.md", "analysis_methods.md"}
    for path in APP_DATA_DIR.iterdir():
        if path.name in allowed_extra:
            continue
        assert path.suffix == ".csv" and path.name.startswith("t"), (
            f"Unexpected file in app/data/: {path.name}. Only analysis_tables CSVs (t0x_*.csv) "
            f"and the three documentation files should live here."
        )

"""
Syncs app/data/ from the analysis outputs. Copies an explicit whitelist
of files - every T01-T17 table CSV plus the three documentation files -
from outputs/ into app/data/, refuses to copy any CSV carrying a
forbidden identifier-like column (see app/lib/privacy.py), and reports
what was added, updated, or already up to date.

This is the only sanctioned way to populate app/data/: never copy a file
into app/data/ by hand, and never copy anything from data/raw/ or
data/clean/ - only from outputs/, which already holds aggregate-only
tables built by scripts/analysis_tables.py.
"""

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import pandas as pd  # noqa: E402

from lib.privacy import find_forbidden_columns  # noqa: E402

OUTPUTS_TABLES_DIR = ROOT / "outputs" / "analysis_tables"
OUTPUTS_DIR = ROOT / "outputs"
APP_DATA_DIR = ROOT / "app" / "data"

# Explicit whitelist - every T01-T16 analysis table, plus the three
# documentation files. A file not on this list is never copied, even if
# it appears in outputs/, and app/data/ should never hold anything else.
TABLE_WHITELIST = [
    "t01_kpis.csv",
    "t02a_coverage_summary.csv",
    "t02b_coverage_by_provider.csv",
    "t02c_delivery_without_contract.csv",
    "t02d_uncontracted_excluding_11k.csv",
    "t03a_matched_pairs.csv",
    "t03b_rollups.csv",
    "t04_coverage_grid.csv",
    "t05a_pairs_geography.csv",
    "t05b_aggregate_geography.csv",
    "t05c_geography_flags.csv",
    "t06a_ahc_by_funding_outcome.csv",
    "t06b_sankey_links.csv",
    "t06c_withdrawn_notachieved_by_funded_flag.csv",
    "t07_completion_by_group.csv",
    "t07_omnibus_tests.csv",
    "t08a_atsi_reach.csv",
    "t08b_vet_in_schools.csv",
    "t08c_at_school_suspect_totals.csv",
    "t09a_unadjusted_completion_by_atsi.csv",
    "t09b_atsi_gap.csv",
    "t09c_adjusted_gee.csv",
    "t10_sensitivity.csv",
    "t11_context.csv",
    "t12a_by_industry.csv",
    "t12b_by_program.csv",
    "t12c_industry_by_funding_source.csv",
    "t12c_industry_by_remoteness.csv",
    "t12d_concentration.csv",
    "t13_by_qualification_level.csv",
    "t14_by_town.csv",
    "t14b_town_summary.csv",
    "t15_program_intensity.csv",
    "t16_student_count_chance_check.csv",
    "t17a_ahc_by_industry_outcome.csv",
    "t18_atsi_enrolled_share.csv",
    "t18b_atsi_omnibus_tests.csv",
    "t19_provider_names.csv",
    "t20_pathway_check.csv",
    "t21_data_quality_figures.csv",
]
DOC_WHITELIST = [
    "cleaning_log.csv",
    "recovered_funding_source.csv",
    "data_quality_summary.md",
    "analysis_methods.md",
]
FULL_WHITELIST = TABLE_WHITELIST + DOC_WHITELIST


def _source_path(name):
    if name in TABLE_WHITELIST:
        return OUTPUTS_TABLES_DIR / name
    return OUTPUTS_DIR / name


def main():
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    added, updated, unchanged, refused, missing_source = [], [], [], [], []

    for name in FULL_WHITELIST:
        src = _source_path(name)
        dst = APP_DATA_DIR / name

        if not src.exists():
            missing_source.append(name)
            continue

        if name.endswith(".csv"):
            offending = find_forbidden_columns(pd.read_csv(src, nrows=0).columns)
            if offending:
                refused.append((name, offending))
                continue

        if not dst.exists():
            shutil.copy2(src, dst)
            added.append(name)
        elif not filecmp.cmp(src, dst, shallow=False):
            shutil.copy2(src, dst)
            updated.append(name)
        else:
            unchanged.append(name)

    extra = sorted(p.name for p in APP_DATA_DIR.iterdir() if p.name not in FULL_WHITELIST)

    print(f"Added ({len(added)}):")
    for name in added:
        print(f"  {name}")
    print(f"Updated ({len(updated)}):")
    for name in updated:
        print(f"  {name}")
    print(f"Unchanged ({len(unchanged)}): {len(unchanged)} file(s)")

    if missing_source:
        print(f"\nWARNING: whitelisted but not found in outputs/ ({len(missing_source)}):")
        for name in missing_source:
            print(f"  {name}")

    if refused:
        print(f"\nREFUSED to copy - forbidden identifier-like column(s) found ({len(refused)}):")
        for name, offending in refused:
            print(f"  {name}: {offending}")

    if extra:
        print(f"\nWARNING: app/data/ has file(s) not on the whitelist (not touched, review by hand) ({len(extra)}):")
        for name in extra:
            print(f"  {name}")

    if refused or missing_source:
        sys.exit(1)


if __name__ == "__main__":
    main()

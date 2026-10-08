"""
Cached data loaders. One function per table, each reading only from
app/data/ (never from data/raw or data/clean - this app must never see
student-level rows). All paths are resolved relative to this file, so the
app works regardless of the process's working directory.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(APP_DATA_DIR / name)


@st.cache_data
def _load_text(name: str) -> str:
    return (APP_DATA_DIR / name).read_text()


@st.cache_data
def _find_table_by_columns(required_columns: frozenset) -> pd.DataFrame:
    """Scan every CSV in app/data/ and return the one whose columns are a
    superset of required_columns, without assuming a filename. Raises a
    clear error if zero or more than one table matches."""
    matches = []
    for path in sorted(APP_DATA_DIR.glob("*.csv")):
        cols = set(pd.read_csv(path, nrows=0).columns)
        if required_columns.issubset(cols):
            matches.append(path)
    if not matches:
        raise FileNotFoundError(f"No table in {APP_DATA_DIR} has all of these columns: {sorted(required_columns)}")
    if len(matches) > 1:
        raise ValueError(
            f"More than one table in {APP_DATA_DIR} has all of these columns {sorted(required_columns)}: "
            f"{[p.name for p in matches]}"
        )
    return _load_csv(matches[0].name)


@st.cache_data
def _find_table_by_metric_contains(substring: str) -> pd.DataFrame:
    """Scan every Metric/Value-shaped CSV in app/data/ and return the one
    whose Metric column contains a cell matching `substring`, without
    assuming a filename. Raises a clear error if zero or more than one
    table matches."""
    matches = []
    for path in sorted(APP_DATA_DIR.glob("*.csv")):
        header = pd.read_csv(path, nrows=0)
        if not {"Metric", "Value"}.issubset(header.columns):
            continue
        full = pd.read_csv(path)
        if full["Metric"].astype(str).str.contains(substring, regex=False).any():
            matches.append(path)
    if not matches:
        raise FileNotFoundError(f"No Metric/Value table in {APP_DATA_DIR} has a Metric containing '{substring}'.")
    if len(matches) > 1:
        raise ValueError(f"More than one Metric/Value table matches '{substring}': {[p.name for p in matches]}")
    return _load_csv(matches[0].name)


def find_coverage_summary() -> pd.DataFrame:
    """Funded AHC split by coverage bucket (matched comparable pair, matched
    with no target set, delivery without a contract), located by its
    Coverage_Bucket/AHC/Share_of_Total_% columns, not by filename."""
    return _find_table_by_columns(frozenset({"Coverage_Bucket", "AHC", "Share_of_Total_%"}))


def find_delivery_without_contract() -> pd.DataFrame:
    """The Provider_ID + Funding_Source pairs with delivery but no contract,
    located by its Flag_P008_FFT column, not by filename."""
    return _find_table_by_columns(frozenset({"Provider_ID", "Funding_Source", "AHC", "Flag_P008_FFT"}))


def find_coverage_grid() -> pd.DataFrame:
    """The Provider_ID x Funding_Source coverage grid with Status, located by
    its Status/Delivered_AHC columns, not by filename."""
    return _find_table_by_columns(frozenset({"Provider_ID", "Funding_Source", "Status", "Delivered_AHC"}))


def find_matched_pairs() -> pd.DataFrame:
    """The 19 matched comparable pairs with delivered vs target AHC,
    located by its Provider_ID/Funding_Source/Delivered_AHC/
    Target_AHC_Total columns, not by filename."""
    return _find_table_by_columns(
        frozenset({"Provider_ID", "Funding_Source", "Delivered_AHC", "Target_AHC_Total", "Delivered_pct_of_Target"})
    )


def find_rollups() -> pd.DataFrame:
    """The delivered-vs-target roll-up by Provider_ID, by Funding_Source,
    and Overall, located by its Level/Key columns, not by filename."""
    return _find_table_by_columns(
        frozenset({"Level", "Key", "Delivered_AHC", "Target_AHC_Total", "Delivered_pct_of_Target"})
    )


def find_pairs_geography() -> pd.DataFrame:
    """The per-pair remoteness mix (target share, delivered share, and
    the difference in percentage points, for each of the 19 matched
    pairs x 3 remoteness classes), located by its Provider_ID/
    Funding_Source/Remoteness/Diff_pp columns, not by filename."""
    return _find_table_by_columns(
        frozenset({"Provider_ID", "Funding_Source", "Remoteness", "Target_Share_%", "Delivered_Share_%", "Diff_pp"})
    )


def find_aggregate_geography() -> pd.DataFrame:
    """The aggregate remoteness mix (summed target and delivered AHC
    across all 19 matched pairs, by Remoteness), located by its
    Target_AHC_Sum/Delivered_AHC_Sum/Delivered_pct_of_Target_% columns,
    not by filename."""
    return _find_table_by_columns(
        frozenset({"Remoteness", "Target_AHC_Sum", "Delivered_AHC_Sum", "Delivered_pct_of_Target_%"})
    )


def find_program_intensity() -> pd.DataFrame:
    """The program intensity table (10 programs plus 2 summary rows),
    located by its AHC_per_Unit/Mean_Nominal_Hours_per_Unit/
    Mean_Funded_Fraction columns, not by filename."""
    return _find_table_by_columns(
        frozenset(
            {
                "Program_ID",
                "Short_Label",
                "Industry",
                "Distinct_Students",
                "Units",
                "AHC_Funded",
                "Share_of_Total_%",
                "AHC_per_Unit",
                "Mean_Nominal_Hours_per_Unit",
                "Mean_Funded_Fraction",
            }
        )
    )


def find_program_labels() -> pd.DataFrame:
    """The program table carrying each program's full qualification
    name, located by its Program_Name/Full_Label columns, not by
    filename."""
    return _find_table_by_columns(frozenset({"Program_ID", "Program_Name", "Full_Label"}))


def find_student_count_chance_check() -> pd.DataFrame:
    """The student-count chance-check table (observed minimum/maximum
    and the two-sided p-value), located by its Metric text mentioning
    'Two-sided p-value', not by filename."""
    return _find_table_by_metric_contains("Two-sided p-value")


def find_uncontracted_excluding_11k() -> pd.DataFrame:
    """The uncontracted-AHC-excluding-11K table, located by its Metric text
    mentioning '11K' (its columns are the generic Metric/Value shape shared
    by several other tables, so filename or column-name matching alone
    would be ambiguous)."""
    return _find_table_by_metric_contains("11K")


def find_stream_outcome() -> pd.DataFrame:
    """Funded AHC by Funding_Source and Outcome_Group, with the share
    within each stream and of the grand total, located by that
    combination of columns, not by filename."""
    return _find_table_by_columns(
        frozenset({"Funding_Source", "Outcome_Group", "AHC_Funded", "Share_within_Stream_%", "Share_Overall_%"})
    )


def find_withdrawn_notachieved_by_funded_flag() -> pd.DataFrame:
    """AHC on withdrawn/not-achieved units split by Funded_Flag, located
    by its Funded_Flag/Share_% columns, not by filename."""
    return _find_table_by_columns(frozenset({"Funded_Flag", "AHC_Funded", "Share_%"}))


def find_completion_by_group() -> pd.DataFrame:
    """Unit-level completion rate with its 95% interval, units and
    students, for Overall and by Funding_Source/Provider_ID/
    Remoteness/Industry/Delivery_Year, located by that combination of
    columns, not by filename."""
    return _find_table_by_columns(frozenset({"Dimension", "Group", "Rate_%", "CI_Lower", "CI_Upper", "Units", "Students"}))


def find_completion_omnibus_tests() -> pd.DataFrame:
    """The omnibus GEE test (any difference between groups) and spread,
    per dimension, located by its Omnibus_GEE_p_value/Spread_pp
    columns, not by filename."""
    return _find_table_by_columns(frozenset({"Dimension", "Omnibus_GEE_p_value", "Spread_pp"}))


def find_industry_outcome() -> pd.DataFrame:
    """Funded AHC by Industry and Outcome_Group, with the share within
    each industry and the industry's not-completed share, located by
    that combination of columns, not by filename."""
    return _find_table_by_columns(
        frozenset({"Industry", "Outcome_Group", "AHC_Funded", "Share_within_Industry_%", "Not_Completed_Share_%"})
    )


def find_atsi_completion() -> pd.DataFrame:
    """Unadjusted unit-level completion rate by ATSI (Y/N), overall and
    by Remoteness/Funding_Source, with achieved units and full-precision
    companions, located by that combination of columns, not by filename."""
    return _find_table_by_columns(
        frozenset(
            {
                "Dimension", "Group", "ATSI", "Rate_%", "CI_Lower", "CI_Upper", "Units",
                "Achieved_units", "Rate_exact", "Lower_exact", "Upper_exact",
            }
        )
    )


def find_atsi_gap() -> pd.DataFrame:
    """The ATSI completion gap (Y minus N) with its 95% interval and
    full-precision companions, overall and by Remoteness/Funding_Source,
    located by that combination of columns, not by filename."""
    return _find_table_by_columns(
        frozenset(
            {
                "Dimension", "Group", "Gap_pp_Y_minus_N", "CI_Lower", "CI_Upper",
                "N_Comparisons_in_Table", "Gap_exact", "Lower_exact", "Upper_exact",
            }
        )
    )


def find_atsi_adjusted_model() -> pd.DataFrame:
    """The adjusted GEE model table (ATSI odds ratio with interval and
    p-value, and model-predicted Y/N completion rates), located by its
    Metric text mentioning 'ATSI odds ratio', not by filename (its
    columns, Metric/Value/Value_exact, are shared with other tables)."""
    return _find_table_by_metric_contains("ATSI odds ratio")


def load_t01_kpis() -> pd.DataFrame:
    return _load_csv("t01_kpis.csv")


def load_t02a_coverage_summary() -> pd.DataFrame:
    return _load_csv("t02a_coverage_summary.csv")


def load_t02b_coverage_by_provider() -> pd.DataFrame:
    return _load_csv("t02b_coverage_by_provider.csv")


def load_t02c_delivery_without_contract() -> pd.DataFrame:
    return _load_csv("t02c_delivery_without_contract.csv")


def load_t02d_uncontracted_excluding_11k() -> pd.DataFrame:
    return _load_csv("t02d_uncontracted_excluding_11k.csv")


def load_t03a_matched_pairs() -> pd.DataFrame:
    return _load_csv("t03a_matched_pairs.csv")


def load_t03b_rollups() -> pd.DataFrame:
    return _load_csv("t03b_rollups.csv")


def load_t04_coverage_grid() -> pd.DataFrame:
    return _load_csv("t04_coverage_grid.csv")


def load_t05a_pairs_geography() -> pd.DataFrame:
    return _load_csv("t05a_pairs_geography.csv")


def load_t05b_aggregate_geography() -> pd.DataFrame:
    return _load_csv("t05b_aggregate_geography.csv")


def load_t05c_geography_flags() -> pd.DataFrame:
    return _load_csv("t05c_geography_flags.csv")


def load_t06a_ahc_by_funding_outcome() -> pd.DataFrame:
    return _load_csv("t06a_ahc_by_funding_outcome.csv")


def load_t06b_sankey_links() -> pd.DataFrame:
    return _load_csv("t06b_sankey_links.csv")


def load_t06c_withdrawn_notachieved_by_funded_flag() -> pd.DataFrame:
    return _load_csv("t06c_withdrawn_notachieved_by_funded_flag.csv")


def load_t07_completion_by_group() -> pd.DataFrame:
    return _load_csv("t07_completion_by_group.csv")


def load_t07_omnibus_tests() -> pd.DataFrame:
    return _load_csv("t07_omnibus_tests.csv")


def load_t08a_atsi_reach() -> pd.DataFrame:
    return _load_csv("t08a_atsi_reach.csv")


def load_t08b_vet_in_schools() -> pd.DataFrame:
    return _load_csv("t08b_vet_in_schools.csv")


def load_t08c_at_school_suspect_totals() -> pd.DataFrame:
    return _load_csv("t08c_at_school_suspect_totals.csv")


def load_t09a_unadjusted_completion_by_atsi() -> pd.DataFrame:
    return _load_csv("t09a_unadjusted_completion_by_atsi.csv")


def load_t09b_atsi_gap() -> pd.DataFrame:
    return _load_csv("t09b_atsi_gap.csv")


def load_t09c_adjusted_gee() -> pd.DataFrame:
    return _load_csv("t09c_adjusted_gee.csv")


def load_t10_sensitivity() -> pd.DataFrame:
    return _load_csv("t10_sensitivity.csv")


def load_t11_context() -> pd.DataFrame:
    return _load_csv("t11_context.csv")


def load_t12a_by_industry() -> pd.DataFrame:
    return _load_csv("t12a_by_industry.csv")


def load_t12b_by_program() -> pd.DataFrame:
    return _load_csv("t12b_by_program.csv")


def load_t15_program_intensity() -> pd.DataFrame:
    return _load_csv("t15_program_intensity.csv")


def load_t16_student_count_chance_check() -> pd.DataFrame:
    return _load_csv("t16_student_count_chance_check.csv")


def load_t17a_ahc_by_industry_outcome() -> pd.DataFrame:
    return _load_csv("t17a_ahc_by_industry_outcome.csv")


def load_cleaning_log() -> pd.DataFrame:
    return _load_csv("cleaning_log.csv")


def load_data_quality_summary_text() -> str:
    return _load_text("data_quality_summary.md")


def load_analysis_methods_text() -> str:
    return _load_text("analysis_methods.md")


def find_atsi_enrolled_share() -> pd.DataFrame:
    """Share of enrolled students recorded as ATSI = Y, overall and by
    Funding_Source, Provider_ID and Remoteness (Reach), located by its
    ATSI_students/Share_exact columns, not by filename."""
    return _find_table_by_columns(frozenset({"Dimension", "Group", "ATSI_students", "Share_exact"}))


def find_atsi_omnibus() -> pd.DataFrame:
    """Per-dimension test for any ATSI-share difference between groups
    (Reach), located by its P_value column, not by filename."""
    return _find_table_by_columns(frozenset({"Dimension", "P_value"}))


def find_sensitivity() -> pd.DataFrame:
    """Completion rate under the alternative definitions (T10), located by
    its Definition/Scope/Rate_% columns, not by filename."""
    return _find_table_by_columns(frozenset({"Definition", "Scope", "Rate_%"}))


def find_provider_names() -> pd.DataFrame:
    """Provider_ID and its organisation name (T19), located by its
    Provider_Name column, not by filename."""
    return _find_table_by_columns(frozenset({"Provider_ID", "Provider_Name"}))


def find_pathway_check() -> pd.DataFrame:
    """The FSK10213-to-higher-program pathway check (T20), located by a
    Metric cell mentioning FSK10213, not by filename."""
    return _find_table_by_metric_contains("FSK10213")


def find_data_quality_figures() -> pd.DataFrame:
    """Small aggregate counts for the Method and data quality page (T21),
    located by a Metric cell mentioning Gender, not by filename."""
    return _find_table_by_metric_contains("Gender = X")


def find_context_by_year() -> pd.DataFrame:
    """Units, funded AHC and valid-start-date counts by Delivery_Year and
    Funding_Source (T11), located by its Note column, not by filename."""
    return _find_table_by_columns(frozenset({"Delivery_Year", "Funding_Source", "AHC", "Note"}))


def find_industry_atsi_share() -> pd.DataFrame:
    """Completion rate and ATSI share of units by Industry (T12a),
    located by its ATSI_Share_of_Units_% column, not by filename."""
    return _find_table_by_columns(frozenset({"Industry", "AHC_Funded", "ATSI_Share_of_Units_%"}))


def find_by_qualification_level() -> pd.DataFrame:
    """Funded AHC and completion rate by Qualification_Level (T13),
    located by its own column, not by filename."""
    return _find_table_by_columns(frozenset({"Qualification_Level", "AHC_Funded", "Share_of_Total_%"}))


def find_by_town() -> pd.DataFrame:
    """Funded AHC, units and distinct providers by town (T14), located by
    its Distinct_Providers column, not by filename."""
    return _find_table_by_columns(frozenset({"Location", "Remoteness", "AHC_Funded", "Distinct_Providers"}))


def load_recovered_funding_source() -> pd.DataFrame:
    return _load_csv("recovered_funding_source.csv")

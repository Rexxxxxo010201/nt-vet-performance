"""
Data-integrity tests for round 4 of the tone rewrite: the Method and
data quality page. Every generated sentence is checked against the
tables with the numfmt helpers. No rendering, no pixels.
"""

import pytest

from lib.numfmt import round_dp, round_whole
from lib.titles import TitleAssumptionError
from lib.data_access import (
    find_coverage_grid,
    find_pathway_check,
    load_analysis_methods_text,
    load_cleaning_log,
    load_data_quality_summary_text,
    load_recovered_funding_source,
)
from lib import method_page as mp

BANNED_SUBSTRINGS = [".csv", ".md", "seed 42", "seeded with 42", "Per the brief", "the brief says", "scripts/"]
RULE_IDS = [
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9",
    "B1", "B2", "B3", "B4", "B5", "B6", "C1", "Validation",
]


@pytest.fixture(scope="module")
def tables():
    return mp.gather_tables()


def _all_page_text(tables):
    text = []
    text.extend(mp.key_points(tables))
    text.extend(mp.owners_list(tables))
    text.append(mp.pathway_note(tables))
    text.append(mp.stream_label_note(tables))
    text.append(mp.town_note(tables))
    text.extend(mp.other_checks(tables))
    methods = mp.split_markdown_sections(load_analysis_methods_text())
    text.extend(methods.values())
    cleaning = mp.parse_cleaning_sections(load_data_quality_summary_text())
    text.extend(cleaning.values())
    return text


def test_key_points_match_the_tables(tables):
    points = mp.key_points(tables)
    assert len(points) == 4
    assert points[0] == "The raw workbook was never edited."
    log = tables["cleaning_log"]
    a1 = log.loc[log["rule_id"] == "A1"].iloc[0]
    assert points[1] == (
        f"The cleaned tables hold {int(a1['rows_after']):,} enrolment rows after removing "
        f"{int(a1['rows_changed'])} exact duplicates."
    )
    assert points[1] == "The cleaned tables hold 5,500 enrolment rows after removing 5 exact duplicates."
    kpi = tables["kpi"]
    total = int(kpi.loc[kpi["Metric"] == "Total funded AHC", "Value"].iloc[0])
    assert points[2] == f"All {total:,} funded hours come from AHC_Funded."
    assert points[3] == "The workbook holds hours, not payments."


def test_owners_list_has_eight_items_matching_the_tables(tables):
    items = mp.owners_list(tables)
    assert len(items) == 8
    t21 = tables["t21"]

    def v(name):
        return int(t21.loc[t21["Metric"] == name, "Value"].iloc[0])

    assert str(v("Rows with Funded_Flag = 85%_only and outcome 51, 52 or 70")) in items[0]
    assert "233 suspect rows" in items[1]
    assert "1,070 of 1,161" in items[1]
    assert f"{v('Gender = X students')} of {v('Student table rows'):,}" in items[2]
    assert f"{v('P008 Fee-Free TAFE enrolment rows'):,}" in items[3]
    assert "771 students have no enrolment record" in items[4]
    assert "2 providers and delivery without one for 5" in items[5]
    assert "Urban and Remote labels" in items[6]
    assert "how Town is recorded" in items[7]


def test_owners_list_raises_if_p008_no_longer_has_three_undelivered_contracts(tables):
    altered = dict(tables)
    grid = tables["grid"].copy()
    grid.loc[(grid["Provider_ID"] == "P008") & (grid["Status"] == "Contract without delivery"), "Status"] = "Matched"
    altered["grid"] = grid
    with pytest.raises(TitleAssumptionError):
        mp.owners_list(altered)


def test_pathway_note_matches_t20_and_says_below(tables):
    t20 = find_pathway_check()

    def v(name):
        return int(t20.loc[t20["Metric"] == name, "Value"].iloc[0])

    both = v("Students in both FSK10213 and a higher program")
    first = v("Started FSK10213 first")
    lo = v("Chance range low (95%)")
    hi = v("Chance range high (95%)")
    assert first < lo  # confirms "below" is the correct word for the current data
    note = mp.pathway_note(tables)
    assert note == (
        f"We tested whether students typically start with the foundation skills unit FSK10213 before a "
        f"Certificate II or III. Of {both} students in both, {first} started with it, which is below the "
        f"{lo} to {hi} expected by chance, so the data shows no such pathway and we did not chart it."
    )
    assert note == (
        "We tested whether students typically start with the foundation skills unit FSK10213 before a "
        "Certificate II or III. Of 102 students in both, 39 started with it, which is below the 41 to 61 "
        "expected by chance, so the data shows no such pathway and we did not chart it."
    )


def test_stream_label_note_reports_both_streams_in_all_three_regions(tables):
    note = mp.stream_label_note(tables)
    assert "11N VET in Schools (Urban)" in note
    assert "11V VET in Schools (Remote)" in note
    assert "44% Remote" in note and "29% Urban" in note and "27% Regional" in note
    assert "55% Remote" in note and "23% Urban" in note and "21% Regional" in note


def test_stream_label_note_raises_if_a_stream_stops_covering_all_regions(tables):
    altered = dict(tables)
    t21 = tables["t21"].copy()
    t21.loc[t21["Metric"] == "11N share of rows in Urban (%)", "Value"] = 0.0
    altered["t21"] = t21
    with pytest.raises(TitleAssumptionError):
        mp.stream_label_note(altered)


def test_town_note_matches_the_town_table(tables):
    by_town = tables["by_town"]
    n_providers = int(by_town["Distinct_Providers"].iloc[0])
    n_towns = len(by_town)
    lo = round_whole(float(by_town["Share_of_Total_%"].min()))
    hi = round_whole(float(by_town["Share_of_Total_%"].max()))
    assert mp.town_note(tables) == (
        f"All {n_providers} providers deliver in all {n_towns} towns, and each town holds {lo}% to {hi}% "
        f"of hours. We did not chart towns. This is very even, so confirm how Town is recorded."
    )
    assert (n_providers, n_towns, lo, hi) == (8, 8, 11, 14)


def test_other_checks_four_lines_match_the_tables(tables):
    lines = mp.other_checks(tables)
    assert len(lines) == 4
    assert "36,839 (2023), 82,309 (2024), 53,646 (2025)" in lines[0]
    assert "(T11, T07)" in lines[0]
    assert "Primary Industry at 56%" in lines[1] and "(T07, T07_omnibus)" in lines[1]
    assert "Certificate III holds 57% of hours. (T13)" == lines[2]
    assert "Industry ATSI share of units ranges 30% to 42%. (T12a)" == lines[3]


def test_sensitivity_table_has_four_rows_matching_t10(tables):
    headers, rows = mp.sensitivity_table_rows(tables)
    assert headers == ["Definition", "Rate (%)"]
    assert len(rows) == 4
    rates = {label: rate for label, rate in rows}
    assert rates["Standard definition"] == "60"
    assert rates["Outcome 20 only"] == "53"
    assert rates["Continuing counted as not completed"] == "53"
    assert rates["Strict student-program version"] == "31"


def test_recovered_rows_table_has_names_and_stream_labels(tables):
    html = mp.recovered_rows_table_html(tables)
    recovered = load_recovered_funding_source()
    assert html.count("<tr") == 1 + len(recovered)
    assert "11K User Choice" in html
    assert "P005 Top End Workforce Solutions" in html


def test_cleaning_log_table_has_every_rule_and_wraps_not_scrolls(tables):
    html = mp.cleaning_log_table_html(tables)
    log = load_cleaning_log()
    assert html.count("<tr") == 1 + len(log)
    assert "white-space:normal" in html
    assert "overflow" not in html  # no scroll container
    # B6 has no logged row change (it is a documentation-only rule, not a
    # data transformation), so it is not in cleaning_log.csv itself.
    for rule_id in log["rule_id"]:
        assert f">{rule_id}<" in html


def test_every_cleaning_rule_appears_exactly_once_across_the_three_groups():
    grouped = [r for _, ids in mp.CLEANING_STEP_GROUPS for r in ids]
    assert sorted(grouped) == sorted(RULE_IDS)
    assert len(grouped) == len(set(grouped)) == 17

    sections = mp.parse_cleaning_sections(load_data_quality_summary_text())
    assert sorted(sections.keys()) == sorted(RULE_IDS)


def test_b2_section_drops_its_embedded_recovered_rows_markdown_tables():
    sections = mp.parse_cleaning_sections(load_data_quality_summary_text())
    assert "Recovered rows by Funding_Source" not in sections["B2"]
    assert "Recovered rows by Provider_ID" not in sections["B2"]


def test_t09b_wording_no_longer_says_nine_subgroup_comparisons():
    with open("outputs/analysis_summary.md") as f:
        text = f.read()
    assert "across 9 subgroup comparisons" not in text
    assert "is the headline comparison" in text


def test_no_file_names_or_seed_42_or_per_the_brief_in_any_visible_page_text(tables):
    for text in _all_page_text(tables):
        for banned in BANNED_SUBSTRINGS:
            assert banned not in text, (banned, text[:200])


def test_no_em_dash_in_any_visible_page_text(tables):
    for text in _all_page_text(tables):
        assert "—" not in text
        assert "—" not in text


def test_t20_and_t21_pass_privacy_and_are_aggregate_only():
    from lib.privacy import find_forbidden_columns

    t20 = find_pathway_check()
    t21 = mp.gather_tables()["t21"]
    assert not find_forbidden_columns(t20.columns)
    assert not find_forbidden_columns(t21.columns)
    # Aggregate counts only: every Value is a plain number, no row is student-level.
    assert len(t20) < 20 and len(t21) < 20

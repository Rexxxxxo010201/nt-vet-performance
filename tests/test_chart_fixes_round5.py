"""
Data-integrity tests for the round-5 wave of small chart fixes (Coverage
leader line already covered in test_table_labels_and_shading.py; this
file covers Delivered vs target, Geography, Programs, Funding vs
outcome, Completion, Equity, Reach and So What). No rendering, no
pixels; every figure is checked against the tables.
"""

import pytest

from lib.numfmt import round_dp, round_whole
from lib.titles import TitleAssumptionError
from lib.data_access import (
    find_coverage_grid,
    find_matched_pairs,
    find_rollups,
    load_t01_kpis,
)
import lib.chart_coverage as cov
import lib.chart_delivered_vs_target as dvt

BANNED_PHRASES = ["partial extract", "workbook may not", "analysed as supplied"]


@pytest.fixture(scope="module")
def dvt_tables():
    return {
        "pairs": find_matched_pairs(),
        "rollups": find_rollups(),
        "grid": find_coverage_grid(),
        "kpi": load_t01_kpis(),
    }


def test_dvt_shading_threshold_is_10_percent_with_six_rows(dvt_tables):
    pairs = dvt_tables["pairs"]
    df = pairs.copy()
    df["pct_exact"] = 100 * df["Delivered_AHC"] / df["Target_AHC_Total"]
    below = df.loc[df["pct_exact"] < 10]
    assert len(below) == 6
    assert 0 < len(below) <= len(df) / 2
    assert dvt.SHADING_THRESHOLD_PCT == 10


def test_dvt_pairs_table_shades_exactly_the_six_rows_below_10_percent(dvt_tables):
    from lib.theme import OCHRE_LIGHT_TINT

    html = dvt.build_pairs_table_html(dvt_tables["pairs"])
    assert html.count(OCHRE_LIGHT_TINT) == 6


def test_dvt_takeaway_states_lowest_and_highest_across_all_19(dvt_tables):
    takeaway = dvt.build_table_takeaway(dvt_tables["pairs"])
    assert takeaway == (
        "6 of 19 contracts have delivered less than a tenth of their target (shaded). "
        "The lowest is P004 11V at 5%; the highest is P002 11J at 51%."
    )


def test_dvt_takeaway_raises_if_threshold_shades_none_or_over_half(dvt_tables, monkeypatch):
    pairs = dvt_tables["pairs"]
    with pytest.raises(TitleAssumptionError):
        dvt.build_table_takeaway(pairs, threshold_pct=0)
    with pytest.raises(TitleAssumptionError):
        dvt.build_table_takeaway(pairs, threshold_pct=100)


def test_dvt_target_coverage_note_matches_a_b_x(dvt_tables):
    grid = dvt_tables["grid"]
    kpi = dvt_tables["kpi"]
    a = float(kpi.loc[kpi["Metric"] == "Total funded AHC", "Value"].iloc[0])
    b = float(grid["Target_AHC"].dropna().sum())
    x = round_whole(100 * a / b)
    note = dvt.build_target_coverage_note(grid, kpi)
    assert note == (
        f"Even if every delivered hour in the workbook belonged to a contract, delivery would be {x}% of "
        f"all contract target hours ({a:,.0f} of {b:,.0f}). The gap to target is not explained by hours "
        f"recorded outside contracts."
    )
    assert (round(a), round(b), x) == (172794, 680790, 25)
    for banned in BANNED_PHRASES:
        assert banned not in note.lower()


def test_dvt_funding_stream_takeaway_matches_t03b(dvt_tables):
    takeaway = dvt.build_funding_stream_takeaway(dvt_tables["rollups"])
    assert takeaway == (
        "The two VET in Schools streams are lowest (9% and 8%); Fee-Free TAFE has the largest target "
        "(39% of all target hours) and has delivered 11% of it."
    )


def test_dvt_caption_says_well_below_target_with_delivery(dvt_tables):
    caption = dvt.build_caption(dvt_tables["pairs"], dvt_tables["rollups"], dvt_tables["grid"])
    assert "Every provider with delivery is well below target" in caption
    assert "Every provider is well below target," not in caption


def test_dvt_caption_precision_sentence_matches_exact_and_whole(dvt_tables):
    rollups = dvt_tables["rollups"]
    overall = rollups.loc[rollups["Level"] == "Overall"].iloc[0]
    exact = 100 * float(overall["Delivered_AHC"]) / float(overall["Target_AHC_Total"])
    d = round_dp(exact, 1)
    x = round_whole(exact)
    caption = dvt.build_caption(dvt_tables["pairs"], dvt_tables["rollups"], dvt_tables["grid"])
    assert d != x  # confirms the sentence should be present for the current data
    assert (
        f"The chart shows one decimal ({d:.1f}%) so providers can be compared; the title rounds it "
        f"to {x}%."
    ) in caption


def test_dvt_hover_matches_table_values(dvt_tables):
    fig = dvt.build_figure(dvt_tables["pairs"], dvt_tables["rollups"])
    rollups = dvt_tables["rollups"]
    overall = rollups.loc[rollups["Level"] == "Overall"].iloc[0]
    for trace in fig.data:
        assert trace.customdata[0][0] == "All providers"
        assert trace.customdata[0][1] == float(overall["Delivered_AHC"])
        assert trace.customdata[0][2] == float(overall["Target_AHC_Total"])
        assert "P002 TAFE NT" in [row[0] for row in trace.customdata]
        assert trace.hoverinfo != "skip"
        assert "<extra></extra>" in trace.hovertemplate


def test_dvt_no_em_dash(dvt_tables):
    texts = [
        dvt.build_table_takeaway(dvt_tables["pairs"]),
        dvt.build_target_coverage_note(dvt_tables["grid"], dvt_tables["kpi"]),
        dvt.build_funding_stream_takeaway(dvt_tables["rollups"]),
        dvt.build_caption(dvt_tables["pairs"], dvt_tables["rollups"], dvt_tables["grid"]),
    ]
    for t in texts:
        assert "—" not in t and "—" not in t


# ----------------------------------------------------------------------
# Geography
# ----------------------------------------------------------------------

import lib.chart_geography as geo
from lib.data_access import find_aggregate_geography, find_coverage_summary, find_pairs_geography

GEO_BANNED = ["partial extract", "as recorded in the workbook", "analysed as supplied"]


def test_geo_caption_drops_the_partial_extract_sentence():
    caption, _ = geo.build_caption(find_pairs_geography(), find_aggregate_geography(), find_coverage_summary(), load_t01_kpis())
    for banned in GEO_BANNED:
        assert banned not in caption.lower()
    assert "Contracts planned for" in caption  # every other sentence is still there


def test_geo_expander_title_count_equals_table_rows():
    pairs = find_pairs_geography()
    n = pairs[["Provider_ID", "Funding_Source"]].drop_duplicates().shape[0]
    assert n == 19


def test_geo_hover_matches_t05b_values():
    agg = find_aggregate_geography()
    rows = geo._rows(agg)
    fig = geo.build_figure(agg)
    for trace in fig.data:
        if trace.mode != "markers":
            continue
        for (region, target_exact, delivered_exact, gap_exact), row in zip(trace.customdata, rows):
            assert region == row["remoteness"]
            assert abs(target_exact - row["target_exact"]) < 1e-9
            assert abs(delivered_exact - row["delivered_exact"]) < 1e-9
            assert abs(gap_exact - row["gap_exact"]) < 1e-9


def test_geo_circle_has_white_outline_and_diamond_drawn_first():
    fig = geo.build_figure(find_aggregate_geography())
    markers = [tr for tr in fig.data if tr.mode == "markers"]
    assert markers[0].marker.symbol == "diamond"
    assert markers[1].marker.symbol == "circle"
    assert markers[1].marker.line.color == "#FFFFFF"


def test_geo_no_em_dash():
    caption, _ = geo.build_caption(find_pairs_geography(), find_aggregate_geography(), find_coverage_summary(), load_t01_kpis())
    assert "—" not in caption and "—" not in caption


# ----------------------------------------------------------------------
# What is being delivered (Programs)
# ----------------------------------------------------------------------

import lib.chart_programs as pr
from lib.data_access import find_program_intensity, find_program_labels, find_student_count_chance_check


@pytest.fixture(scope="module")
def programs_tables():
    return {
        "t15": find_program_intensity(),
        "labels": find_program_labels(),
        "t16": find_student_count_chance_check(),
    }


def test_programs_caption_merges_sentences_and_uses_exact_values(programs_tables):
    t15, t16 = programs_tables["t15"], programs_tables["t16"]
    cs, other = pr._summary_rows(t15)
    a = round_dp(float(cs["AHC_Funded"]) / float(cs["Units"]), 1)
    b = round_dp(float(other["AHC_Funded"]) / float(other["Units"]), 1)
    c = round_whole(float(cs["Mean_Nominal_Hours_per_Unit_exact"]))
    d = round_whole(float(other["Mean_Nominal_Hours_per_Unit_exact"]))
    caption, stats = pr.build_caption(t15, t16)
    assert stats["explain_included"] is True
    expected_p2 = (
        f"Community Services units carry about twice the funded hours of other units ({a:.1f} against "
        f"{b:.1f} funded hours per unit), because they are longer: about {c} nominal hours against {d} "
        f"for other industries. This describes the hours and does not say why units differ. The extra "
        f"hours come from longer units, not from more students."
    )
    assert caption.split("\n\n")[1] == expected_p2
    assert (a, b, c, d) == (46.1, 24.5, 50, 28)
    assert "So funded hours follow the length" not in caption


def test_programs_unit_length_note_matches_distinct_units(programs_tables):
    t15 = programs_tables["t15"]
    programs = pr._program_rows(t15)
    n = round_whole(float(programs["Distinct_Unit_IDs"].mean()))
    note = pr.build_unit_length_note(t15)
    assert note == (
        f"Unit lengths are averaged over the units delivered in the data (about {n} distinct units per "
        f"program), so they are not full qualification lengths."
    )
    assert n == 3


def test_programs_table_takeaway_matches_ahc_per_unit_ranges(programs_tables):
    t15 = programs_tables["t15"]
    programs = pr._program_rows(t15)
    cs_rows = programs.loc[programs["Industry"] == "Community Services"]
    other_rows = programs.loc[programs["Industry"] != "Community Services"]
    takeaway = pr.build_table_takeaway(t15)
    assert takeaway == (
        f"Shaded: the three Community Services programs, with {cs_rows['AHC_per_Unit'].min():.1f} to "
        f"{cs_rows['AHC_per_Unit'].max():.1f} funded hours per unit; all other programs have "
        f"{other_rows['AHC_per_Unit'].min():.1f} to {other_rows['AHC_per_Unit'].max():.1f}. Whole-number "
        f"figures in the chart are rounded from unrounded values, so they can differ slightly from the "
        f"one-decimal figures here."
    )


def test_programs_bar_cell_separates_bar_and_number(programs_tables):
    html = pr.build_table_html(programs_tables["t15"], programs_tables["labels"])
    assert "display:flex" in html
    assert html.count(f"width:{pr.BAR_CELL_BAR_WIDTH_PCT}%") == 10
    # The number sits in its own span, not layered on top of the bar via z-index.
    assert "z-index" not in html


def test_programs_hover_matches_table_for_all_ten(programs_tables):
    t15, labels = programs_tables["t15"], programs_tables["labels"]
    rows = pr._rows(t15, labels)
    fig = pr.build_figure(t15, labels)
    assert len(rows) == 10
    for trace in fig.data:
        assert len(trace.customdata) == 10
        for (full_label, industry, students, units, ahc, share), row in zip(trace.customdata, rows):
            assert full_label == row["full_label"]
            assert industry == row["industry"]
            assert students == row["students"]
            assert units == row["units"]
            assert ahc == row["ahc_funded"]
            assert share == round_whole(row["share_exact"])
        assert "<extra></extra>" in trace.hovertemplate


def test_programs_no_em_dash(programs_tables):
    t15, t16 = programs_tables["t15"], programs_tables["t16"]
    caption, _ = pr.build_caption(t15, t16)
    texts = [caption, pr.build_table_takeaway(t15), pr.build_unit_length_note(t15)]
    for t in texts:
        assert "—" not in t and "—" not in t


# ----------------------------------------------------------------------
# Funding vs outcome
# ----------------------------------------------------------------------

import lib.chart_funding_outcome as fo
from lib.data_access import find_industry_outcome, find_stream_outcome, find_withdrawn_notachieved_by_funded_flag


@pytest.fixture(scope="module")
def fo_tables():
    return {
        "t06a": find_stream_outcome(),
        "t06c": find_withdrawn_notachieved_by_funded_flag(),
        "t17a": find_industry_outcome(),
    }


def test_fo_stream_key_line_removed_everywhere_it_is_fully_labelled():
    """Only one place in the app ever referenced the bare stream key line;
    it is gone now that the Funding vs outcome Sankey and table both show
    full stream names (chart node labels via _stream_node_label, table
    cells via stream_label)."""
    with open("app/Home.py") as f:
        home_text = f.read()
    assert "STREAM_KEY_CAPTION" not in home_text
    assert "Funding streams: 11J" not in home_text


def test_fo_new_column_matches_not_achieved_plus_withdrawn_over_stream_total(fo_tables):
    t06a = fo_tables["t06a"]
    stream_totals = fo._ordered_totals(t06a, "Funding_Source")
    rows = fo._outcome_wide_rows(t06a, "Funding_Source", stream_totals.index.tolist(), float(stream_totals.sum()))
    for row in rows:
        expected = round_dp(100 * row["Not completed"] / (row["Achieved"] + row["Not completed"] + row["Continuing"] + row["Learner support"]), 4)
        assert abs(row["Not_Completed_Share_exact"] - expected) < 1e-6
    html = fo.build_table_html(t06a)
    assert "Share not completed (%)" in html


def test_fo_table_takeaway_range_matches_caption_range(fo_tables):
    caption, _ = fo.build_caption(fo_tables["t06a"], fo_tables["t06c"], fo_tables["t17a"])
    takeaway = fo.build_table_takeaway(fo_tables["t06a"])
    assert "33% to 38%" in caption
    assert "33% to 38%" in takeaway  # the new column's range matches the caption's quoted range exactly
    assert "highest in 11N General Recurrent" not in takeaway  # sanity: not a mismatched stream name
    assert "11N VET in Schools (Urban)" in takeaway
    assert "11V VET in Schools (Remote)" in takeaway


def test_fo_continuing_share_note_replaces_caveat(fo_tables):
    note = fo.build_continuing_share_note(fo_tables["t06a"])
    assert note == (
        "12% of hours are in units still continuing or in learner support, so the final share not "
        "completed could still change. Industry is taken from each unit's program."
    )
    assert "data dictionary" not in note
    assert "as recorded in the workbook" not in note


def test_fo_caption_has_no_banned_phrases(fo_tables):
    caption, _ = fo.build_caption(fo_tables["t06a"], fo_tables["t06c"], fo_tables["t17a"])
    assert "data dictionary" not in caption
    assert "as recorded in the workbook" not in caption


def test_fo_sankey_hover_matches_table_values(fo_tables):
    t06a = fo_tables["t06a"]
    fig = fo.build_figure(t06a)
    sankey = fig.data[0]
    stream_totals = fo._ordered_totals(t06a, "Funding_Source")
    overall_total = float(stream_totals.sum())
    node_customdata = list(sankey.node.customdata)
    for stream in stream_totals.index:
        match = [row for row in node_customdata if row[1] == float(stream_totals[stream])]
        assert match, stream
    assert "<extra></extra>" in sankey.node.hovertemplate
    assert "<extra></extra>" in sankey.link.hovertemplate
    assert "Outcome_Group" not in sankey.link.hovertemplate
    assert "Source" not in sankey.link.hovertemplate


def test_fo_no_em_dash(fo_tables):
    caption, _ = fo.build_caption(fo_tables["t06a"], fo_tables["t06c"], fo_tables["t17a"])
    texts = [caption, fo.build_table_takeaway(fo_tables["t06a"]), fo.build_continuing_share_note(fo_tables["t06a"])]
    for t in texts:
        assert "—" not in t and "—" not in t


import lib.chart_completion as comp
from lib.data_access import find_completion_by_group, find_completion_omnibus_tests, find_sensitivity
from lib.labels import provider_label


@pytest.fixture(scope="module")
def completion_tables():
    return {
        "t07": find_completion_by_group(),
        "t07_omnibus": find_completion_omnibus_tests(),
        "t06a": find_stream_outcome(),
        "t10": find_sensitivity(),
    }


def test_completion_caption_no_longer_has_53_percent_sentence(completion_tables):
    caption, stats = comp.build_caption(completion_tables["t07"], completion_tables["t07_omnibus"], completion_tables["t10"])
    assert "Counting units still continuing" not in caption
    continuing_rows = completion_tables["t10"].loc[
        completion_tables["t10"]["Definition"].str.startswith("(c) Continuing")
        & (completion_tables["t10"]["Scope"] == "Overall")
    ]
    z_exact = float(continuing_rows["Rate_exact"].iloc[0])
    assert stats["continuing_as_not_completed"] == round_whole(z_exact)


def test_completion_remote_sentence_reworded(completion_tables):
    caption, stats = comp.build_caption(completion_tables["t07"], completion_tables["t07_omnibus"], completion_tables["t10"])
    if stats["remote_sentence_included"]:
        assert "Remote areas are not behind:" in caption
        assert "Completion is also no lower in Remote areas" not in caption


def test_completion_table_lead_line_matches_industry_p_value(completion_tables):
    line = comp.build_table_lead_line(completion_tables["t07_omnibus"])
    row = completion_tables["t07_omnibus"].loc[completion_tables["t07_omnibus"]["Dimension"] == "Industry"]
    p = float(row["Omnibus_GEE_p_value"].iloc[0])
    assert f"p = {p:.2f}" in line
    assert "No industry stands out either" in line


def test_completion_hover_uses_provider_label_and_t07_values(completion_tables):
    t07, t06a = completion_tables["t07"], completion_tables["t06a"]
    fig = comp.build_figure(t07, t06a)
    dots = [tr for tr in fig.data if tr.mode == "markers"][0]
    rows, _, _, _ = comp._rows(t07, t06a)
    for row, cd in zip(rows, dots.customdata):
        if row["dimension"] == "Provider_ID":
            assert cd[0] == provider_label(row["group"])
        else:
            assert cd[0] == row["label"]
        assert cd[1] == row["rate"]
        assert cd[2] == row["low"]
        assert cd[3] == row["high"]
        assert cd[4] == row["units"]
        assert cd[5] == row["students"]
    assert "<extra></extra>" in dots.hovertemplate


def test_completion_no_em_dash(completion_tables):
    caption, stats = comp.build_caption(completion_tables["t07"], completion_tables["t07_omnibus"], completion_tables["t10"])
    texts = [caption, stats["stats_line"], comp.build_table_lead_line(completion_tables["t07_omnibus"]), comp.READING_AID]
    for t in texts:
        assert "—" not in t


import lib.chart_equity as eq
from lib.data_access import find_atsi_adjusted_model, find_atsi_completion, find_atsi_gap


@pytest.fixture(scope="module")
def equity_tables():
    return {
        "t09a": find_atsi_completion(),
        "t09b": find_atsi_gap(),
        "t09c": find_atsi_adjusted_model(),
    }


def test_equity_caption_matches_t09b_and_t09c_gap_figures(equity_tables):
    caption, stats = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    y1, n1, gap1 = eq._overall_unadjusted(equity_tables["t09a"], equity_tables["t09b"])
    y2, n2, gap2 = eq._adjusted(equity_tables["t09c"])
    g = round_dp(abs(gap2["gap"]), 1)
    assert f"allowed for ({g} points)" in caption
    rows = [r for r in eq._subgroup_rows(equity_tables["t09a"], equity_tables["t09b"]) if r["dimension"] != "Overall"]
    for r in rows:
        if r["excludes_zero"]:
            assert f"({round_dp(abs(r['gap']), 1)} points)" in caption
    assert "The gap is widest in Remote areas (4.4 points) and Fee-Free TAFE (5.6 points)." in caption
    assert stats["threshold_cleared"] is True


def test_equity_caption_banned_phrases_removed(equity_tables):
    caption, stats = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    for banned in ["one in three", "not headline findings", "holds when other factors"]:
        assert banned not in caption
        assert banned not in stats["stats_line"]


def test_equity_stats_line_has_merged_sentence_and_n_is_8(equity_tables):
    _, stats = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    assert "2 of 8 regional and funding stream gaps exclude zero" in stats["stats_line"]
    assert "Intervals allow for the same student appearing in several units." in stats["stats_line"]


def test_equity_row_labels_renamed():
    assert eq.ROW1_LABEL == "Unadjusted<br>(as recorded)"
    assert eq.ROW2_LABEL == "Adjusted for provider,<br>funding stream, region,<br>industry and year"


def test_equity_summary_table_not_tested_and_interval_note(equity_tables):
    html, note, interval_note = eq.build_summary_table_html(
        equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"]
    )
    assert ">not tested<" in html
    assert "interval only" not in html
    assert interval_note == "The unadjusted gap is shown with its interval only."
    assert "Unadjusted (as recorded)" in html
    assert "Adjusted for provider, funding stream, region, industry and year" in html


def test_equity_subgroup_lead_line_n_and_e(equity_tables):
    line = eq.build_subgroup_lead_line(equity_tables["t09a"], equity_tables["t09b"])
    assert "With 8 comparisons" in line
    assert "about 0.40" in line
    assert "Interval excludes zero" in line
    assert "Shaded rows are the ones that exclude zero" in line


def test_equity_hover_unit_counts_match_table(equity_tables):
    t09a, t09b, t09c = equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"]
    fig = eq.build_figure(t09a, t09b, t09c)
    markers = [tr for tr in fig.data if tr.mode == "markers"]
    atsi, other = markers[0], markers[1]
    assert "1,729 units" in atsi.hovertemplate or "1,729 units" in str(atsi.customdata[0])
    assert str(atsi.customdata[0][2]) == "<br>1,729 units"
    assert str(other.customdata[0][2]) == "<br>3,005 units"
    assert atsi.customdata[1][2] == ""  # adjusted dot has no unit count
    assert other.customdata[1][2] == ""


def test_equity_definition_line_present():
    assert eq.DEFINITION_LINE == "Rates are for units counted in the completion rate (achieved, not achieved or withdrawn)."


def test_equity_no_em_dash(equity_tables):
    caption, stats = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    texts = [
        caption,
        stats["stats_line"],
        eq.DEFINITION_LINE,
        eq.build_subgroup_lead_line(equity_tables["t09a"], equity_tables["t09b"]),
    ]
    for t in texts:
        assert "—" not in t


import lib.so_what as sw
from lib.so_what import gather_tables


def test_excludes_zero_explanation_present_in_equity_expander_and_so_what_card4(equity_tables):
    # So What Card 4's statistics were later shrunk to a one-line pointer to the Equity
    # section (density round), so the "includes zero" bracket now lives only in Equity
    # itself; confirm it is still there.
    _, stats = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    assert "(the range crosses zero, so that gap alone could be chance)" in stats["stats_line"]

    line = eq.build_subgroup_lead_line(equity_tables["t09a"], equity_tables["t09b"])
    assert "Interval excludes zero" in line
    assert "the whole range sits below zero" in line


def test_excludes_zero_k_and_n_match_tables(equity_tables):
    _, stats = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    assert "2 of 8 regional and funding stream gaps exclude zero" in stats["stats_line"]
    assert "about 0.40 would be expected by chance" in stats["stats_line"]


def test_method_page_has_the_new_confidence_interval_sentence():
    from pathlib import Path

    text = Path("app/data/analysis_methods.md").read_text()
    assert (
        "A range (confidence interval) is the set of values the true figure could plausibly take. "
        "If a gap's range includes zero, the data cannot rule out no gap at all; if it excludes "
        "zero, the gap is unlikely to be chance."
    ) in text
    outputs_text = Path("outputs/analysis_methods.md").read_text()
    assert text == outputs_text


def test_excludes_zero_not_added_in_completion_or_reach():
    comp_src = open("app/lib/chart_completion.py").read()
    reach_src = open("app/lib/chart_reach.py").read()
    assert "excludes zero" not in comp_src and "includes zero" not in comp_src
    assert "excludes zero" not in reach_src and "includes zero" not in reach_src


def test_no_em_dash_in_new_excludes_zero_text(equity_tables):
    tables = gather_tables()
    card = sw.action_cards(tables)[3]
    _, stats = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    line = eq.build_subgroup_lead_line(equity_tables["t09a"], equity_tables["t09b"])
    from pathlib import Path

    method_text = Path("app/data/analysis_methods.md").read_text()
    for t in [card["stats_line"], stats["stats_line"], line, method_text]:
        assert "—" not in t


import lib.chart_reach as rc
from lib.data_access import find_atsi_enrolled_share, find_atsi_omnibus


@pytest.fixture(scope="module")
def reach_tables():
    return {
        "t18": find_atsi_enrolled_share(),
        "t18b": find_atsi_omnibus(),
        "t06a": find_stream_outcome(),
    }


def test_reach_caption_consistency_sentence_removed(reach_tables):
    # Density round: this sentence only repeated the title and the caption's own first
    # sentence, so it was cut; the "no detectable difference" claim stays in the title
    # and the "none stands out" claim stays in the reading aid.
    caption, stats = rc.build_caption(reach_tables["t18"], reach_tables["t18b"])
    assert "wherever we look" not in caption
    assert "spread evenly" not in caption
    assert caption.count(f"{stats['share_whole']}%") == 1  # the share is now stated only once


def test_reach_statistics_line_uses_n_equals_p_times_100(reach_tables):
    _, stats = rc.build_caption(reach_tables["t18"], reach_tables["t18b"])
    p_values = stats["p_values"]
    for key, n_phrase in [
        ("Funding_Source", f"about {round_whole(p_values['Funding_Source'] * 100)}"),
        ("Provider_ID", f"{round_whole(p_values['Provider_ID'] * 100)}"),
        ("Remoteness", f"{round_whole(p_values['Remoteness'] * 100)} times in 100"),
    ]:
        assert n_phrase in stats["stats_line"]


def test_reach_duplicate_note_removed_from_home():
    from pathlib import Path

    home_text = Path("app/Home.py").read_text()
    reach_section = home_text.split('st.markdown("## Reach")')[1].split('st.markdown("## So what")')[0]
    assert "caveat=REACH_CAVEAT" not in reach_section
    assert "REACH_CAVEAT" not in home_text  # import removed entirely


def test_reach_table_header_wraps_over_two_lines(reach_tables):
    html = rc.build_table_html(reach_tables["t18"], reach_tables["t18b"], reach_tables["t06a"])
    assert "Aboriginal and Torres<br>Strait Islander students" in html
    assert "95% interval (%)" in html  # unchanged elsewhere


def test_reach_hover_uses_provider_label_and_t18_values(reach_tables):
    t18, t06a = reach_tables["t18"], reach_tables["t06a"]
    fig = rc.build_figure(t18, t06a)
    dots = [tr for tr in fig.data if tr.mode == "markers"][0]
    rows, _ = rc._rows(t18, t06a)
    for row, cd in zip(rows, dots.customdata):
        if row["dimension"] == "Provider_ID":
            assert cd[0] == provider_label(row["group"])
        else:
            assert cd[0] == row["label"]
        assert cd[1] == row["share"]
        assert cd[2] == row["low"]
        assert cd[3] == row["high"]
        assert cd[4] == row["atsi_students"]
        assert cd[5] == row["students"]
    assert "<extra></extra>" in dots.hovertemplate


def test_reach_no_em_dash(reach_tables):
    caption, stats = rc.build_caption(reach_tables["t18"], reach_tables["t18b"])
    texts = [caption, stats["stats_line"], rc.READING_AID]
    for t in texts:
        assert "—" not in t


from lib.so_what import action_cards, gather_tables


def test_so_what_card4_no_tnumber_or_n_equals_p_phrase():
    tables = gather_tables()
    card = action_cards(tables)[3]
    assert "T09c" not in card["found"]
    assert "n = p x 100" not in card["stats_line"]


def test_so_what_card4_rates_match_predicted_values_to_one_decimal():
    tables = gather_tables()
    card = action_cards(tables)[3]
    adjusted = tables["atsi_adjusted"]
    pred_y = float(adjusted.loc[adjusted["Metric"] == "Model-predicted completion rate, ATSI = Y (%)", "Value_exact"].iloc[0])
    pred_n = float(adjusted.loc[adjusted["Metric"] == "Model-predicted completion rate, ATSI = N (%)", "Value_exact"].iloc[0])
    assert f"({round_dp(pred_y, 1):.1f}% against {round_dp(pred_n, 1):.1f}%)" in card["found"]


def test_so_what_card4_stats_line_shrunk_with_no_zero_phrases():
    # Density round: Card 4's statistics line was shrunk to a one-line pointer to the
    # Equity section, so it no longer carries "includes zero"/"exclude zero" text, and
    # so needs no bracket either. A later round put the "times in 100" explanation
    # back in brackets, alongside p, within that same one-line block.
    tables = gather_tables()
    card = action_cards(tables)[3]
    assert card["stats_line"] == (
        "Statistics: p = 0.04 (if there were no real gap, a difference this size would turn up about "
        "4 times in 100); odds ratio 0.88; see the Equity section for the full detail."
    )
    assert "includes zero" not in card["stats_line"]
    assert "exclude zero" not in card["stats_line"]


def test_so_what_no_tnumber_anywhere_in_briefing_text():
    import re

    tables = gather_tables()
    cards = action_cards(tables)
    texts = []
    for c in cards:
        texts.append(c["found"])
        texts.append(c["next_step"])
        if c["likely_explanation"]:
            texts.append(c["likely_explanation"])
        if c["stats_line"]:
            texts.append(c["stats_line"])
        if c["note"]:
            texts.append(c["note"])
    for t in texts:
        assert not re.search(r"\bT0[0-9][a-z]?\b", t)
        assert not re.search(r"\bT1[0-9][a-z]?\b", t)


def test_so_what_card1_likely_explanation_matches_target_text():
    tables = gather_tables()
    card = action_cards(tables)[0]
    assert card["likely_explanation"] == (
        "User Choice delivery may run outside capped contracts. That would not explain P008's "
        "Fee-Free hours."
    )


def test_so_what_card2_next_step_matches_target_text():
    tables = gather_tables()
    card = action_cards(tables)[1]
    assert card["next_step"] == (
        "Compare how remoteness is defined in the contracts and in the delivery records. Once "
        "confirmed, set Urban, Regional and Remote targets from where training is actually delivered."
    )


def test_so_what_card3_title_matches_target_text():
    tables = gather_tables()
    card = action_cards(tables)[2]
    assert card["title"] == "Size the cost of paying for units not completed"


def test_so_what_no_em_dash():
    tables = gather_tables()
    cards = action_cards(tables)
    for c in cards:
        for key in ["title", "found", "next_step", "likely_explanation", "stats_line", "note"]:
            if c[key]:
                assert "—" not in c[key]


def test_equity_t09c_has_no_interval_for_predicted_rates():
    t09c = find_atsi_adjusted_model()
    assert set(t09c.columns) == {"Metric", "Value", "Value_exact"}
    # The odds ratio has its own CI rows, but neither predicted rate does.
    assert any(t09c["Metric"].str.contains("OR 95% CI", case=False))
    predicted_rate_metrics = t09c.loc[t09c["Metric"].str.contains("Model-predicted completion rate")]
    assert len(predicted_rate_metrics) == 2
    assert not any(predicted_rate_metrics["Metric"].str.contains("CI", case=False))


def test_equity_adjusted_row_no_interval_note_appears_once_in_home():
    from pathlib import Path

    home_text = Path("app/Home.py").read_text()
    assert home_text.count("EQUITY_ADJUSTED_ROW_NO_INTERVAL_NOTE") == 2  # import + one use
    assert eq.ADJUSTED_ROW_NO_INTERVAL_NOTE == (
        "Lines show the range we are confident in. The adjusted rates are model estimates, so their "
        "range is shown as the odds ratio on the right instead."
    )
    assert "—" not in eq.ADJUSTED_ROW_NO_INTERVAL_NOTE


# ----------------------------------------------------------------------
# Density round: caption tightening, Card 4 statistics, dot plot takeaways
# ----------------------------------------------------------------------

def test_coverage_caption_bold_first_sentence():
    from lib.data_access import find_coverage_summary, find_delivery_without_contract, find_coverage_grid, find_uncontracted_excluding_11k
    cap = cov.build_caption(find_coverage_summary(), find_delivery_without_contract(), find_coverage_grid(), find_uncontracted_excluding_11k())
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")
    assert "97,550" in first  # adds a number not in the title


def test_dvt_caption_bold_first_sentence(dvt_tables):
    cap = dvt.build_caption(dvt_tables["pairs"], dvt_tables["rollups"], dvt_tables["grid"])
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")
    assert "72,169" in first


def test_geography_caption_bold_first_sentence():
    cap, _ = geo.build_caption(find_pairs_geography(), find_aggregate_geography(), find_coverage_summary(), load_t01_kpis())
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")


def test_programs_caption_sentence_removed_and_first_bold(programs_tables):
    cap, stats = pr.build_caption(programs_tables["t15"], programs_tables["t16"])
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")
    assert f"{stats['pct']}% of funded hours" not in cap  # cut: only repeated the title
    assert "Community Services units carry" in cap  # unique fact kept


def test_fo_caption_first_sentence_does_not_repeat_title_verbatim(fo_tables):
    cap, _ = fo.build_caption(fo_tables["t06a"], fo_tables["t06c"], fo_tables["t17a"])
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")
    title_text = "of funded hours went to units not achieved or withdrawn"
    assert title_text not in first
    assert "99%" in first  # adds the fully-funded number instead


def test_completion_caption_bold_first_sentence_no_cuts(completion_tables):
    cap, _ = comp.build_caption(completion_tables["t07"], completion_tables["t07_omnibus"], completion_tables["t10"])
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")
    assert "Remote areas are not behind" in cap  # unique claim, not cut


def test_equity_caption_redundant_adjusted_rates_sentence_cut(equity_tables):
    cap, _ = eq.build_caption(equity_tables["t09a"], equity_tables["t09b"], equity_tables["t09c"])
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")
    assert "58.4% against 61.5%" not in cap  # already on the chart's row-2 labels
    assert "3.1 points" in cap  # still stated once, in the kept sentence


def test_reach_caption_bold_first_sentence(reach_tables):
    cap, _ = rc.build_caption(reach_tables["t18"], reach_tables["t18b"])
    first = cap.split("\n\n")[0]
    assert first.startswith("**") and first.endswith("**")
    assert cap.count("\n\n") == 1  # paragraph 2 was cut entirely


def test_so_what_card4_found_text_matches_spec():
    tables = gather_tables()
    card = action_cards(tables)[3]
    f = sw._figures(tables)
    g = round_whole(abs(f["pred_gap"]))
    r1 = round_dp(f["pred_y"], 1)
    r2 = round_dp(f["pred_n"], 1)
    z = round_whole(f["completion_exact"])
    assert card["found"] == (
        f"Aboriginal and Torres Strait Islander learners complete about {g} points less often "
        f"({r1:.1f}% against {r2:.1f}%). The gap is similar in size once provider, stream, region, "
        f"industry and year are allowed for. The bigger issue is the {z}% completion for everyone."
    )


def test_completion_takeaway_line_matches_tables(completion_tables):
    line = comp.build_takeaway_line(completion_tables["t07"], completion_tables["t06a"])
    rows, _, _, _ = comp._rows(completion_tables["t07"], completion_tables["t06a"])
    n = len(rows)
    assert n == 16
    lo = round_whole(min(r["rate_exact"] for r in rows))
    hi = round_whole(max(r["rate_exact"] for r in rows))
    overall_rate_exact, _, _ = comp._overall_exact(completion_tables["t07"])
    x = round_whole(overall_rate_exact)
    assert line == f"All {n} groups sit within {lo}% to {hi}%, close to the overall {x}%."


def test_completion_takeaway_raises_when_a_row_is_ochre(completion_tables):
    t07 = completion_tables["t07"].copy()
    mask = (t07["Dimension"] == "Remoteness") & (t07["Group"] == "Remote")
    t07.loc[mask, "CI_Lower"] = 90.0
    t07.loc[mask, "CI_Upper"] = 95.0
    with pytest.raises(TitleAssumptionError):
        comp.build_takeaway_line(t07, completion_tables["t06a"])


def test_reach_takeaway_line_matches_tables(reach_tables):
    line = rc.build_takeaway_line(reach_tables["t18"], reach_tables["t06a"])
    rows, overall = rc._rows(reach_tables["t18"], reach_tables["t06a"])
    n = len(rows)
    assert n == 16
    lo = round_whole(min(r["share"] for r in rows))
    hi = round_whole(max(r["share"] for r in rows))
    x = round_whole(overall["share"])
    assert line == f"All {n} groups sit within {lo}% to {hi}%, close to the overall {x}%."


def test_reach_takeaway_raises_when_a_row_is_ochre(reach_tables):
    t18 = reach_tables["t18"].copy()
    mask = (t18["Dimension"] == "Remoteness") & (t18["Group"] == "Remote")
    t18.loc[mask, "Lower_exact"] = 90.0
    t18.loc[mask, "Upper_exact"] = 95.0
    with pytest.raises(TitleAssumptionError):
        rc.build_takeaway_line(t18, reach_tables["t06a"])


def test_density_round_facts_still_stated_somewhere_in_their_section():
    # Every number cut from a caption in this round must still be visible: on the
    # chart/title, or in the expander table.
    # Programs: 47% lives in the title.
    t15, t16 = find_program_intensity(), find_student_count_chance_check()
    import lib.titles as T
    title = T.title_what_is_delivered(t15, t16)
    assert "47%" in title

    # Reach: "no detectable difference" lives in the title; "none stands out" in the reading aid.
    t18, t18b = find_atsi_enrolled_share(), find_atsi_omnibus()
    title = T.title_reach(t18, t18b)
    assert "no detectable difference" in title
    assert "none stands out" in rc.READING_AID

    # Equity: 58.4%/61.5%/3.1 points still shown in the summary table.
    t09a, t09b, t09c = find_atsi_completion(), find_atsi_gap(), find_atsi_adjusted_model()
    html, _, _ = eq.build_summary_table_html(t09a, t09b, t09c)
    assert ">58.4<" in html and ">61.5<" in html


def test_density_round_no_em_dash():
    tables = gather_tables()
    cards = action_cards(tables)
    texts = [cards[3]["found"], cards[3]["stats_line"]]
    for t in texts:
        assert "—" not in t


# ----------------------------------------------------------------------
# NTG logo
# ----------------------------------------------------------------------

def test_logo_svg_file_exists_and_render_logo_returns_non_empty_content():
    from pathlib import Path
    from lib.theme import LOGO_PATH

    assert LOGO_PATH.exists()
    text = LOGO_PATH.read_text()
    assert text.strip()
    assert "<svg" in text


def test_logo_helper_embeds_inline_svg_with_correct_width_and_no_remote_url():
    import inspect

    from lib import theme

    assert theme.LOGO_WIDTH_PX == 140
    assert theme.LOGO_ALT_TEXT == "Northern Territory Government"
    # The helper reads the local file and embeds it inline - it never fetches a URL.
    source = inspect.getsource(theme.render_logo)
    assert "st.image" not in source or "http" not in source
    for banned in ["requests.get", "urlopen", "http://", "https://"]:
        assert banned not in source


def test_logo_render_logo_called_once_in_home():
    from pathlib import Path

    home_text = Path("app/Home.py").read_text()
    assert home_text.count("render_logo()") == 1
    # It must appear before the H1, not after.
    assert home_text.index("render_logo()") < home_text.index('st.title("NT VET Performance")')


def test_logo_home_imports_without_error():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    home_path = Path(__file__).resolve().parent.parent / "app" / "Home.py"
    at = AppTest.from_file(str(home_path))
    at.run(timeout=60)
    assert not at.exception


# ----------------------------------------------------------------------
# Sankey hover clipping fix
# ----------------------------------------------------------------------

def test_fo_sankey_top_margin_increased_and_plot_area_unchanged(fo_tables):
    from lib.chart_funding_outcome import HOVER_CLIP_FIX_PX, TOP_MARGIN, BOTTOM_MARGIN, _figure_height, _links

    t06a = fo_tables["t06a"]
    _, stream_order, _ = _links(t06a)
    pre_fix_height = _figure_height(len(stream_order))  # the old total height, before this fix
    pre_fix_plot_area = pre_fix_height - TOP_MARGIN - BOTTOM_MARGIN  # what the Sankey itself occupied

    fig = fo.build_figure(t06a)
    assert HOVER_CLIP_FIX_PX >= 45 and HOVER_CLIP_FIX_PX <= 55  # "about 50px"
    assert fig.layout.margin.t == TOP_MARGIN + HOVER_CLIP_FIX_PX
    assert fig.layout.margin.b == BOTTOM_MARGIN  # bottom margin untouched
    assert fig.layout.height == pre_fix_height + HOVER_CLIP_FIX_PX
    # The Sankey's own rendered area is exactly as tall as before the fix.
    actual_plot_area = fig.layout.height - fig.layout.margin.t - fig.layout.margin.b
    assert actual_plot_area == pre_fix_plot_area


def test_fo_sankey_hoverlabel_font_size_13(fo_tables):
    fig = fo.build_figure(fo_tables["t06a"])
    assert fig.layout.hoverlabel.font.size == 13


def test_fo_sankey_node_positions_unchanged_by_the_margin_fix(fo_tables):
    """The node/link y-fractions baked into the Sankey trace must be
    identical before and after the margin change, since they are
    computed from the unchanged plot-area figure_height, not the
    taller overall figure height."""
    from lib.chart_funding_outcome import _figure_height, _links, _stream_y_positions

    t06a = fo_tables["t06a"]
    _, stream_order, _ = _links(t06a)
    plot_area_height = _figure_height(len(stream_order))
    expected_y = _stream_y_positions(len(stream_order), plot_area_height)

    fig = fo.build_figure(t06a)
    sankey = fig.data[0]
    assert list(sankey.node.y[: len(stream_order)]) == expected_y


def test_no_overflow_hidden_anywhere_in_app():
    import pathlib

    app_dir = pathlib.Path("app")
    for path in app_dir.rglob("*.py"):
        text = path.read_text()
        assert "overflow" not in text.lower(), f"unexpected overflow CSS in {path}"

"""
Data-integrity tests for round 2 of the tone rewrite: chart titles and
captions. Every new sentence is checked against the tables with the
numfmt helpers, and no chart caption may contain a defensive hedge.
No rendering, no pixels.
"""

import pandas as pd
import pytest

from lib.numfmt import round_dp, round_whole
from lib.titles import TitleAssumptionError
from lib.data_access import (
    find_aggregate_geography,
    find_atsi_adjusted_model,
    find_atsi_completion,
    find_atsi_enrolled_share,
    find_atsi_gap,
    find_atsi_omnibus,
    find_coverage_grid,
    find_coverage_summary,
    find_completion_by_group,
    find_completion_omnibus_tests,
    find_delivery_without_contract,
    find_industry_outcome,
    find_matched_pairs,
    find_pairs_geography,
    find_program_intensity,
    find_rollups,
    find_sensitivity,
    find_stream_outcome,
    find_student_count_chance_check,
    find_withdrawn_notachieved_by_funded_flag,
    load_t01_kpis,
)
from lib import titles as T
import lib.chart_coverage as cov
import lib.chart_delivered_vs_target as dvt
import lib.chart_geography as geo
import lib.chart_programs as pr
import lib.chart_funding_outcome as fo
import lib.chart_completion as cc
import lib.chart_equity as eq
import lib.chart_reach as rc

BANNED = [
    "analysed as supplied",
    "workbook may not",
    "cannot say",
    "data cannot say",
    "not a settled difference",
]


def _all_chart_texts():
    texts = []

    texts.append(T.title_coverage(find_coverage_summary()))
    texts.append(cov.build_likely_explanation(find_delivery_without_contract()))
    texts.append(cov.build_table_takeaway(find_delivery_without_contract()))
    from lib.data_access import find_uncontracted_excluding_11k

    texts.append(
        cov.build_caption(find_coverage_summary(), find_delivery_without_contract(), find_coverage_grid(), find_uncontracted_excluding_11k())
    )

    texts.append(T.title_delivered_vs_target(find_rollups()))
    texts.append(dvt.build_table_takeaway(find_matched_pairs()))

    texts.append(geo.GEOGRAPHY_LIKELY_EXPLANATION)
    geo_caption, _ = geo.build_caption(find_pairs_geography(), find_aggregate_geography(), find_coverage_summary(), load_t01_kpis())
    texts.append(geo_caption)

    prog_caption, prog_stats = pr.build_caption(find_program_intensity(), find_student_count_chance_check())
    texts.append(prog_caption)
    texts.append(prog_stats["stats_line"])

    fo_caption, _ = fo.build_caption(find_stream_outcome(), find_withdrawn_notachieved_by_funded_flag(), find_industry_outcome())
    texts.append(fo_caption)

    comp_caption, comp_stats = cc.build_caption(find_completion_by_group(), find_completion_omnibus_tests(), find_sensitivity())
    texts.append(comp_caption)
    texts.append(comp_stats["stats_line"])
    texts.append(cc.build_reading_aid(find_completion_by_group(), find_stream_outcome()))

    eq_caption, eq_stats = eq.build_caption(find_atsi_completion(), find_atsi_gap(), find_atsi_adjusted_model())
    texts.append(eq_caption)
    texts.append(eq_stats["stats_line"])
    texts.append(eq.DEFINITION_LINE)
    texts.append(eq.build_subgroup_lead_line(find_atsi_completion(), find_atsi_gap()))

    reach_caption, reach_stats = rc.build_caption(find_atsi_enrolled_share(), find_atsi_omnibus())
    texts.append(reach_caption)
    texts.append(reach_stats["stats_line"])
    texts.append(rc.TABLE_NOTE_COUNTING)
    texts.append(rc.build_reading_aid(find_atsi_enrolled_share(), find_stream_outcome()))

    return [t for t in texts if t]


def test_no_banned_hedging_phrase_in_any_chart_caption():
    for text in _all_chart_texts():
        lowered = text.lower()
        for banned in BANNED:
            assert banned not in lowered, (banned, text)


def test_no_em_dash_in_any_chart_caption():
    for text in _all_chart_texts():
        assert "—" not in text
        assert "—" not in text


def test_coverage_table_takeaway_matches_the_table():
    dwc = find_delivery_without_contract()
    total = float(dwc["AHC"].sum())
    top5 = dwc.sort_values("AHC", ascending=False).head(5)
    top5_share = round_whole(100 * float(top5["AHC"].sum()) / total)
    p008 = dwc.loc[dwc["Flag_P008_FFT"] == True]  # noqa: E712
    p008_share = round_whole(100 * float(p008["AHC"].iloc[0]) / total)
    takeaway = cov.build_table_takeaway(dwc)
    assert takeaway == f"The 5 largest uncontracted lines hold {top5_share}% of the uncontracted hours; P008 Fee-Free TAFE alone holds {p008_share}%."
    assert (top5_share, p008_share) == (53, 22)


def test_coverage_likely_explanation_names_p008_fft_hours():
    dwc = find_delivery_without_contract()
    p008_ahc = float(dwc.loc[dwc["Flag_P008_FFT"] == True, "AHC"].iloc[0])  # noqa: E712
    text = cov.build_likely_explanation(dwc)
    assert f"{round_whole(p008_ahc):,} Fee-Free TAFE hours" in text
    assert "21,678 Fee-Free TAFE hours" in text
    assert text.startswith("Likely explanation to test:")


def test_dvt_title_is_whole_number_from_exact_overall_row():
    rollups = find_rollups()
    overall = rollups.loc[rollups["Level"] == "Overall"].iloc[0]
    pct_exact = 100 * float(overall["Delivered_AHC"]) / float(overall["Target_AHC_Total"])
    title = T.title_delivered_vs_target(rollups)
    assert title == f"On contracts with a target, delivery is about {round_whole(pct_exact)}% of 3-year target hours"
    assert title == "On contracts with a target, delivery is about 12% of 3-year target hours"


def test_dvt_table_takeaway_raises_if_threshold_shades_none_or_all():
    pairs = find_matched_pairs().copy()
    with pytest.raises(TitleAssumptionError):
        dvt.build_table_takeaway(pairs, threshold_pct=0)
    with pytest.raises(TitleAssumptionError):
        dvt.build_table_takeaway(pairs, threshold_pct=100)


def test_completion_reading_aid_raises_if_a_row_is_ochre():
    t07 = find_completion_by_group().copy()
    t06a = find_stream_outcome()
    overall = t07.loc[t07["Dimension"] == "Overall"].iloc[0]
    row = (t07["Dimension"] == "Provider_ID") & (t07["Group"] == "P002")
    t07.loc[row, "CI_Lower"] = float(overall["CI_Upper"]) + 5
    t07.loc[row, "CI_Upper"] = float(overall["CI_Upper"]) + 10
    with pytest.raises(TitleAssumptionError):
        cc.build_reading_aid(t07, t06a)


def test_reach_reading_aid_raises_if_a_row_is_ochre():
    t18 = find_atsi_enrolled_share().copy()
    t06a = find_stream_outcome()
    overall = t18.loc[t18["Dimension"] == "Overall"].iloc[0]
    row = (t18["Dimension"] == "Provider_ID") & (t18["Group"] == "P007")
    t18.loc[row, "Lower_exact"] = float(overall["Upper_exact"]) + 1
    t18.loc[row, "Upper_exact"] = float(overall["Upper_exact"]) + 10
    with pytest.raises(TitleAssumptionError):
        rc.build_reading_aid(t18, t06a)


def test_equity_stats_line_figures_match_the_tables():
    t09c = find_atsi_adjusted_model()
    t09b = find_atsi_gap()
    _, stats = eq.build_caption(find_atsi_completion(), t09b, t09c)
    p = float(t09c.loc[t09c["Metric"] == "OR p-value", "Value_exact"].iloc[0])
    assert f"p = {round_dp(p, 2):.2f}" in stats["stats_line"]
    assert f"about {round_whole(p * 100)} times in 100" in stats["stats_line"]
    assert "2 of 8 regional and funding stream gaps exclude zero, where about 0.40" in stats["stats_line"]


def test_reach_stats_line_figures_match_the_tables():
    t18b = find_atsi_omnibus()
    _, stats = rc.build_caption(find_atsi_enrolled_share(), t18b)
    for dim, key in [("Funding_Source", "for streams"), ("Provider_ID", "for providers"), ("Remoteness", "for regions")]:
        p = float(t18b.loc[t18b["Dimension"] == dim, "P_value"].iloc[0])
        assert f"{round_dp(p, 2):.2f} {key}" in stats["stats_line"]


def test_completion_stats_line_figures_match_the_tables():
    t07_omnibus = find_completion_omnibus_tests()
    _, stats = cc.build_caption(find_completion_by_group(), t07_omnibus, find_sensitivity())
    for dim, key in [("Funding_Source", "for streams"), ("Provider_ID", "for providers"), ("Remoteness", "for regions")]:
        p = float(t07_omnibus.loc[t07_omnibus["Dimension"] == dim, "Omnibus_GEE_p_value"].iloc[0])
        assert f"{round_dp(p, 2):.2f} {key}" in stats["stats_line"]

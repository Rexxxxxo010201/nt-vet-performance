"""
Each title's wording and figures are checked against a fresh, independent
read of the source CSVs (not by reusing titles.py's own arithmetic), so a
bug in titles.py can't mark its own homework. Each title also gets a
negative test: a deliberately broken copy of its source data that should
make the function raise TitleAssumptionError instead of returning wording
that misrepresents the data.
"""

import pandas as pd
import pytest

from lib.chart_coverage import build_caption, build_table_heading, build_table_html
from lib.chart_delivered_vs_target import build_caption as build_dvt_caption
from lib.chart_delivered_vs_target import build_figure as build_dvt_figure
from lib.chart_delivered_vs_target import build_funding_stream_table_html, build_pairs_table_html
from lib.chart_geography import build_caption as build_geo_caption
from lib.chart_geography import build_figure as build_geo_figure
from lib.chart_geography import build_pairs_table_html as build_geo_pairs_table_html
from lib.chart_programs import build_caption as build_programs_caption
from lib.chart_programs import build_cer40115_note
from lib.chart_programs import build_figure as build_programs_figure
from lib.chart_programs import build_table_html as build_programs_table_html
from lib.chart_funding_outcome import OUTCOME_NODE_ORDER
from lib.chart_funding_outcome import _links as _fo_links
from lib.chart_funding_outcome import build_caption as build_fo_caption
from lib.chart_funding_outcome import build_figure as build_fo_figure
from lib.chart_funding_outcome import build_table_html as build_fo_table_html
from lib.chart_completion import any_row_ochre as completion_any_row_ochre
from lib.chart_completion import build_caption as build_completion_caption
from lib.chart_completion import build_figure as build_completion_figure
from lib.chart_completion import build_table_html as build_completion_table_html
from lib.chart_equity import build_caption as build_equity_caption
from lib.chart_equity import subgroup_comparison_count
from lib.chart_equity import build_figure as build_equity_figure
from lib.chart_reach import REACH_CAVEAT
from lib.chart_reach import TABLE_NOTE_COUNTING, TABLE_NOTE_INTERVAL
from lib.chart_reach import any_row_ochre as reach_any_row_ochre
from lib.chart_reach import build_caption as build_reach_caption
from lib.chart_reach import build_figure as build_reach_figure
from lib.chart_reach import build_table_html as build_reach_table_html
from lib.chart_reach import _rows as reach_rows
from lib.chart_reach import _axis_range as reach_axis_range
from lib.chart_equity import build_subgroup_table_html as build_equity_subgroup_table_html
from lib.chart_equity import build_summary_table_html as build_equity_summary_table_html
from lib.data_access import (
    find_aggregate_geography,
    find_atsi_adjusted_model,
    find_atsi_completion,
    find_atsi_enrolled_share,
    find_atsi_gap,
    find_atsi_omnibus,
    find_completion_by_group,
    find_completion_omnibus_tests,
    find_sensitivity,
    find_coverage_grid,
    find_coverage_summary,
    find_delivery_without_contract,
    find_industry_outcome,
    find_matched_pairs,
    find_pairs_geography,
    find_program_intensity,
    find_program_labels,
    find_rollups,
    find_stream_outcome,
    find_student_count_chance_check,
    find_uncontracted_excluding_11k,
    find_withdrawn_notachieved_by_funded_flag,
    load_t01_kpis,
    load_t02a_coverage_summary,
    load_t03b_rollups,
    load_t05b_aggregate_geography,
    load_t06a_ahc_by_funding_outcome,
    load_t06c_withdrawn_notachieved_by_funded_flag,
    load_t07_completion_by_group,
    load_t07_omnibus_tests,
    load_t08a_atsi_reach,
    load_t09a_unadjusted_completion_by_atsi,
    load_t09c_adjusted_gee,
    load_t12a_by_industry,
    load_t12b_by_program,
    load_t15_program_intensity,
    load_t16_student_count_chance_check,
    load_t17a_ahc_by_industry_outcome,
)
from lib.titles import (
    TitleAssumptionError,
    title_completion,
    title_coverage,
    title_delivered_vs_target,
    title_equity,
    title_funding_outcome,
    title_geography,
    title_reach,
    title_what_is_delivered,
)


def test_title_coverage():
    t02a = load_t02a_coverage_summary()
    share = float(t02a.loc[t02a["Coverage_Bucket"] == "Delivery without a contract", "Share_of_Total_%"].iloc[0])
    expected_pct = round(share)
    assert share > 50
    title = title_coverage(t02a)
    assert title == f"{expected_pct}% of delivered hours have no matching contract"
    assert title == "56% of delivered hours have no matching contract"


def test_title_coverage_raises_if_not_majority():
    broken = pd.DataFrame({"Coverage_Bucket": ["Delivery without a contract"], "Share_of_Total_%": [45.0]})
    with pytest.raises(TitleAssumptionError):
        title_coverage(broken)


def test_chart1_tables_located_by_content_not_filename():
    """find_* locates each table by its columns/content; confirm each
    resolves to exactly one table and that table has the expected shape."""
    coverage = find_coverage_summary()
    assert {"Coverage_Bucket", "AHC", "Share_of_Total_%"}.issubset(coverage.columns)
    dwc = find_delivery_without_contract()
    assert {"Provider_ID", "Funding_Source", "AHC", "Flag_P008_FFT"}.issubset(dwc.columns)
    grid = find_coverage_grid()
    assert {"Provider_ID", "Funding_Source", "Status", "Delivered_AHC"}.issubset(grid.columns)
    uncontracted = find_uncontracted_excluding_11k()
    assert set(uncontracted.columns) == {"Metric", "Value"}
    assert uncontracted["Metric"].str.contains("11K", regex=False).any()


def test_title_coverage_matches_via_content_located_table():
    """The title must agree regardless of whether the table was loaded by
    filename (load_t02a_coverage_summary) or located by content (find_coverage_summary)."""
    assert title_coverage(find_coverage_summary()) == title_coverage(load_t02a_coverage_summary())


def test_build_caption_matches_target_wording_and_numbers():
    coverage = find_coverage_summary()
    dwc = find_delivery_without_contract()
    grid = find_coverage_grid()
    uncontracted = find_uncontracted_excluding_11k()

    total_ahc = int(coverage["AHC"].sum())
    no_contract_ahc = int(coverage.loc[coverage["Coverage_Bucket"] == "Delivery without a contract", "AHC"].iloc[0])
    largest = dwc.sort_values("AHC", ascending=False).iloc[0]
    assert (dwc["AHC"] == largest["AHC"]).sum() == 1, "largest uncontracted line must be unambiguous for this test"
    n_no_delivery = len(
        grid[(grid["Provider_ID"] == largest["Provider_ID"]) & (grid["Status"] == "Contract without delivery")]
    )
    non_11k_share = float(uncontracted.loc[uncontracted["Metric"].str.contains("Share of non-11K AHC", regex=False), "Value"].iloc[0])

    assert total_ahc == 172794
    assert no_contract_ahc == 97550
    assert largest["Provider_ID"] == "P008" and largest["Funding_Source"] == "FFT"
    assert n_no_delivery == 3
    assert non_11k_share == 48.5

    caption = build_caption(coverage, dwc, grid, uncontracted)
    assert caption == (
        "Of 172,794 funded hours delivered in 2023 to 2025, 97,550 sit in a provider and funding "
        "stream that has no contract in the workbook. P008's FFT delivery is the largest single "
        "line, while its 3 contracts show no delivery. Setting aside 11K, 48.5% of the remaining hours "
        "still have no matching contract."
    )


def test_build_caption_raises_if_largest_line_is_tied():
    coverage = find_coverage_summary()
    grid = find_coverage_grid()
    uncontracted = find_uncontracted_excluding_11k()
    tied_dwc = pd.DataFrame(
        {
            "Provider_ID": ["P008", "P005"],
            "Funding_Source": ["FFT", "11K"],
            "AHC": [21678, 21678],
            "Share_of_Total_%": [12.5, 12.5],
            "Flag_P008_FFT": [True, False],
        }
    )
    with pytest.raises(TitleAssumptionError):
        build_caption(coverage, tied_dwc, grid, uncontracted)


def test_build_caption_adapts_contracts_wording_when_count_differs():
    coverage = find_coverage_summary()
    dwc = find_delivery_without_contract()
    uncontracted = find_uncontracted_excluding_11k()
    largest = dwc.sort_values("AHC", ascending=False).iloc[0]
    # A coverage grid where the largest line's provider has only 1
    # contract-without-delivery row, not 3 - the sentence must say "1
    # contract", not silently keep saying "3 contracts".
    fake_grid = pd.DataFrame(
        {
            "Provider_ID": [largest["Provider_ID"]],
            "Funding_Source": ["ZZZ"],
            "Status": ["Contract without delivery"],
            "Delivered_AHC": [0],
        }
    )
    caption = build_caption(coverage, dwc, fake_grid, uncontracted)
    assert "its 1 contract shows no delivery" in caption
    assert "its 1 contracts" not in caption


def test_build_table_html_highlights_the_largest_row():
    dwc = find_delivery_without_contract()
    html, highlight_provider, highlight_fs = build_table_html(dwc)
    top5 = dwc.sort_values("AHC", ascending=False).head(5)
    assert len(top5) == 5
    assert highlight_provider == top5.iloc[0]["Provider_ID"]
    assert highlight_fs == top5.iloc[0]["Funding_Source"]
    assert highlight_provider == "P008" and highlight_fs == "FFT"
    from lib.theme import OCHRE_LIGHT_TINT

    assert OCHRE_LIGHT_TINT.lstrip("#") in html  # the light ochre tint is actually applied
    for _, row in top5.iterrows():
        assert row["Provider_ID"] in html
        assert f"{row['AHC']:,.0f}" in html


def test_build_table_heading_counts_and_names_the_dominant_stream():
    dwc = find_delivery_without_contract()
    top5 = dwc.sort_values("AHC", ascending=False).head(5)
    counts = top5["Funding_Source"].value_counts()
    top_stream, top_count = counts.index[0], int(counts.iloc[0])
    assert top_stream == "11K" and top_count == 4

    heading = build_table_heading(dwc)
    assert heading == "Largest uncontracted lines (4 of the 5 are 11K, User Choice)"


def test_build_table_heading_raises_on_a_tie():
    tied = pd.DataFrame(
        {
            "Provider_ID": ["P001", "P002", "P003", "P004"],
            "Funding_Source": ["11K", "11K", "FFT", "FFT"],
            "AHC": [100, 90, 80, 70],
            "Share_of_Total_%": [1.0, 0.9, 0.8, 0.7],
        }
    )
    with pytest.raises(TitleAssumptionError):
        build_table_heading(tied, n=4)


def test_title_delivered_vs_target():
    from lib.numfmt import round_whole

    t03b = load_t03b_rollups()
    overall = t03b.loc[t03b["Level"] == "Overall"].iloc[0]
    pct_exact = 100 * float(overall["Delivered_AHC"]) / float(overall["Target_AHC_Total"])
    title = title_delivered_vs_target(t03b)
    assert title == f"On contracts with a target, delivery is about {round_whole(pct_exact)}% of 3-year target hours"
    assert title == "On contracts with a target, delivery is about 12% of 3-year target hours"


def test_title_delivered_vs_target_raises_if_overall_row_missing():
    broken = pd.DataFrame({"Level": ["Funding_Source"], "Delivered_pct_of_Target": [12.5]})
    with pytest.raises(TitleAssumptionError):
        title_delivered_vs_target(broken)


def test_title_delivered_vs_target_raises_if_share_50_or_more():
    broken = pd.DataFrame({"Level": ["Overall"], "Delivered_AHC": [60.0], "Target_AHC_Total": [100.0]})
    with pytest.raises(TitleAssumptionError):
        title_delivered_vs_target(broken)


def test_chart2_tables_located_by_content_not_filename():
    pairs = find_matched_pairs()
    assert len(pairs) == 19
    assert {"Provider_ID", "Funding_Source", "Delivered_AHC", "Target_AHC_Total", "Delivered_pct_of_Target"}.issubset(
        pairs.columns
    )
    rollups = find_rollups()
    assert {"Level", "Key", "Delivered_AHC", "Target_AHC_Total", "Delivered_pct_of_Target"}.issubset(rollups.columns)


def test_chart2_figure_row_order_matches_sorted_share():
    pairs = find_matched_pairs()
    rollups = find_rollups()
    fig = build_dvt_figure(pairs, rollups)
    row_labels = list(fig.data[0].y)

    assert row_labels[0] == "All providers"
    provider_rollups = rollups.loc[rollups["Level"] == "Provider_ID"].set_index("Key")
    expected_order = (
        provider_rollups.loc[list(pairs["Provider_ID"].unique())]
        .sort_values("Delivered_pct_of_Target", ascending=False)
        .index.tolist()
    )
    assert row_labels[1:] == expected_order
    # strictly descending share for the provider rows (ties would still sort stably, but the
    # data should not actually tie here)
    shares = provider_rollups.loc[row_labels[1:], "Delivered_pct_of_Target"].tolist()
    assert shares == sorted(shares, reverse=True)


def test_chart2_provider_rows_sum_to_overall():
    pairs = find_matched_pairs()
    rollups = find_rollups()
    provider_rollups = rollups.loc[rollups["Level"] == "Provider_ID"]
    overall = rollups.loc[rollups["Level"] == "Overall"].iloc[0]

    providers_in_pairs = set(pairs["Provider_ID"].unique())
    relevant = provider_rollups[provider_rollups["Key"].isin(providers_in_pairs)]

    assert relevant["Delivered_AHC"].sum() == overall["Delivered_AHC"]
    assert relevant["Target_AHC_Total"].sum() == overall["Target_AHC_Total"]
    assert len(relevant) == 7
    assert "P008" not in providers_in_pairs


def test_chart2_caption_matches_target_wording_and_numbers():
    pairs = find_matched_pairs()
    rollups = find_rollups()
    grid = find_coverage_grid()

    overall = rollups.loc[rollups["Level"] == "Overall"].iloc[0]
    provider_rollups = rollups.loc[rollups["Level"] == "Provider_ID"]
    providers_in_pairs = provider_rollups[provider_rollups["Key"].isin(pairs["Provider_ID"].unique())]
    min_pct = float(providers_in_pairs["Delivered_pct_of_Target"].min())
    max_pct = float(providers_in_pairs["Delivered_pct_of_Target"].max())
    assert max_pct < 50

    p008_no_delivery = grid[(grid["Provider_ID"] == "P008") & (grid["Status"] == "Contract without delivery")]
    assert "P008" not in pairs["Provider_ID"].unique()
    assert len(p008_no_delivery) == 3

    from lib.numfmt import round_dp, round_whole

    overall_exact = 100 * float(overall["Delivered_AHC"]) / float(overall["Target_AHC_Total"])
    d = round_dp(overall_exact, 1)
    x = round_whole(overall_exact)
    precision_sentence = (
        f" The chart shows one decimal ({d:.1f}%) so providers can be compared; the title rounds it "
        f"to {x}%."
        if d != x
        else ""
    )

    caption = build_dvt_caption(pairs, rollups, grid)
    assert caption == (
        f"**Across the 19 contracts with a target, providers delivered {int(overall['Delivered_AHC']):,} of "
        f"{int(overall['Target_AHC_Total']):,} contracted hours.**\n\nEvery provider with delivery is well "
        f"below target, from {min_pct:.1f}% to {max_pct:.1f}%. P008 is not shown because none of its 3 "
        f"contracts has any delivery.{precision_sentence}"
    )
    assert caption == (
        "**Across the 19 contracts with a target, providers delivered 72,169 of 578,860 contracted "
        "hours.**\n\nEvery provider with delivery is well below target, from 7.6% to 18.4%. P008 is not "
        "shown because none of its 3 contracts has any delivery. The chart shows one decimal (12.5%) so "
        "providers can be compared; the title rounds it to 12%."
    )


def test_chart2_caption_raises_if_a_provider_is_not_well_below_target():
    pairs = find_matched_pairs()
    grid = find_coverage_grid()
    broken_rollups = pd.DataFrame(
        {
            "Level": ["Overall"] + ["Provider_ID"] * 7,
            "Key": ["All matched pairs"] + sorted(pairs["Provider_ID"].unique()),
            "Delivered_AHC": [72169] * 8,
            "Target_AHC_Total": [578860] * 8,
            "Delivered_pct_of_Target": [12.5] + [60.0] * 7,
        }
    )
    with pytest.raises(TitleAssumptionError):
        build_dvt_caption(pairs, broken_rollups, grid)


def test_chart2_figure_raises_if_p008_gains_a_pair_with_no_rollup_row():
    rollups = find_rollups()
    pairs_with_p008 = pd.DataFrame(
        {
            "Provider_ID": ["P001", "P008"],
            "Funding_Source": ["11J", "FFT"],
            "Delivered_AHC": [6214, 100],
            "Target_AHC_Total": [41000, 1000],
            "Delivered_pct_of_Target": [15.2, 10.0],
        }
    )
    # P008 has no Provider_ID roll-up row in the real rollups table, so
    # this should raise rather than silently miscount - confirming the
    # chart does not assume P008 is always absent without checking.
    with pytest.raises(TitleAssumptionError):
        build_dvt_figure(pairs_with_p008, rollups)


def test_chart2_caption_adapts_wording_if_p008_gains_a_consistent_pair():
    grid = find_coverage_grid()
    pairs_with_p008 = pd.DataFrame(
        {
            "Provider_ID": ["P001", "P008"],
            "Funding_Source": ["11J", "FFT"],
            "Delivered_AHC": [6214, 100],
            "Target_AHC_Total": [41000, 1000],
            "Delivered_pct_of_Target": [15.2, 10.0],
        }
    )
    rollups_with_p008 = pd.DataFrame(
        {
            "Level": ["Overall", "Provider_ID", "Provider_ID"],
            "Key": ["All matched pairs", "P001", "P008"],
            "Delivered_AHC": [6314, 6214, 100],
            "Target_AHC_Total": [42000, 41000, 1000],
            "Delivered_pct_of_Target": [15.0, 15.2, 10.0],
        }
    )
    caption = build_dvt_caption(pairs_with_p008, rollups_with_p008, grid)
    assert "P008 now has a contract with a target" in caption
    assert "P008 is not shown" not in caption


def test_title_geography():
    t05b = load_t05b_aggregate_geography()
    remote = t05b.loc[t05b["Remoteness"] == "Remote"]
    delivered = float(remote["Delivered_Share_%"].iloc[0])
    target = float(remote["Target_Share_%"].iloc[0])
    assert delivered - target >= 10
    title = title_geography(t05b)
    assert title == (
        f"Where there is a contract, delivery is weighted to Remote areas: {round(delivered)}% of hours "
        f"against {round(target)}% in contracts"
    )
    assert title == "Where there is a contract, delivery is weighted to Remote areas: 48% of hours against 27% in contracts"


def test_title_geography_raises_if_delivered_not_above_target():
    broken = pd.DataFrame({"Remoteness": ["Remote"], "Delivered_Share_%": [20.0], "Target_Share_%": [25.0]})
    with pytest.raises(TitleAssumptionError):
        title_geography(broken)


def test_title_geography_raises_if_gap_below_10_points():
    # Delivered is above target, but only by 5 points - not enough for
    # this headline's "skews Remote" framing.
    broken = pd.DataFrame({"Remoteness": ["Remote"], "Delivered_Share_%": [30.0], "Target_Share_%": [25.0]})
    with pytest.raises(TitleAssumptionError):
        title_geography(broken)


def test_title_funding_outcome():
    t06a = load_t06a_ahc_by_funding_outcome()
    t06c = load_t06c_withdrawn_notachieved_by_funded_flag()
    total = t06a["AHC_Funded"].sum()
    bad = t06a.loc[t06a["Outcome_Group"].isin(["Withdrawn", "Not achieved"]), "AHC_Funded"].sum()
    share = 100 * bad / total
    assert share >= 25
    title = title_funding_outcome(t06a, t06c)
    assert title == f"{round(share)}% of funded hours went to units not achieved or withdrawn"
    assert title == "36% of funded hours went to units not achieved or withdrawn"


def test_title_funding_outcome_raises_if_below_a_quarter():
    t06a = pd.DataFrame(
        {
            "Outcome_Group": ["Achieved", "Withdrawn", "Not achieved"],
            "AHC_Funded": [900, 50, 50],
        }
    )
    t06c = pd.DataFrame({"Funded_Flag": ["Y"], "AHC_Funded": [100]})
    with pytest.raises(TitleAssumptionError):
        title_funding_outcome(t06a, t06c)


def test_title_funding_outcome_raises_if_t06a_t06c_disagree():
    t06a = load_t06a_ahc_by_funding_outcome()
    t06c_wrong = pd.DataFrame({"Funded_Flag": ["Y"], "AHC_Funded": [1]})
    with pytest.raises(TitleAssumptionError):
        title_funding_outcome(t06a, t06c_wrong)


def test_title_funding_outcome_does_not_raise_between_25_and_a_third():
    # 30% is below the old one-third threshold but above the new 25%
    # threshold used by the Sankey charts - confirms the boundary moved,
    # not just the error message.
    t06a = pd.DataFrame(
        {
            "Outcome_Group": ["Achieved", "Withdrawn", "Not achieved"],
            "AHC_Funded": [700, 150, 150],
        }
    )
    t06c = pd.DataFrame({"Funded_Flag": ["Y"], "AHC_Funded": [300]})
    assert title_funding_outcome(t06a, t06c) == "30% of funded hours went to units not achieved or withdrawn"


def test_title_completion():
    t07 = load_t07_completion_by_group()
    t07_omnibus = load_t07_omnibus_tests()
    overall_rate = float(t07.loc[t07["Dimension"] == "Overall", "Rate_%"].iloc[0])
    assert 55 <= overall_rate <= 65
    fs_p = float(t07_omnibus.loc[t07_omnibus["Dimension"] == "Funding_Source", "Omnibus_GEE_p_value"].iloc[0])
    prov_p = float(t07_omnibus.loc[t07_omnibus["Dimension"] == "Provider_ID", "Omnibus_GEE_p_value"].iloc[0])
    remote_p = float(t07_omnibus.loc[t07_omnibus["Dimension"] == "Remoteness", "Omnibus_GEE_p_value"].iloc[0])
    assert fs_p > 0.05 and prov_p > 0.05 and remote_p > 0.05
    title = title_completion(t07, t07_omnibus)
    assert title == (
        f"About {round(overall_rate)}% of units with a final outcome are achieved, with no detectable difference "
        f"between streams, providers or regions"
    )
    assert title == (
        "About 60% of units with a final outcome are achieved, with no detectable difference between streams, providers or regions"
    )


def test_title_completion_raises_if_rate_not_about_60():
    t07 = pd.DataFrame({"Dimension": ["Overall"], "Rate_%": [80.0]})
    t07_omnibus = pd.DataFrame(
        {"Dimension": ["Funding_Source", "Provider_ID", "Remoteness"], "Omnibus_GEE_p_value": [0.5, 0.5, 0.5]}
    )
    with pytest.raises(TitleAssumptionError):
        title_completion(t07, t07_omnibus)


def test_title_completion_raises_if_a_dimension_is_significant():
    t07 = pd.DataFrame({"Dimension": ["Overall"], "Rate_%": [60.4]})
    t07_omnibus = pd.DataFrame(
        {"Dimension": ["Funding_Source", "Provider_ID", "Remoteness"], "Omnibus_GEE_p_value": [0.01, 0.5, 0.5]}
    )
    with pytest.raises(TitleAssumptionError):
        title_completion(t07, t07_omnibus)


def test_title_completion_raises_if_remoteness_p_value_is_significant():
    t07 = pd.DataFrame({"Dimension": ["Overall"], "Rate_%": [60.4]})
    t07_omnibus = pd.DataFrame(
        {"Dimension": ["Funding_Source", "Provider_ID", "Remoteness"], "Omnibus_GEE_p_value": [0.5, 0.5, 0.03]}
    )
    with pytest.raises(TitleAssumptionError):
        title_completion(t07, t07_omnibus)


def test_title_completion_does_not_raise_at_exactly_p_0_05():
    # The raise condition is "below 0.05", so a p-value of exactly 0.05
    # must not trigger it.
    t07 = pd.DataFrame({"Dimension": ["Overall"], "Rate_%": [60.4], "Rate_exact": [60.4321]})
    t07_omnibus = pd.DataFrame(
        {"Dimension": ["Funding_Source", "Provider_ID", "Remoteness"], "Omnibus_GEE_p_value": [0.05, 0.5, 0.5]}
    )
    assert title_completion(t07, t07_omnibus) == (
        "About 60% of units with a final outcome are achieved, with no detectable difference between streams, providers or regions"
    )


def test_title_equity():
    from lib.numfmt import round_whole

    t09b = find_atsi_gap()
    t09c = find_atsi_adjusted_model()
    gap_row = t09b.loc[t09b["Dimension"] == "Overall"].iloc[0]
    unadjusted_whole = round_whole(gap_row["Gap_exact"])
    adjusted_whole = round_whole(
        t09c.loc[t09c["Metric"] == "Model-predicted gap, Y minus N (pp)", "Value_exact"].iloc[0]
    )
    assert unadjusted_whole == adjusted_whole == -3
    or_p = float(t09c.loc[t09c["Metric"] == "OR p-value", "Value_exact"].iloc[0])
    assert 0.01 <= or_p < 0.05

    title = title_equity(t09b, t09c)
    assert title == f"Aboriginal and Torres Strait Islander learners complete about {abs(unadjusted_whole)} points less often"
    assert title == "Aboriginal and Torres Strait Islander learners complete about 3 points less often"


def test_title_equity_raises_if_gaps_round_to_different_whole_numbers():
    t09b = pd.DataFrame(
        {"Dimension": ["Overall"], "Group": ["Overall"], "Gap_exact": [-2.8], "Lower_exact": [-5.6], "Upper_exact": [0.1]}
    )
    t09c = pd.DataFrame(
        {
            "Metric": ["Model-predicted gap, Y minus N (pp)", "OR p-value"],
            "Value_exact": [-4.0, 0.02],
        }
    )
    with pytest.raises(TitleAssumptionError):
        title_equity(t09b, t09c)


def test_title_equity_raises_if_gap_not_negative():
    t09b = pd.DataFrame(
        {"Dimension": ["Overall"], "Group": ["Overall"], "Gap_exact": [3.0], "Lower_exact": [-1.0], "Upper_exact": [7.0]}
    )
    t09c = pd.DataFrame(
        {
            "Metric": ["Model-predicted gap, Y minus N (pp)", "OR p-value"],
            "Value_exact": [3.0, 0.02],
        }
    )
    with pytest.raises(TitleAssumptionError):
        title_equity(t09b, t09c)


def test_title_equity_raises_if_evidence_neither_borderline_nor_zero_interval():
    # Gaps agree (both round to -3) and the gap is negative, but the p-value is far
    # from borderline (0.3) AND the unadjusted interval does not include zero -
    # neither signal of "borderline" holds, so this must raise rather than print
    # wording that calls strong (or absent) evidence "borderline".
    t09b = pd.DataFrame(
        {"Dimension": ["Overall"], "Group": ["Overall"], "Gap_exact": [-2.6], "Lower_exact": [-5.0], "Upper_exact": [-1.0]}
    )
    t09c = pd.DataFrame(
        {
            "Metric": ["Model-predicted gap, Y minus N (pp)", "OR p-value"],
            "Value_exact": [-3.2, 0.3],
        }
    )
    with pytest.raises(TitleAssumptionError):
        title_equity(t09b, t09c)


def test_title_equity_does_not_raise_when_only_interval_includes_zero():
    # p-value is NOT in the borderline band (it is very small), but the unadjusted
    # interval still includes zero - the "or" means this is still enough to print.
    t09b = pd.DataFrame(
        {"Dimension": ["Overall"], "Group": ["Overall"], "Gap_exact": [-2.6], "Lower_exact": [-5.0], "Upper_exact": [0.5]}
    )
    t09c = pd.DataFrame(
        {
            "Metric": ["Model-predicted gap, Y minus N (pp)", "OR p-value"],
            "Value_exact": [-3.2, 0.001],
        }
    )
    title = title_equity(t09b, t09c)
    assert title.startswith("Aboriginal and Torres Strait Islander learners complete about 3")


def _reach_tables():
    return find_atsi_enrolled_share(), find_atsi_omnibus()


def test_title_reach_matches_tables():
    from lib.numfmt import round_whole

    t18, t18b = _reach_tables()
    overall = t18.loc[t18["Dimension"] == "Overall"].iloc[0]
    expected = (
        f"About {round_whole(float(overall['Share_exact']))}% of enrolled students are Aboriginal and Torres "
        f"Strait Islander, with no detectable difference between funding streams, providers or regions"
    )
    assert title_reach(t18, t18b) == expected
    assert title_reach(t18, t18b) == (
        "About 36% of enrolled students are Aboriginal and Torres Strait Islander, with no detectable "
        "difference between funding streams, providers or regions"
    )


def test_title_reach_raises_if_a_p_value_is_below_0_05():
    t18, t18b = _reach_tables()
    altered = t18b.copy()
    altered.loc[altered["Dimension"] == "Provider_ID", "P_value"] = 0.04
    with pytest.raises(TitleAssumptionError):
        title_reach(t18, altered)


def test_title_reach_raises_if_overall_share_is_outside_25_to_50():
    t18, t18b = _reach_tables()
    altered = t18.copy()
    overall = altered["Dimension"] == "Overall"
    altered.loc[overall, "Share_exact"] = 55.0
    with pytest.raises(TitleAssumptionError):
        title_reach(altered, t18b)


def test_chart2_pairs_table_html_shows_all_19_rows_formatted():
    pairs = find_matched_pairs()
    html = build_pairs_table_html(pairs)

    assert html.count("<tr") == 1 + 19  # one header row, no inner-scroll limit on the 19 body rows
    assert "Provider" in html and "Funding stream" in html
    assert "Delivered hours" in html and "Target hours" in html and "Delivered as % of target" in html

    for _, row in pairs.iterrows():
        assert f"{row['Delivered_AHC']:,.0f}" in html  # thousands separator, e.g. 5,283
        assert f"{row['Target_AHC_Total']:,.0f}" in html  # e.g. 10,400
        assert f">{row['Delivered_pct_of_Target']:.1f}<" in html  # 1 decimal place, no "%" suffix

    # Spot-check the specific values named in the brief, confirming they
    # are real rows in the table, not just coincidentally-formatted numbers.
    for pct in ["18.0", "15.0", "7.0", "5.0"]:
        assert f">{pct}<" in html

    # Funding stream values are left-aligned (text), not right-aligned (numbers).
    assert "text-align:left" in html.split("Funding stream</th>")[0].split("<th")[-1]


def test_chart2_pairs_table_html_numbers_are_right_aligned():
    pairs = find_matched_pairs()
    html = build_pairs_table_html(pairs)
    for header in ["Delivered hours", "Target hours", "Delivered as % of target"]:
        th_fragment = [h for h in html.split("<th") if header in h][0]
        assert "text-align:right" in th_fragment


def test_chart2_funding_stream_table_html_matches_source_and_headers():
    rollups = find_rollups()
    html = build_funding_stream_table_html(rollups)
    funding_rows = rollups.loc[rollups["Level"] == "Funding_Source"]

    assert html.count("<tr") == 1 + len(funding_rows)
    assert "Delivered as % of target" in html
    assert ">%</th>" not in html  # the bare "%" header was replaced, not just supplemented

    for _, row in funding_rows.iterrows():
        assert row["Key"] in html
        assert f"{row['Delivered_AHC']:,.0f}" in html
        assert f"{row['Target_AHC_Total']:,.0f}" in html
        assert f">{row['Delivered_pct_of_Target']:.1f}<" in html


def test_chart2_separator_line_stops_at_the_track_not_the_labels():
    pairs = find_matched_pairs()
    rollups = find_rollups()
    fig = build_dvt_figure(pairs, rollups)
    separator = next(s for s in fig.layout.shapes if s.y0 == 0.5 and s.y1 == 0.5)
    assert separator.xref == "x"
    assert separator.x1 == 100  # stops at the track's right edge, not xref='paper' x1=1


def test_chart3_tables_located_by_content_not_filename():
    pairs = find_pairs_geography()
    agg = find_aggregate_geography()
    assert len(pairs) == 57  # 19 pairs x 3 remoteness classes
    assert len(pairs[["Provider_ID", "Funding_Source"]].drop_duplicates()) == 19
    assert set(agg["Remoteness"]) == {"Urban", "Regional", "Remote"}


def test_chart3_aggregate_shares_sum_to_100():
    agg = find_aggregate_geography()
    assert abs(agg["Target_Share_%"].sum() - 100) <= 0.5
    assert abs(agg["Delivered_Share_%"].sum() - 100) <= 0.5


def test_chart3_caption_matches_target_wording_and_numbers():
    pairs = find_pairs_geography()
    agg = find_aggregate_geography()

    urban_agg = agg.loc[agg["Remoteness"] == "Urban"].iloc[0]
    remote_agg = agg.loc[agg["Remoteness"] == "Remote"].iloc[0]
    urban_pairs = pairs.loc[pairs["Remoteness"] == "Urban"]
    remote_pairs = pairs.loc[pairs["Remoteness"] == "Remote"]

    n_urban_below = int((urban_pairs["Diff_pp"] < 0).sum())
    m_remote_above = int((remote_pairs["Diff_pp"] > 0).sum())
    assert n_urban_below == 19
    assert m_remote_above == 17

    pct_of_target = {row["Remoteness"]: float(row["Delivered_pct_of_Target_%"]) for _, row in agg.iterrows()}
    assert pct_of_target["Urban"] == min(pct_of_target.values())
    assert pct_of_target["Remote"] < 100

    caption, stats = build_geo_caption(pairs, agg, find_coverage_summary(), load_t01_kpis())
    assert stats == {
        "n_urban_below": 19,
        "m_remote_above": 17,
        "n_total": 19,
        "pattern_included": True,
        "pct_of_target": pct_of_target,
        "furthest_behind_included": True,
    }

    assert caption == (
        f"**Contracts planned for {round(urban_agg['Target_Share_%'])}% of hours in Urban areas and "
        f"{round(remote_agg['Target_Share_%'])}% in Remote areas.**\n\nDelivery went the other way: "
        f"{round(urban_agg['Delivered_Share_%'])}% Urban and {round(remote_agg['Delivered_Share_%'])}% "
        f"Remote. This held in 19 of 19 contracts for Urban and 17 of 19 for Remote, so it is a "
        f"pattern, not a few providers. Remote areas still received only "
        f"{round(pct_of_target['Remote'])}% of their contracted hours (Urban "
        f"{round(pct_of_target['Urban'])}%), so Urban is falling furthest behind, not Remote "
        f"exceeding its plan. These figures cover the 19 contracts with matching delivery "
        f"(72,169 of 172,794 funded hours, 42%). Across all funded hours the Remote share is 47%.\n\n"
        "Either the contracts' geographic targets do not reflect where training happens, or delivery "
        "is not following the contracts; this needs confirming against the contract register."
    )
    assert caption.startswith(
        "**Contracts planned for 46% of hours in Urban areas and 27% in Remote areas.**\n\nDelivery "
        "went the other way: 26% Urban and 48% Remote."
    )
    assert "pair" not in caption.lower()
    assert "comparable" not in caption.lower()
    assert "aggregate" not in caption.lower()


def test_chart3_caption_drops_pattern_clause_when_below_80_percent():
    agg = find_aggregate_geography()
    # Urban's delivery sits below its contracted share in only 10 of 19
    # contracts - just over half, well under the 80% bar - so the "a
    # pattern, not a few providers" clause must be dropped while the
    # plain counts stay in the sentence.
    urban_rows = pd.DataFrame(
        {
            "Provider_ID": [f"P{i}" for i in range(19)],
            "Funding_Source": ["11J"] * 19,
            "Remoteness": ["Urban"] * 19,
            "Target_Share_%": [45.0] * 19,
            "Delivered_Share_%": [40.0] * 10 + [50.0] * 9,
            "Diff_pp": [-5.0] * 10 + [5.0] * 9,
        }
    )
    remote_rows = pd.DataFrame(
        {
            "Provider_ID": [f"P{i}" for i in range(19)],
            "Funding_Source": ["11J"] * 19,
            "Remoteness": ["Remote"] * 19,
            "Target_Share_%": [27.0] * 19,
            "Delivered_Share_%": [48.0] * 19,
            "Diff_pp": [21.0] * 19,
        }
    )
    pairs = pd.concat([urban_rows, remote_rows], ignore_index=True)
    caption, stats = build_geo_caption(pairs, agg, find_coverage_summary(), load_t01_kpis())
    assert stats["n_urban_below"] == 10
    assert stats["m_remote_above"] == 19
    assert stats["pattern_included"] is False
    assert "This held in 10 of 19 contracts for Urban and 19 of 19 for Remote." in caption
    assert "pattern" not in caption


def test_chart3_caption_drops_furthest_behind_clause_when_urban_is_not_lowest():
    pairs = find_pairs_geography()
    # Urban's own percentage of target (30%) is no longer the lowest of
    # the three regions (Regional's 10% is lower), so the "Urban is
    # falling furthest behind" clause must be dropped.
    agg = pd.DataFrame(
        {
            "Remoteness": ["Urban", "Regional", "Remote"],
            "Target_Share_%": [45.9, 27.2, 26.9],
            "Delivered_Share_%": [25.6, 26.4, 48.0],
            "Diff_pp": [-20.3, -0.8, 21.1],
            "Delivered_pct_of_Target_%": [30.0, 10.0, 90.0],
            # Chosen so Delivered_AHC_Sum / Target_AHC_Sum * 100 reproduces the
            # Delivered_pct_of_Target_% values above exactly (100 as a common target
            # base keeps the arithmetic obvious: 30/100, 10/100, 90/100).
            "Target_AHC_Sum": [100, 100, 100],
            "Delivered_AHC_Sum": [30, 10, 90],
        }
    )
    caption, stats = build_geo_caption(pairs, agg, find_coverage_summary(), load_t01_kpis())
    assert stats["furthest_behind_included"] is False
    assert "Remote areas still received only 90% of their contracted hours (Urban 30%)." in caption
    assert "falling furthest behind" not in caption


def test_chart3_figure_has_diamond_behind_circle_and_a_line_per_row():
    agg = find_aggregate_geography()
    fig = build_geo_figure(agg)
    symbols = [t.marker.symbol for t in fig.data if t.mode == "markers"]
    assert symbols == ["diamond", "circle"]  # diamond trace added first -> rendered behind
    diamond_trace = [t for t in fig.data if t.mode == "markers" and t.marker.symbol == "diamond"][0]
    circle_trace = [t for t in fig.data if t.mode == "markers" and t.marker.symbol == "circle"][0]
    assert diamond_trace.marker.size > circle_trace.marker.size
    line_traces = [t for t in fig.data if t.mode == "lines"]
    assert len(line_traces) == 3


def test_chart3_figure_labels_use_whole_numbers_and_singular_point():
    # Regional's gap (-0.6) rounds to exactly 1 point, to check the
    # singular "1 point" (not "1 points") wording; Urban's larger gap
    # checks the plural, and all three check whole-number rounding.
    # Target_AHC_Sum/Delivered_AHC_Sum (each summing to 100, so the shares equal
    # the raw values directly) are chosen so the exact figures reproduce the
    # same whole-number outcomes the old one-decimal columns used to give:
    # Regional's gap rounds to exactly 1 point (26.46 - 27 = -0.54), Urban's
    # gap rounds to 20 points, Remote's to 21 points.
    agg = pd.DataFrame(
        {
            "Remoteness": ["Urban", "Regional", "Remote"],
            "Target_Share_%": [45.9, 27.0, 26.9],
            "Delivered_Share_%": [25.6, 26.4, 48.0],
            "Diff_pp": [-20.3, -0.6, 21.1],
            "Delivered_pct_of_Target_%": [7.0, 97.8, 22.2],
            "Target_AHC_Sum": [46, 27, 27],
            "Delivered_AHC_Sum": [25.6, 26.46, 47.94],
        }
    )
    fig = build_geo_figure(agg)
    annotation_texts = [a.text for a in fig.layout.annotations]

    assert any(t == "Contracted 46%" for t in annotation_texts)
    assert any(t == "Delivered 26%" for t in annotation_texts)
    assert any(t == "Contracted 27%" for t in annotation_texts)
    assert any(t == "Delivered 48%" for t in annotation_texts)

    singular_texts = [t for t in annotation_texts if "<b>1 point below contract</b>" in t]
    assert len(singular_texts) == 1
    assert "98% of contracted hours delivered" in singular_texts[0]
    assert "1 points" not in singular_texts[0]

    plural_texts = [t for t in annotation_texts if "<b>20 points below contract</b>" in t]
    assert len(plural_texts) == 1

    above_texts = [t for t in annotation_texts if "points above contract" in t]
    assert len(above_texts) == 1
    assert "<b>21 points above contract</b>" in above_texts[0]


def test_chart3_pairs_table_html_has_19_rows_and_five_region_columns():
    pairs = find_pairs_geography()
    html = build_geo_pairs_table_html(pairs)
    assert html.count("<tr>") == 1 + 19  # one header row, 19 body rows, no inner-scroll cap
    assert "Provider" in html and "Funding stream" in html
    for remoteness in ["Urban", "Regional", "Remote"]:
        assert f">{remoteness}<" in html

    wide = pairs.pivot_table(
        index=["Provider_ID", "Funding_Source"],
        columns="Remoteness",
        values=["Target_Share_%", "Delivered_Share_%", "Diff_pp"],
    )
    wide.columns = [f"{value}_{remoteness}" for value, remoteness in wide.columns]
    wide = wide.reset_index()
    assert len(wide) == 19

    for _, row in wide.iterrows():
        for remoteness in ["Urban", "Regional", "Remote"]:
            gap = row[f"Diff_pp_{remoteness}"]
            target = row[f"Target_Share_%_{remoteness}"]
            delivered = row[f"Delivered_Share_%_{remoteness}"]
            assert f"<b>{gap:+.1f}</b>" in html
            assert f"{target:.1f} to {delivered:.1f}" in html

    # Text columns left-aligned, not right-aligned like the region columns.
    provider_header = [h for h in html.split("<th") if "Provider" in h][0]
    assert "text-align:left" in provider_header
    for remoteness in ["Urban", "Regional", "Remote"]:
        region_header = [h for h in html.split("<th") if f">{remoteness}<" in h][0]
        assert "text-align:right" in region_header


def test_chart3_pairs_table_html_sorted_by_remote_gap_descending():
    import re

    pairs = find_pairs_geography()
    html = build_geo_pairs_table_html(pairs)

    wide = pairs.pivot_table(index=["Provider_ID", "Funding_Source"], columns="Remoteness", values="Diff_pp")
    wide = wide.reset_index()
    expected_order = wide.sort_values("Remote", ascending=False)["Provider_ID"].tolist()

    providers_in_html = re.findall(r"<td[^>]*>(P\d{3})[^<]*</td><td[^>]*>", html)
    assert providers_in_html == expected_order


def test_chart3_pairs_table_html_tint_direction_matches_gap_sign():
    from lib.theme import BLUE, OCHRE

    pairs = find_pairs_geography()
    html = build_geo_pairs_table_html(pairs)
    blue_rgb = tuple(int(BLUE.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    ochre_rgb = tuple(int(OCHRE.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    assert f"rgba({blue_rgb[0]},{blue_rgb[1]},{blue_rgb[2]}," in html  # at least one below-contract cell
    assert f"rgba({ochre_rgb[0]},{ochre_rgb[1]},{ochre_rgb[2]}," in html  # at least one above-contract cell


def test_chart3_pairs_table_html_shares_text_uses_the_darker_grey():
    from lib.theme import GREY_DARK, GREY_MID

    pairs = find_pairs_geography()
    html = build_geo_pairs_table_html(pairs)
    assert f"color:{GREY_DARK}" in html  # the readable-over-tint grey, not the lighter chart-ink grey
    assert f"color:{GREY_MID}" not in html


def test_chart3_tint_opacity_formula():
    from lib.chart_geography import _tint_style

    assert _tint_style(0.5) == ""  # under the 1-point floor: no tint
    assert _tint_style(-0.9) == ""
    assert _tint_style(40) == "background-color:rgba(163,90,22,0.350);"  # max opacity at 40 points
    assert _tint_style(80) == "background-color:rgba(163,90,22,0.350);"  # still capped beyond 40
    assert _tint_style(-20) == "background-color:rgba(43,108,176,0.175);"  # half of 40 -> half of max


def test_vocab_stream_key_caption_and_names():
    from lib.vocab import FUNDING_STREAM_NAMES, STREAM_KEY_CAPTION

    assert FUNDING_STREAM_NAMES == {
        "11J": "General Recurrent",
        "11K": "User Choice",
        "11N": "VET in Schools (Urban)",
        "11V": "VET in Schools (Remote)",
        "FFT": "Fee-Free TAFE",
    }
    assert STREAM_KEY_CAPTION == (
        "Funding streams: 11J General Recurrent, 11K User Choice, 11N and 11V VET in Schools, "
        "FFT Fee-Free TAFE."
    )


def test_chart1_uses_shared_vocab_funding_stream_names():
    from lib.chart_coverage import FUNDING_STREAM_NAMES as chart1_names
    from lib.vocab import FUNDING_STREAM_NAMES as vocab_names

    assert chart1_names is vocab_names


def test_chart4_tables_located_by_content_not_filename():
    intensity = find_program_intensity()
    assert {
        "Program_ID", "Short_Label", "Industry", "Distinct_Students", "Units", "AHC_Funded",
        "Share_of_Total_%", "AHC_per_Unit", "Mean_Nominal_Hours_per_Unit", "Mean_Funded_Fraction",
    }.issubset(intensity.columns)
    assert len(intensity) == 12  # 10 programs + 2 summary rows

    labels = find_program_labels()
    assert {"Program_ID", "Program_Name", "Full_Label"}.issubset(labels.columns)

    chance_check = find_student_count_chance_check()
    assert set(chance_check.columns) == {"Metric", "Value"}
    assert chance_check["Metric"].str.contains("Two-sided p-value", regex=False).any()


def test_title_what_is_delivered():
    t15 = load_t15_program_intensity()
    t16 = load_t16_student_count_chance_check()

    programs = t15.loc[~t15["Program_ID"].astype(str).str.contains(" ")]
    assert len(programs) == 10
    top3 = programs.sort_values("AHC_Funded", ascending=False).head(3)
    assert (top3["Industry"] == "Community Services").all()

    p_value = float(t16.loc[t16["Metric"].str.contains("Two-sided", regex=False), "Value"].iloc[0])
    min_students = float(t16.loc[t16["Metric"].str.contains("minimum", regex=False), "Value"].iloc[0])
    max_students = float(t16.loc[t16["Metric"].str.contains("maximum", regex=False), "Value"].iloc[0])
    assert p_value >= 0.05
    assert max_students <= 1.5 * min_students

    pct = round(float(top3["Share_of_Total_%"].sum()))
    title = title_what_is_delivered(t15, t16)
    assert title == (
        f"Student numbers are similar across programs, but three Community Services programs take "
        f"{pct}% of funded hours"
    )
    assert title == (
        "Student numbers are similar across programs, but three Community Services programs take "
        "47% of funded hours"
    )
    for banned in ["popular", "in demand", "most", "second"]:
        assert banned not in title.lower()


def test_title_what_is_delivered_raises_if_top3_not_all_community_services():
    t16 = load_t16_student_count_chance_check()
    broken = pd.DataFrame(
        {
            "Program_ID": [f"P{i}00001" for i in range(10)],
            "Industry": ["Business"] + ["Community Services"] * 2 + ["Other"] * 7,
            "AHC_Funded": [50000, 40000, 30000] + [10000] * 7,
            "Share_of_Total_%": [30.0, 25.0, 20.0] + [3.57] * 7,
        }
    )
    with pytest.raises(TitleAssumptionError):
        title_what_is_delivered(broken, t16)


def test_title_what_is_delivered_raises_if_pvalue_below_threshold():
    t15 = load_t15_program_intensity()
    broken_t16 = pd.DataFrame(
        {
            "Metric": ["Observed minimum students (any program)", "Observed maximum students (any program)", "Two-sided p-value for observed spread"],
            "Value": [169, 204, 0.04],
        }
    )
    with pytest.raises(TitleAssumptionError):
        title_what_is_delivered(t15, broken_t16)


def test_title_what_is_delivered_raises_if_student_ratio_exceeds_1_5():
    t15 = load_t15_program_intensity()
    broken_t16 = pd.DataFrame(
        {
            "Metric": ["Observed minimum students (any program)", "Observed maximum students (any program)", "Two-sided p-value for observed spread"],
            "Value": [100, 160, 0.7314],
        }
    )
    with pytest.raises(TitleAssumptionError):
        title_what_is_delivered(t15, broken_t16)


def test_chart4_caption_matches_target_wording_and_numbers():
    t15 = load_t15_program_intensity()
    t16 = load_t16_student_count_chance_check()

    programs = t15.loc[~t15["Program_ID"].astype(str).str.contains(" ")]
    top3 = programs.sort_values("AHC_Funded", ascending=False).head(3)
    pct = round(float(top3["Share_of_Total_%"].sum()))

    summary = t15.loc[t15["Program_ID"].astype(str).str.contains(" ")]
    cs = summary.loc[summary["Industry"] == "Community Services"].iloc[0]
    other = summary.loc[summary["Industry"] != "Community Services"].iloc[0]
    ahc_ratio = float(cs["AHC_per_Unit"]) / float(other["AHC_per_Unit"])
    assert 1.75 <= ahc_ratio <= 2.25  # "about twice" branch, for the real data

    caption, stats = build_programs_caption(t15, t16)
    assert stats["pct"] == pct == 47
    assert stats["min_students"] == 169
    assert stats["max_students"] == 204
    assert stats["ratio_phrase"] == "about twice"
    assert stats["explain_included"] is True
    assert stats["cs_hours"] == 50
    assert stats["other_hours"] == 28
    assert stats["cs_fraction"] == 91
    assert stats["other_fraction"] == 89

    assert caption == (
        "**Student numbers are similar across the ten programs (169 to 204 students each).**\n\n"
        "Community Services units carry about twice the funded hours of other units (46.1 against 24.5 "
        "funded hours per unit), because they are longer: about 50 nominal hours against 28 for other "
        "industries. This describes the hours and does not say why units differ. The extra hours come "
        "from longer units, not from more students."
    )
    assert "47%" not in caption  # that figure now lives only in the title, not repeated in the caption
    assert stats["stats_line"] == (
        "For readers who want the statistics: p = 0.73. If program size did not vary beyond chance, a "
        "spread this wide would turn up about 73 times in 100."
    )
    for banned in ["popular", "in demand", "most", "second"]:
        assert banned not in caption.lower()


def test_chart4_caption_drops_explain_clause_when_fractions_differ_too_much():
    t15 = load_t15_program_intensity().copy()
    t16 = load_t16_student_count_chance_check()
    # Push the "Other 7 programs combined" funded fraction far below the
    # Community Services one (more than 5 percentage points apart), so
    # the "because the units are longer, not because of a higher
    # funding rate" clause must be dropped even though the hours ratio
    # is unchanged.
    other_mask = t15["Program_ID"] == "Other 7 programs combined"
    t15.loc[other_mask, "Mean_Funded_Fraction"] = 0.60

    caption, stats = build_programs_caption(t15, t16)
    assert stats["explain_included"] is False
    assert "So funded hours follow" not in caption
    assert "because the units are longer" not in caption
    assert "Why is not confirmed." in caption
    assert "about 50 hours against 28" in caption  # observed numbers are still stated


def test_chart4_caption_drops_explain_clause_when_ratio_mismatch_too_large():
    t15 = load_t15_program_intensity().copy()
    t16 = load_t16_student_count_chance_check()
    # Keep the funded fractions close, but make the nominal-hours ratio
    # drift well away from the AHC-per-unit ratio (more than 15%
    # relative difference), so the clause must be dropped on this
    # condition alone.
    cs_mask = t15["Program_ID"] == "Community Services (3 programs)"
    t15.loc[cs_mask, "Mean_Nominal_Hours_per_Unit"] = 35.0

    caption, stats = build_programs_caption(t15, t16)
    assert stats["explain_included"] is False
    assert "So funded hours follow" not in caption
    assert "Why is not confirmed." in caption


def test_chart4_caption_uses_times_phrase_when_ratio_outside_about_twice_range():
    t15 = load_t15_program_intensity().copy()
    t16 = load_t16_student_count_chance_check()
    cs_mask = t15["Program_ID"] == "Community Services (3 programs)"
    other_mask = t15["Program_ID"] == "Other 7 programs combined"
    other_ahc_per_unit_exact = float(t15.loc[other_mask, "AHC_Funded"].iloc[0]) / float(t15.loc[other_mask, "Units"].iloc[0])
    cs_units = float(t15.loc[cs_mask, "Units"].iloc[0])
    # Push the exact AHC_Funded (not the one-decimal AHC_per_Unit column) so the
    # ratio comes out to 3.0, outside the 1.75-2.25 "about twice" band.
    t15.loc[cs_mask, "AHC_Funded"] = round(3.0 * other_ahc_per_unit_exact * cs_units)

    caption, stats = build_programs_caption(t15, t16)
    assert stats["ratio_phrase"] == "3.0 times"
    assert "3.0 times the funded hours" in caption
    assert "about twice" not in caption


def test_chart4_cer40115_note_matches_source():
    t15 = load_t15_program_intensity()
    t12b = load_t12b_by_program()

    row = t15.loc[t15["Program_ID"] == "CER40115"].iloc[0]
    label_row = t12b.loc[t12b["Program_ID"] == "CER40115"].iloc[0]
    students = int(row["Distinct_Students"])
    share = round(float(row["Share_of_Total_%"]))

    note = build_cer40115_note(t15, t12b)
    assert note == f"Bold row: {label_row['Full_Label']}, {students} students and {share}% of funded hours."
    assert note == (
        "Bold row: Certificate IV in Early Childhood Education and Care, 191 students and 15% of "
        "funded hours."
    )
    for banned in ["popular", "in demand", "most", "second"]:
        assert banned not in note.lower()


def test_chart4_figure_rows_in_funded_hours_order_and_cs_colored_in_both_panels():
    t15 = load_t15_program_intensity()
    programs = t15.loc[~t15["Program_ID"].astype(str).str.contains(" ")]
    expected_order = programs.sort_values("AHC_Funded", ascending=False)["Short_Label"].tolist()
    expected_is_cs = programs.sort_values("AHC_Funded", ascending=False)["Industry"].eq("Community Services").tolist()

    fig = build_programs_figure(t15)
    students_trace, share_trace = fig.data[0], fig.data[1]

    assert list(students_trace.y) == expected_order
    assert list(share_trace.y) == expected_order

    from lib.theme import GREY_MID, OCHRE

    expected_colors = [OCHRE if is_cs else GREY_MID for is_cs in expected_is_cs]
    assert list(students_trace.marker.color) == expected_colors
    assert list(share_trace.marker.color) == expected_colors

    # Both panels' bars start at zero.
    assert fig.layout.xaxis.range[0] == 0
    assert fig.layout.xaxis2.range[0] == 0

    # The right panel's y-axis is fully hidden, not just its tick labels.
    assert fig.layout.yaxis2.visible is False


def test_chart4_figure_row_height_increased_about_40_percent_with_a_larger_bar_gap():
    from lib.chart_programs import BAR_GAP, BOTTOM_MARGIN, ROW_HEIGHT, TOP_MARGIN

    t15 = load_t15_program_intensity()
    fig = build_programs_figure(t15)

    assert 1.35 <= ROW_HEIGHT / 32 <= 1.45  # "about 40%" taller than the original 32px rows
    assert fig.layout.height == TOP_MARGIN + ROW_HEIGHT * 10 + BOTTOM_MARGIN
    assert fig.layout.bargap == BAR_GAP
    assert BAR_GAP > 0.2  # a deliberately larger gap than Plotly's own default


def test_chart4_figure_row_labels_are_dark_text_with_grey_industry_and_cer40115_bold():
    t15 = load_t15_program_intensity()
    fig = build_programs_figure(t15)
    row_label_anns = [a for a in fig.layout.annotations if a.text not in ("Students", "Share of funded hours")]
    assert len(row_label_anns) == 10

    bold_anns = [a for a in row_label_anns if a.text.startswith("<b>")]
    assert len(bold_anns) == 1
    assert "Cert IV Early Childhood" in bold_anns[0].text  # CER40115's short label

    for ann in row_label_anns:
        assert "<span style=" in ann.text  # the industry sub-line is present and styled
        assert ann.yanchor == "middle"  # the two-line label is centred on its own bar, not top/bottom anchored


def test_chart4_table_html_has_10_rows_matching_source_sorted_by_funded_hours():
    t15 = load_t15_program_intensity()
    t12b = load_t12b_by_program()
    html = build_programs_table_html(t15, t12b)

    assert html.count("<tr") == 1 + 10  # one header row, 10 body rows, no inner-scroll cap

    programs = t15.loc[~t15["Program_ID"].astype(str).str.contains(" ")].merge(
        t12b[["Program_ID", "Full_Label"]], on="Program_ID", how="left"
    )
    programs = programs.sort_values("AHC_Funded", ascending=False)

    for _, row in programs.iterrows():
        assert row["Full_Label"] in html
        assert f"{int(row['Distinct_Students']):,}" in html
        assert f"{int(row['Units']):,}" in html
        assert f"{int(row['AHC_Funded']):,}" in html
        assert f">{row['Share_of_Total_%']:.1f}<" in html
        assert f">{row['AHC_per_Unit']:.1f}<" in html

    from lib.theme import OCHRE_LIGHT_TINT

    assert html.count(OCHRE_LIGHT_TINT) == 3  # exactly the 3 Community Services rows

    # Text columns left-aligned, numeric columns right-aligned.
    program_header = [h for h in html.split("<th") if "Program<" in h][0]
    assert "text-align:left" in program_header
    students_header = [h for h in html.split("<th") if "Students<" in h][0]
    assert "text-align:right" in students_header


def test_t17a_located_by_content_and_totals_match_existing_tables():
    industry_outcome = find_industry_outcome()
    assert len(industry_outcome) == 42  # 7 industries x 6 outcome groups

    t17a = load_t17a_ahc_by_industry_outcome()
    t12a = load_t12a_by_industry()
    assert t17a["AHC_Funded"].sum() == 172794

    t12a_totals = t12a.set_index("Industry")["AHC_Funded"]
    for industry, grp in t17a.groupby("Industry"):
        assert grp["AHC_Funded"].sum() == t12a_totals.loc[industry]

    expected_outcome_totals = {
        "Achieved": 90449,
        "Not achieved": 36763,
        "Withdrawn": 25318,
        "Continuing": 18604,
        "Learner support": 1660,
        "Not funded / not started": 0,
    }
    for group, expected in expected_outcome_totals.items():
        assert t17a.loc[t17a["Outcome_Group"] == group, "AHC_Funded"].sum() == expected

    for industry, grp in t17a.groupby("Industry"):
        assert grp["Not_Completed_Share_%"].nunique() == 1


def test_t17b_no_longer_exists_anywhere():
    from pathlib import Path

    import lib.data_access as data_access

    root = Path(__file__).resolve().parent.parent

    assert not (root / "outputs" / "analysis_tables" / "t17b_ahc_by_stream_industry.csv").exists()
    assert not (root / "app" / "data" / "t17b_ahc_by_stream_industry.csv").exists()

    assert not hasattr(data_access, "find_stream_industry")
    assert not hasattr(data_access, "load_t17b_ahc_by_stream_industry")

    assert "t17b" not in (root / "outputs" / "analysis_summary.md").read_text().lower()
    assert "t17b" not in (root / "scripts" / "sync_app_data.py").read_text().lower()
    assert "t17b" not in (root / "scripts" / "analysis_tables.py").read_text().lower()


def test_title_funding_outcome_used_by_funding_vs_outcome_section():
    t06a = find_stream_outcome()
    t06c = find_withdrawn_notachieved_by_funded_flag()
    assert title_funding_outcome(t06a, t06c) == "36% of funded hours went to units not achieved or withdrawn"


def test_title_funding_outcome_raises_below_25_percent():
    broken_t06a = pd.DataFrame(
        {
            "Outcome_Group": ["Achieved", "Withdrawn", "Not achieved"],
            "AHC_Funded": [800, 100, 100],
        }
    )
    broken_t06c = pd.DataFrame({"Funded_Flag": ["Y"], "AHC_Funded": [200]})
    with pytest.raises(TitleAssumptionError):
        title_funding_outcome(broken_t06a, broken_t06c)


def test_funding_outcome_links_conservation_and_no_bad_values():
    t06a = find_stream_outcome()
    links, stream_order, stream_totals = _fo_links(t06a)

    assert all(link["value"] > 0 for link in links)
    assert stream_order == stream_totals.sort_values(ascending=False).index.tolist()

    outflow = {}
    for link in links:
        outflow[link["source"]] = outflow.get(link["source"], 0) + link["value"]
    for stream in stream_order:
        assert abs(outflow[stream] - stream_totals[stream]) < 1

    outcome_totals = {}
    for link in links:
        outcome_totals[link["target"]] = outcome_totals.get(link["target"], 0) + link["value"]
    assert abs(outcome_totals["Achieved"] - 90449) < 1
    assert abs(outcome_totals["Not achieved"] - 36763) < 1
    assert abs(outcome_totals["Withdrawn"] - 25318) < 1
    assert abs(outcome_totals["Continuing or learner support"] - (18604 + 1660)) < 1
    assert "Not funded / not started" not in outcome_totals


def test_funding_outcome_figure_uses_fixed_arrangement_and_outcome_order():
    t06a = find_stream_outcome()
    fig = build_fo_figure(t06a)
    sankey = fig.data[0]

    assert sankey.arrangement == "fixed"
    assert sankey.node.x is not None and sankey.node.y is not None
    assert all(v > 0 for v in sankey.link.value)
    # Native node text is hidden - every row/industry/outcome label is drawn as an annotation instead.
    assert all(label == "" for label in sankey.node.label)

    # The four outcome nodes keep the fixed semantic order (not sorted by size): their labels,
    # drawn as annotations (long names may carry an explicit <br> break), must appear in exactly
    # this order among the annotations.
    label_annotations = [a.text.replace("<br>", " ") for a in fig.layout.annotations]
    label_annotations = [t for t in label_annotations if t.split(" ")[0] in ("Achieved", "Continuing", "Not", "Withdrawn")]
    outcome_order_found = [name for name in OUTCOME_NODE_ORDER if any(text.startswith(name) for text in label_annotations)]
    assert outcome_order_found == OUTCOME_NODE_ORDER


def test_funding_outcome_figure_node_colours_ochre_only_on_not_achieved_and_withdrawn():
    from lib.theme import OCHRE

    t06a = find_stream_outcome()
    fig = build_fo_figure(t06a)
    sankey = fig.data[0]
    colors = list(sankey.node.color)
    assert colors.count(OCHRE) == 2
    assert colors.count("#9AA0A6") == len(colors) - 2

    link_colors = set(sankey.link.color)
    assert len(link_colors) == 2  # exactly the grey and ochre rgba strings, nothing else
    assert any("163,90,22" in c for c in link_colors)
    assert any("201,205,210" in c for c in link_colors)


def test_funding_outcome_figure_has_bracket_shape_and_labels_use_hidden_axis():
    t06a = find_stream_outcome()
    fig = build_fo_figure(t06a)

    assert len(fig.layout.shapes) == 1
    bracket = fig.layout.shapes[0]
    assert bracket.xref == "x" and bracket.yref == "y"  # axis-domain-relative, not 'paper'

    label_annotations = [a for a in fig.layout.annotations if a.xref == "x"]
    assert len(label_annotations) == 5 + 4 + 1  # 5 streams, 4 outcomes, 1 bracket text
    for ann in label_annotations:
        assert ann.yref == "y"

    assert fig.layout.xaxis.visible is False
    assert fig.layout.yaxis.visible is False


def test_funding_outcome_margins_and_height_leave_room_for_labels():
    t06a = find_stream_outcome()
    fig = build_fo_figure(t06a)
    assert fig.layout.margin.l == 210
    assert fig.layout.margin.r == 380
    assert fig.layout.margin.t >= 12
    assert fig.layout.margin.b >= 12
    assert fig.layout.height >= 440


def test_funding_outcome_long_outcome_label_has_explicit_line_break():
    # Plotly annotation width does not auto-wrap text (it only clips
    # anything wider than the given box), so a label this long needs
    # an explicit <br>, not just a width setting, or it gets cut off.
    t06a = find_stream_outcome()
    fig = build_fo_figure(t06a)
    matches = [a.text for a in fig.layout.annotations if "Continuing" in a.text]
    assert len(matches) == 1
    assert matches[0].startswith("Continuing or<br>learner support")
    assert matches[0].count("<br>") == 1


def test_funding_outcome_stream_nodes_have_a_visible_gap_and_keep_order_and_centring():
    from lib.chart_funding_outcome import BASE_HEIGHT, NODE_Y_MARGIN, STREAM_GAP_FRACTION, _figure_height, _stream_y_positions

    t06a = find_stream_outcome()
    links, stream_order, stream_totals = _fo_links(t06a)
    n = len(stream_order)
    figure_height = _figure_height(n)

    # The figure grew by exactly (n - 1) gaps worth of BASE_HEIGHT pixels.
    assert figure_height == BASE_HEIGHT + (n - 1) * STREAM_GAP_FRACTION * BASE_HEIGHT

    positions = _stream_y_positions(n, figure_height)
    assert len(positions) == n
    assert positions == sorted(positions)  # largest-funded-hours-first order is preserved (top to bottom)

    # Centring: first/last node sit the same NODE_Y_MARGIN-of-BASE_HEIGHT pixel distance from
    # the edge as before, now expressed as a (slightly smaller) fraction of the taller figure.
    margin_px = NODE_Y_MARGIN * BASE_HEIGHT
    assert abs(positions[0] * figure_height - margin_px) < 0.01
    assert abs((1 - positions[-1]) * figure_height - margin_px) < 0.01
    assert positions[0] * figure_height >= 12
    assert (1 - positions[-1]) * figure_height >= 12

    # A real gap between adjacent node centres, in excess of even spacing, of about 2.5% of
    # BASE_HEIGHT - this is the actual fix, not just a bigger figure.
    actual_step_px = (positions[1] - positions[0]) * figure_height
    natural_step_px = (BASE_HEIGHT - 2 * margin_px) / (n - 1)
    assert abs((actual_step_px - natural_step_px) - STREAM_GAP_FRACTION * BASE_HEIGHT) < 0.01

    fig = build_fo_figure(t06a)
    from lib.chart_funding_outcome import HOVER_CLIP_FIX_PX

    # The plot area (figure_height) is unchanged; HOVER_CLIP_FIX_PX is added to both the
    # overall height and the top margin, so the Sankey itself stays the same size and the
    # extra space is genuinely empty headroom above the topmost node, for its hover label.
    assert fig.layout.height == figure_height + HOVER_CLIP_FIX_PX
    assert fig.layout.margin.t == 20 + HOVER_CLIP_FIX_PX
    assert fig.layout.margin.b == 20
    plot_area_height = fig.layout.height - fig.layout.margin.t - fig.layout.margin.b
    assert plot_area_height == figure_height - 20 - 20


def test_build_caption_matches_target_wording_and_numbers():
    t06a = find_stream_outcome()
    t06c = find_withdrawn_notachieved_by_funded_flag()
    t17a = find_industry_outcome()

    total = t06a["AHC_Funded"].sum()
    not_achieved = t06a.loc[t06a["Outcome_Group"] == "Not achieved", "AHC_Funded"].sum()
    withdrawn = t06a.loc[t06a["Outcome_Group"] == "Withdrawn", "AHC_Funded"].sum()
    not_completed = not_achieved + withdrawn

    caption, stats = build_fo_caption(t06a, t06c, t17a)
    assert stats["low_industry"] == "Business"
    assert stats["high_industry"] == "Primary Industry"
    assert stats["funded_in_full_included"] is True
    # p is now the exact share recomputed from AHC_Funded (not the one-decimal
    # Share_% column), so it is close to but not exactly 99.0.
    assert abs(stats["p"] - 99.00774794220455) < 1e-6

    assert caption == (
        "**99% of the hours on units not achieved or withdrawn are recorded as fully funded.**\n\n"
        "The share ranges from 33% to 38% across funding streams and 34% to 40% across industries.\n\n"
        "To size the cost, payment records for these units are the next thing to obtain."
    )
    for banned in [
        "pair", "comparable", "aggregate", "over-delivery", "exceeds mandate",
        "workbook has no payment data", "cannot say", "analysed as supplied",
    ]:
        assert banned not in caption.lower()


def test_build_caption_range_sentence_uses_exact_stream_shares():
    t06c = find_withdrawn_notachieved_by_funded_flag()
    t17a = find_industry_outcome()
    # Exact not-completed shares per stream (Not achieved + Withdrawn): 30, 50, 50, 5, 20.
    t06a = pd.DataFrame(
        {
            "Funding_Source": ["11J"] * 2 + ["11K"] * 2 + ["11N"] * 2 + ["11V"] * 2 + ["FFT"] * 2,
            "Outcome_Group": ["Achieved", "Not achieved", "Achieved", "Withdrawn", "Achieved", "Not achieved",
                              "Achieved", "Withdrawn", "Achieved", "Not achieved"],
            "AHC_Funded": [700, 300, 700, 300, 500, 500, 950, 50, 800, 200],
            "Share_within_Stream_exact": [70.0, 30.0, 50.0, 50.0, 50.0, 50.0, 95.0, 5.0, 80.0, 20.0],
        }
    )
    caption, stats = build_fo_caption(t06a, t06c, t17a)
    assert stats["stream_shares"] == {"11J": 30.0, "11K": 50.0, "11N": 50.0, "11V": 5.0, "FFT": 20.0}
    assert "The share ranges from 5% to 50% across funding streams and 34% to 40% across industries." in caption
    assert "The split is similar" not in caption


def test_build_caption_funded_in_full_share_reflects_the_data_even_when_low():
    t06a = find_stream_outcome()
    t17a = find_industry_outcome()
    broken_t06c = pd.DataFrame({"Funded_Flag": ["Y", "15%_only"], "AHC_Funded": [50, 50], "Share_%": [50.0, 50.0]})
    caption, stats = build_fo_caption(t06a, broken_t06c, t17a)
    assert stats["funded_in_full_included"] is False
    assert "50% of the hours on units not achieved or withdrawn are recorded as fully funded" in caption
    assert "To size the cost, payment records for these units are the next thing to obtain." in caption


def test_build_caption_industry_range_reacts_to_t17a_changes():
    t06a = find_stream_outcome()
    t06c = find_withdrawn_notachieved_by_funded_flag()
    t17a = find_industry_outcome().copy()
    # Push Foundation Skills' exact not-completed share below Business's
    # 34.1%, so it must become the new low end of the range instead.
    mask = t17a["Industry"] == "Foundation Skills"
    t17a.loc[mask, "Not_Completed_Share_exact"] = 30.0

    caption, stats = build_fo_caption(t06a, t06c, t17a)
    assert stats["low_industry"] == "Foundation Skills"
    assert "The share ranges from 33% to 38% across funding streams and 30% to 40% across industries." in caption


def test_build_table_html_matches_source():
    t06a = find_stream_outcome()
    html = build_fo_table_html(t06a)
    assert html.count("<tr") == 1 + 5  # one header, 5 streams

    for stream, grp in t06a.groupby("Funding_Source"):
        achieved = grp.loc[grp["Outcome_Group"] == "Achieved", "AHC_Funded"].sum()
        not_completed = grp.loc[grp["Outcome_Group"].isin(["Not achieved", "Withdrawn"]), "AHC_Funded"].sum()
        assert f"{achieved:,.0f}" in html
        assert f"{not_completed:,.0f}" in html

    assert "Not completed" in html
    assert "Share of all funded hours (%)" in html


def test_chart6_tables_located_by_content_not_filename():
    completion = find_completion_by_group()
    assert {"Dimension", "Group", "Rate_%", "CI_Lower", "CI_Upper", "Units", "Students"}.issubset(completion.columns)
    assert len(completion) == 1 + 5 + 8 + 3 + 7 + 3  # Overall + Funding_Source + Provider_ID + Remoteness + Industry + Delivery_Year

    omnibus = find_completion_omnibus_tests()
    assert {"Dimension", "Omnibus_GEE_p_value", "Spread_pp"}.issubset(omnibus.columns)
    assert set(omnibus["Dimension"]) == {"Funding_Source", "Provider_ID", "Remoteness", "Industry"}


def test_chart6_row_order_is_funded_hours_for_streams_id_for_providers_fixed_for_regions_not_rate():
    t07 = find_completion_by_group()
    t06a = find_stream_outcome()
    from lib.chart_completion import REGION_ORDER, _rows

    rows, _, _, _ = _rows(t07, t06a)
    assert len(rows) == 16
    stream_rows = [r for r in rows if r["dimension"] == "Funding_Source"]
    provider_rows = [r for r in rows if r["dimension"] == "Provider_ID"]
    region_rows = [r for r in rows if r["dimension"] == "Remoteness"]

    assert [r["group"] for r in rows] == (
        [r["group"] for r in stream_rows] + [r["group"] for r in provider_rows] + [r["group"] for r in region_rows]
    )

    expected_stream_order = (
        t06a.groupby("Funding_Source")["AHC_Funded"].sum().sort_values(ascending=False).index.tolist()
    )
    assert [r["group"] for r in stream_rows] == expected_stream_order
    # Not sorted by rate: the funded-hours order and the rate order differ for the real data.
    assert [r["group"] for r in stream_rows] != [
        r["group"] for r in sorted(stream_rows, key=lambda r: r["rate"], reverse=True)
    ]

    assert [r["group"] for r in provider_rows] == sorted(r["group"] for r in provider_rows)
    assert [r["group"] for r in provider_rows] == [f"P{str(i).zfill(3)}" for i in range(1, 9)]

    assert [r["group"] for r in region_rows] == REGION_ORDER == ["Urban", "Regional", "Remote"]
    # Not sorted by rate: Regional (lowest rate) sits before Remote (highest rate) in the fixed order.
    assert [r["group"] for r in region_rows] != [
        r["group"] for r in sorted(region_rows, key=lambda r: r["rate"], reverse=True)
    ]


def test_chart6_ochre_rule_only_fires_when_interval_entirely_outside_overall():
    import pandas as pd

    from lib.chart_completion import _rows

    t06a = find_stream_outcome()
    # Real data: no row should qualify.
    t07_real = find_completion_by_group()
    rows, overall_low, overall_high, _ = _rows(t07_real, t06a)
    assert overall_low == 59.0 and overall_high == 61.8
    assert not any(r["is_ochre"] for r in rows)
    assert completion_any_row_ochre(t07_real, t06a) is False

    # Altered data: push 11N's whole interval below the overall interval - must turn ochre.
    t07_broken = t07_real.copy()
    mask_below = (t07_broken["Dimension"] == "Funding_Source") & (t07_broken["Group"] == "11N")
    t07_broken.loc[mask_below, ["Rate_%", "CI_Lower", "CI_Upper"]] = [50.0, 48.0, 52.0]
    rows_broken, _, _, _ = _rows(t07_broken, t06a)
    by_group = {r["group"]: r for r in rows_broken}
    assert by_group["11N"]["is_ochre"] is True
    assert all(r["is_ochre"] is False for g, r in by_group.items() if g != "11N")
    assert completion_any_row_ochre(t07_broken, t06a) is True

    # A row that merely does not overlap the overall RATE, but still overlaps the overall
    # INTERVAL, must not turn ochre - the rule is about the whole interval, not the point rate.
    t07_touching = t07_real.copy()
    mask_touch = (t07_touching["Dimension"] == "Funding_Source") & (t07_touching["Group"] == "11N")
    t07_touching.loc[mask_touch, ["Rate_%", "CI_Lower", "CI_Upper"]] = [55.0, 54.0, 59.0]  # upper touches overall_low exactly
    rows_touch, _, _, _ = _rows(t07_touching, t06a)
    assert next(r for r in rows_touch if r["group"] == "11N")["is_ochre"] is False


def test_chart6_figure_axis_range_and_shapes():
    t07 = find_completion_by_group()
    t06a = find_stream_outcome()
    fig = build_completion_figure(t07, t06a)

    assert fig.layout.xaxis.range == (50, 70)
    assert fig.layout.xaxis.dtick == 5
    assert fig.layout.xaxis.ticksuffix == "%"
    # Ochre band, ochre dashed overall line, and one grey separator per group gap (2, for 3 groups).
    assert len(fig.layout.shapes) == 4

    band = fig.layout.shapes[0]
    assert band.type == "rect"
    assert band.x0 == 59.0 and band.x1 == 61.8
    assert band.yref == "paper" and band.y0 == 0 and band.y1 == 1

    separators = [s for s in fig.layout.shapes if s.type == "line" and s.yref == "y"]
    assert len(separators) == 2
    assert {s.y0 for s in separators} == {"__gap_before_Provider_ID__", "__gap_before_Remoteness__"}

    # 16 rows (5 streams + 8 providers + 3 regions): one CI-line trace per row, plus one combined dot trace.
    assert len(fig.data) == 16 + 1
    assert fig.layout.margin.l == 220
    assert fig.layout.margin.r == 200
    assert fig.layout.yaxis.visible is False


def test_chart6_figure_row_labels_and_group_headers_present():
    t07 = find_completion_by_group()
    t06a = find_stream_outcome()
    fig = build_completion_figure(t07, t06a)

    texts = [a.text for a in fig.layout.annotations]
    assert any(t == "<b>Funding stream</b>" for t in texts)
    assert any(t == "<b>Provider</b>" for t in texts)
    assert any("11K User Choice" in t for t in texts)
    assert any(t == "P001" for t in texts)
    assert any(t.startswith("Overall 60%") for t in texts)
    assert any(t.startswith("Axis shows 50% to 70%, not zero") for t in texts)


def test_build_completion_caption_matches_target_wording_and_numbers():
    from lib.numfmt import round_whole

    t07 = find_completion_by_group()
    t07_omnibus = find_completion_omnibus_tests()

    overall = t07.loc[t07["Dimension"] == "Overall"].iloc[0]
    streams = t07.loc[t07["Dimension"] == "Funding_Source"]
    providers = t07.loc[t07["Dimension"] == "Provider_ID"]
    regions = t07.loc[t07["Dimension"] == "Remoteness"]

    caption, stats = build_completion_caption(t07, t07_omnibus, find_sensitivity())
    assert stats["overall_rate"] == 60
    assert stats["stream_min"] == 57 and stats["stream_max"] == 62
    assert stats["provider_min"] == 58 and stats["provider_max"] == 64
    assert stats["region_min"] == 58 and stats["region_max"] == 62
    assert stats["no_basis_included"] is True
    assert stats["remote_sentence_included"] is True

    # Independent check, from Rate_exact (never the one-decimal Rate_%/CI columns),
    # so this test cannot pass just because chart_completion.py's own rounding agrees
    # with itself.
    assert caption == (
        f"**About {round_whole(overall['Rate_exact'])}% of units were achieved overall (between "
        f"{round_whole(overall['Lower_exact'])}% and {round_whole(overall['Upper_exact'])}%).**\n\n"
        f"Rates range from {round_whole(streams['Rate_exact'].min())}% to {round_whole(streams['Rate_exact'].max())}% "
        f"across funding streams, {round_whole(providers['Rate_exact'].min())}% to "
        f"{round_whole(providers['Rate_exact'].max())}% across providers and "
        f"{round_whole(regions['Rate_exact'].min())}% to {round_whole(regions['Rate_exact'].max())}% "
        f"across regions.\n\n"
        "No funding stream, provider or region stands out, so the data gives no basis for ranking them "
        "on completion. Remote areas are not behind: 62% against 59% in Urban and 58% "
        "in Regional."
    )
    assert stats["continuing_as_not_completed"] == 53
    assert stats["industry_p"] == pytest.approx(0.6641, abs=1e-4)
    assert stats["stats_line"] == (
        "For readers who want the statistics: the tests give p = 0.23 for streams, 0.27 for providers, "
        "0.12 for regions and 0.66 for industries. If groups did not really differ, differences this "
        "large would turn up about 23, 27, 12 and 66 times in 100."
    )
    assert caption.startswith("**About 60% of units were achieved overall (between 59% and 62%).**")
    # The regression this whole fix was for: Urban must read 59%, not 60%.
    assert "59% in Urban" in caption
    assert "60% in Urban" not in caption


def test_build_completion_caption_drops_no_basis_sentence_when_a_dimension_is_significant():
    t07 = find_completion_by_group()
    broken_omnibus = pd.DataFrame(
        {
            "Dimension": ["Funding_Source", "Provider_ID", "Remoteness", "Industry"],
            "Omnibus_GEE_p_value": [0.5, 0.012, 0.5, 0.5],
        }
    )
    caption, stats = build_completion_caption(t07, broken_omnibus, find_sensitivity())
    assert stats["no_basis_included"] is False
    assert "no basis for ranking" not in caption
    assert "providers (p = 0.01)" in caption
    assert "funding streams" not in caption.split("\n\n")[2].split(" Remote areas are not behind")[0]
    # The Remote sentence is independent of the "no basis" clause and should still appear,
    # since remoteness's own p-value (0.5) is still at least 0.05.
    assert stats["remote_sentence_included"] is True
    assert "Remote areas are not behind" in caption


def test_build_completion_caption_remote_sentence_switches_off_when_remote_is_lower():
    t07 = find_completion_by_group().copy()
    t07_omnibus = find_completion_omnibus_tests()
    mask = (t07["Dimension"] == "Remoteness") & (t07["Group"] == "Remote")
    # The comparison now reads Rate_exact (not the display Rate_% column), so that is
    # what has to change to move the logic - Urban/Regional's exact rates are ~59.5/58.5.
    t07.loc[mask, "Rate_exact"] = 50.0
    t07.loc[mask, "Rate_%"] = 50.0
    caption, stats = build_completion_caption(t07, t07_omnibus, find_sensitivity())
    assert stats["remote_sentence_included"] is False
    assert "There is no sign that completion is lower in Remote areas" not in caption


def test_build_completion_caption_remote_sentence_switches_off_when_remoteness_p_below_0_05():
    t07 = find_completion_by_group()
    broken_omnibus = pd.DataFrame(
        {
            "Dimension": ["Funding_Source", "Provider_ID", "Remoteness", "Industry"],
            "Omnibus_GEE_p_value": [0.5, 0.5, 0.04, 0.5],
        }
    )
    caption, stats = build_completion_caption(t07, broken_omnibus, find_sensitivity())
    assert stats["remote_sentence_included"] is False
    assert "There is no sign that completion is lower in Remote areas" not in caption
    # This also makes regions the significant dimension, so the "no basis" sentence drops too.
    assert stats["no_basis_included"] is False
    assert "regions (p = 0.04)" in caption


def test_build_completion_table_html_has_26_group_rows_and_delivery_year_has_no_p_value():
    t07 = find_completion_by_group()
    t07_omnibus = find_completion_omnibus_tests()
    t06a = find_stream_outcome()

    html = build_completion_table_html(t07, t07_omnibus, t06a)
    # 1 header row + 5 section header rows + 26 group rows (5 + 8 + 7 + 3 + 3).
    assert html.count("<tr") == 1 + 5 + 26

    assert "Delivery year (context only, no test run)" in html
    for dim, label in [
        ("Funding_Source", "Funding stream"),
        ("Provider_ID", "Provider"),
        ("Industry", "Industry"),
        ("Remoteness", "Remoteness"),
    ]:
        p = float(t07_omnibus.loc[t07_omnibus["Dimension"] == dim, "Omnibus_GEE_p_value"].iloc[0])
        assert f"{label} (test for any difference: p = {p:.2f})" in html

    for _, row in t07.loc[t07["Dimension"] != "Overall"].iterrows():
        assert f"{int(row['Units']):,}" in html
        assert f">{float(row['Rate_%']):.1f}<" in html

    # Stream names use the vocab stream key, not the bare code.
    assert "11K User Choice" in html
    # Text columns left-aligned, numeric columns right-aligned.
    group_header = [h for h in html.split("<th") if "Group<" in h][0]
    assert "text-align:left" in group_header
    units_header = [h for h in html.split("<th") if "Units<" in h][0]
    assert "text-align:right" in units_header


def test_chart6_group_headers_do_not_share_a_row_position_with_any_data_row_label():
    t07 = find_completion_by_group()
    t06a = find_stream_outcome()
    from lib.chart_completion import CHARTED_DIMENSIONS, GROUP_HEADER_LABELS, _category_layout, _rows

    rows, _, _, _ = _rows(t07, t06a)
    categories, header_category, gap_category = _category_layout(rows)

    row_labels = {r["label"] for r in rows}
    header_labels = set(header_category.values())
    gap_labels = set(gap_category.values())

    # No header or gap placeholder collides with any real row's label - each occupies its own
    # distinct category, so a header can never land on the same y-position as a data row.
    assert header_labels.isdisjoint(row_labels)
    assert gap_labels.isdisjoint(row_labels)
    assert header_labels.isdisjoint(gap_labels)

    # Every category in the full array is unique (categoryarray cannot have duplicate entries).
    assert len(categories) == len(set(categories))
    assert len(categories) == len(rows) + len(CHARTED_DIMENSIONS) + (len(CHARTED_DIMENSIONS) - 1)

    # Each group header sits immediately before that group's first row, and (for every group
    # after the first) immediately after a dedicated blank gap slot.
    for i, dimension in enumerate(CHARTED_DIMENSIONS):
        header_pos = categories.index(header_category[dimension])
        first_row_pos = categories.index(next(r["label"] for r in rows if r["dimension"] == dimension))
        assert first_row_pos == header_pos + 1
        if i > 0:
            gap_pos = categories.index(gap_category[dimension])
            assert header_pos == gap_pos + 1


def test_completion_table_has_the_two_new_note_lines_in_home():
    from pathlib import Path

    home_text = (Path(__file__).resolve().parent.parent / "app" / "Home.py").read_text()
    completion_section = home_text.split('st.markdown("## Completion")')[1]
    completion_section = completion_section.split("REMAINING_SECTIONS")[0]
    # Adjacent string literals in the source are split across lines, so check each half
    # rather than the single joined sentence.
    assert "Whole-number figures in the chart are rounded from unrounded values" in completion_section
    assert "differ" in completion_section and "slightly from the one-decimal figures here." in completion_section
    assert "Students are counted within" in completion_section
    assert "each group, so one student can appear in several groups." in completion_section
    assert "build_completion_table_lead_line" in completion_section


def test_round_whole_basic_cases():
    from lib.numfmt import round_whole

    assert round_whole(59.4988) == 59
    assert round_whole(58.5) == 59  # half up, not half to even (Python's round(58.5) is 58)
    assert round_whole(59.5) == 60
    assert round_whole(0.4999) == 0
    assert round_whole(100.0) == 100


def test_round_dp_basic_cases():
    from lib.numfmt import round_dp

    assert round_dp(58.549, 1) == 58.5
    assert round_dp(58.55, 1) == 58.6  # half up, not half to even (Python's round(58.55,1) is 58.5)
    assert round_dp(-4.4281, 1) == -4.4  # the Remote-region regression this fix covers
    assert round_dp(0.005, 2) == 0.01  # half up at two decimals
    assert round_dp(0.004999, 2) == 0.0
    assert round_dp(100.0, 1) == 100.0


def test_chart6_urban_rate_is_59_not_60():
    """The regression case this whole fix was for: Urban's true rate is
    736/1237 = 59.4988%, stored as the one-decimal display value 59.5 -
    which must display as 59, not 60."""
    t07 = find_completion_by_group()
    t06a = find_stream_outcome()

    urban = t07.loc[(t07["Dimension"] == "Remoteness") & (t07["Group"] == "Urban")].iloc[0]
    assert urban["Rate_%"] == 59.5
    assert abs(urban["Rate_exact"] - 59.4988) < 0.001
    assert int(urban["Achieved_units"]) == 736
    assert int(urban["Units"]) == 1237

    from lib.numfmt import round_whole

    assert round_whole(float(urban["Rate_exact"])) == 59

    fig = build_completion_figure(t07, t06a)
    urban_label = next(
        a.text for a in fig.layout.annotations if a.y == "Urban" and a.xanchor == "left" and "%" in a.text
    )
    assert urban_label.startswith("59%")

    caption, _ = build_completion_caption(t07, find_completion_omnibus_tests(), find_sensitivity())
    assert "59% in Urban" in caption
    assert "60% in Urban" not in caption


def test_no_module_in_app_lib_uses_bare_round_or_point_zero_f():
    """round_whole() (lib/numfmt.py) must be the only way any module in
    app/lib turns a value into a whole-number figure. A bare round(x)
    or round(x, 0) call, or an ':.0f' format spec, anywhere else in
    app/lib is exactly the bug this module exists to prevent (rounding
    an already-rounded one-decimal display value, or using a rounding
    rule other than round_whole's), so any such use fails this test."""
    import ast
    from pathlib import Path

    lib_dir = Path(__file__).resolve().parent.parent / "app" / "lib"
    violations = []

    for path in sorted(lib_dir.glob("*.py")):
        if path.name == "numfmt.py":
            continue  # round_whole's own implementation, uses Decimal, not round()
        text = path.read_text()

        for lineno, line in enumerate(text.splitlines(), start=1):
            if ":.0f" in line:
                violations.append(f"{path.name}:{lineno}: uses ':.0f' instead of round_whole()")

        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "round"):
                continue
            is_whole_number_round = len(node.args) == 1 and not node.keywords
            if not is_whole_number_round and len(node.args) == 2 and isinstance(node.args[1], ast.Constant):
                is_whole_number_round = node.args[1].value == 0
            if is_whole_number_round:
                violations.append(f"{path.name}:{node.lineno}: bare round() instead of round_whole()")

    assert not violations, "Found disallowed whole-number rounding:\n" + "\n".join(violations)


def test_chart7_tables_located_by_content_not_filename():
    t09a = find_atsi_completion()
    assert len(t09a) == 18  # 9 comparisons x 2 ATSI levels
    assert {"Dimension", "Group", "ATSI", "Rate_exact", "Lower_exact", "Upper_exact", "Achieved_units"}.issubset(
        t09a.columns
    )

    t09b = find_atsi_gap()
    assert len(t09b) == 9
    assert {"Dimension", "Group", "Gap_exact", "Lower_exact", "Upper_exact"}.issubset(t09b.columns)

    t09c = find_atsi_adjusted_model()
    assert {"Metric", "Value_exact"}.issubset(t09c.columns)
    assert t09c["Metric"].str.contains("ATSI odds ratio", regex=False).any()


def test_chart7_figure_axis_and_structure():
    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    t09c = find_atsi_adjusted_model()
    fig = build_equity_figure(t09a, t09b, t09c)

    assert fig.layout.xaxis.range == (50, 70)
    assert fig.layout.xaxis.dtick == 5
    assert fig.layout.xaxis.ticksuffix == "%"
    assert fig.layout.yaxis.visible is False
    assert fig.layout.margin.l == 230
    assert fig.layout.margin.r == 260

    texts = [a.text for a in fig.layout.annotations]
    assert any(t == "58.6%" for t in texts)
    assert any(t == "61.4%" for t in texts)
    assert any(t == "58.4%" for t in texts)
    assert any(t == "61.5%" for t in texts)
    assert any("Unadjusted" in t and "as recorded" in t for t in texts)
    assert any("Adjusted for provider" in t for t in texts)
    assert any(t.startswith("Axis shows 50% to 70%, not zero") for t in texts)
    assert any("2.8 points lower" in t for t in texts)
    assert any("3.1 points lower" in t for t in texts)
    assert any("odds ratio 0.88" in t for t in texts)


def _chart7_figure():
    return build_equity_figure(find_atsi_completion(), find_atsi_gap(), find_atsi_adjusted_model())


def test_chart7_figure_row1_has_intervals_row2_does_not():
    from lib.chart_equity import ROW1_ATSI_Y, ROW1_OTHER_Y, ROW2_ATSI_Y, ROW2_OTHER_Y
    from lib.theme import GREY_LIGHT

    fig = _chart7_figure()

    # Two step connectors (one per row) plus two interval lines (row 1 only) = 4 line traces.
    line_traces = [tr for tr in fig.data if tr.mode == "lines"]
    assert len(line_traces) == 4

    row1_interval_atsi = [tr for tr in line_traces if list(tr.y) == [ROW1_ATSI_Y, ROW1_ATSI_Y]]
    row1_interval_other = [tr for tr in line_traces if list(tr.y) == [ROW1_OTHER_Y, ROW1_OTHER_Y]]
    assert len(row1_interval_atsi) == 1
    assert len(row1_interval_other) == 1
    assert row1_interval_atsi[0].line.color != GREY_LIGHT  # interval lines are not connectors

    row2_interval = [tr for tr in line_traces if tr.y[0] in (ROW2_ATSI_Y, ROW2_OTHER_Y) and tr.y[0] == tr.y[-1]]
    assert row2_interval == []  # no row 2 interval lines

    connectors = [tr for tr in line_traces if tr.line.color == GREY_LIGHT]
    assert len(connectors) == 2
    assert {tuple(tr.y) for tr in connectors} == {
        (ROW1_ATSI_Y, 0.5, 0.5, ROW1_OTHER_Y),
        (ROW2_ATSI_Y, 2.8, 2.8, ROW2_OTHER_Y),
    }


def test_chart7_all_elements_share_one_numeric_y_scale():
    """Every trace and annotation that uses yref='y' must be a number inside
    the y-axis range. Text category names on this axis would be read as
    unmatched categories and drawn in the wrong place."""
    fig = _chart7_figure()
    bottom, top = fig.layout.yaxis.range
    assert top < bottom  # reversed: row 1 at the top

    for tr in fig.data:
        assert tr.yaxis in (None, "y")
        for y in tr.y:
            assert isinstance(y, (int, float)), f"non-numeric y on a trace: {y!r}"
            assert top <= y <= bottom

    for a in fig.layout.annotations:
        if a.yref == "y":
            assert isinstance(a.y, (int, float)), f"non-numeric annotation y: {a.y!r}"
            assert top <= a.y <= bottom

    assert len(fig.layout.shapes) == 0


def test_chart7_key_clears_value_labels():
    from lib.chart_equity import KEY_YSHIFT_PX, PX_PER_UNIT, VALUE_LABEL_HEIGHT_PX, VALUE_LABEL_YSHIFT_PX, Y_RANGE

    fig = _chart7_figure()
    key = next(a for a in fig.layout.annotations if a.yref == "paper" and "Other learners" in a.text)
    assert key.yshift == KEY_YSHIFT_PX

    # Pixel distances measured from the top of the plot area (positive = down).
    key_centre_px = -(KEY_YSHIFT_PX + VALUE_LABEL_HEIGHT_PX / 2)
    for a in fig.layout.annotations:
        if a.yref != "y" or not a.text.endswith("%"):
            continue
        dot_px = (a.y - Y_RANGE[1]) * PX_PER_UNIT
        label_centre_px = dot_px - VALUE_LABEL_YSHIFT_PX if a.yshift > 0 else dot_px + abs(VALUE_LABEL_YSHIFT_PX)
        assert abs(label_centre_px - key_centre_px) >= VALUE_LABEL_HEIGHT_PX, a.text


def test_chart7_dot_traces_carry_the_exact_source_rates():
    from lib.chart_equity import ROW1_ATSI_Y, ROW1_OTHER_Y, ROW2_ATSI_Y, ROW2_OTHER_Y

    t09a = find_atsi_completion()
    t09c = find_atsi_adjusted_model()
    fig = _chart7_figure()

    y1 = t09a.loc[(t09a["Dimension"] == "Overall") & (t09a["ATSI"] == "Y")].iloc[0]
    n1 = t09a.loc[(t09a["Dimension"] == "Overall") & (t09a["ATSI"] == "N")].iloc[0]
    pred_y = float(t09c.loc[t09c["Metric"] == "Model-predicted completion rate, ATSI = Y (%)", "Value_exact"].iloc[0])
    pred_n = float(t09c.loc[t09c["Metric"] == "Model-predicted completion rate, ATSI = N (%)", "Value_exact"].iloc[0])

    markers = [tr for tr in fig.data if tr.mode == "markers"]
    atsi, other = markers[0], markers[1]
    assert list(atsi.x) == [float(y1["Rate_exact"]), pred_y]
    assert list(atsi.y) == [ROW1_ATSI_Y, ROW2_ATSI_Y]
    assert list(other.x) == [float(n1["Rate_exact"]), pred_n]
    assert list(other.y) == [ROW1_OTHER_Y, ROW2_OTHER_Y]


def test_chart7_connectors_join_the_same_dot_positions():
    from lib.chart_equity import ROW1_ATSI_Y, ROW1_OTHER_Y, ROW2_ATSI_Y, ROW2_OTHER_Y

    fig = _chart7_figure()
    markers = [tr for tr in fig.data if tr.mode == "markers"]
    dot_xy = {(round(x, 9), y) for tr in markers for x, y in zip(tr.x, tr.y)}
    connectors = [tr for tr in fig.data if tr.mode == "lines" and len(tr.x) == 4]
    assert len(connectors) == 2
    for tr in connectors:
        assert (round(tr.x[0], 9), tr.y[0]) in dot_xy
        assert (round(tr.x[-1], 9), tr.y[-1]) in dot_xy
    assert {tr.y[0] for tr in connectors} == {ROW1_ATSI_Y, ROW2_ATSI_Y}
    assert {tr.y[-1] for tr in connectors} == {ROW1_OTHER_Y, ROW2_OTHER_Y}


def test_chart7_figure_key_is_on_paper_coordinates_and_visible():
    """The key must use xref='paper' (0 to 1 across the whole plot area),
    not xref='x' - the x-axis range is [50, 70], so x=0 under xref='x'
    would sit far outside the visible figure and never render."""
    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    t09c = find_atsi_adjusted_model()
    fig = build_equity_figure(t09a, t09b, t09c)

    key_annotations = [
        a for a in fig.layout.annotations
        if "Aboriginal and Torres Strait Islander learners" in a.text and "Other learners" in a.text
    ]
    assert len(key_annotations) == 1
    key = key_annotations[0]
    assert key.xref == "paper"
    assert key.yref == "paper"
    assert key.font.size == 13


def test_chart7_figure_margin_leaves_room_for_key():
    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    t09c = find_atsi_adjusted_model()
    fig = build_equity_figure(t09a, t09b, t09c)

    # Top margin must be positive and comfortably hold a 13px annotation
    # plus its yshift, but the fix cuts the old, much larger margin.
    assert 0 < fig.layout.margin.t < 60


def test_build_equity_caption_matches_target_wording_and_numbers():
    from lib.numfmt import round_dp, round_whole

    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    t09c = find_atsi_adjusted_model()

    y1 = t09a.loc[(t09a["Dimension"] == "Overall") & (t09a["ATSI"] == "Y")].iloc[0]
    n1 = t09a.loc[(t09a["Dimension"] == "Overall") & (t09a["ATSI"] == "N")].iloc[0]
    gap1 = t09b.loc[t09b["Dimension"] == "Overall"].iloc[0]
    pred_y = float(t09c.loc[t09c["Metric"] == "Model-predicted completion rate, ATSI = Y (%)", "Value_exact"].iloc[0])
    pred_n = float(t09c.loc[t09c["Metric"] == "Model-predicted completion rate, ATSI = N (%)", "Value_exact"].iloc[0])
    pred_gap = float(t09c.loc[t09c["Metric"] == "Model-predicted gap, Y minus N (pp)", "Value_exact"].iloc[0])
    or_point = float(t09c.loc[t09c["Metric"] == "ATSI odds ratio (Y vs N)", "Value_exact"].iloc[0])
    or_lo = float(t09c.loc[t09c["Metric"] == "OR 95% CI lower", "Value_exact"].iloc[0])
    or_hi = float(t09c.loc[t09c["Metric"] == "OR 95% CI upper", "Value_exact"].iloc[0])
    or_p = float(t09c.loc[t09c["Metric"] == "OR p-value", "Value_exact"].iloc[0])

    caption, stats = build_equity_caption(t09a, t09b, t09c)
    assert stats["y1_rate"] == 58.6 and stats["n1_rate"] == 61.4 and stats["gap1"] == -2.8
    assert stats["y2_rate"] == 58.4 and stats["n2_rate"] == 61.5 and stats["gap2"] == -3.1
    assert stats["includes_zero"] is True
    assert stats["excluding_labels"] == ["Remote", "FFT Fee-Free TAFE"]
    assert stats["threshold_cleared"] is True

    assert caption == (
        f"**Aboriginal and Torres Strait Islander learners achieved {round_dp(y1['Rate_exact'], 1):.1f}% "
        f"of their units against {round_dp(n1['Rate_exact'], 1):.1f}% for other learners, a gap of "
        f"{round_dp(abs(gap1['Gap_exact']), 1):.1f} points.**\n\nThe gap is small. It is "
        f"similar in size once those factors are allowed for ({round_dp(abs(pred_gap), 1):.1f} points), "
        f"and that adjusted result is the one that clears the usual threshold. The gap is widest in "
        f"Remote areas (4.4 points) and Fee-Free TAFE (5.6 points)."
    )
    assert "58.4% against 61.5%" not in caption  # adjusted rates now shown only on the chart/table
    assert stats["stats_line"] == (
        f"For readers who want the statistics: the adjusted result is p = {round_dp(or_p, 2):.2f}. If "
        f"there were no real gap, a difference this size would turn up about {round_whole(or_p * 100)} "
        f"times in 100. The unadjusted gap of {round_dp(abs(gap1['Gap_exact']), 1):.1f} points has an "
        f"interval of {round_dp(gap1['Lower_exact'], 1):.1f} to {round_dp(gap1['Upper_exact'], 1):.1f} "
        f"points, which includes zero (the range crosses zero, so that gap alone could be chance). 2 of "
        f"8 regional and funding stream gaps exclude zero, where about 0.40 would be expected by chance. "
        f"Intervals allow for the same student appearing in several units."
    )
    assert caption.startswith(
        "**Aboriginal and Torres Strait Islander learners achieved 58.6% of their units against 61.4% "
        "for other learners, a gap of 2.8 points.**"
    )
    for banned in ["pair", "comparable", "aggregate", "closing the gap"]:
        assert banned not in caption.lower()
    assert "ranking" not in caption.lower()
    assert "holds when other factors" not in caption
    assert "one in three" not in caption


def test_build_equity_caption_interval_excludes_zero_phrasing():
    t09a = find_atsi_completion()
    t09c = find_atsi_adjusted_model()
    broken_t09b = pd.DataFrame(
        {
            "Dimension": ["Overall"] + ["Remoteness"] * 3 + ["Funding_Source"] * 5,
            "Group": ["Overall", "Regional", "Remote", "Urban", "11J", "11K", "11N", "11V", "FFT"],
            "Gap_exact": [-4.0, -0.3, -4.4, -2.6, 3.5, -3.4, -5.9, -1.8, -5.6],
            "Lower_exact": [-6.0, -6.2, -8.5, -8.2, -2.4, -8.9, -13.9, -12.4, -10.7],
            "Upper_exact": [-2.0, 5.8, -0.4, 3.2, 9.5, 2.5, 2.6, 8.0, -0.2],
        }
    )
    caption, stats = build_equity_caption(t09a, broken_t09b, t09c)
    assert stats["includes_zero"] is False
    assert stats["stats_line"].split("which ")[1].startswith("excludes zero")
    assert "includes zero" not in stats["stats_line"]


def test_build_equity_caption_clears_word_switches_with_p_value():
    t09a = find_atsi_completion()
    t09b = find_atsi_gap()

    def t09c_with_p(p):
        return pd.DataFrame(
            {
                "Metric": [
                    "Model-predicted completion rate, ATSI = Y (%)",
                    "Model-predicted completion rate, ATSI = N (%)",
                    "Model-predicted gap, Y minus N (pp)",
                    "ATSI odds ratio (Y vs N)",
                    "OR 95% CI lower",
                    "OR 95% CI upper",
                    "OR p-value",
                ],
                "Value_exact": [58.4, 61.5, -3.1, 0.88, 0.78, 0.99, p],
            }
        )

    _, stats_02 = build_equity_caption(t09a, t09b, t09c_with_p(0.02))
    assert "p = 0.02" in stats_02["stats_line"] and "about 2 times in 100" in stats_02["stats_line"]
    _, stats_04 = build_equity_caption(t09a, t09b, t09c_with_p(0.04))
    assert "p = 0.04" in stats_04["stats_line"] and "about 4 times in 100" in stats_04["stats_line"]
    _, stats_20 = build_equity_caption(t09a, t09b, t09c_with_p(0.2))
    assert "p = 0.20" in stats_20["stats_line"] and "about 20 times in 100" in stats_20["stats_line"]


def test_build_equity_caption_closing_sentence_switches_off_below_p_0_01():
    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    t09c = pd.DataFrame(
        {
            "Metric": [
                "Model-predicted completion rate, ATSI = Y (%)",
                "Model-predicted completion rate, ATSI = N (%)",
                "Model-predicted gap, Y minus N (pp)",
                "ATSI odds ratio (Y vs N)",
                "OR 95% CI lower",
                "OR 95% CI upper",
                "OR p-value",
            ],
            "Value_exact": [58.4, 61.5, -3.1, 0.7, 0.6, 0.8, 0.002],
        }
    )
    caption, stats = build_equity_caption(t09a, t09b, t09c)
    assert "Treat this as a signal to monitor" not in caption
    assert "not a settled difference" not in caption


def test_build_equity_summary_table_html_matches_source():
    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    t09c = find_atsi_adjusted_model()
    html, note, interval_note = build_equity_summary_table_html(t09a, t09b, t09c)

    assert html.count("<tr") == 1 + 2
    assert "Unadjusted (as recorded)" in html
    assert "Adjusted for provider, funding stream, region, industry and year" in html
    assert ">not tested<" in html
    assert ">interval only<" not in html
    assert "As recorded<" not in html
    assert ">58.6<" in html and ">61.4<" in html and ">-2.8<" in html
    assert ">0.88 (0.78 to 0.99)<" in html
    assert note == "Units counted: Aboriginal and Torres Strait Islander learners 1,729, other learners 3,005."
    assert interval_note == "The unadjusted gap is shown with its interval only."

    # The Aboriginal and Torres Strait Islander column must come before the Other learners column.
    header = html.split("</tr>")[0]
    assert header.index("Aboriginal and Torres Strait Islander learners") < header.index("Other learners")


def test_build_equity_subgroup_table_html_has_9_rows_and_correct_tinting():
    from lib.theme import OCHRE_LIGHT_TINT

    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    html, rounding_note = build_equity_subgroup_table_html(t09a, t09b)

    assert html.count("<tr") == 1 + 9
    assert html.count(OCHRE_LIGHT_TINT) == 2  # exactly Remote and FFT exclude zero
    assert ">-4.4<" in html  # the regression this task's rounding fix covers
    assert ">-4.5<" not in html
    assert rounding_note == (
        "Gaps are calculated before rounding, so they can differ by 0.1 from the difference of the "
        "two rates shown."
    )

    # Tinting follows the computed Yes/No column exactly - no row is tinted without a Yes.
    rows_html = html.split("<tr")[2:]  # skip the header row's own leading split artifact
    for row_html in rows_html:
        is_tinted = OCHRE_LIGHT_TINT in row_html
        says_yes = ">Yes<" in row_html
        assert is_tinted == says_yes


def test_build_equity_subgroup_lead_line_matches_table():
    from lib.chart_equity import build_subgroup_lead_line

    t09a = find_atsi_completion()
    t09b = find_atsi_gap()
    line = build_subgroup_lead_line(t09a, t09b)
    assert line == (
        "Each gap comes with a range we are confident it falls within. 'Interval excludes zero' means "
        "the whole range sits below zero, so the gap is unlikely to be chance. Where the range crosses "
        "zero, the gap could be chance. Shaded rows are the ones that exclude zero. With 8 comparisons, "
        "about 0.40 would exclude zero by chance alone."
    )


def test_build_equity_subgroup_table_excludes_zero_uses_strict_sign_not_touching():
    """A row whose interval touches zero exactly must not count as excluding it -
    only a strictly one-sided interval (entirely above or entirely below zero) does."""
    t09a = find_atsi_completion()
    t09b = pd.DataFrame(
        [
            ["Overall", "Overall", -2.8, -5.6, 0.1, 9, -2.8, -5.6, 0.0],
            ["Remoteness", "Urban", -2.6, -8.2, 3.2, 9, -2.6, -8.2, 3.2],
            ["Remoteness", "Regional", -0.3, -6.2, 5.8, 9, -0.3, -6.2, 5.8],
            ["Remoteness", "Remote", -4.5, -8.5, -0.4, 9, -4.4281, -8.5224, -0.4112],
            ["Funding_Source", "11J", 3.5, -2.4, 9.5, 9, 3.4746, -2.4498, 9.4548],
            ["Funding_Source", "11K", -3.4, -8.9, 2.5, 9, -3.3832, -8.9342, 2.5375],
            ["Funding_Source", "11N", -5.9, -13.9, 2.6, 9, -5.8812, -13.9154, 2.5651],
            ["Funding_Source", "11V", -1.8, -12.4, 8.0, 9, -1.8353, -12.3589, 8.0185],
            ["Funding_Source", "FFT", -5.6, -10.7, -0.2, 9, -5.6344, -10.681, -0.1888],
        ],
        columns=[
            "Dimension", "Group", "Gap_pp_Y_minus_N", "CI_Lower", "CI_Upper", "N_Comparisons_in_Table",
            "Gap_exact", "Lower_exact", "Upper_exact",
        ],
    )
    from lib.chart_equity import _subgroup_rows

    rows = _subgroup_rows(t09a, t09b)
    overall = next(r for r in rows if r["group"] == "Overall")
    assert overall["high"] == 0.0
    assert overall["excludes_zero"] is False  # touches zero exactly - must not count as excluding it


# ----------------------------------------------------------------------
# Reach (T18 / T18b) and the Equity wording fixes
# ----------------------------------------------------------------------

def test_t18_counts_and_shares_match_validation():
    from lib.numfmt import round_dp

    t18 = find_atsi_enrolled_share()
    overall = t18.loc[t18["Dimension"] == "Overall"].iloc[0]
    assert int(overall["Students"]) == 1203  # enrolled students
    assert int(overall["ATSI_students"]) == 437

    assert (t18["ATSI_students"] <= t18["Students"]).all()
    for dim, expected_groups in [("Funding_Source", 5), ("Provider_ID", 8), ("Remoteness", 3)]:
        assert (t18["Dimension"] == dim).sum() == expected_groups
    assert len(t18) == 1 + 5 + 8 + 3

    for _, r in t18.iterrows():
        assert r["Lower_exact"] <= r["Share_exact"] <= r["Upper_exact"]
        assert r["Share_%"] == round_dp(float(r["Share_exact"]), 1)
        assert r["CI_Lower"] == round_dp(float(r["Lower_exact"]), 1)
        assert r["CI_Upper"] == round_dp(float(r["Upper_exact"]), 1)
        direct = 100 * int(r["ATSI_students"]) / int(r["Students"])
        assert abs(direct - float(r["Share_exact"])) < 1e-3


def test_t18b_has_three_p_values_at_four_decimals():
    t18b = find_atsi_omnibus()
    assert list(t18b["Dimension"]) == ["Funding_Source", "Provider_ID", "Remoteness"]
    for p in t18b["P_value"]:
        assert round(p, 4) == p
        assert 0 <= p <= 1
    p_values = dict(zip(t18b["Dimension"], t18b["P_value"]))
    assert p_values["Funding_Source"] == pytest.approx(0.3279, abs=1e-4)
    assert p_values["Provider_ID"] == pytest.approx(0.3741, abs=1e-4)
    assert p_values["Remoteness"] == pytest.approx(0.6423, abs=1e-4)


def test_reach_caption_numbers_match_tables():
    from lib.numfmt import round_whole

    t18, t18b = _reach_tables()
    caption, stats = build_reach_caption(t18, t18b)
    paragraph1 = "\n\n".join(caption.split("\n\n")[:2])

    overall = t18.loc[t18["Dimension"] == "Overall"].iloc[0]
    assert paragraph1.startswith(
        f"**Of {int(overall['Students']):,} enrolled students, {int(overall['ATSI_students']):,} "
        f"({round_whole(float(overall['Share_exact']))}%) are recorded as Aboriginal and Torres Strait Islander.**"
    )
    assert "Of 1,203 enrolled students, 437 (36%)" in paragraph1

    def rng(dim):
        sub = t18.loc[t18["Dimension"] == dim, "Share_exact"]
        return round_whole(float(sub.min())), round_whole(float(sub.max()))

    s_lo, s_hi = rng("Funding_Source")
    p_lo, p_hi = rng("Provider_ID")
    r_lo, r_hi = rng("Remoteness")
    assert f"ranges from {s_lo}% to {s_hi}% across funding streams" in paragraph1
    assert f"{p_lo}% to {p_hi}% across providers" in paragraph1
    assert f"{r_lo}% to {r_hi}% across regions" in paragraph1
    assert (s_lo, s_hi, p_lo, p_hi, r_lo, r_hi) == (34, 40, 31, 41, 35, 37)


def test_reach_caption_raises_when_a_p_value_is_below_0_05():
    t18, t18b = _reach_tables()
    caption, stats = build_reach_caption(t18, t18b)
    assert stats["first_sentence_included"] is True
    assert "spread evenly" not in caption
    assert "consistent across every funding stream" not in caption  # now covered by the title alone

    altered = t18b.copy()
    altered.loc[altered["Dimension"] == "Remoteness", "P_value"] = 0.04
    with pytest.raises(TitleAssumptionError):
        build_reach_caption(t18, altered)


def test_reach_caption_avoids_banned_words_and_has_caveat():
    t18, t18b = _reach_tables()
    caption, _ = build_reach_caption(t18, t18b)
    for banned in ["pair", "comparable", "aggregate", "omnibus", "cluster"]:
        assert banned not in caption.lower()
        assert banned not in REACH_CAVEAT.lower()
    assert REACH_CAVEAT == "Each student counts once within a group, so one student can appear in several groups."


def test_reach_chart_has_16_rows_in_the_specified_order():
    from lib.vocab import FUNDING_STREAM_NAMES

    t18, _ = _reach_tables()
    t06a = find_stream_outcome()
    rows, _ = reach_rows(t18, t06a)
    assert len(rows) == 16
    assert [r["dimension"] for r in rows] == ["Funding_Source"] * 5 + ["Provider_ID"] * 8 + ["Remoteness"] * 3
    assert [r["group"] for r in rows[5:13]] == ["P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008"]
    assert [r["group"] for r in rows[13:]] == ["Urban", "Regional", "Remote"]
    stream_codes = [r["group"] for r in rows[:5]]
    assert stream_codes[0] == "11K"  # largest funded hours first, as on the Completion chart
    assert set(stream_codes) == set(FUNDING_STREAM_NAMES)

    fig = build_reach_figure(t18, t06a)
    dots = [tr for tr in fig.data if tr.mode == "markers"]
    assert len(dots) == 1
    assert len(dots[0].x) == 16


def test_reach_chart_every_y_position_inside_the_axis_range():
    t18, _ = _reach_tables()
    fig = build_reach_figure(t18, find_stream_outcome())
    bottom, top = fig.layout.yaxis.range
    assert top < bottom
    for tr in fig.data:
        for y in tr.y:
            assert isinstance(y, (int, float))
            assert top <= y <= bottom
    for a in fig.layout.annotations:
        if a.yref == "y":
            assert isinstance(a.y, (int, float))
            assert top <= a.y <= bottom
    for s in fig.layout.shapes:
        if s.yref == "y":
            assert top <= s.y0 <= bottom and top <= s.y1 <= bottom


def test_reach_axis_is_multiples_of_5_with_span_of_at_least_20():
    t18, _ = _reach_tables()
    rows, overall = reach_rows(t18, find_stream_outcome())
    axis_min, axis_max = reach_axis_range(rows, overall)
    assert axis_min % 5 == 0 and axis_max % 5 == 0
    assert axis_max - axis_min >= 20
    assert (axis_min, axis_max) == (25, 50)


def test_reach_right_hand_labels_use_whole_numbers_from_exact_values():
    t18, _ = _reach_tables()
    fig = build_reach_figure(t18, find_stream_outcome())
    texts = [a.text for a in fig.layout.annotations]
    assert "40%  (35 to 44)" in texts  # 11K: 39.6963 (35.3329 to 44.2301)
    assert "31%  (26 to 38)" in texts  # P004: 31.3043 (25.66 to 37.56)
    assert "Overall 36% (34 to 39)" in texts  # 36.3259 (33.6556 to 39.0831)


def test_reach_row_turns_ochre_only_if_entirely_outside_overall_interval():
    t18, _ = _reach_tables()
    t06a = find_stream_outcome()
    assert reach_any_row_ochre(t18, t06a) is False  # every real interval overlaps the overall one

    altered = t18.copy()
    # Overall interval is 33.6556 to 39.0831. Make P007 sit entirely above it.
    p007 = (altered["Dimension"] == "Provider_ID") & (altered["Group"] == "P007")
    altered.loc[p007, ["Lower_exact", "Upper_exact"]] = [39.5, 47.0]
    rows, _ = reach_rows(altered, t06a)
    ochre = [r["group"] for r in rows if r["is_ochre"]]
    assert ochre == ["P007"]

    # Touching the overall interval edge is not "entirely outside".
    altered2 = t18.copy()
    p004 = (altered2["Dimension"] == "Provider_ID") & (altered2["Group"] == "P004")
    altered2.loc[p004, ["Lower_exact", "Upper_exact"]] = [20.0, 33.6556]
    rows2, _ = reach_rows(altered2, t06a)
    assert not any(r["is_ochre"] for r in rows2 if r["group"] == "P004")


def test_reach_table_html_has_sections_p_values_and_all_rows():
    t18, t18b = _reach_tables()
    html = build_reach_table_html(t18, t18b, find_stream_outcome())
    # 1 header row, 4 section rows (Overall + 3 dimensions), 17 data rows.
    assert html.count("<tr") == 1 + 4 + 17
    assert "test for any difference: p = 0.33" in html
    assert "test for any difference: p = 0.37" in html
    assert "test for any difference: p = 0.64" in html
    assert "Aboriginal and Torres<br>Strait Islander students" in html
    header = html.split("</tr>")[0]
    assert header.index("Aboriginal and Torres<br>Strait Islander students") < header.index("Share (%)")


def test_reach_table_notes_are_the_agreed_wording():
    assert TABLE_NOTE_COUNTING == (
        "Students are counted within each group, so one student can appear in several groups; the figures do "
        "not add up to the total number of students."
    )
    assert TABLE_NOTE_INTERVAL == "Each interval treats the group on its own."


def test_equity_subgroup_comparison_count_is_eight():
    t09b = find_atsi_gap()
    assert subgroup_comparison_count(t09b) == 8  # 3 regions + 5 funding streams, Overall excluded


# ----------------------------------------------------------------------
# Wording and rounding fixes: exact-value companions and the t09b / t05b rules
# ----------------------------------------------------------------------

def test_t09b_stored_gap_equals_rounded_exact_gap_in_every_row():
    from lib.numfmt import round_dp

    t09b = find_atsi_gap()
    for _, r in t09b.iterrows():
        assert float(r["Gap_pp_Y_minus_N"]) == float(round_dp(float(r["Gap_exact"]), 1)), r["Group"]
    remote = t09b.loc[t09b["Group"] == "Remote"].iloc[0]
    assert float(remote["Gap_pp_Y_minus_N"]) == -4.4  # exact -4.4281; the old stored -4.5 was a double rounding


def test_t05b_regional_targets_reconcile_to_the_overall_total_in_t03b():
    t05b = find_aggregate_geography()
    t03b = find_rollups()
    overall_total = int(t03b.loc[t03b["Level"] == "Overall", "Target_AHC_Total"].iloc[0])
    assert overall_total == 578860
    assert int(t05b["Target_AHC_Sum"].sum()) == overall_total


def test_t06a_exact_within_stream_shares_agree_with_display_column():
    from lib.numfmt import round_dp

    t06a = find_stream_outcome()
    assert "Share_within_Stream_exact" in t06a.columns
    for _, r in t06a.iterrows():
        assert abs(float(r["Share_within_Stream_exact"]) - float(r["Share_within_Stream_%"])) < 0.05 + 1e-9
        assert round_dp(float(r["Share_within_Stream_exact"]), 1) == float(r["Share_within_Stream_%"])


def test_t17a_exact_columns_and_industry_top_end_is_40_percent():
    from lib.numfmt import round_dp, round_whole

    t17a = find_industry_outcome()
    assert {"Share_within_Industry_exact", "Not_Completed_Share_exact"}.issubset(t17a.columns)
    for _, r in t17a.iterrows():
        assert round_dp(float(r["Not_Completed_Share_exact"]), 1) == float(r["Not_Completed_Share_%"])
    by_industry = t17a.groupby("Industry")["Not_Completed_Share_exact"].first()
    assert round_whole(float(by_industry["Primary Industry"])) == 40  # exact 39.5017 rounds up to 40
    assert round_whole(float(by_industry["Business"])) == 34
    assert round_dp(float(by_industry["Primary Industry"]), 1) == 39.5


def test_t10_exact_rate_and_continuing_sentence_figure():
    from lib.numfmt import round_dp, round_whole

    t10 = find_sensitivity()
    overall = t10.loc[(t10["Scope"] == "Overall") & t10["Definition"].str.startswith("(c) Continuing")].iloc[0]
    assert round_dp(float(overall["Rate_exact"]), 1) == float(overall["Rate_%"])
    assert round_whole(float(overall["Rate_exact"])) == 53


def test_completion_title_and_caption_read_the_exact_figures():
    from lib.numfmt import round_whole

    t07 = find_completion_by_group()
    overall = t07.loc[t07["Dimension"] == "Overall"].iloc[0]
    title = title_completion(t07, find_completion_omnibus_tests())
    assert title.startswith(f"About {round_whole(float(overall['Rate_exact']))}% of units with a final outcome are achieved")
    caption, stats = build_completion_caption(t07, find_completion_omnibus_tests(), find_sensitivity())
    assert caption.split("\n\n")[1].endswith("across regions.")
    assert stats["continuing_as_not_completed"] == 53


def test_geography_title_and_caption_coverage_sentence_numbers():
    from lib.numfmt import round_whole

    t05b = find_aggregate_geography()
    title = title_geography(t05b)
    assert title == "Where there is a contract, delivery is weighted to Remote areas: 48% of hours against 27% in contracts"

    pairs = find_pairs_geography()
    coverage = find_coverage_summary()
    kpis = load_t01_kpis()
    caption, _ = build_geo_caption(pairs, find_aggregate_geography(), coverage, kpis)
    matched = int(coverage.loc[coverage["Coverage_Bucket"] == "Matched comparable pair", "AHC"].iloc[0])
    total = int(kpis.loc[kpis["Metric"] == "Total funded AHC", "Value"].iloc[0])
    remote_exact = float(kpis.loc[kpis["Metric"] == "Share of funded AHC delivered in Remote (%)", "Value_exact"].iloc[0])
    assert total == 172794 and matched == 72169
    expected = (
        f"These figures cover the 19 contracts with matching delivery ({matched:,} of {total:,} funded hours, "
        f"{round_whole(100 * matched / total)}%). Across all funded hours the Remote share is "
        f"{round_whole(remote_exact)}%."
    )
    assert expected in caption
    assert "42%" in expected and "47%" in expected


def test_funding_caption_funded_hours_sentence_is_factual_and_names_no_payment():
    t06a = find_stream_outcome()
    t06c = find_withdrawn_notachieved_by_funded_flag()
    t17a = find_industry_outcome()
    caption, stats = build_fo_caption(t06a, t06c, t17a)
    assert stats["funded_in_full_included"] is True
    assert "99% of the hours on units not achieved or withdrawn are recorded as fully funded." in caption
    assert "To size the cost, payment records for these units are the next thing to obtain." in caption
    assert "workbook has no payment data" not in caption
    assert "cannot say" not in caption
    assert "funding does not fall" not in caption


def test_programs_caption_uses_consistent_with_chance_and_describes_hours_not_cause():
    t15 = find_program_intensity()
    t16 = find_student_count_chance_check()
    caption, stats = build_programs_caption(t15, t16)
    assert stats["explain_included"] is True
    assert "Student numbers are similar across the ten programs (169 to 204 students each)." in caption
    assert "explained by chance" not in caption
    assert "a spread consistent with chance" not in caption
    assert "about 50 nominal hours against 28 for other industries" in caption
    assert "This describes the hours and does not say why units differ." in caption
    assert "The extra hours come from longer units, not from more students." in caption
    assert stats["stats_line"] == (
        "For readers who want the statistics: p = 0.73. If program size did not vary beyond chance, a "
        "spread this wide would turn up about 73 times in 100."
    )


def test_coverage_caption_does_not_say_11k_is_not_limited_by_contracts():
    text = build_caption(
        find_coverage_summary(), find_delivery_without_contract(), find_coverage_grid(), find_uncontracted_excluding_11k()
    )
    assert "may not be" not in text
    assert "limited by contracts" not in text
    assert "Setting aside 11K, 48.5% of the remaining hours still have no matching contract." in text

"""
Briefing page: the executive summary, Chart 1 (Coverage), Chart 2
(Delivered vs target), Chart 3 (Geography), and the remaining section
placeholders. Each later section will show a data-driven title (from
lib/titles.py), one or more chart_card blocks, and a short narrative,
the same way these three do now. The app is laptop-only: there is one
fixed desktop layout, no narrow/phone variant.
"""

import streamlit as st

from lib.chart_coverage import (
    SHADING_TAKEAWAY as COVERAGE_SHADING_TAKEAWAY,
    build_caption,
    build_figure,
    build_likely_explanation as build_coverage_likely_explanation,
    build_table_heading,
    build_table_html,
    build_table_takeaway as build_coverage_takeaway,
)
from lib.chart_delivered_vs_target import (
    build_caption as build_dvt_caption,
    build_figure as build_dvt_figure,
    build_funding_stream_table_html,
    build_funding_stream_takeaway,
    build_pairs_table_html as build_dvt_pairs_table_html,
    build_table_takeaway as build_dvt_takeaway,
    build_target_coverage_note,
)
from lib.chart_geography import (
    GEOGRAPHY_LIKELY_EXPLANATION,
    build_caption as build_geo_caption,
    build_figure as build_geo_figure,
    build_pairs_table_html as build_geo_pairs_table_html,
)
from lib.chart_programs import (
    build_caption as build_programs_caption,
    build_cer40115_note,
    build_figure as build_programs_figure,
    build_table_html as build_programs_table_html,
    build_table_takeaway as build_programs_table_takeaway,
    build_unit_length_note,
)
from lib.chart_funding_outcome import (
    build_caption as build_fo_caption,
    build_continuing_share_note,
    build_figure as build_fo_figure,
    build_table_html as build_fo_table,
    build_table_takeaway as build_fo_table_takeaway,
)
from lib.chart_completion import (
    PVALUE_KEY_LINE as COMPLETION_PVALUE_KEY_LINE,
    any_row_ochre as completion_any_row_ochre,
    build_caption as build_completion_caption,
    build_figure as build_completion_figure,
    build_reading_aid as build_completion_reading_aid,
    build_table_html as build_completion_table,
    build_table_lead_line as build_completion_table_lead_line,
    build_takeaway_line as build_completion_takeaway_line,
)
from lib.chart_equity import (
    ADJUSTED_ROW_NO_INTERVAL_NOTE as EQUITY_ADJUSTED_ROW_NO_INTERVAL_NOTE,
    DEFINITION_LINE as EQUITY_DEFINITION_LINE,
    PVALUE_KEY_LINE as EQUITY_PVALUE_KEY_LINE,
    build_caption as build_equity_caption,
    build_figure as build_equity_figure,
    build_subgroup_lead_line as build_equity_subgroup_lead_line,
    build_subgroup_table_html as build_equity_subgroup_table,
    build_summary_table_html as build_equity_summary_table,
)
from lib.chart_reach import (
    PVALUE_KEY_LINE as REACH_PVALUE_KEY_LINE,
    TABLE_NOTE_COUNTING,
    TABLE_NOTE_INTERVAL,
    build_caption as build_reach_caption,
    build_figure as build_reach_figure,
    build_reading_aid as build_reach_reading_aid,
    build_table_html as build_reach_table_html,
    build_takeaway_line as build_reach_takeaway_line,
)
from lib.data_access import (
    find_aggregate_geography,
    find_atsi_adjusted_model,
    find_atsi_completion,
    find_atsi_enrolled_share,
    find_atsi_gap,
    find_atsi_omnibus,
    find_sensitivity,
    load_t01_kpis,
    find_completion_by_group,
    find_completion_omnibus_tests,
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
)
from lib.theme import (
    GREY_DARK,
    GREY_DOT,
    PLOTLY_CONFIG,
    TEXT,
    action_card,
    apply_template,
    chart_card,
    configure_page,
    likely_explanation_note,
    render_logo,
)
from lib.titles import (
    title_completion,
    title_coverage,
    title_delivered_vs_target,
    title_equity,
    title_funding_outcome,
    title_geography,
    title_reach,
    title_what_is_delivered,
)
from lib.so_what import (
    ACTION_LEAD,
    DATA_LIMITS_HEADING,
    action_cards,
    data_limits_paragraph,
    executive_summary,
    gather_tables,
)

configure_page("NT VET Performance - Briefing")

render_logo()
st.title("NT VET Performance")
st.caption("Briefing for the Executive Director, Skills and Pathways NT. VET delivery 2023 to 2025.")

so_what_tables = gather_tables()
summary_bullets, summary_footnote = executive_summary(so_what_tables)

st.markdown("## Summary")
st.markdown("\n".join(f"- {bullet}" for bullet in summary_bullets))
st.caption(summary_footnote)

st.markdown("## Coverage")

coverage_df = find_coverage_summary()
dwc_df = find_delivery_without_contract()
coverage_grid_df = find_coverage_grid()
uncontracted_df = find_uncontracted_excluding_11k()

chart_card(
    title=title_coverage(coverage_df),
    fig=build_figure(coverage_df),
    caption=build_caption(coverage_df, dwc_df, coverage_grid_df, uncontracted_df),
)
likely_explanation_note(build_coverage_likely_explanation(dwc_df))

table_html, highlight_provider, highlight_fs = build_table_html(dwc_df)
st.markdown(f"**{build_table_heading(dwc_df)}**")
st.caption(f"{build_coverage_takeaway(dwc_df)} {COVERAGE_SHADING_TAKEAWAY}")
st.markdown(table_html, unsafe_allow_html=True)

st.markdown("## Delivered vs target")

pairs_df = find_matched_pairs()
rollups_df = find_rollups()

chart_card(
    title=title_delivered_vs_target(rollups_df),
    fig=build_dvt_figure(pairs_df, rollups_df),
    caption=build_dvt_caption(pairs_df, rollups_df, coverage_grid_df),
)
st.markdown(
    f"<p style='color:{TEXT};font-size:14px;'>{build_target_coverage_note(coverage_grid_df, load_t01_kpis())}</p>",
    unsafe_allow_html=True,
)

with st.expander("Show all 19 contracts with a target"):
    st.caption(build_dvt_takeaway(pairs_df))
    st.markdown(build_dvt_pairs_table_html(pairs_df), unsafe_allow_html=True)
    st.caption(build_funding_stream_takeaway(rollups_df))
    st.markdown("**Funding stream roll-up**")
    st.markdown(build_funding_stream_table_html(rollups_df), unsafe_allow_html=True)

st.markdown("## Geography")

pairs_geo_df = find_pairs_geography()
agg_geo_df = find_aggregate_geography()
geo_caption, _geo_stats = build_geo_caption(pairs_geo_df, agg_geo_df, coverage_df, load_t01_kpis())

chart_card(
    title=title_geography(agg_geo_df),
    fig=build_geo_figure(agg_geo_df),
    caption=geo_caption,
)
likely_explanation_note(GEOGRAPHY_LIKELY_EXPLANATION)

n_geo_contracts = pairs_geo_df[["Provider_ID", "Funding_Source"]].drop_duplicates().shape[0]
with st.expander(f"Show the gap by region for each of the {n_geo_contracts} contracts"):
    st.caption(
        "Each cell shows delivered share minus contracted share, in points, with the contracted and "
        "delivered shares beneath it. Blue means delivery is below the contract, ochre means above. "
        "Sorted by the Remote gap."
    )
    st.markdown(build_geo_pairs_table_html(pairs_geo_df), unsafe_allow_html=True)
    st.caption(
        "Gaps are calculated before rounding, so they can differ by 0.1 from the difference of the "
        "two shares shown."
    )

st.markdown("## What is being delivered")

program_intensity_df = find_program_intensity()
program_labels_df = find_program_labels()
chance_check_df = find_student_count_chance_check()
programs_caption, _programs_stats = build_programs_caption(program_intensity_df, chance_check_df)

programs_fig = build_programs_figure(program_intensity_df, program_labels_df)
st.markdown(f"#### {title_what_is_delivered(program_intensity_df, chance_check_df)}")
apply_template(programs_fig)
st.plotly_chart(programs_fig, config=PLOTLY_CONFIG, width="stretch")
st.caption(build_cer40115_note(program_intensity_df, program_labels_df))
st.write(programs_caption)
st.caption(_programs_stats["stats_line"])
st.caption(build_unit_length_note(program_intensity_df))

with st.expander("Show all 10 programs"):
    st.caption(build_programs_table_takeaway(program_intensity_df))
    st.markdown(build_programs_table_html(program_intensity_df, program_labels_df), unsafe_allow_html=True)

st.markdown("## Funding vs outcome")

stream_outcome_df = find_stream_outcome()
withdrawn_notachieved_df = find_withdrawn_notachieved_by_funded_flag()
industry_outcome_df = find_industry_outcome()

funding_outcome_caption, _funding_outcome_stats = build_fo_caption(
    stream_outcome_df, withdrawn_notachieved_df, industry_outcome_df
)

chart_card(
    title=title_funding_outcome(stream_outcome_df, withdrawn_notachieved_df),
    fig=build_fo_figure(stream_outcome_df),
    caption=funding_outcome_caption,
    caveat=build_continuing_share_note(stream_outcome_df),
)
with st.expander("Show the numbers"):
    st.caption(build_fo_table_takeaway(stream_outcome_df))
    st.markdown(build_fo_table(stream_outcome_df), unsafe_allow_html=True)

st.markdown("## Completion")

completion_df = find_completion_by_group()
completion_omnibus_df = find_completion_omnibus_tests()

completion_caption, _completion_stats = build_completion_caption(completion_df, completion_omnibus_df, find_sensitivity())

chart_card(
    title=title_completion(completion_df, completion_omnibus_df),
    takeaway=build_completion_takeaway_line(completion_df, stream_outcome_df),
    fig=build_completion_figure(completion_df, stream_outcome_df),
    reading_aid=build_completion_reading_aid(completion_df, stream_outcome_df),
    caption=completion_caption,
    stats_line=_completion_stats["stats_line"],
    caveat=(
        "Rates exclude units still continuing, learner support units and unfunded units (about 12% of "
        "hours). Intervals allow for the same student appearing in several units. If units still "
        f"continuing were counted as not completed, the rate would be about "
        f"{_completion_stats['continuing_as_not_completed']}%."
    ),
)

with st.expander("Show the numbers"):
    st.markdown(
        f"<p style='color:{GREY_DOT};font-size:13px;'>{COMPLETION_PVALUE_KEY_LINE}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:{GREY_DOT};font-size:13px;'>{build_completion_table_lead_line(completion_omnibus_df)}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(build_completion_table(completion_df, completion_omnibus_df, stream_outcome_df), unsafe_allow_html=True)
    st.caption(
        "Each test asks whether any group differs from the others, one dimension at a time, without "
        "adjusting for the others. Whole-number figures in the chart are rounded from unrounded values, "
        "so they can differ slightly from the one-decimal figures here. Students are counted within "
        "each group, so one student can appear in several groups."
    )

st.markdown("## Equity")

atsi_completion_df = find_atsi_completion()
atsi_gap_df = find_atsi_gap()
atsi_adjusted_df = find_atsi_adjusted_model()

equity_caption, _equity_stats = build_equity_caption(atsi_completion_df, atsi_gap_df, atsi_adjusted_df)

chart_card(
    title=title_equity(atsi_gap_df, atsi_adjusted_df),
    fig=build_equity_figure(atsi_completion_df, atsi_gap_df, atsi_adjusted_df),
    reading_aid=f"{EQUITY_DEFINITION_LINE}<br>{EQUITY_ADJUSTED_ROW_NO_INTERVAL_NOTE}",
    caption=equity_caption,
    stats_line=_equity_stats["stats_line"],
)

with st.expander("Show the numbers"):
    st.markdown(
        f"<p style='color:{GREY_DOT};font-size:13px;'>{EQUITY_PVALUE_KEY_LINE}</p>",
        unsafe_allow_html=True,
    )
    summary_table_html, summary_note, summary_interval_note = build_equity_summary_table(
        atsi_completion_df, atsi_gap_df, atsi_adjusted_df
    )
    st.markdown(summary_table_html, unsafe_allow_html=True)
    st.caption(summary_note)
    st.caption(summary_interval_note)

    st.markdown("**Gap by region and funding stream**")
    st.markdown(
        f"<p style='color:{GREY_DOT};font-size:13px;'>"
        f"{build_equity_subgroup_lead_line(atsi_completion_df, atsi_gap_df)}</p>",
        unsafe_allow_html=True,
    )
    subgroup_table_html, subgroup_rounding_note = build_equity_subgroup_table(atsi_completion_df, atsi_gap_df)
    st.markdown(subgroup_table_html, unsafe_allow_html=True)
    st.caption(subgroup_rounding_note)

st.markdown("## Reach")

atsi_share_df = find_atsi_enrolled_share()
atsi_omnibus_df = find_atsi_omnibus()

reach_caption, _reach_stats = build_reach_caption(atsi_share_df, atsi_omnibus_df)

chart_card(
    title=title_reach(atsi_share_df, atsi_omnibus_df),
    takeaway=build_reach_takeaway_line(atsi_share_df, stream_outcome_df),
    fig=build_reach_figure(atsi_share_df, stream_outcome_df),
    reading_aid=build_reach_reading_aid(atsi_share_df, stream_outcome_df),
    caption=reach_caption,
    stats_line=_reach_stats["stats_line"],
)

with st.expander("Show the numbers"):
    st.markdown(
        f"<p style='color:{GREY_DOT};font-size:13px;'>{REACH_PVALUE_KEY_LINE}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(build_reach_table_html(atsi_share_df, atsi_omnibus_df, stream_outcome_df), unsafe_allow_html=True)
    st.caption(TABLE_NOTE_COUNTING)
    st.caption(TABLE_NOTE_INTERVAL)

st.markdown("## So what")
st.write(ACTION_LEAD)
for card in action_cards(so_what_tables):
    action_card(**card)
st.markdown(f"<span style='color:{GREY_DARK};font-size:13px;'><b>{DATA_LIMITS_HEADING}</b></span>", unsafe_allow_html=True)
st.write(data_limits_paragraph(so_what_tables))

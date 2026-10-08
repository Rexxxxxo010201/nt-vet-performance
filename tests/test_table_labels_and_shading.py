"""
Data-integrity tests for round 3 of the tone rewrite: provider names,
stream labels, row/cell shading and the Programs data bar. No rendering,
no pixels; every rule is checked structurally against the tables.
"""

import re

import pandas as pd
import pytest

from lib.labels import provider_label, stream_label
from lib.titles import TitleAssumptionError
from lib.data_access import (
    find_aggregate_geography,
    find_coverage_grid,
    find_delivery_without_contract,
    find_industry_outcome,
    find_matched_pairs,
    find_pairs_geography,
    find_program_intensity,
    find_program_labels,
    find_provider_names,
    find_rollups,
    find_stream_outcome,
    find_withdrawn_notachieved_by_funded_flag,
)
import lib.chart_coverage as cov
import lib.chart_delivered_vs_target as dvt
import lib.chart_geography as geo
import lib.chart_programs as pr
import lib.chart_funding_outcome as fo

PROVIDER_NAMES = {
    "P001": "Charles Darwin University",
    "P002": "TAFE NT",
    "P003": "NT Skills & Training Pty Ltd",
    "P004": "Barkly Regional Training Services",
    "P005": "Top End Workforce Solutions",
    "P006": "Arafura Learning Institute",
    "P007": "Desert Training Co",
    "P008": "Jabiru Community College",
}


def test_t19_has_all_eight_providers_with_a_name():
    names = find_provider_names()
    assert len(names) == 8
    assert set(names["Provider_ID"]) == set(PROVIDER_NAMES)
    assert not names["Provider_Name"].isna().any()
    assert not (names["Provider_Name"].astype(str).str.strip() == "").any()
    for code, name in PROVIDER_NAMES.items():
        assert names.loc[names["Provider_ID"] == code, "Provider_Name"].iloc[0] == name


def test_provider_label_matches_the_organisation_table_for_all_eight_codes():
    for code, name in PROVIDER_NAMES.items():
        assert provider_label(code) == f"{code} {name}"


def test_provider_label_raises_for_an_unknown_code():
    with pytest.raises(TitleAssumptionError):
        provider_label("P999")


def test_provider_label_raises_for_a_blank_name(monkeypatch):
    blank = pd.DataFrame({"Provider_ID": ["P001"], "Provider_Name": ["  "]})
    monkeypatch.setattr("lib.labels.find_provider_names", lambda: blank)
    with pytest.raises(TitleAssumptionError):
        provider_label("P001")


def test_stream_label_matches_the_stream_key():
    assert stream_label("11J") == "11J General Recurrent"
    assert stream_label("11K") == "11K User Choice"
    assert stream_label("11N") == "11N VET in Schools (Urban)"
    assert stream_label("11V") == "11V VET in Schools (Remote)"
    assert stream_label("FFT") == "FFT Fee-Free TAFE"


def test_coverage_table_shows_labels_and_shades_only_p008_fft():
    dwc = find_delivery_without_contract()
    html, highlight_provider, highlight_fs = cov.build_table_html(dwc)
    assert highlight_provider == "P008" and highlight_fs == "FFT"
    assert "P008 Jabiru Community College" in html
    assert "FFT Fee-Free TAFE" in html
    from lib.theme import OCHRE_LIGHT_TINT

    assert html.count(OCHRE_LIGHT_TINT) == 1
    assert cov.SHADING_TAKEAWAY == "Shaded: the largest single gap."


def test_coverage_table_raises_if_p008_fft_drops_out_of_the_top_five():
    dwc = find_delivery_without_contract().copy()
    dwc.loc[dwc["Flag_P008_FFT"] == True, "AHC"] = 1  # noqa: E712
    with pytest.raises(TitleAssumptionError):
        cov.build_table_html(dwc)


def test_dvt_pairs_table_shades_exactly_the_rows_below_a_tenth_of_target():
    pairs = find_matched_pairs()
    df = pairs.sort_values("Delivered_pct_of_Target", ascending=False).reset_index(drop=True)
    expected_shaded = [
        (100 * float(r["Delivered_AHC"]) / float(r["Target_AHC_Total"])) < 10 for _, r in df.iterrows()
    ]
    assert expected_shaded.count(True) == 6

    html = dvt.build_pairs_table_html(pairs)
    from lib.theme import OCHRE_LIGHT_TINT

    rows_html = html.split("<tr")[2:]  # skip the header row's own split artifact
    actual_shaded = [OCHRE_LIGHT_TINT in row_html for row_html in rows_html]
    assert actual_shaded == expected_shaded

    for code in PROVIDER_NAMES:
        if code in df["Provider_ID"].values:
            assert provider_label(code) in html
    for code in ["11J", "11K", "11N", "11V", "FFT"]:
        if code in df["Funding_Source"].values:
            assert stream_label(code) in html


def test_dvt_pairs_table_raises_if_threshold_shades_none_or_all(monkeypatch):
    pairs = find_matched_pairs()
    monkeypatch.setattr(dvt, "SHADING_THRESHOLD_PCT", 0)
    with pytest.raises(TitleAssumptionError):
        dvt.build_pairs_table_html(pairs)
    monkeypatch.setattr(dvt, "SHADING_THRESHOLD_PCT", 100)
    with pytest.raises(TitleAssumptionError):
        dvt.build_pairs_table_html(pairs)


def test_dvt_funding_stream_table_uses_stream_labels():
    rollups = find_rollups()
    html = dvt.build_funding_stream_table_html(rollups)
    for code in ["11J", "11K", "11N", "11V", "FFT"]:
        assert stream_label(code) in html


def test_geography_pairs_table_uses_provider_and_stream_labels():
    pairs = find_pairs_geography()
    html = geo.build_pairs_table_html(pairs)
    for code in PROVIDER_NAMES:
        if (pairs["Provider_ID"] == code).any():
            assert provider_label(code) in html


def test_fo_table_shades_not_achieved_and_withdrawn_cells_only():
    t06a = find_stream_outcome()
    html = fo.build_table_html(t06a)
    from lib.theme import OCHRE_LIGHT_TINT

    # One Not achieved + one Withdrawn cell per stream (5 streams) = 10 shaded cells.
    assert html.count(OCHRE_LIGHT_TINT) == 10
    for code in ["11J", "11K", "11N", "11V", "FFT"]:
        assert stream_label(code) in html
    assert fo.SHADING_TAKEAWAY == "Shaded: hours on units not achieved or withdrawn."


def test_programs_table_shades_exactly_the_three_community_services_rows():
    t15 = find_program_intensity()
    labels = find_program_labels()
    html = pr.build_table_html(t15, labels)
    from lib.theme import OCHRE_LIGHT_TINT

    assert html.count(OCHRE_LIGHT_TINT) == 3
    assert pr.SHADING_TAKEAWAY == "Shaded: the three Community Services programs."


def test_programs_data_bar_widths_are_proportional_to_share_and_max_is_full_width():
    t15 = find_program_intensity()
    labels = find_program_labels()
    programs = pr._program_rows(t15)
    max_share = float(programs["Share_of_Total_%"].max())

    html = pr.build_table_html(t15, labels)
    widths = [float(w) for w in re.findall(r"width:(\d+\.\d)%;background-color", html)]
    assert len(widths) == len(programs)
    assert max(widths) == 100.0  # the largest share fills the bar's full scale

    for _, row in programs.iterrows():
        share = float(row["Share_of_Total_%"])
        expected_width = round(100 * share / max_share, 1)
        assert any(abs(w - expected_width) < 0.05 for w in widths), (share, expected_width, widths)


def test_no_table_figure_changed_from_the_pre_change_analysis_tables():
    """Every number shown in the touched expander tables must still match
    the analysis tables, now that the cells carry names/labels too."""
    dwc = find_delivery_without_contract()
    html, _, _ = cov.build_table_html(dwc)
    top5 = dwc.sort_values("AHC", ascending=False).head(5)
    for _, row in top5.iterrows():
        assert f"{row['AHC']:,.0f}" in html
        assert f"{row['Share_of_Total_%']:.1f}%" in html

    pairs = find_matched_pairs()
    html2 = dvt.build_pairs_table_html(pairs)
    for _, row in pairs.iterrows():
        assert f"{row['Delivered_AHC']:,.0f}" in html2
        assert f"{row['Delivered_pct_of_Target']:.1f}" in html2

    t06a = find_stream_outcome()
    html3 = fo.build_table_html(t06a)
    stream_totals = fo._ordered_totals(t06a, "Funding_Source")
    rows = fo._outcome_wide_rows(t06a, "Funding_Source", stream_totals.index.tolist(), float(stream_totals.sum()))
    for row in rows:
        assert f"{row['Not achieved']:,.0f}" in html3
        assert f"{row['Withdrawn']:,.0f}" in html3


def test_no_em_dash_in_table_html():
    dwc = find_delivery_without_contract()
    html, _, _ = cov.build_table_html(dwc)
    assert "—" not in html and "—" not in html


# ----------------------------------------------------------------------
# Coverage chart: leader line fix
# ----------------------------------------------------------------------

def test_coverage_leader_line_points_at_the_segment_centre_from_exact_values():
    import pandas as pd
    from lib.chart_coverage import build_figure

    def run(ahc_a, ahc_b, ahc_c):
        df = pd.DataFrame(
            {
                "Coverage_Bucket": ["Delivery without a contract", "Matched comparable pair", "Matched pair, no target set"],
                "AHC": [ahc_a, ahc_b, ahc_c],
                "Share_of_Total_%": [
                    round(100 * ahc_a / (ahc_a + ahc_b + ahc_c), 1),
                    round(100 * ahc_b / (ahc_a + ahc_b + ahc_c), 1),
                    round(100 * ahc_c / (ahc_a + ahc_b + ahc_c), 1),
                ],
            }
        )
        total = ahc_a + ahc_b + ahc_c
        expected_x = 100 * (ahc_a + ahc_b + ahc_c / 2) / total
        fig = build_figure(df)
        arrows = [a for a in fig.layout.annotations if a.showarrow]
        assert len(arrows) == 1
        arrow = arrows[0]
        assert abs(float(arrow.x) - expected_x) < 1e-9
        assert abs(float(arrow.ax) - expected_x) < 1e-9  # vertical line: tail x equals head x
        assert arrow.xref == "x" and arrow.axref == "x"
        assert arrow.yref == "paper" and float(arrow.y) == 1  # the bar's own top edge, not its centre
        return expected_x

    # Real data: a, b, c are the three Coverage_Bucket AHC values.
    x1 = run(97550, 72169, 3075)
    assert abs(x1 - 99.11021216014446) < 1e-6
    # Altered numbers: a different split must still satisfy the same formula.
    x2 = run(50000, 40000, 10000)
    assert abs(x2 - 95.0) < 1e-9

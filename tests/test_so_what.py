"""
Data-integrity tests for the executive summary and the So what action
cards (app/lib/so_what.py). Each generated figure is checked against the
analysis tables, with the numfmt helpers applied to exact values. No
rendering, no pixels.
"""

import pandas as pd
import pytest

from lib.numfmt import round_dp, round_whole
from lib.so_what import (
    action_cards,
    data_limits_paragraph,
    executive_summary,
    gather_tables,
)
from lib.titles import TitleAssumptionError

BANNED_STRINGS = ["workbook may not", "cannot say", "analysed as supplied", "does not know"]


@pytest.fixture(scope="module")
def tables():
    return gather_tables()


def _all_text(tables):
    bullets, footnote = executive_summary(tables)
    cards = action_cards(tables)
    text = list(bullets) + [footnote, data_limits_paragraph(tables)]
    for c in cards:
        text.append(c["title"])
        text.append(c["found"])
        text.extend(c["to_confirm"])
        text.append(c["next_step"])
        if c["note"]:
            text.append(c["note"])
        if c["likely_explanation"]:
            text.append(c["likely_explanation"])
        if c["stats_line"]:
            text.append(c["stats_line"])
    return text


def test_summary_has_five_bullets_in_order(tables):
    bullets, footnote = executive_summary(tables)
    assert len(bullets) == 5
    assert bullets[0] == (
        "56% of delivered hours (97,550 of 172,794) have no matching contract. "
        "The largest gap is 21,678 Fee-Free TAFE hours at P008."
    )
    assert bullets[1] == (
        "Where contracts match, delivery is 12% of 3-year target hours, and it leans to Remote: "
        "48% of hours against 27% in contracts."
    )
    assert bullets[2] == (
        "36% of funded hours went to units not achieved or withdrawn, and 99% of those hours are "
        "recorded as fully funded."
    )
    assert bullets[3] == (
        "About 60% of units with a final outcome are achieved, and no funding stream, provider or "
        "region stands out on completion, so none should be ranked on it."
    )
    assert bullets[4] == (
        "Aboriginal and Torres Strait Islander learners (36% of enrolled students) complete about 3 "
        "points less often, a small gap that remains when providers, regions and programs are "
        "compared like for like."
    )
    assert footnote == "The sections below show the evidence for each point. The last section sets out what to do about it."


def test_summary_figures_match_the_tables_with_numfmt_rounding(tables):
    cov = tables["coverage"]
    no_contract = float(cov.loc[cov["Coverage_Bucket"] == "Delivery without a contract", "AHC"].iloc[0])
    total = float(cov["AHC"].sum())
    assert round_whole(100 * no_contract / total) == 56
    assert round_whole(no_contract) == 97550 and round_whole(total) == 172794

    dwc = tables["dwc"]
    p008_fft = float(dwc.loc[dwc["Flag_P008_FFT"] == True, "AHC"].iloc[0])  # noqa: E712
    assert round_whole(p008_fft) == 21678

    rollups = tables["rollups"]
    overall = rollups.loc[rollups["Level"] == "Overall"].iloc[0]
    assert round_whole(100 * float(overall["Delivered_AHC"]) / float(overall["Target_AHC_Total"])) == 12

    agg = tables["agg_geo"]
    remote = agg.loc[agg["Remoteness"] == "Remote"].iloc[0]
    assert round_whole(100 * float(remote["Delivered_AHC_Sum"]) / float(agg["Delivered_AHC_Sum"].sum())) == 48
    assert round_whole(100 * float(remote["Target_AHC_Sum"]) / float(agg["Target_AHC_Sum"].sum())) == 27

    stream = tables["stream_outcome"]
    total_stream = float(stream["AHC_Funded"].sum())
    not_completed = float(stream.loc[stream["Outcome_Group"].isin(["Not achieved", "Withdrawn"]), "AHC_Funded"].sum())
    assert round_whole(100 * not_completed / total_stream) == 36
    withdrawn = tables["withdrawn"]
    y = float(withdrawn.loc[withdrawn["Funded_Flag"] == "Y", "AHC_Funded"].iloc[0])
    assert round_whole(100 * y / float(withdrawn["AHC_Funded"].sum())) == 99

    comp = tables["completion"]
    assert round_whole(float(comp.loc[comp["Dimension"] == "Overall", "Rate_exact"].iloc[0])) == 60

    atsi = tables["atsi_share"]
    assert round_whole(float(atsi.loc[atsi["Dimension"] == "Overall", "Share_exact"].iloc[0])) == 36

    adjusted = tables["atsi_adjusted"]
    gap = float(adjusted.loc[adjusted["Metric"] == "Model-predicted gap, Y minus N (pp)", "Value_exact"].iloc[0])
    assert round_whole(abs(gap)) == 3


def test_cards_appear_in_order_and_no_field_is_empty(tables):
    cards = action_cards(tables)
    assert [c["priority"] for c in cards] == ["Now", "Next", "Next", "Monitor"]
    for c in cards:
        assert c["title"].strip()
        assert c["found"].strip()
        assert c["next_step"].strip()
        assert 1 <= len(c["to_confirm"]) <= 2
        assert all(item.strip() for item in c["to_confirm"])


def test_likely_explanation_only_on_card_one(tables):
    cards = action_cards(tables)
    assert cards[0]["likely_explanation"] is not None
    assert cards[0]["likely_explanation"].strip()
    for c in cards[1:]:
        assert c["likely_explanation"] is None


def test_card_one_numbers_match_the_tables(tables):
    card = action_cards(tables)[0]
    assert card["title"] == "Audit the 56% of hours with no contract"
    assert "97,550 of 172,794 hours have no matching contract." in card["found"]
    assert "21,678 FFT hours at P008, which has no FFT contract." in card["found"]
    assert "delivery is 12% of 3-year target hours" in card["found"]
    assert card["likely_explanation"] == (
        "User Choice delivery may run outside capped contracts. That would not explain P008's "
        "Fee-Free hours."
    )
    assert any("has a contract for 2 providers and delivery without one for 5" in u for u in card["to_confirm"])

    grid = tables["grid"]
    user_choice = grid.loc[grid["Funding_Source"] == "11K"]
    assert int((user_choice["Status"] == "Matched").sum()) == 2
    assert int((user_choice["Status"] == "Delivery without contract").sum()) == 5


def test_card_two_numbers_and_note_match_the_tables(tables):
    card = action_cards(tables)[1]
    assert card["found"] == (
        "Delivery is weighted to Remote areas: 48% of hours against 27% in contracts. "
        "Urban delivery is 7% of contracted hours; Remote is 22%."
    )
    assert card["note"] == "Figures cover the 19 contracts with matching delivery."


def test_card_three_numbers_match_the_tables(tables):
    card = action_cards(tables)[2]
    assert card["title"] == "Size the cost of paying for units not completed"
    assert card["found"] == (
        "99% of the hours on units not achieved or withdrawn are recorded as fully funded. "
        "That is 36% of all funded hours. The share is 34% to 40% across industries."
    )
    assert any("What the 12% of hours still continuing or in learner support" in u for u in card["to_confirm"])


def test_card_four_numbers_match_the_tables(tables):
    card = action_cards(tables)[3]
    assert card["title"] == "Keep watching the Aboriginal and Torres Strait Islander completion gap"
    assert card["found"] == (
        "Aboriginal and Torres Strait Islander learners complete about 3 points less often "
        "(58.4% against 61.5%). The gap is similar in size once provider, stream, region, industry "
        "and year are allowed for. The bigger issue is the 60% completion for everyone."
    )
    assert "T09c" not in card["found"]
    assert card["stats_line"] == (
        "Statistics: p = 0.04 (if there were no real gap, a difference this size would turn up about "
        "4 times in 100); odds ratio 0.88; see the Equity section for the full detail."
    )
    assert "n = p x 100" not in card["stats_line"]
    assert "odds of completing are about" not in card["stats_line"]
    assert "regional and funding stream gaps" not in card["stats_line"]

    adjusted = tables["atsi_adjusted"]
    pred_y = float(adjusted.loc[adjusted["Metric"] == "Model-predicted completion rate, ATSI = Y (%)", "Value_exact"].iloc[0])
    pred_n = float(adjusted.loc[adjusted["Metric"] == "Model-predicted completion rate, ATSI = N (%)", "Value_exact"].iloc[0])
    assert round_whole(pred_y) == 58 and round_whole(pred_n) == 61
    # The whole-number pair (58, 61) differs from naively rounding the Equity chart's one-decimal
    # display (58.4%, 61.5%): rounding 61.5 the usual way gives 62, not 61. Flagged in the report.
    assert round(61.5) == 62

    or_value = float(adjusted.loc[adjusted["Metric"] == "ATSI odds ratio (Y vs N)", "Value_exact"].iloc[0])
    p_value = float(adjusted.loc[adjusted["Metric"] == "OR p-value", "Value_exact"].iloc[0])
    assert round_dp(or_value, 2) == 0.88
    assert round_dp(p_value, 2) == 0.04
    assert round_whole(p_value * 100) == 4
    assert round_whole((1 - or_value) * 100) == 12

    gap = tables["atsi_gap"]
    overall_gap = gap.loc[gap["Dimension"] == "Overall"].iloc[0]
    assert round_dp(abs(float(overall_gap["Gap_exact"])), 1) == 2.8
    subgroups = gap.loc[gap["Dimension"] != "Overall"]
    assert len(subgroups) == 8
    assert int(((subgroups["Lower_exact"] > 0) | (subgroups["Upper_exact"] < 0)).sum()) == 2
    assert round_dp(0.05 * len(subgroups), 2) == 0.40


def test_data_limits_paragraph_matches_completion_figure_and_drops_method_page_sentence(tables):
    text = data_limits_paragraph(tables)
    assert text == (
        "About 60% of units with a final outcome are achieved across funding streams, providers and "
        "regions, so none should be ranked on completion."
    )
    assert "Method and data quality" not in text


def test_no_em_dash_or_en_dash_in_any_generated_text(tables):
    for text in _all_text(tables):
        assert "—" not in text
        assert "–" not in text
        assert "—" not in text


def test_no_banned_words_or_hedging_phrases_in_generated_text(tables):
    for text in _all_text(tables):
        lowered = text.lower()
        for banned in ["pair", "comparable", "aggregate", "omnibus", "cluster", "systemic failure", "parity", "policy success"]:
            assert banned not in lowered, (banned, text)
        for banned in BANNED_STRINGS:
            assert banned not in lowered, (banned, text)


def test_summary_raises_when_coverage_is_outside_range(tables):
    altered = dict(tables)
    cov = tables["coverage"].copy()
    cov.loc[cov["Coverage_Bucket"] == "Delivery without a contract", "AHC"] = 1000
    altered["coverage"] = cov
    with pytest.raises(TitleAssumptionError):
        executive_summary(altered)


def test_summary_raises_when_delivery_against_target_is_outside_range(tables):
    altered = dict(tables)
    rollups = tables["rollups"].copy()
    rollups.loc[rollups["Level"] == "Overall", "Delivered_AHC"] = 10000
    altered["rollups"] = rollups
    with pytest.raises(TitleAssumptionError):
        executive_summary(altered)


def test_summary_raises_when_not_completed_is_outside_range(tables):
    altered = dict(tables)
    stream = tables["stream_outcome"].copy()
    stream.loc[stream["Outcome_Group"].isin(["Not achieved", "Withdrawn"]), "AHC_Funded"] = 0
    altered["stream_outcome"] = stream
    with pytest.raises(TitleAssumptionError):
        executive_summary(altered)


def test_summary_raises_when_completion_is_outside_range(tables):
    altered = dict(tables)
    comp = tables["completion"].copy()
    comp.loc[comp["Dimension"] == "Overall", "Rate_exact"] = 75.0
    altered["completion"] = comp
    with pytest.raises(TitleAssumptionError):
        executive_summary(altered)


def test_summary_raises_when_completion_has_a_significant_dimension(tables):
    altered = dict(tables)
    omnibus = tables["completion_omnibus"].copy()
    omnibus.loc[omnibus["Dimension"] == "Provider_ID", "Omnibus_GEE_p_value"] = 0.01
    altered["completion_omnibus"] = omnibus
    with pytest.raises(TitleAssumptionError):
        executive_summary(altered)


def test_summary_raises_when_atsi_share_is_outside_range(tables):
    altered = dict(tables)
    atsi = tables["atsi_share"].copy()
    atsi.loc[atsi["Dimension"] == "Overall", "Share_exact"] = 60.0
    altered["atsi_share"] = atsi
    with pytest.raises(TitleAssumptionError):
        executive_summary(altered)


def test_summary_raises_when_gap_is_outside_range(tables):
    altered = dict(tables)
    adj = tables["atsi_adjusted"].copy()
    adj.loc[adj["Metric"] == "Model-predicted gap, Y minus N (pp)", "Value_exact"] = -8.0
    altered["atsi_adjusted"] = adj
    with pytest.raises(TitleAssumptionError):
        executive_summary(altered)


def test_cards_raise_when_p008_fft_is_no_longer_uncontracted(tables):
    altered = dict(tables)
    grid = tables["grid"].copy()
    grid.loc[(grid["Provider_ID"] == "P008") & (grid["Funding_Source"] == "FFT"), "Status"] = "Matched"
    altered["grid"] = grid
    with pytest.raises(TitleAssumptionError):
        action_cards(altered)


def test_cards_raise_when_unadjusted_interval_stops_including_zero(tables):
    altered = dict(tables)
    gap = tables["atsi_gap"].copy()
    gap.loc[gap["Dimension"] == "Overall", "Lower_exact"] = 0.5
    altered["atsi_gap"] = gap
    with pytest.raises(TitleAssumptionError):
        action_cards(altered)

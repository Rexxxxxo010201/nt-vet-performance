"""
Executive summary and the "So what" action cards. Every sentence and
field is generated here from the analysis tables, with round_whole and
round_dp (lib/numfmt.py) applied to exact values, never to a one-decimal
display column and never typed by hand.

Each figure is checked against the range the wording assumes. A figure
outside its range raises TitleAssumptionError instead of printing wording
that no longer fits the data. Qualitative claims (for example "no basis for
ranking", "the gap holds after allowing for other factors") are checked by
calling the same title functions that already enforce them, even though
their own wording is no longer quoted here.

Tone (round 1 of the rewrite): state what we know as fact. Never write
"the workbook may not", "we cannot say" or "analysed as supplied" in this
module. A gap in what the tables can show becomes a "To confirm" check
(what we would need to look at next), not a hedge. Exactly one place,
Card 1, carries a labelled "Likely explanation to test" - an unproven idea
plus the check that would test it. No other block states a cause.

Text is kept here, in one place, so the PDF step can reuse the same strings.
"""

from .numfmt import round_dp, round_whole
from .titles import TitleAssumptionError, title_completion, title_equity
from .data_access import (
    find_atsi_adjusted_model,
    find_atsi_completion,
    find_atsi_enrolled_share,
    find_atsi_gap,
    find_atsi_omnibus,
    find_aggregate_geography,
    find_completion_by_group,
    find_completion_omnibus_tests,
    find_coverage_grid,
    find_coverage_summary,
    find_delivery_without_contract,
    find_industry_outcome,
    find_pairs_geography,
    find_rollups,
    find_stream_outcome,
    find_withdrawn_notachieved_by_funded_flag,
)

# Ranges each headline figure must sit in for the wording to hold.
RANGES = {
    "coverage_pct": (40, 70),
    "delivery_pct": (5, 30),
    "not_completed_pct": (25, 45),
    "completion_pct": (50, 70),
    "atsi_share_pct": (25, 50),
    "gap_points": (1, 6),
}

SUMMARY_FOOTNOTE = "The sections below show the evidence for each point. The last section sets out what to do about it."
ACTION_LEAD = "Four actions, in priority order. Each says what we found, what to confirm and the next step."
DATA_LIMITS_HEADING = "What the data does not support"


def _check(name, value):
    lo, hi = RANGES[name]
    if not (lo <= value <= hi):
        raise TitleAssumptionError(f"So what: {name} is {value:.2f}, outside the {lo} to {hi} range the wording assumes.")
    return value


def _row(df, mask, what):
    sub = df.loc[mask]
    if sub.empty:
        raise TitleAssumptionError(f"So what: the tables have no {what}.")
    return sub.iloc[0]


def _figures(tables):
    """Every number used by the summary and the cards, computed once from exact values."""
    cov = tables["coverage"]
    total_hours = float(cov["AHC"].sum())
    no_contract_row = _row(cov, cov["Coverage_Bucket"] == "Delivery without a contract", "'Delivery without a contract' row")
    no_contract = float(no_contract_row["AHC"])
    coverage_exact = 100 * no_contract / total_hours

    rollups = tables["rollups"]
    overall = _row(rollups, rollups["Level"] == "Overall", "matched-contract 'Overall' row")
    matched_delivered = float(overall["Delivered_AHC"])
    matched_target = float(overall["Target_AHC_Total"])
    delivery_exact = 100 * matched_delivered / matched_target

    pairs = tables["pairs"]
    n_contracts = int(pairs[["Provider_ID", "Funding_Source"]].drop_duplicates().shape[0])

    agg = tables["agg_geo"]
    delivered_sum = float(agg["Delivered_AHC_Sum"].sum())
    target_sum = float(agg["Target_AHC_Sum"].sum())
    remote = _row(agg, agg["Remoteness"] == "Remote", "Remote row")
    urban = _row(agg, agg["Remoteness"] == "Urban", "Urban row")
    remote_delivered_exact = 100 * float(remote["Delivered_AHC_Sum"]) / delivered_sum
    remote_target_exact = 100 * float(remote["Target_AHC_Sum"]) / target_sum
    urban_pct_of_target = 100 * float(urban["Delivered_AHC_Sum"]) / float(urban["Target_AHC_Sum"])
    remote_pct_of_target = 100 * float(remote["Delivered_AHC_Sum"]) / float(remote["Target_AHC_Sum"])

    stream = tables["stream_outcome"]
    stream_total = float(stream["AHC_Funded"].sum())
    not_completed_ahc = float(stream.loc[stream["Outcome_Group"].isin(["Not achieved", "Withdrawn"]), "AHC_Funded"].sum())
    not_completed_exact = 100 * not_completed_ahc / stream_total
    continuing_ahc = float(
        stream.loc[stream["Outcome_Group"].isin(["Continuing", "Learner support"]), "AHC_Funded"].sum()
    )
    continuing_exact = 100 * continuing_ahc / stream_total

    withdrawn = tables["withdrawn"]
    funded_y_row = _row(withdrawn, withdrawn["Funded_Flag"] == "Y", "Funded_Flag = Y row")
    funded_y_ahc = float(funded_y_row["AHC_Funded"])
    funded_y_exact = 100 * funded_y_ahc / float(withdrawn["AHC_Funded"].sum())
    funded_y_share_of_total_exact = 100 * funded_y_ahc / total_hours

    industry = tables["industry"]
    industry_exact = industry.groupby("Industry")["Not_Completed_Share_exact"].first()
    industry_low = float(industry_exact.min())
    industry_high = float(industry_exact.max())

    completion = tables["completion"]
    completion_overall = _row(completion, completion["Dimension"] == "Overall", "completion 'Overall' row")
    completion_exact = float(completion_overall["Rate_exact"])

    atsi_share = tables["atsi_share"]
    atsi_overall = _row(atsi_share, atsi_share["Dimension"] == "Overall", "ATSI share 'Overall' row")
    atsi_share_exact = float(atsi_overall["Share_exact"])

    adjusted = tables["atsi_adjusted"]
    pred_gap = _adjusted_value(adjusted, "Model-predicted gap, Y minus N (pp)")
    pred_y = _adjusted_value(adjusted, "Model-predicted completion rate, ATSI = Y (%)")
    pred_n = _adjusted_value(adjusted, "Model-predicted completion rate, ATSI = N (%)")
    or_value = _adjusted_value(adjusted, "ATSI odds ratio (Y vs N)")
    or_p = _adjusted_value(adjusted, "OR p-value")

    gap = tables["atsi_gap"]
    gap_overall = _row(gap, gap["Dimension"] == "Overall", "ATSI gap 'Overall' row")
    unadjusted_gap = float(gap_overall["Gap_exact"])
    unadjusted_lo = float(gap_overall["Lower_exact"])
    unadjusted_hi = float(gap_overall["Upper_exact"])
    subgroups = gap.loc[gap["Dimension"] != "Overall"]
    n_subgroups = int(len(subgroups))
    k_excluding = int(((subgroups["Lower_exact"] > 0) | (subgroups["Upper_exact"] < 0)).sum())

    grid = tables["grid"]
    p008_fft = _row(grid, (grid["Provider_ID"] == "P008") & (grid["Funding_Source"] == "FFT"), "P008 FFT grid row")
    if p008_fft["Status"] != "Delivery without contract":
        raise TitleAssumptionError("So what: P008 FFT is no longer recorded as delivery without a contract.")
    fft_rows = tables["dwc"].loc[tables["dwc"]["Flag_P008_FFT"] == True]  # noqa: E712
    if fft_rows.empty:
        raise TitleAssumptionError("So what: the delivery-without-contract table has no P008 FFT line.")
    p008_fft_ahc = float(fft_rows["AHC"].iloc[0])
    user_choice = grid.loc[grid["Funding_Source"] == "11K"]
    k_user_choice_contracts = int((user_choice["Status"] == "Matched").sum())
    m_user_choice_uncontracted = int((user_choice["Status"] == "Delivery without contract").sum())

    return {
        "no_contract": no_contract,
        "total_hours": total_hours,
        "coverage_exact": coverage_exact,
        "delivery_exact": delivery_exact,
        "n_contracts": n_contracts,
        "remote_delivered_exact": remote_delivered_exact,
        "remote_target_exact": remote_target_exact,
        "urban_pct_of_target": urban_pct_of_target,
        "remote_pct_of_target": remote_pct_of_target,
        "not_completed_exact": not_completed_exact,
        "continuing_exact": continuing_exact,
        "funded_y_exact": funded_y_exact,
        "funded_y_share_of_total_exact": funded_y_share_of_total_exact,
        "industry_low": industry_low,
        "industry_high": industry_high,
        "completion_exact": completion_exact,
        "atsi_share_exact": atsi_share_exact,
        "pred_gap": pred_gap,
        "pred_y": pred_y,
        "pred_n": pred_n,
        "or_value": or_value,
        "or_p": or_p,
        "unadjusted_gap": unadjusted_gap,
        "unadjusted_lo": unadjusted_lo,
        "unadjusted_hi": unadjusted_hi,
        "n_subgroups": n_subgroups,
        "k_excluding": k_excluding,
        "p008_fft_ahc": p008_fft_ahc,
        "k_user_choice_contracts": k_user_choice_contracts,
        "m_user_choice_uncontracted": m_user_choice_uncontracted,
    }


def _adjusted_value(adjusted, metric):
    row = adjusted.loc[adjusted["Metric"] == metric]
    if row.empty:
        raise TitleAssumptionError(f"So what: t09c has no '{metric}' row.")
    return float(row["Value_exact"].iloc[0])


def _check_all_ranges(f):
    _check("coverage_pct", f["coverage_exact"])
    _check("delivery_pct", f["delivery_exact"])
    _check("not_completed_pct", f["not_completed_exact"])
    _check("completion_pct", f["completion_exact"])
    _check("atsi_share_pct", f["atsi_share_exact"])
    _check("gap_points", abs(f["pred_gap"]))


def _check_claims(tables):
    """The qualitative claims behind the summary and the cards are checked
    by the title functions that already enforce them: no detectable
    difference in completion (all three p-values at least 0.05), and a
    small, borderline Equity gap. Either raises if it no longer holds.
    Their returned wording is not quoted here; only the check is reused."""
    title_completion(tables["completion"], tables["completion_omnibus"])
    title_equity(tables["atsi_gap"], tables["atsi_adjusted"])


def _check_unadjusted_includes_zero(f):
    if not (f["unadjusted_lo"] <= 0 <= f["unadjusted_hi"]):
        raise TitleAssumptionError(
            "So what: the unadjusted gap interval no longer includes zero, so 'includes zero' does not hold."
        )


def executive_summary(tables):
    """Returns (bullets, footnote). Five short bullets, in the agreed order."""
    f = _figures(tables)
    _check_all_ranges(f)
    _check_claims(tables)

    bullets = [
        f"{round_whole(f['coverage_exact'])}% of delivered hours ({round_whole(f['no_contract']):,} of "
        f"{round_whole(f['total_hours']):,}) have no matching contract. The largest gap is "
        f"{round_whole(f['p008_fft_ahc']):,} Fee-Free TAFE hours at P008.",
        f"Where contracts match, delivery is {round_whole(f['delivery_exact'])}% of 3-year target hours, and it "
        f"leans to Remote: {round_whole(f['remote_delivered_exact'])}% of hours against "
        f"{round_whole(f['remote_target_exact'])}% in contracts.",
        f"{round_whole(f['not_completed_exact'])}% of funded hours went to units not achieved or withdrawn, and "
        f"{round_whole(f['funded_y_exact'])}% of those hours are recorded as fully funded.",
        f"About {round_whole(f['completion_exact'])}% of units with a final outcome are achieved, and no "
        f"funding stream, provider or region stands out on completion, so none should be ranked on it.",
        f"Aboriginal and Torres Strait Islander learners ({round_whole(f['atsi_share_exact'])}% of enrolled "
        f"students) complete about {round_whole(abs(f['pred_gap']))} points less often, a small gap that "
        f"remains when providers, regions and programs are compared like for like.",
    ]
    if len(bullets) > 5:
        raise TitleAssumptionError("So what: the summary must have five bullets or fewer.")
    return bullets, SUMMARY_FOOTNOTE


def action_cards(tables):
    """The four cards, in order: Now, Next, Next, Monitor. Each is a dict
    with the keys theme.action_card() takes."""
    f = _figures(tables)
    _check_all_ranges(f)
    _check_claims(tables)
    _check_unadjusted_includes_zero(f)

    coverage_whole = round_whole(f["coverage_exact"])
    no_contract_whole = round_whole(f["no_contract"])
    total_whole = round_whole(f["total_hours"])
    delivery_whole = round_whole(f["delivery_exact"])
    remote_whole = round_whole(f["remote_delivered_exact"])
    remote_target_whole = round_whole(f["remote_target_exact"])
    funded_y_whole = round_whole(f["funded_y_exact"])
    funded_y_of_total_whole = round_whole(f["funded_y_share_of_total_exact"])
    continuing_whole = round_whole(f["continuing_exact"])
    industry_low_whole = round_whole(f["industry_low"])
    industry_high_whole = round_whole(f["industry_high"])
    p008_fft_whole = round_whole(f["p008_fft_ahc"])

    card1 = {
        "priority": "Now",
        "title": f"Audit the {coverage_whole}% of hours with no contract",
        "found": (
            f"{no_contract_whole:,} of {total_whole:,} hours have no matching contract. The largest gap is "
            f"{p008_fft_whole:,} FFT hours at P008, which has no FFT contract. On the contracts that do match, "
            f"delivery is {delivery_whole}% of 3-year target hours."
        ),
        "likely_explanation": (
            "User Choice delivery may run outside capped contracts. That would not explain P008's "
            "Fee-Free hours."
        ),
        "to_confirm": [
            f"Which funding streams are meant to have contracts (User Choice has a contract for "
            f"{f['k_user_choice_contracts']} providers and delivery without one for "
            f"{f['m_user_choice_uncontracted']}).",
            "Whether the missing contracts sit under another provider code or funding stream.",
        ],
        "next_step": (
            "Review P008's Fee-Free delivery first, then reconcile the remaining delivery lines against the "
            "contract register."
        ),
        "note": None,
        "stats_line": None,
    }
    card2 = {
        "priority": "Next",
        "title": "Check how remoteness is recorded, then revisit targets",
        "found": (
            f"Delivery is weighted to Remote areas: {remote_whole}% of hours against {remote_target_whole}% in "
            f"contracts. Urban delivery is {round_whole(f['urban_pct_of_target'])}% of contracted hours; Remote is "
            f"{round_whole(f['remote_pct_of_target'])}%."
        ),
        "likely_explanation": None,
        "to_confirm": [
            "Whether remoteness is assigned the same way in contracts and in delivery records.",
            "Whether the sites in each contract match where the units were meant to be delivered.",
        ],
        "next_step": (
            "Compare how remoteness is defined in the contracts and in the delivery records. Once confirmed, "
            "set Urban, Regional and Remote targets from where training is actually delivered."
        ),
        "note": f"Figures cover the {f['n_contracts']} contracts with matching delivery.",
        "stats_line": None,
    }
    card3 = {
        "priority": "Next",
        "title": "Size the cost of paying for units not completed",
        "found": (
            f"{funded_y_whole}% of the hours on units not achieved or withdrawn are recorded as fully funded. "
            f"That is {funded_y_of_total_whole}% of all funded hours. The share is {industry_low_whole}% to "
            f"{industry_high_whole}% across industries."
        ),
        "likely_explanation": None,
        "to_confirm": [
            "What was actually paid for these units, so the cost can be sized.",
            f"What the {continuing_whole}% of hours still continuing or in learner support will turn into.",
        ],
        "next_step": (
            "Pull payment records for these units to size the cost, then trial paying part of the funding on "
            "completion."
        ),
        "note": None,
        "stats_line": None,
    }

    gap_whole = round_whole(abs(f["pred_gap"]))
    pred_y_dp = round_dp(f["pred_y"], 1)
    pred_n_dp = round_dp(f["pred_n"], 1)
    completion_whole = round_whole(f["completion_exact"])
    or_dp = round_dp(f["or_value"], 2)
    p_dp = round_dp(f["or_p"], 2)
    n_in_100 = round_whole(f["or_p"] * 100)

    card4 = {
        "priority": "Monitor",
        "title": "Keep watching the Aboriginal and Torres Strait Islander completion gap",
        "found": (
            f"Aboriginal and Torres Strait Islander learners complete about {gap_whole} points less often "
            f"({pred_y_dp:.1f}% against {pred_n_dp:.1f}%). The gap is similar in size once provider, stream, "
            f"region, industry and year are allowed for. The bigger issue is the {completion_whole}% "
            f"completion for everyone."
        ),
        "likely_explanation": None,
        "to_confirm": [
            "Whether the gap persists in another year of data.",
            "How Aboriginal and Torres Strait Islander status is recorded.",
        ],
        "next_step": (
            "Report completion by Aboriginal and Torres Strait Islander status every period, and watch Remote "
            "and Fee-Free TAFE, where the gap is clearest."
        ),
        "note": None,
        "stats_line": (
            f"Statistics: p = {p_dp:.2f} (if there were no real gap, a difference this size would turn up "
            f"about {n_in_100} times in 100); odds ratio {or_dp:.2f}; see the Equity section for the full "
            f"detail."
        ),
    }
    return [card1, card2, card3, card4]


def data_limits_paragraph(tables):
    """The closing paragraph under the cards. Completion is about the same
    in every stream, provider and region, so none should be ranked on it."""
    f = _figures(tables)
    _check("completion_pct", f["completion_exact"])
    return (
        f"About {round_whole(f['completion_exact'])}% of units with a final outcome are achieved across funding "
        f"streams, providers and regions, so none should be ranked on completion."
    )


def gather_tables():
    """Every table the summary and cards read, loaded through data_access."""
    return {
        "coverage": find_coverage_summary(),
        "dwc": find_delivery_without_contract(),
        "grid": find_coverage_grid(),
        "rollups": find_rollups(),
        "pairs": find_pairs_geography(),
        "agg_geo": find_aggregate_geography(),
        "stream_outcome": find_stream_outcome(),
        "withdrawn": find_withdrawn_notachieved_by_funded_flag(),
        "industry": find_industry_outcome(),
        "completion": find_completion_by_group(),
        "completion_omnibus": find_completion_omnibus_tests(),
        "atsi_share": find_atsi_enrolled_share(),
        "atsi_gap": find_atsi_gap(),
        "atsi_adjusted": find_atsi_adjusted_model(),
    }

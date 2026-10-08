"""
One function per headline title. Every number is pulled from the source
CSVs and formatted here, never typed by hand elsewhere in the app.

Each function also checks the qualitative claim embedded in its wording
(for example "no detectable difference", "borderline", "similar across
regions") against the current data. If that claim no longer holds, the
function raises TitleAssumptionError with a clear message rather than
silently returning wording that misrepresents the data. The numbers
themselves are always recomputed fresh, so a small drift in the
underlying rate (say 60.4% becoming 61.1%) updates the headline number
without needing a code change; it is only a change big enough to flip the
qualitative claim that is treated as an error.
"""

from .numfmt import round_whole


class TitleAssumptionError(ValueError):
    """Raised when the data no longer supports a title's qualitative claim."""


def title_coverage(t02a: "pd.DataFrame") -> str:
    """Section: Coverage. Source: t02a (coverage summary)."""
    row = t02a.loc[t02a["Coverage_Bucket"] == "Delivery without a contract"]
    if row.empty:
        raise TitleAssumptionError("t02a has no 'Delivery without a contract' row.")
    share = float(row["Share_of_Total_%"].iloc[0])
    if share <= 50:
        raise TitleAssumptionError(
            f"Coverage headline assumes a majority of delivered hours lack a matching contract; "
            f"the current share is {share}%, not a majority."
        )
    # AHC is an exact integer sum (never itself rounded with precision loss), so the share
    # is recomputed fresh here rather than rounding the one-decimal Share_of_Total_% column.
    exact_share = 100 * float(row["AHC"].iloc[0]) / float(t02a["AHC"].sum())
    pct = round_whole(exact_share)
    return f"{pct}% of delivered hours have no matching contract"


def title_delivered_vs_target(t03b: "pd.DataFrame") -> str:
    """Section: Delivered vs target. Source: t03b (rollups)."""
    row = t03b.loc[(t03b["Level"] == "Overall")]
    if row.empty:
        raise TitleAssumptionError("t03b has no 'Overall' rollup row.")
    delivered = float(row["Delivered_AHC"].iloc[0])
    target = float(row["Target_AHC_Total"].iloc[0])
    pct_exact = 100 * delivered / target
    if pct_exact >= 50:
        raise TitleAssumptionError(
            f"Delivered-vs-target headline assumes delivery is well under half of the 3-year target; "
            f"the current overall share is {pct_exact:.1f}%, which is 50% or more."
        )
    return f"On contracts with a target, delivery is about {round_whole(pct_exact)}% of 3-year target hours"


def title_geography(t05b: "pd.DataFrame") -> str:
    """Section: Geography. Source: t05b (aggregate geography)."""
    row = t05b.loc[t05b["Remoteness"] == "Remote"]
    if row.empty:
        raise TitleAssumptionError("t05b has no 'Remote' row.")
    delivered = float(row["Delivered_Share_%"].iloc[0])
    target = float(row["Target_Share_%"].iloc[0])
    if delivered - target < 10:
        raise TitleAssumptionError(
            f"Geography headline assumes delivered Remote share exceeds the contracted Remote "
            f"share by at least 10 percentage points; got delivered={delivered}% vs target={target}% "
            f"(gap {delivered - target:.1f}pp)."
        )
    # Target_AHC_Sum/Delivered_AHC_Sum are exact, stored sums - the shares are recomputed
    # fresh from them rather than rounding the one-decimal Share_% columns.
    delivered_exact = 100 * float(row["Delivered_AHC_Sum"].iloc[0]) / float(t05b["Delivered_AHC_Sum"].sum())
    target_exact = 100 * float(row["Target_AHC_Sum"].iloc[0]) / float(t05b["Target_AHC_Sum"].sum())
    return (
        f"Where there is a contract, delivery is weighted to Remote areas: {round_whole(delivered_exact)}% of "
        f"hours against {round_whole(target_exact)}% in contracts"
    )


def title_what_is_delivered(t15: "pd.DataFrame", t16: "pd.DataFrame") -> str:
    """Section: What is being delivered. Source: t15 (program intensity), t16 (student-count chance check)."""
    programs = t15.loc[~t15["Program_ID"].astype(str).str.contains(" ")]
    if len(programs) != 10:
        raise TitleAssumptionError(
            f"What is being delivered headline expects 10 individual program rows; got {len(programs)}."
        )

    top3 = programs.sort_values("AHC_Funded", ascending=False).head(3)
    if not (top3["Industry"] == "Community Services").all():
        raise TitleAssumptionError(
            f"What is being delivered headline assumes the top three programs by funded hours are all "
            f"Community Services; got industries {top3['Industry'].tolist()}."
        )

    p_row = t16.loc[t16["Metric"].str.contains("Two-sided", case=False, regex=False)]
    if p_row.empty:
        raise TitleAssumptionError("t16 has no two-sided p-value row.")
    p_value = float(p_row["Value"].iloc[0])
    if p_value < 0.05:
        raise TitleAssumptionError(
            f"What is being delivered headline assumes the student-count spread is explainable by "
            f"chance (p of 0.05 or above); the current two-sided p-value is {p_value}."
        )

    min_row = t16.loc[t16["Metric"].str.contains("minimum", case=False, regex=False)]
    max_row = t16.loc[t16["Metric"].str.contains("maximum", case=False, regex=False)]
    if min_row.empty or max_row.empty:
        raise TitleAssumptionError("t16 is missing the observed minimum/maximum student-count row.")
    min_students = float(min_row["Value"].iloc[0])
    max_students = float(max_row["Value"].iloc[0])
    if max_students > 1.5 * min_students:
        raise TitleAssumptionError(
            f"What is being delivered headline assumes student counts are similar across programs "
            f"(largest no more than 1.5 times the smallest); got min={min_students}, max={max_students}."
        )

    # AHC_Funded is an exact integer sum, so the combined share is recomputed fresh from it
    # rather than summing the three rounded one-decimal Share_of_Total_% values.
    pct_exact = 100 * float(top3["AHC_Funded"].sum()) / float(programs["AHC_Funded"].sum())
    pct = round_whole(pct_exact)
    return (
        "Student numbers are similar across programs, but three Community Services programs take "
        f"{pct}% of funded hours"
    )


def title_funding_outcome(t06a: "pd.DataFrame", t06c: "pd.DataFrame") -> str:
    """Section: Funding vs outcome. Source: t06a (AHC by stream/outcome), t06c (withdrawn/not-achieved by Funded_Flag)."""
    total = t06a["AHC_Funded"].sum()
    bad = t06a.loc[t06a["Outcome_Group"].isin(["Withdrawn", "Not achieved"]), "AHC_Funded"].sum()
    if total <= 0:
        raise TitleAssumptionError("t06a has no funded AHC to compute a share from.")
    # Cross-check t06a and t06c are describing the same underlying rows: t06c's total AHC
    # (withdrawn/not-achieved units broken out by Funded_Flag) must equal t06a's bad-outcome total.
    t06c_total = t06c["AHC_Funded"].sum()
    if abs(t06c_total - bad) > 1:
        raise TitleAssumptionError(
            f"t06a and t06c disagree on withdrawn/not-achieved AHC: t06a gives {bad}, t06c gives "
            f"{t06c_total}."
        )
    share = 100 * bad / total
    pct = round_whole(share)
    if share < 25:
        raise TitleAssumptionError(
            f"Funding-vs-outcome headline assumes at least a quarter of funded hours are withdrawn "
            f"or not achieved; the current share is {share:.1f}%."
        )
    return f"{pct}% of funded hours went to units not achieved or withdrawn"


def title_completion(t07: "pd.DataFrame", t07_omnibus: "pd.DataFrame") -> str:
    """Section: Completion. Source: t07 (completion by group), t07_omnibus (omnibus GEE tests)."""
    overall = t07.loc[t07["Dimension"] == "Overall"]
    if overall.empty:
        raise TitleAssumptionError("t07 has no 'Overall' row.")
    rate = float(overall["Rate_%"].iloc[0])
    if not (55 <= rate <= 65):
        raise TitleAssumptionError(
            f"Completion headline assumes the overall rate is about 60%; the current rate is {rate}%."
        )
    p_values = {}
    for dim in ["Funding_Source", "Provider_ID", "Remoteness"]:
        row = t07_omnibus.loc[t07_omnibus["Dimension"] == dim]
        if row.empty:
            raise TitleAssumptionError(f"t07_omnibus has no row for {dim}.")
        p_values[dim] = float(row["Omnibus_GEE_p_value"].iloc[0])
    not_significant = [dim for dim, p in p_values.items() if p < 0.05]
    if not_significant:
        raise TitleAssumptionError(
            f"Completion headline assumes no detectable difference between streams, providers or regions "
            f"(omnibus p at least 0.05); {', '.join(not_significant)} now has p below 0.05: {p_values}."
        )
    rate_exact = float(overall["Rate_exact"].iloc[0])
    return (
        f"About {round_whole(rate_exact)}% of units with a final outcome are achieved, with no detectable "
        f"difference between streams, providers or regions"
    )


def title_equity(t09b: "pd.DataFrame", t09c: "pd.DataFrame") -> str:
    """Section: Equity. Source: t09b (ATSI gap), t09c (adjusted GEE).

    Both gaps are read Y minus N, matching how the source tables store
    them (negative means ATSI = Y completes less often). The title
    prints only if: the unadjusted gap (t09b, Overall) and the adjusted
    (model-predicted) gap (t09c) round, half up from their exact
    values, to the same whole number; that whole number is negative;
    and the evidence actually is borderline - either the adjusted
    p-value sits in 0.01 to 0.05, or the unadjusted interval includes
    zero (or both). If the evidence is stronger or weaker than that,
    the wording above would misrepresent it, so this raises instead."""
    gap_row = t09b.loc[t09b["Dimension"] == "Overall"]
    if gap_row.empty:
        raise TitleAssumptionError("t09b has no 'Overall' row.")
    unadjusted_gap_exact = float(gap_row["Gap_exact"].iloc[0])
    unadjusted_lo = float(gap_row["Lower_exact"].iloc[0])
    unadjusted_hi = float(gap_row["Upper_exact"].iloc[0])

    pred_gap_row = t09c.loc[t09c["Metric"] == "Model-predicted gap, Y minus N (pp)"]
    if pred_gap_row.empty:
        raise TitleAssumptionError("t09c has no 'Model-predicted gap, Y minus N (pp)' row.")
    adjusted_gap_exact = float(pred_gap_row["Value_exact"].iloc[0])

    unadjusted_whole = round_whole(unadjusted_gap_exact)
    adjusted_whole = round_whole(adjusted_gap_exact)
    if unadjusted_whole != adjusted_whole:
        raise TitleAssumptionError(
            f"Equity headline needs the unadjusted and adjusted gaps to round to the same whole "
            f"number; got {unadjusted_whole} (unadjusted, from {unadjusted_gap_exact}) and "
            f"{adjusted_whole} (adjusted, from {adjusted_gap_exact})."
        )
    if unadjusted_whole >= 0:
        raise TitleAssumptionError(
            f"Equity headline assumes a negative Y-minus-N gap (ATSI = Y completing less often); "
            f"the current gap rounds to {unadjusted_whole} points."
        )

    or_p_row = t09c.loc[t09c["Metric"] == "OR p-value"]
    if or_p_row.empty:
        raise TitleAssumptionError("t09c has no 'OR p-value' row.")
    or_p = float(or_p_row["Value_exact"].iloc[0])

    borderline_p = 0.01 <= or_p < 0.05
    includes_zero = unadjusted_lo <= 0 <= unadjusted_hi
    if not (borderline_p or includes_zero):
        raise TitleAssumptionError(
            f"Equity headline calls the evidence 'borderline', which needs the adjusted p-value "
            f"between 0.01 and 0.05 or the unadjusted interval to include zero; neither holds here "
            f"(p={or_p}, unadjusted interval {unadjusted_lo} to {unadjusted_hi})."
        )

    return f"Aboriginal and Torres Strait Islander learners complete about {abs(unadjusted_whole)} points less often"


def title_reach(t18: "pd.DataFrame", t18b: "pd.DataFrame") -> str:
    """Section: Reach. Source: t18 (ATSI share of enrolled students by group),
    t18b (omnibus test per dimension).

    The title prints only if the overall share sits between 25% and 50%
    and no dimension's omnibus p-value is below 0.05 (no detectable
    difference between funding streams, providers or regions). Either
    condition failing would make the wording misleading, so this raises."""
    overall = t18.loc[t18["Dimension"] == "Overall"]
    if overall.empty:
        raise TitleAssumptionError("t18 has no 'Overall' row.")
    share_exact = float(overall["Share_exact"].iloc[0])
    if not (25 <= share_exact <= 50):
        raise TitleAssumptionError(
            f"Reach headline assumes the ATSI share of enrolled students is between 25% and 50%; "
            f"the current share is {share_exact:.4f}%."
        )
    p_values = {}
    for dim in ["Funding_Source", "Provider_ID", "Remoteness"]:
        row = t18b.loc[t18b["Dimension"] == dim]
        if row.empty:
            raise TitleAssumptionError(f"t18b has no row for {dim}.")
        p_values[dim] = float(row["P_value"].iloc[0])
    significant = {dim: p for dim, p in p_values.items() if p < 0.05}
    if significant:
        raise TitleAssumptionError(
            f"Reach headline assumes no detectable difference between funding streams, providers or regions "
            f"(p at least 0.05); {', '.join(significant)} now has p below 0.05: {p_values}."
        )
    return (
        f"About {round_whole(share_exact)}% of enrolled students are Aboriginal and Torres Strait Islander, "
        f"with no detectable difference between funding streams, providers or regions"
    )

"""
Chart 1: Coverage. One horizontal 100% stacked bar showing how funded AHC
splits across matched-with-a-target, matched-with-no-target-set, and
no-matching-contract, plus the table of the largest uncontracted lines and
a data-driven caption.

Every number is pulled from app/data/ at call time - nothing here is
typed in by hand. The caption's two factual claims ("largest single
line", "N contracts show no delivery") are checked against the data each
time; if they no longer hold, the wording adapts or a clear error is
raised (see build_caption). The app is laptop-only, so this builds one
fixed desktop layout - no narrow/phone variant.
"""

import plotly.graph_objects as go

from .labels import provider_label, stream_label
from .numfmt import round_whole
from .theme import GREY_LIGHT, GREY_MID, OCHRE, OCHRE_LIGHT_TINT, TEXT, WHITE
from .titles import TitleAssumptionError
from .vocab import FUNDING_STREAM_NAMES

# Coverage_Bucket value -> (display label, colour). Order matters: it is
# the left-to-right order of the stacked bar.
SEGMENT_SPECS = [
    ("Delivery without a contract", "No matching contract", OCHRE),
    ("Matched comparable pair", "Contract with a target", GREY_MID),
    ("Matched pair, no target set", "Contract, no target set", GREY_LIGHT),
]

BAR_HEIGHT = 75
TOP_BLANK = 10  # blank space between the chart_card title and the label zone
LABEL_ZONE = 45  # reserved for the small segment's label text
GAP = 20  # leader-line clearance between the label and the bar
TOP_MARGIN = TOP_BLANK + LABEL_ZONE + GAP  # = 75
BOTTOM_MARGIN = 10
SIDE_MARGIN = 2  # near-zero so the bar's edges line up with the text column
FIGURE_HEIGHT = TOP_MARGIN + BAR_HEIGHT + BOTTOM_MARGIN  # = 160


def _segment_values(coverage_df):
    segs = []
    for bucket, label, color in SEGMENT_SPECS:
        row = coverage_df.loc[coverage_df["Coverage_Bucket"] == bucket]
        if row.empty:
            raise TitleAssumptionError(f"Coverage chart: no '{bucket}' row in the coverage summary table.")
        segs.append(
            {
                "bucket": bucket,
                "label": label,
                "color": color,
                "ahc": float(row["AHC"].iloc[0]),
                "share": float(row["Share_of_Total_%"].iloc[0]),
            }
        )
    cum = 0.0
    for seg in segs:
        seg["start"] = cum
        seg["mid"] = cum + seg["share"] / 2
        cum += seg["share"]

    # mid_exact is the same running "everything before it plus half its own
    # share" as seg["mid"], but computed from the exact AHC values rather
    # than the rounded one-decimal Share_of_Total_% column, so a leader
    # line pointing at it is not built from an already-rounded display
    # figure. The bar's own segment widths are unchanged (still the
    # display shares above) - only the leader line's target uses this.
    total_ahc = sum(s["ahc"] for s in segs)
    cum_ahc = 0.0
    for seg in segs:
        seg["mid_exact"] = 100 * (cum_ahc + seg["ahc"] / 2) / total_ahc
        cum_ahc += seg["ahc"]
    return segs


def build_figure(coverage_df):
    """Build the Coverage stacked-bar figure (one fixed desktop layout)."""
    segs = _segment_values(coverage_df)

    fig = go.Figure()
    external = []

    for seg in segs:
        inline_ok = seg["share"] >= 15
        label_text = f"{seg['label']}<br>{seg['share']:.1f}% ({seg['ahc']:,.0f} hrs)"
        text_color = WHITE if seg["color"] == OCHRE else TEXT
        fig.add_trace(
            go.Bar(
                x=[seg["share"]],
                y=["Coverage"],
                orientation="h",
                marker_color=seg["color"],
                marker_line_width=0,
                text=[label_text] if inline_ok else [""],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color=text_color, size=13),
                customdata=[[seg["label"], seg["ahc"], seg["share"]]],
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,.0f} hours (%{customdata[2]:.1f}%)<extra></extra>",
                showlegend=False,
            )
        )
        if not inline_ok:
            external.append(seg)

    n_ext = len(external)
    for j, seg in enumerate(external):
        # Stack external labels in rows above the bar, highest row last so
        # nothing in this list can ever overlap another entry in it. This
        # spacing is tuned for exactly one external segment (the current
        # data); an extra row stacks LABEL_ZONE px further up.
        row_from_top = n_ext - j
        label_bottom_px = TOP_BLANK + LABEL_ZONE - (row_from_top - 1) * (LABEL_ZONE + 10)
        # The line's target is the segment's own centre (seg["mid"], already
        # computed as a share of the total - the same "everything before it
        # plus half its own share" the inline labels use), at the bar's top
        # edge. yref="paper" is the plot area only (0 = bottom of the bar,
        # 1 = top of the bar, since the margins already consume everything
        # else - see the module docstring's TOP_MARGIN/BAR_HEIGHT layout),
        # so y=1 sits exactly on the bar's top edge and the line can never
        # run into the bar. ax uses axref="x" (not "pixel"): per Plotly,
        # when axref equals xref, ax is an absolute x-axis value rather
        # than a pixel offset, so setting ax to the same value as x draws
        # a plain vertical line at the segment's centre with no pixel
        # arithmetic for its position. The label's right edge sits at that
        # same x (xanchor="right"), which is always <= 100, so it can
        # never clip off the bar's right edge.
        ay = label_bottom_px - TOP_MARGIN
        fig.add_annotation(
            x=seg["mid_exact"],
            y=1,
            xref="x",
            yref="paper",
            text=f"{seg['label']}<br>{seg['share']:.1f}% ({seg['ahc']:,.0f} hrs)",
            showarrow=True,
            arrowhead=0,
            arrowwidth=1,
            arrowcolor=GREY_MID,
            ax=seg["mid_exact"],
            ay=ay,
            axref="x",
            ayref="pixel",
            xanchor="right",
            yanchor="bottom",
            font=dict(size=12, color=TEXT),
            align="right",
            bgcolor="rgba(0,0,0,0)",  # transparent - never covers the bar
            borderwidth=0,
        )

    fig.update_layout(
        barmode="stack",
        height=FIGURE_HEIGHT,
        margin=dict(l=SIDE_MARGIN, r=SIDE_MARGIN, t=TOP_MARGIN, b=BOTTOM_MARGIN),
        xaxis=dict(visible=False, range=[0, 100], fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        showlegend=False,
        bargap=0,
    )
    return fig


def build_table_heading(dwc_df, n=5):
    """'Largest uncontracted lines (K of the N are <code>, <name>)' - K and
    the dominant Funding_Source among the top N are computed, not assumed.
    Raises if there is a tie for the most common stream among the top N."""
    top = dwc_df.sort_values("AHC", ascending=False).head(n)
    counts = top["Funding_Source"].value_counts()
    if len(counts) > 1 and counts.iloc[0] == counts.iloc[1]:
        raise TitleAssumptionError(
            f"Table heading: no single dominant Funding_Source among the top {n} uncontracted lines - "
            f"tied at {counts.iloc[0]} each: {counts.to_dict()}."
        )
    top_stream = counts.index[0]
    top_count = int(counts.iloc[0])
    stream_name = FUNDING_STREAM_NAMES.get(top_stream, top_stream)
    return f"Largest uncontracted lines ({top_count} of the {len(top)} are {top_stream}, {stream_name})"


SHADING_TAKEAWAY = "Shaded: the largest single gap."


def build_table_html(dwc_df, n=5):
    """The n largest delivery-without-contract lines, as an HTML table
    with the P008 Fee-Free TAFE row shaded (the stated rule: that line
    only), names and stream labels shown beside the codes, and cells
    that wrap rather than scroll. Returns (html, highlight_provider,
    highlight_funding_source)."""
    top = dwc_df.sort_values("AHC", ascending=False).head(n).reset_index(drop=True)
    highlight_rows = top.loc[(top["Provider_ID"] == "P008") & (top["Funding_Source"] == "FFT")]
    if highlight_rows.empty:
        raise TitleAssumptionError("Coverage table: the P008 Fee-Free TAFE line is not among the largest lines shown.")
    highlight_provider, highlight_fs = "P008", "FFT"

    cell_style = f"padding:6px 10px;color:{TEXT};word-wrap:break-word;white-space:normal;"
    header = (
        "<tr>"
        f"<th style='text-align:left;padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};'>Provider</th>"
        f"<th style='text-align:left;padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};'>Funding stream</th>"
        f"<th style='text-align:right;padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};'>Funded hours</th>"
        f"<th style='text-align:right;padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};'>Share of all funded hours</th>"
        "</tr>"
    )
    rows = []
    for _, row in top.iterrows():
        is_highlight = row["Provider_ID"] == highlight_provider and row["Funding_Source"] == highlight_fs
        bg = f"background-color:{OCHRE_LIGHT_TINT};" if is_highlight else ""
        rows.append(
            f"<tr style='{bg}'>"
            f"<td style='{cell_style}'>{provider_label(row['Provider_ID'])}</td>"
            f"<td style='{cell_style}'>{stream_label(row['Funding_Source'])}</td>"
            f"<td style='padding:6px 10px;text-align:right;color:{TEXT};'>{row['AHC']:,.0f}</td>"
            f"<td style='padding:6px 10px;text-align:right;color:{TEXT};'>{row['Share_of_Total_%']:.1f}%</td>"
            "</tr>"
        )
    html = f"<table style='width:100%;border-collapse:collapse;font-size:14px;'>{header}{''.join(rows)}</table>"
    return html, highlight_provider, highlight_fs


def build_table_takeaway(dwc_df, n=5):
    """One-line takeaway above the uncontracted-lines table: how much of
    the uncontracted hours the top n lines hold, and how much P008's
    Fee-Free TAFE line holds on its own. Both shares are exact, computed
    fresh from the AHC column, not read from a one-decimal column."""
    total = float(dwc_df["AHC"].sum())
    top = dwc_df.sort_values("AHC", ascending=False).head(n)
    top_share_exact = 100 * float(top["AHC"].sum()) / total
    p008_rows = dwc_df.loc[dwc_df["Flag_P008_FFT"] == True]  # noqa: E712
    if p008_rows.empty:
        raise TitleAssumptionError("Coverage table takeaway: no P008 Fee-Free TAFE row in the uncontracted table.")
    p008_share_exact = 100 * float(p008_rows["AHC"].iloc[0]) / total
    return (
        f"The {n} largest uncontracted lines hold {round_whole(top_share_exact)}% of the uncontracted "
        f"hours; P008 Fee-Free TAFE alone holds {round_whole(p008_share_exact)}%."
    )


def build_likely_explanation(dwc_df):
    """The Coverage chart's 'Likely explanation to test' line, replacing
    the old 'workbook may not hold every contract' caveat. P008's Fee-Free
    TAFE hours are read fresh from the table, not typed in."""
    p008_rows = dwc_df.loc[dwc_df["Flag_P008_FFT"] == True]  # noqa: E712
    if p008_rows.empty:
        raise TitleAssumptionError("Coverage likely explanation: no P008 Fee-Free TAFE row in the uncontracted table.")
    p008_ahc = float(p008_rows["AHC"].iloc[0])
    return (
        f"Likely explanation to test: User Choice delivery may run outside capped contracts. That would "
        f"not explain P008, which delivered {round_whole(p008_ahc):,} Fee-Free TAFE hours with no "
        f"Fee-Free contract. To check, compare the uncontracted lines against the contract register."
    )


def build_caption(coverage_df, dwc_df, coverage_grid_df, uncontracted_df):
    """Build the 2-3 sentence caption. Every number is read from the
    tables; the 'largest single line' and 'N contracts show no delivery'
    claims are checked against the data, not assumed."""
    total_ahc = int(coverage_df["AHC"].sum())
    no_contract_row = coverage_df.loc[coverage_df["Coverage_Bucket"] == "Delivery without a contract"]
    if no_contract_row.empty:
        raise TitleAssumptionError("Coverage caption: no 'Delivery without a contract' row in the coverage summary table.")
    no_contract_ahc = int(no_contract_row["AHC"].iloc[0])

    sorted_dwc = dwc_df.sort_values("AHC", ascending=False)
    largest = sorted_dwc.iloc[0]
    largest_ahc = float(largest["AHC"])
    if (sorted_dwc["AHC"] == largest_ahc).sum() > 1:
        raise TitleAssumptionError(
            f"Coverage caption: the largest uncontracted line is tied at {largest_ahc:,.0f} AHC - "
            f"'largest single line' no longer holds unambiguously."
        )
    largest_provider, largest_fs = largest["Provider_ID"], largest["Funding_Source"]

    no_delivery_rows = coverage_grid_df[
        (coverage_grid_df["Provider_ID"] == largest_provider) & (coverage_grid_df["Status"] == "Contract without delivery")
    ]
    n_no_delivery = len(no_delivery_rows)
    if n_no_delivery > 0:
        noun = "contract" if n_no_delivery == 1 else "contracts"
        verb = "shows" if n_no_delivery == 1 else "show"
        contracts_clause = f"while its {n_no_delivery} {noun} {verb} no delivery"
    else:
        contracts_clause = "though none of its contracts show zero delivery"

    unc_row = uncontracted_df.loc[uncontracted_df["Metric"].str.contains("Share of non-11K AHC", regex=False)]
    if unc_row.empty:
        raise TitleAssumptionError("Coverage caption: no 'Share of non-11K AHC' row in the uncontracted-excluding-11K table.")
    non_11k_share = float(unc_row["Value"].iloc[0])

    first = (
        f"**Of {total_ahc:,} funded hours delivered in 2023 to 2025, {no_contract_ahc:,} sit in a "
        f"provider and funding stream that has no contract in the workbook.**"
    )
    rest = (
        f"{largest_provider}'s {largest_fs} delivery is the largest single line, {contracts_clause}. "
        f"Setting aside 11K, {non_11k_share:.1f}% of the remaining hours still have no matching contract."
    )
    return f"{first}\n\n{rest}"

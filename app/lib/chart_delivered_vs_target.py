"""
Chart 2: Delivered vs target. One row per provider with a matched
comparable pair (sorted by share delivered, highest first), plus an "All
providers" row pinned at the top, each row a light-grey track (100% of
the 3-year target) with an ochre fill showing the share actually
delivered. The app is laptop-only: one fixed desktop layout.
"""

import plotly.graph_objects as go

from .theme import GREY_LIGHT, GREY_MID, OCHRE, OCHRE_LIGHT_TINT, TEXT
from .numfmt import round_dp, round_whole
from .labels import provider_label, stream_label
from .titles import TitleAssumptionError

ALL_PROVIDERS_LABEL = "All providers"

# The x-axis spans beyond 100 so every row's label sits in reserved space
# to the right of the 100%-of-target mark, without the bars themselves
# running under the text.
AXIS_MAX = 150
ROW_HEIGHT = 34
TOP_MARGIN = 14
BOTTOM_MARGIN = 10
LEFT_MARGIN = 92
RIGHT_MARGIN = 8


def _rows(pairs_df, rollups_df):
    """One row per provider with a comparable pair, sorted by share
    delivered (highest first), plus the Overall row. Returns a list of
    dicts: label, delivered, target, pct."""
    overall = rollups_df.loc[rollups_df["Level"] == "Overall"]
    if overall.empty:
        raise TitleAssumptionError("Delivered-vs-target chart: rollups table has no 'Overall' row.")
    overall_row = overall.iloc[0]

    provider_codes = sorted(pairs_df["Provider_ID"].unique())
    provider_rollups = rollups_df.loc[rollups_df["Level"] == "Provider_ID"]
    missing = set(provider_codes) - set(provider_rollups["Key"])
    if missing:
        raise TitleAssumptionError(
            f"Delivered-vs-target chart: provider(s) {sorted(missing)} appear in the per-pair table but "
            f"have no Provider_ID roll-up row."
        )

    provider_rows = provider_rollups[provider_rollups["Key"].isin(provider_codes)].copy()
    provider_rows = provider_rows.sort_values("Delivered_pct_of_Target", ascending=False)

    rows = [
        {
            "label": ALL_PROVIDERS_LABEL,
            "delivered": float(overall_row["Delivered_AHC"]),
            "target": float(overall_row["Target_AHC_Total"]),
            "pct": float(overall_row["Delivered_pct_of_Target"]),
            "is_overall": True,
        }
    ]
    for _, r in provider_rows.iterrows():
        rows.append(
            {
                "label": r["Key"],
                "delivered": float(r["Delivered_AHC"]),
                "target": float(r["Target_AHC_Total"]),
                "pct": float(r["Delivered_pct_of_Target"]),
                "is_overall": False,
            }
        )
    return rows


def build_figure(pairs_df, rollups_df):
    rows = _rows(pairs_df, rollups_df)
    n = len(rows)
    # Top-to-bottom reading order in `rows` is mapped to top-to-bottom on
    # the chart via a reversed category axis.
    labels = [r["label"] for r in rows]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[r["pct"] for r in rows],
            y=labels,
            orientation="h",
            marker_color=OCHRE,
            marker_line_width=0,
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[100 - r["pct"] for r in rows],
            y=labels,
            orientation="h",
            marker_color=GREY_LIGHT,
            marker_line_width=0,
            hoverinfo="skip",
            showlegend=False,
        )
    )

    for r in rows:
        fig.add_annotation(
            x=100,
            y=r["label"],
            xref="x",
            yref="y",
            xanchor="left",
            yanchor="middle",
            xshift=10,
            showarrow=False,
            align="left",
            text=(
                f"<b>{r['pct']:.1f}%</b>  "
                f"<span style='color:{GREY_MID};font-size:11px'>"
                f"({r['delivered']:,.0f} of {r['target']:,.0f} hrs)</span>"
            ),
            font=dict(size=13, color=TEXT),
        )

    hover_name = [ALL_PROVIDERS_LABEL if r["is_overall"] else provider_label(r["label"]) for r in rows]
    hover_customdata = [[name, r["delivered"], r["target"], r["pct"]] for name, r in zip(hover_name, rows)]
    hovertemplate = (
        "<b>%{customdata[0]}</b><br>Delivered %{customdata[1]:,.0f} of %{customdata[2]:,.0f} target hours"
        "<br>%{customdata[3]:.1f}% of target<extra></extra>"
    )
    for trace in fig.data:
        trace.update(hoverinfo="all", hovertemplate=hovertemplate, customdata=hover_customdata)

    # Thin separator between "All providers" and the first provider row.
    # Stops at the track's right edge (x=100), not the label text to its
    # right - xref='x' with x1=100, not xref='paper' with x1=1.
    fig.add_shape(
        type="line",
        xref="x",
        x0=0,
        x1=100,
        yref="y",
        y0=0.5,
        y1=0.5,
        line=dict(color=GREY_MID, width=1),
    )

    # "100% of target" marker, first track only.
    fig.add_shape(
        type="line",
        xref="x",
        x0=100,
        x1=100,
        yref="y",
        y0=-0.4,
        y1=0.4,
        line=dict(color=GREY_MID, width=1),
    )
    fig.add_annotation(
        x=100,
        y=rows[0]["label"],
        xref="x",
        yref="y",
        xanchor="center",
        yanchor="bottom",
        yshift=22,
        showarrow=False,
        text=f"<span style='color:{GREY_MID};font-size:11px'>100% of target</span>",
    )

    fig.update_layout(
        barmode="stack",
        height=TOP_MARGIN + BOTTOM_MARGIN + ROW_HEIGHT * n + 20,
        margin=dict(l=LEFT_MARGIN, r=RIGHT_MARGIN, t=TOP_MARGIN + 20, b=BOTTOM_MARGIN),
        xaxis=dict(visible=False, range=[0, AXIS_MAX], fixedrange=True),
        yaxis=dict(
            visible=True,
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            autorange="reversed",
            categoryorder="array",
            categoryarray=labels,
            fixedrange=True,
            tickfont=dict(color=TEXT, size=13),
        ),
        showlegend=False,
        bargap=0.35,
    )
    return fig


def build_table_takeaway(pairs_df, threshold_pct=10):
    """One-line takeaway above the 19-contract table: how many contracts
    delivered less than threshold_pct of their 3-year target (shaded),
    and the lowest and highest delivery-against-target figures across
    all 19. Computed fresh from exact AHC figures, not the one-decimal
    Delivered_pct_of_Target column. Stops if the threshold shades none
    or more than half the rows."""
    df = pairs_df.copy()
    df["pct_exact"] = 100 * df["Delivered_AHC"] / df["Target_AHC_Total"]
    below = df.loc[df["pct_exact"] < threshold_pct]
    if len(below) == 0 or len(below) > len(df) / 2:
        raise TitleAssumptionError(
            f"Delivered-vs-target takeaway: {len(below)} of {len(df)} contracts are below {threshold_pct}% "
            f"of target - the threshold shades none, or more than half, of the rows."
        )
    lowest = df.loc[df["pct_exact"].idxmin()]
    highest = df.loc[df["pct_exact"].idxmax()]
    lowest_name = f"{lowest['Provider_ID']} {lowest['Funding_Source']}"
    highest_name = f"{highest['Provider_ID']} {highest['Funding_Source']}"
    return (
        f"{len(below)} of {len(df)} contracts have delivered less than a tenth of their target (shaded). "
        f"The lowest is {lowest_name} at {round_whole(float(lowest['pct_exact']))}%; the highest is "
        f"{highest_name} at {round_whole(float(highest['pct_exact']))}%."
    )


def build_target_coverage_note(coverage_grid_df, kpi_df):
    """Replaces the old 'partial extract' caveat: how far total funded
    hours would go against the sum of every contract's 3-year target
    (including P008's three contracts with no delivery), if every hour
    in the workbook belonged to a contract. Both figures are exact sums
    read fresh from the tables."""
    total_funded = kpi_df.loc[kpi_df["Metric"] == "Total funded AHC", "Value"]
    if total_funded.empty:
        raise TitleAssumptionError("Delivered-vs-target note: no 'Total funded AHC' row in T01.")
    a = float(total_funded.iloc[0])
    b = float(coverage_grid_df["Target_AHC"].dropna().sum())
    if b <= 0:
        raise TitleAssumptionError("Delivered-vs-target note: the sum of contract targets is not positive.")
    x = round_whole(100 * a / b)
    return (
        f"Even if every delivered hour in the workbook belonged to a contract, delivery would be {x}% of "
        f"all contract target hours ({a:,.0f} of {b:,.0f}). The gap to target is not explained by hours "
        f"recorded outside contracts."
    )


def build_funding_stream_takeaway(rollups_df):
    """One-line takeaway above the funding stream roll-up table: the two
    lowest streams by delivered-against-target, and the stream with the
    largest 3-year target and how much of it that stream has delivered.
    Computed fresh from exact AHC figures."""
    fs = rollups_df.loc[rollups_df["Level"] == "Funding_Source"].copy()
    fs["pct_exact"] = 100 * fs["Delivered_AHC"] / fs["Target_AHC_Total"]
    vet_rows = fs.loc[fs["Key"].isin(["11N", "11V"])]
    if len(vet_rows) != 2:
        raise TitleAssumptionError("Delivered-vs-target roll-up: expected both 11N and 11V rows.")
    two_lowest = set(fs.nsmallest(2, "pct_exact")["Key"])
    if two_lowest != {"11N", "11V"}:
        raise TitleAssumptionError(
            f"Delivered-vs-target roll-up: 11N and 11V are no longer the two lowest streams; "
            f"the two lowest are now {sorted(two_lowest)}."
        )
    n_pct = round_whole(float(vet_rows.loc[vet_rows["Key"] == "11N", "pct_exact"].iloc[0]))
    v_pct = round_whole(float(vet_rows.loc[vet_rows["Key"] == "11V", "pct_exact"].iloc[0]))

    largest_target_row = fs.loc[fs["Target_AHC_Total"].idxmax()]
    if largest_target_row["Key"] != "FFT":
        raise TitleAssumptionError(
            f"Delivered-vs-target roll-up: the largest target is no longer Fee-Free TAFE's; it is now "
            f"{largest_target_row['Key']}'s."
        )
    total_target = float(fs["Target_AHC_Total"].sum())
    fft_target_share = round_whole(100 * float(largest_target_row["Target_AHC_Total"]) / total_target)
    fft_delivered_pct = round_whole(float(largest_target_row["pct_exact"]))

    return (
        f"The two VET in Schools streams are lowest ({n_pct}% and {v_pct}%); Fee-Free TAFE has the "
        f"largest target ({fft_target_share}% of all target hours) and has delivered {fft_delivered_pct}% "
        f"of it."
    )


def build_caption(pairs_df, rollups_df, coverage_grid_df):
    """Build the 2-3 sentence caption. Every number is read from the
    tables. 'Every provider with delivery is well below target' is
    checked (max provider share < 50%) and the wording adapts or raises
    if not; the P008-has-no-comparable-pair sentence likewise adapts if
    that changes. The closing sentence comparing the one-decimal and
    whole-number overall figures is skipped if the two would print the
    same value."""
    rows = _rows(pairs_df, rollups_df)
    overall = next(r for r in rows if r["is_overall"])
    provider_rows = [r for r in rows if not r["is_overall"]]

    min_row = min(provider_rows, key=lambda r: r["pct"])
    max_row = max(provider_rows, key=lambda r: r["pct"])

    if max_row["pct"] < 50:
        below_target_clause = (
            f"Every provider with delivery is well below target, from {min_row['pct']:.1f}% to "
            f"{max_row['pct']:.1f}%."
        )
    else:
        raise TitleAssumptionError(
            f"Delivered-vs-target caption assumes every provider is well below target; {max_row['label']} "
            f"is at {max_row['pct']:.1f}%, which is not well below target."
        )

    all_providers = {f"P{str(i).zfill(3)}" for i in range(1, 9)}
    providers_with_pairs = {r["label"] for r in provider_rows}
    missing_providers = all_providers - providers_with_pairs
    if "P008" not in missing_providers:
        p008_clause = (
            "P008 now has a contract with a target - this caption needs updating, since it no longer holds."
        )
    else:
        no_delivery_rows = coverage_grid_df[
            (coverage_grid_df["Provider_ID"] == "P008") & (coverage_grid_df["Status"] == "Contract without delivery")
        ]
        n_no_delivery = len(no_delivery_rows)
        noun = "contract" if n_no_delivery == 1 else "contracts"
        p008_clause = f"P008 is not shown because none of its {n_no_delivery} {noun} has any delivery."

    overall_exact = 100 * overall["delivered"] / overall["target"]
    d = round_dp(overall_exact, 1)
    x = round_whole(overall_exact)
    precision_sentence = (
        f" The chart shows one decimal ({d:.1f}%) so providers can be compared; the title rounds it "
        f"to {x}%."
        if d != x
        else ""
    )

    first = (
        f"**Across the 19 contracts with a target, providers delivered {overall['delivered']:,.0f} of "
        f"{overall['target']:,.0f} contracted hours.**"
    )
    rest = f"{below_target_clause} {p008_clause}{precision_sentence}"
    return f"{first}\n\n{rest}"


TABLE_HEADERS = ["Provider", "Funding stream", "Delivered hours", "Target hours", "Delivered as % of target"]
TABLE_ALIGN = ["left", "left", "right", "right", "right"]
FUNDING_TABLE_HEADERS = ["Funding stream", "Delivered hours", "Target hours", "Delivered as % of target"]
FUNDING_TABLE_ALIGN = ["left", "right", "right", "right"]


def _table_html(headers, aligns, body_rows, row_shaded=None):
    """A static HTML table in the same style as Chart 1's table (see
    chart_coverage.build_table_html): text columns left-aligned, numeric
    columns right-aligned per `aligns`, cells that wrap rather than
    scroll, so all rows and all of each cell always show. row_shaded,
    if given, is a list of booleans (one per body row) that tints that
    row the same pale ochre as the Equity subgroup table."""
    header_html = "".join(
        f"<th style='text-align:{align};padding:6px 10px;"
        f"border-bottom:1px solid {GREY_LIGHT};color:{TEXT};'>{h}</th>"
        for h, align in zip(headers, aligns)
    )
    if row_shaded is None:
        row_shaded = [False] * len(body_rows)
    rows_html = []
    for cells, shaded in zip(body_rows, row_shaded):
        bg = f"background-color:{OCHRE_LIGHT_TINT};" if shaded else ""
        tds = "".join(
            f"<td style='padding:6px 10px;text-align:{align};color:{TEXT};word-wrap:break-word;"
            f"white-space:normal;'>{cell}</td>"
            for cell, align in zip(cells, aligns)
        )
        rows_html.append(f"<tr style='{bg}'>{tds}</tr>")
    return f"<table style='width:100%;border-collapse:collapse;font-size:14px;'><tr>{header_html}</tr>{''.join(rows_html)}</table>"


SHADING_THRESHOLD_PCT = 10
# The takeaway above this table states the same shading rule in plain
# words ("... have delivered less than a tenth of their target (shaded)"),
# so no separate "Shaded rows..." line is added here.


def build_pairs_table_html(pairs_df):
    """All 19 pairs, sorted by Delivered_pct_of_Target descending, as a
    static HTML table for the 'Show all 19 contract pairs' expander.
    Shaded rows are the stated rule: delivered less than a tenth of
    target, computed fresh from exact AHC figures each call."""
    df = pairs_df.sort_values("Delivered_pct_of_Target", ascending=False)
    body_rows = []
    row_shaded = []
    for _, row in df.iterrows():
        pct_exact = 100 * float(row["Delivered_AHC"]) / float(row["Target_AHC_Total"])
        body_rows.append(
            [
                provider_label(row["Provider_ID"]),
                stream_label(row["Funding_Source"]),
                f"{row['Delivered_AHC']:,.0f}",
                f"{row['Target_AHC_Total']:,.0f}",
                f"{row['Delivered_pct_of_Target']:.1f}",
            ]
        )
        row_shaded.append(pct_exact < SHADING_THRESHOLD_PCT)
    if len(row_shaded) - sum(row_shaded) == 0 or sum(row_shaded) == 0 or sum(row_shaded) > len(row_shaded) / 2:
        raise TitleAssumptionError(
            f"Delivered-vs-target table: the {SHADING_THRESHOLD_PCT}% shading rule now shades "
            f"{sum(row_shaded)} of {len(row_shaded)} rows (expected some, but not more than half)."
        )
    return _table_html(TABLE_HEADERS, TABLE_ALIGN, body_rows, row_shaded)


def build_funding_stream_table_html(rollups_df):
    """The Funding_Source roll-up, as a static HTML table for the second
    small table in the same expander, using the same column headers as
    the main pairs table. No shading: the stated rule is about contracts,
    not stream totals."""
    df = rollups_df.loc[rollups_df["Level"] == "Funding_Source"].sort_values("Delivered_pct_of_Target", ascending=False)
    body_rows = [
        [
            stream_label(row["Key"]),
            f"{row['Delivered_AHC']:,.0f}",
            f"{row['Target_AHC_Total']:,.0f}",
            f"{row['Delivered_pct_of_Target']:.1f}",
        ]
        for _, row in df.iterrows()
    ]
    return _table_html(FUNDING_TABLE_HEADERS, FUNDING_TABLE_ALIGN, body_rows)

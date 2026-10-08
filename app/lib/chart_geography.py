"""
Chart 3: Geography. A dumbbell chart with three rows (Urban, Regional,
Remote): a blue diamond for the contracted (target) share of AHC and an
ochre circle for the delivered share, joined by a thin grey line, for
the 19 matched comparable pairs aggregated by remoteness class.

Every number is pulled from app/data/ at call time. The caption's two
conditional clauses ("a pattern, not a few providers" and "Urban is
falling furthest behind") are each only added if the data actually
supports them (see build_caption). The app is laptop-only: one fixed
desktop layout.

Per the working agreement in CLAUDE.md, this module is never rendered to
an image or inspected by pixel for development - visual review happens
in the browser. The geometry constants below are deliberately generous
(wide margins, wide label zones) specifically because of that: there is
no screenshot step to catch a tight-fitting label clipping.
"""

import plotly.graph_objects as go

from .numfmt import round_whole
from .theme import BLUE, GREY_DARK, GREY_LIGHT, GREY_MID, OCHRE, TEXT, WHITE
from .labels import provider_label, stream_label
from .titles import TitleAssumptionError

REMOTENESS_ORDER = ["Urban", "Regional", "Remote"]

# The axis runs 0-105: real share values (all comfortably under 60) use
# the left ~0-60 of that range, and the single right-hand text column
# (gap line + smaller "% of target" line, one annotation) starts at
# RIGHT_TEXT_X, well clear of the markers.
AXIS_MAX = 105
RIGHT_TEXT_X = 68

ROW_HEIGHT = 64  # about 20% less than the original 80; tall enough that
# one row's "Delivered" label (below its circle) still clears the next
# row's "Contracted" label (above its diamond) - LABEL_Y_SHIFT is well
# under half of this.
LABEL_Y_SHIFT = 18
TOP_MARGIN = 50  # room for the key, above the plot area
BOTTOM_MARGIN = 14
LEFT_MARGIN = 80  # room for "Regional", the longest row label
RIGHT_MARGIN = 6

DIAMOND_SIZE = 18
CIRCLE_SIZE = 13


def _rows(agg_df):
    # Target_AHC_Sum/Delivered_AHC_Sum are exact, stored sums - every exact_* value
    # below is recomputed fresh from them rather than reading the one-decimal
    # Target_Share_%/Delivered_Share_%/Diff_pp/Delivered_pct_of_Target_% columns
    # (Diff_pp itself is stored as the difference of the two *rounded* shares, so it
    # carries its own extra rounding error on top).
    target_total = float(agg_df["Target_AHC_Sum"].sum())
    delivered_total = float(agg_df["Delivered_AHC_Sum"].sum())

    rows = []
    for remoteness in REMOTENESS_ORDER:
        row = agg_df.loc[agg_df["Remoteness"] == remoteness]
        if row.empty:
            raise TitleAssumptionError(f"Geography chart: no '{remoteness}' row in the aggregate geography table.")
        r = row.iloc[0]
        target_exact = 100 * float(r["Target_AHC_Sum"]) / target_total
        delivered_exact = 100 * float(r["Delivered_AHC_Sum"]) / delivered_total
        rows.append(
            {
                "remoteness": remoteness,
                "target": float(r["Target_Share_%"]),
                "delivered": float(r["Delivered_Share_%"]),
                "gap": float(r["Diff_pp"]),
                "pct_of_target": float(r["Delivered_pct_of_Target_%"]),
                "target_exact": target_exact,
                "delivered_exact": delivered_exact,
                "gap_exact": delivered_exact - target_exact,
                "pct_of_target_exact": 100 * float(r["Delivered_AHC_Sum"]) / float(r["Target_AHC_Sum"]),
            }
        )
    return rows


def build_figure(agg_df):
    """Build the Geography dumbbell figure (one fixed desktop layout)."""
    rows = _rows(agg_df)
    labels = [r["remoteness"] for r in rows]

    fig = go.Figure()

    # Thin connecting line, one per row - added first so the markers sit
    # visually on top of it.
    for r in rows:
        fig.add_trace(
            go.Scatter(
                x=[r["target"], r["delivered"]],
                y=[r["remoteness"], r["remoteness"]],
                mode="lines",
                line=dict(color=GREY_MID, width=1.5),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    hover_customdata = [
        [r["remoteness"], r["target_exact"], r["delivered_exact"], r["gap_exact"]] for r in rows
    ]
    hovertemplate = (
        "<b>%{customdata[0]}</b><br>Contracted share %{customdata[1]:.1f}%<br>"
        "Delivered share %{customdata[2]:.1f}%<br>Gap %{customdata[3]:+.1f} points<extra></extra>"
    )

    # Diamond (contracted share): added before the circle trace, and
    # drawn larger, so it sits visibly behind the circle when the two
    # are close together (Regional: target and delivered are under one
    # point apart). The circle also carries a thin white outline (below)
    # so it stays visibly distinct from the diamond at that overlap,
    # without moving either marker's data position.
    fig.add_trace(
        go.Scatter(
            x=[r["target"] for r in rows],
            y=labels,
            mode="markers",
            marker=dict(symbol="diamond", size=DIAMOND_SIZE, color=BLUE),
            customdata=hover_customdata,
            hovertemplate=hovertemplate,
            showlegend=False,
        )
    )

    # Circle (delivered share): added after, so it renders on top.
    fig.add_trace(
        go.Scatter(
            x=[r["delivered"] for r in rows],
            y=labels,
            mode="markers",
            marker=dict(symbol="circle", size=CIRCLE_SIZE, color=OCHRE, line=dict(color=WHITE, width=1.5)),
            customdata=hover_customdata,
            hovertemplate=hovertemplate,
            showlegend=False,
        )
    )

    for r in rows:
        # "Contracted X%" directly above the diamond.
        fig.add_annotation(
            x=r["target"],
            y=r["remoteness"],
            xref="x",
            yref="y",
            text=f"Contracted {round_whole(r['target_exact'])}%",
            showarrow=False,
            yshift=LABEL_Y_SHIFT,
            font=dict(size=12, color=TEXT),
        )
        # "Delivered X%" directly below the circle.
        fig.add_annotation(
            x=r["delivered"],
            y=r["remoteness"],
            xref="x",
            yref="y",
            text=f"Delivered {round_whole(r['delivered_exact'])}%",
            showarrow=False,
            yshift=-LABEL_Y_SHIFT,
            font=dict(size=12, color=TEXT),
        )
        # Single right-hand column, two lines in one annotation: the bold
        # "N points below/above contract" line (singular "1 point"), then
        # the smaller grey "% of contracted hours delivered" line underneath.
        n_points = round_whole(abs(r["gap_exact"]))
        point_noun = "point" if n_points == 1 else "points"
        direction = "below" if r["gap_exact"] < 0 else "above"
        fig.add_annotation(
            x=RIGHT_TEXT_X,
            y=r["remoteness"],
            xref="x",
            yref="y",
            xanchor="left",
            align="left",
            text=(
                f"<b>{n_points} {point_noun} {direction} contract</b><br>"
                f"<span style='color:{GREY_MID};font-size:11px'>"
                f"{round_whole(r['pct_of_target_exact'])}% of contracted hours delivered</span>"
            ),
            showarrow=False,
            font=dict(size=13, color=TEXT),
        )

    # Key, above the plot area: a diamond + "Contracted share", a circle
    # + "Delivered share". Unicode marker glyphs coloured inline, since
    # there is no legend.
    fig.add_annotation(
        x=0,
        y=1,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="bottom",
        yshift=10,
        showarrow=False,
        align="left",
        text=(
            f"<span style='color:{BLUE}'>&#9670;</span> Contracted share"
            f"&nbsp;&nbsp;&nbsp;&nbsp;"
            f"<span style='color:{OCHRE}'>&#9679;</span> Delivered share"
        ),
        font=dict(size=12, color=TEXT),
    )

    fig.update_layout(
        height=TOP_MARGIN + ROW_HEIGHT * len(rows) + BOTTOM_MARGIN,
        margin=dict(l=LEFT_MARGIN, r=RIGHT_MARGIN, t=TOP_MARGIN, b=BOTTOM_MARGIN),
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
    )
    return fig


def _coverage_sentence(pairs_df, coverage_df, kpi_df):
    """Says how many contracts the figures cover, how much of all funded
    hours that is, and the Remote share across all funded hours. Counts
    and hours are exact integers from the tables; the share is rounded once."""
    n_contracts = int(pairs_df[["Provider_ID", "Funding_Source"]].drop_duplicates().shape[0])
    matched = coverage_df.loc[coverage_df["Coverage_Bucket"] == "Matched comparable pair", "AHC"]
    if matched.empty:
        raise TitleAssumptionError("Geography caption: t02a has no matched-contract row.")
    matched_hours = float(matched.iloc[0])
    total_row = kpi_df.loc[kpi_df["Metric"] == "Total funded AHC", "Value"]
    if total_row.empty:
        raise TitleAssumptionError("Geography caption: t01 has no 'Total funded AHC' row.")
    total_hours = float(total_row.iloc[0])
    remote_row = kpi_df.loc[kpi_df["Metric"] == "Share of funded AHC delivered in Remote (%)", "Value_exact"]
    if remote_row.empty:
        raise TitleAssumptionError("Geography caption: t01 has no Remote share row.")
    all_remote_exact = float(remote_row.iloc[0])
    return (
        f"These figures cover the {n_contracts} contracts with matching delivery "
        f"({matched_hours:,.0f} of {total_hours:,.0f} funded hours, {round_whole(100 * matched_hours / total_hours)}%). "
        f"Across all funded hours the Remote share is {round_whole(all_remote_exact)}%."
    )


GEOGRAPHY_LIKELY_EXPLANATION = (
    "Likely explanation to test: remoteness may be recorded differently in contracts and in "
    "delivery records. To check, compare how each defines Urban, Regional and Remote."
)


def build_caption(pairs_df, agg_df, coverage_df, kpi_df):
    """Build the caption. Every number is read from the tables.

    The "so it is a pattern, not a few providers" clause is only
    included if the Urban-below-contract and Remote-above-contract
    directions each hold in at least 80% of the 19 contracts with a
    target; otherwise the clause is dropped, not forced, and the
    sentence ends after the plain counts.

    The "so Urban is falling furthest behind, not Remote exceeding its
    plan" clause is only included if Urban's delivered share of its
    contracted hours is the lowest of the three remoteness classes and
    Remote's is still below 100%; otherwise it is dropped and the
    sentence ends after the plain percentages."""
    rows = {r["remoteness"]: r for r in _rows(agg_df)}
    urban, remote = rows["Urban"], rows["Remote"]

    urban_pairs = pairs_df.loc[pairs_df["Remoteness"] == "Urban"]
    remote_pairs = pairs_df.loc[pairs_df["Remoteness"] == "Remote"]
    n_total = len(urban_pairs)
    if n_total != 19 or len(remote_pairs) != 19:
        raise TitleAssumptionError(
            f"Geography caption expects 19 contracts with a target per remoteness class; got {n_total} "
            f"Urban, {len(remote_pairs)} Remote."
        )

    n_urban_below = int((urban_pairs["Diff_pp"] < 0).sum())
    m_remote_above = int((remote_pairs["Diff_pp"] > 0).sum())
    pattern_included = bool(n_urban_below / n_total >= 0.8 and m_remote_above / n_total >= 0.8)

    held_sentence = (
        f"This held in {n_urban_below} of {n_total} contracts for Urban and {m_remote_above} of "
        f"{n_total} for Remote"
    )
    held_sentence += ", so it is a pattern, not a few providers." if pattern_included else "."

    # The condition keeps comparing the one-decimal pct_of_target column (unchanged
    # chart behaviour); only the displayed whole numbers below use the exact value.
    pct_of_target = {name: rows[name]["pct_of_target"] for name in REMOTENESS_ORDER}
    pct_of_target_exact = {name: rows[name]["pct_of_target_exact"] for name in REMOTENESS_ORDER}
    furthest_behind_included = bool(
        pct_of_target["Urban"] == min(pct_of_target.values()) and pct_of_target["Remote"] < 100
    )
    behind_sentence = (
        f"Remote areas still received only {round_whole(pct_of_target_exact['Remote'])}% of their "
        f"contracted hours (Urban {round_whole(pct_of_target_exact['Urban'])}%)"
    )
    behind_sentence += (
        ", so Urban is falling furthest behind, not Remote exceeding its plan."
        if furthest_behind_included
        else "."
    )

    coverage_sentence = _coverage_sentence(pairs_df, coverage_df, kpi_df)

    first = (
        f"**Contracts planned for {round_whole(urban['target_exact'])}% of hours in Urban areas and "
        f"{round_whole(remote['target_exact'])}% in Remote areas.**"
    )
    rest = (
        f"Delivery went the other way: {round_whole(urban['delivered_exact'])}% Urban and "
        f"{round_whole(remote['delivered_exact'])}% Remote. {held_sentence} {behind_sentence} "
        f"{coverage_sentence}"
    )
    caption = (
        f"{first}\n\n{rest}\n\n"
        "Either the contracts' geographic targets do not reflect where training happens, or delivery "
        "is not following the contracts; this needs confirming against the contract register."
    )

    return caption, {
        "n_urban_below": n_urban_below,
        "m_remote_above": m_remote_above,
        "n_total": n_total,
        "pattern_included": pattern_included,
        "pct_of_target": pct_of_target,
        "furthest_behind_included": furthest_behind_included,
    }


def _pivot_pairs(pairs_df):
    """Long format (one row per pair x remoteness) -> one row per pair,
    with a Target_%, Delivered_% and Diff_pp column for each remoteness
    class."""
    wide = pairs_df.pivot_table(
        index=["Provider_ID", "Funding_Source"],
        columns="Remoteness",
        values=["Target_Share_%", "Delivered_Share_%", "Diff_pp"],
    )
    wide.columns = [f"{value}_{remoteness}" for value, remoteness in wide.columns]
    wide = wide.reset_index()
    missing = set(REMOTENESS_ORDER) - {
        c.rsplit("_", 1)[1] for c in wide.columns if c.startswith("Target_Share_%_")
    }
    if missing:
        raise TitleAssumptionError(f"Geography expander: pivot is missing remoteness class(es) {sorted(missing)}.")
    return wide


# Cell tint by direction (blue = delivery below the contracted share,
# ochre = above) and by the size of the gap: no tint under 1 point,
# scaling up to the maximum opacity at a 40-point gap or more, so the
# bold gap figure stays readable even at the darkest tint.
TINT_GAP_FLOOR = 1
TINT_GAP_FOR_MAX_OPACITY = 40
MAX_TINT_OPACITY = 0.35


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _tint_style(gap_pp):
    abs_gap = abs(gap_pp)
    if abs_gap < TINT_GAP_FLOOR:
        return ""
    opacity = min(MAX_TINT_OPACITY, MAX_TINT_OPACITY * abs_gap / TINT_GAP_FOR_MAX_OPACITY)
    r, g, b = _hex_to_rgb(BLUE if gap_pp < 0 else OCHRE)
    return f"background-color:rgba({r},{g},{b},{opacity:.3f});"


def _region_cell_html(target, delivered, gap):
    """One region cell: the bold signed gap (delivered minus contracted
    share, in percentage points), then the two underlying shares below
    it in small dark-grey text as 'contracted to delivered' (GREY_DARK,
    not GREY_MID, so it stays readable over the blue/ochre tint),
    tinted by direction and size (see _tint_style)."""
    return (
        f"<td style='padding:6px 10px;text-align:right;color:{TEXT};{_tint_style(gap)}'>"
        f"<b>{gap:+.1f}</b><br>"
        f"<span style='color:{GREY_DARK};font-size:11px'>{target:.1f} to {delivered:.1f}</span>"
        "</td>"
    )


def build_pairs_table_html(pairs_df):
    """All 19 contracts with a target, one row each: Provider, Funding
    stream, and one cell per remoteness class (see _region_cell_html).
    Sorted by the Remote gap, largest first. A static HTML table, same
    style as Chart 2's expander - no inner scroll, so all 19 rows
    always show."""
    wide = _pivot_pairs(pairs_df)
    wide = wide.sort_values("Diff_pp_Remote", ascending=False)

    if len(wide) != 19:
        raise TitleAssumptionError(f"Geography expander: expected 19 contracts with a target, got {len(wide)}.")

    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header = (
        f"<th style='text-align:left;{th_style}'>Provider</th>"
        f"<th style='text-align:left;{th_style}'>Funding stream</th>"
        + "".join(f"<th style='text-align:right;{th_style}'>{remoteness}</th>" for remoteness in REMOTENESS_ORDER)
    )

    body_rows = []
    for _, row in wide.iterrows():
        tds = (
            f"<td style='padding:6px 10px;text-align:left;color:{TEXT};word-wrap:break-word;"
            f"white-space:normal;'>{provider_label(row['Provider_ID'])}</td>"
            f"<td style='padding:6px 10px;text-align:left;color:{TEXT};word-wrap:break-word;"
            f"white-space:normal;'>{stream_label(row['Funding_Source'])}</td>"
        )
        for remoteness in REMOTENESS_ORDER:
            target = row[f"Target_Share_%_{remoteness}"]
            delivered = row[f"Delivered_Share_%_{remoteness}"]
            gap = row[f"Diff_pp_{remoteness}"]
            tds += _region_cell_html(target, delivered, gap)
        body_rows.append(f"<tr>{tds}</tr>")

    return (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header}</tr>{''.join(body_rows)}</table>"
    )

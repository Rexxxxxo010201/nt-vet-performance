"""
Reach: the share of enrolled students recorded as Aboriginal and Torres
Strait Islander (ATSI = Y), overall and within each funding stream,
provider and region. One dot plot in the same layout as the Completion
chart, with three labelled groups (Funding stream, Provider, Region).

Rows are NOT sorted by share - streams stay in funded-hours order (the
same order as the Completion chart), providers stay in ID order, and
regions stay in the fixed order Urban, Regional, Remote.

Every y position is numeric and comes from one place: _assign_positions
gives each group header, each blank gap slot and each charted row an
integer position, and every dot, interval line, separator, shape,
annotation and label is placed at one of those numbers. The y-axis range
is set explicitly from the same positions, with padding above and below.
A text category axis is deliberately not used: mixing text category names
with numeric positions on one axis puts elements in the wrong place.

A row's dot and interval line turn ochre only if its entire Wilson
interval sits outside the overall interval, compared on the exact
(4-decimal) interval values and computed fresh from the data every call.

Rounding: every whole-number label and caption figure reads the
*_exact column of the analysis table and rounds it once with round_whole
(lib/numfmt.py). The expander table reads the one-decimal display columns
directly, which is safe because they are already one decimal.

Coordinate reference note: `yref='paper'` refers to the plotting area only
(0 = bottom of the plot area, 1 = top), excluding the margins. Shapes and
annotations here use yref='y' with the numeric positions above, except
the axis note, which is placed relative to the plot area's bottom edge.

Every number is pulled from app/data/ at call time. The app is
laptop-only: one fixed desktop layout.
"""

import math

import plotly.graph_objects as go

from .chart_completion import _stream_order as funded_hours_stream_order
from .labels import provider_label, stream_label
from .numfmt import round_dp, round_whole
from .theme import GREY_DARK, GREY_DOT, GREY_LIGHT, OCHRE, TEXT
from .titles import TitleAssumptionError
from .vocab import FUNDING_STREAM_NAMES

CHARTED_DIMENSIONS = ["Funding_Source", "Provider_ID", "Remoteness"]
GROUP_HEADER_LABELS = {"Funding_Source": "Funding stream", "Provider_ID": "Provider", "Remoteness": "Region"}
REGION_ORDER = ["Urban", "Regional", "Remote"]
EXPECTED_GROUP_COUNTS = {"Funding_Source": 5, "Provider_ID": 8, "Remoteness": 3}

ROW_PX = 30  # pixels per slot on the numeric y scale
TOP_MARGIN = 40  # room for the "Overall X% (Y to Z)" label above the plot
BOTTOM_MARGIN = 70  # x-axis tick labels, the axis title and the "Axis shows..." note
LEFT_MARGIN = 220
RIGHT_MARGIN = 200

Y_TOP_PAD = 0.6  # plot space above the first slot
Y_BOTTOM_PAD = 0.6  # plot space below the last slot
MIN_AXIS_SPAN = 20
LABEL_FONT_SIZE = 13
OVERALL_LABEL_YSHIFT_PX = 8

REACH_CAVEAT = "Each student counts once within a group, so one student can appear in several groups."

READING_AID = (
    "Each dot is one group. The line shows the range we are confident in. Every group overlaps the "
    "shaded band, so none stands out."
)
TABLE_NOTE_COUNTING = (
    "Students are counted within each group, so one student can appear in several groups; the figures do "
    "not add up to the total number of students."
)
TABLE_NOTE_INTERVAL = "Each interval treats the group on its own."

# The 13px grey line above the "Show the numbers" table, explaining in plain
# words what each dimension's p-value means.
PVALUE_KEY_LINE = (
    "Each p-value asks whether the groups in that block differ by more than chance would produce. "
    "Above 0.05 means the data is consistent with no difference; below 0.05 means a difference is "
    "unlikely to be chance."
)


def _stream_label(code):
    return f"{code} {FUNDING_STREAM_NAMES.get(code, code)}"


def _overall(t18):
    overall = t18.loc[t18["Dimension"] == "Overall"]
    if overall.empty:
        raise TitleAssumptionError("Reach chart: t18 has no 'Overall' row.")
    r = overall.iloc[0]
    return {
        "share": float(r["Share_exact"]),
        "low": float(r["Lower_exact"]),
        "high": float(r["Upper_exact"]),
        "students": int(r["Students"]),
        "atsi_students": int(r["ATSI_students"]),
    }


def _rows(t18, t06a):
    """One dict per charted row (5 streams, then 8 providers, then 3
    regions), in the fixed display order, with the ochre flag computed."""
    overall = _overall(t18)
    stream_order = funded_hours_stream_order(t06a)
    provider_order = sorted(t18.loc[t18["Dimension"] == "Provider_ID", "Group"].unique())

    rows = []
    for dimension, group_order, label_fn in [
        ("Funding_Source", stream_order, _stream_label),
        ("Provider_ID", provider_order, lambda g: g),
        ("Remoteness", REGION_ORDER, lambda g: g),
    ]:
        if len(group_order) != EXPECTED_GROUP_COUNTS[dimension]:
            raise TitleAssumptionError(
                f"Reach chart: expected {EXPECTED_GROUP_COUNTS[dimension]} {dimension} groups, "
                f"found {len(group_order)}."
            )
        for group in group_order:
            match = t18.loc[(t18["Dimension"] == dimension) & (t18["Group"] == group)]
            if match.empty:
                raise TitleAssumptionError(f"Reach chart: t18 has no row for {dimension} = {group}.")
            r = match.iloc[0]
            low, high = float(r["Lower_exact"]), float(r["Upper_exact"])
            rows.append(
                {
                    "dimension": dimension,
                    "group": group,
                    "label": label_fn(group),
                    "share": float(r["Share_exact"]),
                    "low": low,
                    "high": high,
                    "students": int(r["Students"]),
                    "atsi_students": int(r["ATSI_students"]),
                    "is_ochre": bool(high < overall["low"] or low > overall["high"]),
                }
            )
    return rows, overall


def _hover_label(row):
    """The group-label text shown in the dot's hover: provider_label()
    for Provider_ID rows, and row['label'] unchanged for Funding_Source
    (already '{code} {name}') and Remoteness (already a plain region
    name)."""
    if row["dimension"] == "Provider_ID":
        return provider_label(row["group"])
    return row["label"]


def _assign_positions(rows):
    """Give every header, gap and row its numeric y position. Returns
    (header_y, gap_y, last_position). Each group after the first gets a
    blank gap slot above its header, so the separator line sits in that
    slot's own position."""
    y = 0
    header_y, gap_y = {}, {}
    for i, dimension in enumerate(CHARTED_DIMENSIONS):
        if i > 0:
            gap_y[dimension] = y
            y += 1
        header_y[dimension] = y
        y += 1
        for row in rows:
            if row["dimension"] == dimension:
                row["y"] = y
                y += 1
    return header_y, gap_y, y - 1


def _axis_range(rows, overall):
    lows = [r["low"] for r in rows] + [overall["low"]]
    highs = [r["high"] for r in rows] + [overall["high"]]
    raw_min = 5 * math.floor(min(lows) / 5)
    raw_max = 5 * math.ceil(max(highs) / 5)
    if raw_max - raw_min < MIN_AXIS_SPAN:
        raw_max = raw_min + MIN_AXIS_SPAN
    return raw_min, raw_max


def build_figure(t18, t06a):
    rows, overall = _rows(t18, t06a)
    header_y, gap_y, last = _assign_positions(rows)
    top = -Y_TOP_PAD
    bottom = last + Y_BOTTOM_PAD
    axis_min, axis_max = _axis_range(rows, overall)

    fig = go.Figure()

    # Pale ochre band for the overall interval, spanning every row. Added
    # first so the rows' dots and lines draw on top of it.
    fig.add_shape(
        type="rect",
        xref="x",
        yref="y",
        x0=overall["low"],
        x1=overall["high"],
        y0=top,
        y1=bottom,
        fillcolor="rgba(163,90,22,0.15)",
        line=dict(width=0),
        layer="below",
    )
    fig.add_shape(
        type="line",
        xref="x",
        yref="y",
        x0=overall["share"],
        x1=overall["share"],
        y0=top,
        y1=bottom,
        line=dict(color=OCHRE, width=1.5, dash="dash"),
    )

    for position in gap_y.values():
        fig.add_shape(
            type="line",
            xref="x",
            yref="y",
            x0=axis_min,
            x1=axis_max,
            y0=position,
            y1=position,
            line=dict(color=GREY_LIGHT, width=1),
        )

    for row in rows:
        color = OCHRE if row["is_ochre"] else GREY_DOT
        fig.add_trace(
            go.Scatter(
                x=[row["low"], row["high"]],
                y=[row["y"], row["y"]],
                mode="lines",
                line=dict(color=color, width=1.5),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=[r["share"] for r in rows],
            y=[r["y"] for r in rows],
            mode="markers",
            marker=dict(color=[OCHRE if r["is_ochre"] else GREY_DOT for r in rows], size=10),
            customdata=[
                [_hover_label(r), r["share"], r["low"], r["high"], r["atsi_students"], r["students"]]
                for r in rows
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]:.1f}% (%{customdata[2]:.1f} to %{customdata[3]:.1f})"
                "<br>%{customdata[4]:,} of %{customdata[5]:,} students<extra></extra>"
            ),
            showlegend=False,
        )
    )

    for row in rows:
        fig.add_annotation(
            x=axis_min,
            y=row["y"],
            xref="x",
            yref="y",
            xanchor="right",
            yanchor="middle",
            xshift=-10,
            align="right",
            showarrow=False,
            text=row["label"],
            font=dict(size=LABEL_FONT_SIZE, color=TEXT),
        )
        fig.add_annotation(
            x=axis_max,
            y=row["y"],
            xref="x",
            yref="y",
            xanchor="left",
            yanchor="middle",
            xshift=14,
            align="left",
            showarrow=False,
            text=(
                f"{round_whole(row['share'])}%  "
                f"({round_whole(row['low'])} to {round_whole(row['high'])})"
            ),
            font=dict(size=LABEL_FONT_SIZE, color=GREY_DARK),
        )

    for dimension, position in header_y.items():
        fig.add_annotation(
            x=axis_min,
            y=position,
            xref="x",
            yref="y",
            xanchor="right",
            yanchor="middle",
            xshift=-10,
            align="right",
            showarrow=False,
            text=f"<b>{GROUP_HEADER_LABELS[dimension]}</b>",
            font=dict(size=LABEL_FONT_SIZE, color=TEXT),
        )

    fig.add_annotation(
        x=overall["share"],
        y=top,
        xref="x",
        yref="y",
        xanchor="center",
        yanchor="bottom",
        yshift=OVERALL_LABEL_YSHIFT_PX,
        showarrow=False,
        text=(
            f"Overall {round_whole(overall['share'])}% "
            f"({round_whole(overall['low'])} to {round_whole(overall['high'])})"
        ),
        font=dict(size=LABEL_FONT_SIZE, color=OCHRE),
    )
    fig.add_annotation(
        x=(axis_min + axis_max) / 2,
        y=0,
        xref="x",
        yref="paper",
        xanchor="center",
        yanchor="top",
        yshift=-34,
        showarrow=False,
        text="Aboriginal and Torres Strait Islander students (% of enrolled students)",
        font=dict(size=13, color=TEXT),
    )
    fig.add_annotation(
        x=(axis_min + axis_max) / 2,
        y=0,
        xref="x",
        yref="paper",
        xanchor="center",
        yanchor="top",
        yshift=-54,
        showarrow=False,
        text=f"Axis shows {axis_min}% to {axis_max}%, not zero.",
        font=dict(size=11, color=GREY_DOT),
    )

    plot_px = math.ceil((bottom - top) * ROW_PX)
    fig.update_layout(
        height=TOP_MARGIN + plot_px + BOTTOM_MARGIN,
        margin=dict(l=LEFT_MARGIN, r=RIGHT_MARGIN, t=TOP_MARGIN, b=BOTTOM_MARGIN),
        showlegend=False,
        xaxis=dict(
            range=[axis_min, axis_max],
            dtick=5,
            ticksuffix="%",
            showgrid=True,
            gridcolor=GREY_LIGHT,
            zeroline=False,
            showline=False,
            ticks="",
            fixedrange=True,
            tickfont=dict(color=TEXT, size=12),
        ),
        yaxis=dict(visible=False, range=[bottom, top], autorange=False, fixedrange=True),
    )
    return fig


def build_takeaway_line(t18, t06a):
    """The bold 14px line shown directly above the chart, below the
    title: how tightly the 16 charted shares cluster around the overall
    share. Raises if any row's interval sits entirely outside the
    overall interval (the same condition any_row_ochre checks), since
    'close to the overall' would then no longer be true."""
    rows, overall = _rows(t18, t06a)
    if any(r["is_ochre"] for r in rows):
        raise TitleAssumptionError(
            "Reach takeaway: a row's interval sits entirely outside the overall interval, so 'close to "
            "the overall' no longer holds."
        )
    n = len(rows)
    lo = round_whole(min(r["share"] for r in rows))
    hi = round_whole(max(r["share"] for r in rows))
    x = round_whole(overall["share"])
    return f"All {n} groups sit within {lo}% to {hi}%, close to the overall {x}%."


def any_row_ochre(t18, t06a):
    rows, _ = _rows(t18, t06a)
    return any(r["is_ochre"] for r in rows)


def build_reading_aid(t18, t06a):
    """The one-line reading aid under the chart. Checked against the data
    each call: if a row ever turns ochre, 'none stands out' would be
    false, so this raises instead of printing stale wording."""
    if any_row_ochre(t18, t06a):
        raise TitleAssumptionError("Reach reading aid: a row is ochre, so 'none stands out' no longer holds.")
    return READING_AID


def _p_values(t18b):
    p_values = {}
    for dim in CHARTED_DIMENSIONS:
        row = t18b.loc[t18b["Dimension"] == dim]
        if row.empty:
            raise TitleAssumptionError(f"Reach caption: t18b has no row for {dim}.")
        p_values[dim] = float(row["P_value"].iloc[0])
    return p_values


def build_caption(t18, t18b):
    """Build the caption (paragraphs 1 and 2). The caveat is a separate
    constant, REACH_CAVEAT. Every number is read from the tables.

    The first sentence of paragraph 2 (no difference beyond chance in
    any of the three) is included only if all three p-values are at
    least 0.05; otherwise it is left out, not softened."""
    overall = _overall(t18)
    share_whole = round_whole(overall["share"])

    def group_range(dimension):
        rows = t18.loc[(t18["Dimension"] == dimension)]
        return round_whole(float(rows["Share_exact"].min())), round_whole(float(rows["Share_exact"].max()))

    stream_min, stream_max = group_range("Funding_Source")
    provider_min, provider_max = group_range("Provider_ID")
    region_min, region_max = group_range("Remoteness")

    paragraph1_bold = (
        f"**Of {overall['students']:,} enrolled students, {overall['atsi_students']:,} ({share_whole}%) "
        f"are recorded as Aboriginal and Torres Strait Islander.**"
    )
    paragraph1_rest = (
        f"The share ranges from {stream_min}% to {stream_max}% across funding streams, {provider_min}% "
        f"to {provider_max}% across providers and {region_min}% to {region_max}% across regions."
    )

    p_values = _p_values(t18b)
    first_sentence_included = bool(all(p >= 0.05 for p in p_values.values()))
    if not first_sentence_included:
        raise TitleAssumptionError(
            f"Reach caption assumes no dimension's omnibus p-value is below 0.05; it is not true here: {p_values}."
        )
    stats_line = (
        f"For readers who want the statistics: the tests give p = {round_dp(p_values['Funding_Source'], 2):.2f} "
        f"for streams, {round_dp(p_values['Provider_ID'], 2):.2f} for providers and "
        f"{round_dp(p_values['Remoteness'], 2):.2f} for regions. If the groups did not really differ, spreads "
        f"this large would turn up about {round_whole(p_values['Funding_Source'] * 100)}, "
        f"{round_whole(p_values['Provider_ID'] * 100)} and {round_whole(p_values['Remoteness'] * 100)} times "
        f"in 100."
    )

    caption = f"{paragraph1_bold}\n\n{paragraph1_rest}"
    return caption, {
        "students": overall["students"],
        "atsi_students": overall["atsi_students"],
        "share_whole": share_whole,
        "stream_min": stream_min,
        "stream_max": stream_max,
        "provider_min": provider_min,
        "provider_max": provider_max,
        "region_min": region_min,
        "region_max": region_max,
        "p_values": p_values,
        "first_sentence_included": first_sentence_included,
        "stats_line": stats_line,
    }


TABLE_HEADERS = ["Group", "Students", "Aboriginal and Torres<br>Strait Islander students", "Share (%)", "95% interval (%)"]
TABLE_ALIGN = ["left", "right", "right", "right", "right"]


def build_table_html(t18, t18b, t06a):
    """The 'Show the numbers' table: an Overall row, then one section per
    dimension with its omnibus test p-value, then one row per group.
    Funding streams keep the chart's funded-hours order. Shares and
    intervals are read from the one-decimal display columns, which are
    already one decimal, so no value is rounded twice."""
    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header_html = "".join(f"<th style='text-align:{a};{th_style}'>{h}</th>" for h, a in zip(TABLE_HEADERS, TABLE_ALIGN))
    p_values = _p_values(t18b)

    def cells_html(cells):
        tds = "".join(
            f"<td style='padding:6px 10px;text-align:{a};color:{TEXT};word-wrap:break-word;"
            f"white-space:normal;'>{c}</td>"
            for c, a in zip(cells, TABLE_ALIGN)
        )
        return f"<tr>{tds}</tr>"

    def section_html(text):
        return (
            f"<tr><td colspan='{len(TABLE_HEADERS)}' style='padding:8px 10px;background-color:{GREY_LIGHT};"
            f"color:{TEXT};font-weight:bold;'>{text}</td></tr>"
        )

    body = []
    overall = t18.loc[t18["Dimension"] == "Overall"]
    if overall.empty:
        raise TitleAssumptionError("Reach table: t18 has no 'Overall' row.")
    o = overall.iloc[0]
    body.append(section_html("Overall (all enrolled students)"))
    body.append(
        cells_html(
            [
                "All enrolled students",
                f"{int(o['Students']):,}",
                f"{int(o['ATSI_students']):,}",
                f"{float(o['Share_%']):.1f}",
                f"{float(o['CI_Lower']):.1f} to {float(o['CI_Upper']):.1f}",
            ]
        )
    )

    for dimension in CHARTED_DIMENSIONS:
        p = round_dp(p_values[dimension], 2)
        body.append(section_html(f"{GROUP_HEADER_LABELS[dimension]} (test for any difference: p = {p:.2f})"))
        if dimension == "Funding_Source":
            group_order = funded_hours_stream_order(t06a)
        elif dimension == "Remoteness":
            group_order = REGION_ORDER
        else:
            group_order = sorted(t18.loc[t18["Dimension"] == dimension, "Group"].unique())
        for group in group_order:
            match = t18.loc[(t18["Dimension"] == dimension) & (t18["Group"] == group)]
            if match.empty:
                raise TitleAssumptionError(f"Reach table: t18 has no row for {dimension} = {group}.")
            r = match.iloc[0]
            if dimension == "Funding_Source":
                label = stream_label(group)
            elif dimension == "Provider_ID":
                label = provider_label(group)
            else:
                label = group
            body.append(
                cells_html(
                    [
                        label,
                        f"{int(r['Students']):,}",
                        f"{int(r['ATSI_students']):,}",
                        f"{float(r['Share_%']):.1f}",
                        f"{float(r['CI_Lower']):.1f} to {float(r['CI_Upper']):.1f}",
                    ]
                )
            )

    return (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header_html}</tr>{''.join(body)}</table>"
    )



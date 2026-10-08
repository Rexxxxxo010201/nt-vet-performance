"""
Chart 6: Completion. One dot plot with three labelled groups (Funding
stream, Provider, Region), each row showing a unit-level completion
rate and its 95% confidence interval against a pale ochre band for the
overall rate's own interval.

Rows are NOT sorted by rate within a group - streams stay in
funded-hours order (largest first, from the stream-by-outcome table),
providers stay in ID order, and regions stay in the fixed order Urban,
Regional, Remote - specifically so the chart cannot be read as a
league table.

Group headers and the blank row above each one (after the first group)
are both given their own dedicated category slot on the y-axis, the
same way a real data row gets one - not squeezed into the margin above
the group's first row - so a header can never overlap the previous
group's last row label regardless of how long that label is. The
category array is: [header, row, row, ..., gap, header, row, row,
...], with gap/header slots carrying no trace data (see
_category_layout). The separator line for each gap sits at that gap
slot's own category position (its vertical centre), needing no pixel
shift.

A row's dot and interval line turn ochre only if its entire interval
sits outside the overall interval (computed fresh from the data every
call, not assumed). Industry and Delivery_Year are not charted - they
stay in the "Show the numbers" table only; Remoteness is both charted
(as "Region") and kept in the table.

Rounding note: Rate_%, CI_Lower and CI_Upper are one-decimal display
values. t07 also carries full-precision companions - Rate_exact,
Lower_exact and Upper_exact (4 decimals), plus Achieved_units - added
specifically because rounding the one-decimal value a second time can
give the wrong whole number even with a correct half-up rule: Urban's
true rate is 59.4988%, stored as the display value 59.5, which rounds
up to 60 under any half-up rule, but the true value rounds down to 59.
Every whole-number label and caption figure in this module reads the
*_exact column and rounds it once, with round_whole() (see
lib/numfmt.py), never the one-decimal display column. The ochre rule
(whether a row's interval sits entirely outside the overall interval)
still compares the one-decimal CI_Lower/CI_Upper, unchanged from
before - only the whole-number display figures use the exact columns.

Coordinate reference note: `yref='paper'` (and `xref='paper'`) refer to
the plotting area only (0 = bottom/left of the plot area, 1 = top/
right), excluding the margins - confirmed from Plotly's own
`go.layout.Shape.yref` docstring ("paper... refers to the distance from
the bottom of the plotting area"), not the whole figure.

Every number is pulled from app/data/ at call time. The app is
laptop-only: one fixed desktop layout.
"""

import plotly.graph_objects as go

from .labels import provider_label
from .numfmt import round_dp, round_whole
from .theme import GREY_DARK, GREY_DOT, GREY_LIGHT, OCHRE, TEXT
from .titles import TitleAssumptionError
from .vocab import FUNDING_STREAM_NAMES

CHARTED_DIMENSIONS = ["Funding_Source", "Provider_ID", "Remoteness"]
GROUP_HEADER_LABELS = {"Funding_Source": "Funding stream", "Provider_ID": "Provider", "Remoteness": "Region"}
REGION_ORDER = ["Urban", "Regional", "Remote"]

TABLE_DIMENSION_ORDER = ["Funding_Source", "Provider_ID", "Industry", "Remoteness", "Delivery_Year"]
TABLE_DIMENSION_LABELS = {
    "Funding_Source": "Funding stream",
    "Provider_ID": "Provider",
    "Industry": "Industry",
    "Remoteness": "Remoteness",
    "Delivery_Year": "Delivery year",
}

ROW_HEIGHT = 30
TOP_MARGIN = 40  # room for the "Overall X% (Y to Z)" label above the plot
BOTTOM_MARGIN = 70  # x-axis tick labels, the axis title and the "Axis shows..." note
LEFT_MARGIN = 220
RIGHT_MARGIN = 200

AXIS_MIN_FLOOR = 50
AXIS_MAX_FLOOR = 70

LABEL_FONT_SIZE = 13


def _stream_order(t06a):
    totals = t06a.groupby("Funding_Source")["AHC_Funded"].sum()
    return totals.sort_values(ascending=False).index.tolist()


def _stream_label(code):
    return f"{code} {FUNDING_STREAM_NAMES.get(code, code)}"


def _rows(t07, t06a):
    """One dict per charted row (5 streams, then 8 providers, then 3
    regions), in the fixed display order. Each dict carries everything
    the figure and the hover text need."""
    stream_order = _stream_order(t06a)
    provider_order = sorted(t07.loc[t07["Dimension"] == "Provider_ID", "Group"].unique())

    overall = t07.loc[t07["Dimension"] == "Overall"]
    if overall.empty:
        raise TitleAssumptionError("Completion chart: t07 has no 'Overall' row.")
    overall_low = float(overall["CI_Lower"].iloc[0])
    overall_high = float(overall["CI_Upper"].iloc[0])

    rows = []
    for dimension, group_order, label_fn in [
        ("Funding_Source", stream_order, _stream_label),
        ("Provider_ID", provider_order, lambda g: g),
        ("Remoteness", REGION_ORDER, lambda g: g),
    ]:
        for group in group_order:
            match = t07.loc[(t07["Dimension"] == dimension) & (t07["Group"] == group)]
            if match.empty:
                raise TitleAssumptionError(f"Completion chart: t07 has no row for {dimension} = {group}.")
            r = match.iloc[0]
            low, high = float(r["CI_Lower"]), float(r["CI_Upper"])
            # The ochre rule compares the one-decimal display interval, unchanged from
            # before - only the whole-number labels below switch to the exact columns.
            is_ochre = bool(high < overall_low or low > overall_high)
            rows.append(
                {
                    "dimension": dimension,
                    "group": group,
                    "label": label_fn(group),
                    "rate": float(r["Rate_%"]),
                    "low": low,
                    "high": high,
                    "rate_exact": float(r["Rate_exact"]),
                    "low_exact": float(r["Lower_exact"]),
                    "high_exact": float(r["Upper_exact"]),
                    "units": int(r["Units"]),
                    "students": int(r["Students"]),
                    "is_ochre": is_ochre,
                }
            )
    return rows, overall_low, overall_high, float(overall["Rate_%"].iloc[0])


def _overall_exact(t07):
    """(rate_exact, low_exact, high_exact) for the Overall row."""
    overall = t07.loc[t07["Dimension"] == "Overall"]
    if overall.empty:
        raise TitleAssumptionError("Completion chart: t07 has no 'Overall' row.")
    r = overall.iloc[0]
    return float(r["Rate_exact"]), float(r["Lower_exact"]), float(r["Upper_exact"])


def _axis_range(rows):
    import math

    raw_min = 5 * math.floor(min(r["low"] for r in rows) / 5)
    raw_max = 5 * math.ceil(max(r["high"] for r in rows) / 5)
    return min(raw_min, AXIS_MIN_FLOOR), max(raw_max, AXIS_MAX_FLOOR)


def _category_layout(rows):
    """The full y-axis category order, including a dedicated slot for
    each group header and, for every group after the first, a
    dedicated blank slot immediately above it. Returns (categories,
    header_category_by_dimension, gap_category_by_dimension) - the
    header/gap entries are plain strings that no trace ever uses as a
    y-value, so Plotly reserves their row height without drawing
    anything there unless this module adds an annotation or shape at
    that exact category."""
    categories = []
    header_category = {}
    gap_category = {}
    for i, dimension in enumerate(CHARTED_DIMENSIONS):
        if i > 0:
            gap_key = f"__gap_before_{dimension}__"
            categories.append(gap_key)
            gap_category[dimension] = gap_key
        header_key = GROUP_HEADER_LABELS[dimension]
        categories.append(header_key)
        header_category[dimension] = header_key
        categories.extend(r["label"] for r in rows if r["dimension"] == dimension)
    return categories, header_category, gap_category


def _hover_label(row):
    """The group-label text shown in the dot's hover: provider_label()
    for Provider_ID rows, and row['label'] unchanged for Funding_Source
    (already '{code} {name}') and Remoteness (already a plain region
    name)."""
    if row["dimension"] == "Provider_ID":
        return provider_label(row["group"])
    return row["label"]


def build_figure(t07, t06a):
    rows, overall_low, overall_high, overall_rate = _rows(t07, t06a)
    overall_rate_exact, overall_low_exact, overall_high_exact = _overall_exact(t07)
    axis_min, axis_max = _axis_range(rows)
    categories, header_category, gap_category = _category_layout(rows)

    fig = go.Figure()

    # Pale ochre band for the overall interval, spanning every row -
    # added first so the rows' dots/lines render on top of it.
    fig.add_shape(
        type="rect",
        xref="x",
        yref="paper",
        x0=overall_low,
        x1=overall_high,
        y0=0,
        y1=1,
        fillcolor="rgba(163,90,22,0.15)",
        line=dict(width=0),
        layer="below",
    )
    fig.add_shape(
        type="line",
        xref="x",
        yref="paper",
        x0=overall_rate,
        x1=overall_rate,
        y0=0,
        y1=1,
        line=dict(color=OCHRE, width=1.5, dash="dash"),
    )

    # Separator line in each gap slot's own (blank) category position.
    for gap_key in gap_category.values():
        fig.add_shape(
            type="line",
            xref="x",
            x0=axis_min,
            x1=axis_max,
            yref="y",
            y0=gap_key,
            y1=gap_key,
            line=dict(color=GREY_LIGHT, width=1),
        )

    for row in rows:
        color = OCHRE if row["is_ochre"] else GREY_DOT
        fig.add_trace(
            go.Scatter(
                x=[row["low"], row["high"]],
                y=[row["label"], row["label"]],
                mode="lines",
                line=dict(color=color, width=1.5),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=[r["rate"] for r in rows],
            y=[r["label"] for r in rows],
            mode="markers",
            marker=dict(color=[OCHRE if r["is_ochre"] else GREY_DOT for r in rows], size=10),
            customdata=[
                [_hover_label(r), r["rate"], r["low"], r["high"], r["units"], r["students"]]
                for r in rows
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]:.1f}% (%{customdata[2]:.1f} to %{customdata[3]:.1f})"
                "<br>%{customdata[4]:,} units, %{customdata[5]:,} students<extra></extra>"
            ),
            showlegend=False,
        )
    )

    for row in rows:
        fig.add_annotation(
            x=axis_min,
            y=row["label"],
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
            y=row["label"],
            xref="x",
            yref="y",
            xanchor="left",
            yanchor="middle",
            xshift=14,
            align="left",
            showarrow=False,
            text=(
                f"{round_whole(row['rate_exact'])}%  "
                f"({round_whole(row['low_exact'])} to {round_whole(row['high_exact'])})"
            ),
            font=dict(size=LABEL_FONT_SIZE, color=GREY_DARK),
        )

    for dimension in CHARTED_DIMENSIONS:
        fig.add_annotation(
            x=axis_min,
            y=header_category[dimension],
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
        x=overall_rate,
        y=1,
        xref="x",
        yref="paper",
        xanchor="center",
        yanchor="bottom",
        yshift=10,
        showarrow=False,
        text=(
            f"Overall {round_whole(overall_rate_exact)}% "
            f"({round_whole(overall_low_exact)} to {round_whole(overall_high_exact)})"
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
        text="Units achieved (%)",
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

    fig.update_layout(
        height=TOP_MARGIN + ROW_HEIGHT * len(categories) + BOTTOM_MARGIN,
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
        yaxis=dict(
            visible=False,
            autorange="reversed",
            categoryorder="array",
            categoryarray=categories,
            fixedrange=True,
        ),
    )
    return fig


def build_takeaway_line(t07, t06a):
    """The bold 14px line shown directly above the chart, below the
    title: how tightly the 16 charted rates cluster around the overall
    rate. Raises if any row's interval sits entirely outside the
    overall interval (the same condition any_row_ochre checks), since
    'close to the overall' would then no longer be true."""
    rows, _, _, _ = _rows(t07, t06a)
    if any(r["is_ochre"] for r in rows):
        raise TitleAssumptionError(
            "Completion takeaway: a row's interval sits entirely outside the overall interval, so "
            "'close to the overall' no longer holds."
        )
    overall_rate_exact, _, _ = _overall_exact(t07)
    n = len(rows)
    lo = round_whole(min(r["rate_exact"] for r in rows))
    hi = round_whole(max(r["rate_exact"] for r in rows))
    x = round_whole(overall_rate_exact)
    return f"All {n} groups sit within {lo}% to {hi}%, close to the overall {x}%."


def any_row_ochre(t07, t06a):
    """True if at least one charted row's interval sits entirely
    outside the overall interval - exposed separately so callers (and
    this module's own build step) can report it rather than silently
    colour a row without comment."""
    rows, _, _, _ = _rows(t07, t06a)
    return any(r["is_ochre"] for r in rows)


READING_AID = (
    "Each dot is one group. The line shows the range we are confident in. Every group overlaps the "
    "shaded band, so none stands out."
)

# The 13px grey line above the "Show the numbers" table, explaining in plain
# words what each dimension's p-value means. Distinct from the table lead
# line (build_table_lead_line), which gives the industry-specific result.
PVALUE_KEY_LINE = (
    "Each p-value asks whether the groups in that block differ by more than chance would produce. "
    "Above 0.05 means the data is consistent with no difference; below 0.05 means a difference is "
    "unlikely to be chance."
)


def build_reading_aid(t07, t06a):
    """The one-line reading aid under the chart. Checked against the data
    each call: if a row ever turns ochre, 'none stands out' would be
    false, so this raises instead of printing stale wording."""
    if any_row_ochre(t07, t06a):
        raise TitleAssumptionError("Completion reading aid: a row is ochre, so 'none stands out' no longer holds.")
    return READING_AID


def build_caption(t07, t07_omnibus, t10):
    """Build the caption. Every number is read from the tables.

    The "no basis for ranking" sentence is only included if the
    funding-stream, provider AND remoteness omnibus p-values are all
    at least 0.05; otherwise the sentence names whichever dimension's
    test is below 0.05, with its p-value, and "no basis for ranking"
    is dropped rather than stated regardless.

    The closing "no sign that completion is lower in Remote areas"
    sentence is appended only if the remoteness p-value is at least
    0.05 AND the Remote rate is not below the lower of the Urban and
    Regional rates; otherwise it is left out entirely, not softened."""
    overall_rate_exact, overall_low_exact, overall_high_exact = _overall_exact(t07)

    streams = t07.loc[t07["Dimension"] == "Funding_Source"]
    providers = t07.loc[t07["Dimension"] == "Provider_ID"]
    regions = t07.loc[t07["Dimension"] == "Remoteness"]
    if streams.empty or providers.empty or regions.empty:
        raise TitleAssumptionError(
            "Completion caption: t07 is missing Funding_Source, Provider_ID or Remoteness rows."
        )

    def _min_max_exact(df):
        return float(df["Rate_exact"].min()), float(df["Rate_exact"].max())

    stream_min_exact, stream_max_exact = _min_max_exact(streams)
    provider_min_exact, provider_max_exact = _min_max_exact(providers)
    region_min_exact, region_max_exact = _min_max_exact(regions)

    paragraph1_bold = (
        f"**About {round_whole(overall_rate_exact)}% of units were achieved overall (between "
        f"{round_whole(overall_low_exact)}% and {round_whole(overall_high_exact)}%).**"
    )
    paragraph1_rest = (
        f"Rates range from {round_whole(stream_min_exact)}% to {round_whole(stream_max_exact)}% "
        f"across funding streams, {round_whole(provider_min_exact)}% to {round_whole(provider_max_exact)}% "
        f"across providers and {round_whole(region_min_exact)}% to {round_whole(region_max_exact)}% "
        f"across regions."
    )

    continuing_rows = t10.loc[t10["Definition"].str.startswith("(c) Continuing") & (t10["Scope"] == "Overall")]
    if continuing_rows.empty or "Rate_exact" not in t10.columns:
        raise TitleAssumptionError("Completion caption: t10 has no exact 'Continuing counted as non-completion' overall rate.")
    continuing_exact = float(continuing_rows["Rate_exact"].iloc[0])
    z = round_whole(continuing_exact)

    p_values = {}
    for dim in ["Funding_Source", "Provider_ID", "Remoteness"]:
        row = t07_omnibus.loc[t07_omnibus["Dimension"] == dim]
        if row.empty:
            raise TitleAssumptionError(f"Completion caption: t07_omnibus has no row for {dim}.")
        p_values[dim] = float(row["Omnibus_GEE_p_value"].iloc[0])

    no_basis_included = bool(all(p >= 0.05 for p in p_values.values()))
    if no_basis_included:
        paragraph2 = "No funding stream, provider or region stands out, so the data gives no basis for ranking them on completion."
    else:
        significant = {dim: p for dim, p in p_values.items() if p < 0.05}
        names = {"Funding_Source": "funding streams", "Provider_ID": "providers", "Remoteness": "regions"}
        parts = [f"{names[dim]} (p = {p:.2f})" for dim, p in significant.items()]
        paragraph2 = f"A statistical test finds a real difference between {' and '.join(parts)}."

    remote_row = regions.loc[regions["Group"] == "Remote"].iloc[0]
    urban_row = regions.loc[regions["Group"] == "Urban"].iloc[0]
    regional_row = regions.loc[regions["Group"] == "Regional"].iloc[0]
    remote_rate_exact = float(remote_row["Rate_exact"])
    urban_rate_exact = float(urban_row["Rate_exact"])
    regional_rate_exact = float(regional_row["Rate_exact"])
    remoteness_p = p_values["Remoteness"]

    remote_not_lower = bool(remote_rate_exact >= min(urban_rate_exact, regional_rate_exact))
    remote_sentence_included = bool(remoteness_p >= 0.05 and remote_not_lower)
    if remote_sentence_included:
        paragraph2 += (
            f" Remote areas are not behind: {round_whole(remote_rate_exact)}% against "
            f"{round_whole(urban_rate_exact)}% in Urban and {round_whole(regional_rate_exact)}% in Regional."
        )

    industry_row = t07_omnibus.loc[t07_omnibus["Dimension"] == "Industry"]
    if industry_row.empty:
        raise TitleAssumptionError("Completion caption: t07_omnibus has no row for Industry.")
    industry_p = float(industry_row["Omnibus_GEE_p_value"].iloc[0])

    stats_line = (
        f"For readers who want the statistics: the tests give p = {round_dp(p_values['Funding_Source'], 2):.2f} "
        f"for streams, {round_dp(p_values['Provider_ID'], 2):.2f} for providers, "
        f"{round_dp(p_values['Remoteness'], 2):.2f} for regions and {round_dp(industry_p, 2):.2f} for "
        f"industries. If groups did not really differ, differences this large would turn up about "
        f"{round_whole(p_values['Funding_Source'] * 100)}, {round_whole(p_values['Provider_ID'] * 100)}, "
        f"{round_whole(p_values['Remoteness'] * 100)} and {round_whole(industry_p * 100)} times in 100."
    )

    caption = f"{paragraph1_bold}\n\n{paragraph1_rest}\n\n{paragraph2}"
    return caption, {
        "stats_line": stats_line,
        "overall_rate": round_whole(overall_rate_exact),
        "stream_min": round_whole(stream_min_exact),
        "stream_max": round_whole(stream_max_exact),
        "provider_min": round_whole(provider_min_exact),
        "provider_max": round_whole(provider_max_exact),
        "region_min": round_whole(region_min_exact),
        "region_max": round_whole(region_max_exact),
        "p_values": p_values,
        "industry_p": industry_p,
        "no_basis_included": no_basis_included,
        "remote_sentence_included": remote_sentence_included,
        "continuing_as_not_completed": z,
    }


def build_table_lead_line(t07_omnibus):
    """The 13px grey line above the 'Show the numbers' table, naming the
    industry p-value fresh from t07_omnibus each call: raises if
    industry ever does stand out, rather than printing stale wording."""
    row = t07_omnibus.loc[t07_omnibus["Dimension"] == "Industry"]
    if row.empty:
        raise TitleAssumptionError("Completion table lead line: t07_omnibus has no row for Industry.")
    p = float(row["Omnibus_GEE_p_value"].iloc[0])
    if p < 0.05:
        raise TitleAssumptionError(
            "Completion table lead line: industry's p-value is below 0.05, so 'No industry stands out "
            "either' no longer holds."
        )
    return (
        "The chart shows streams, providers and regions. Industry and delivery year are added for "
        f"context. No industry stands out either (p = {p:.2f})."
    )


TABLE_HEADERS = ["Group", "Units", "Students", "Rate (%)", "95% interval"]
TABLE_ALIGN = ["left", "right", "right", "right", "right"]


def _table_group_label(dimension, group):
    from .labels import provider_label, stream_label

    if dimension == "Funding_Source":
        return stream_label(group)
    if dimension == "Provider_ID":
        return provider_label(group)
    return group


def build_table_html(t07, t07_omnibus, t06a):
    """The 'Show the numbers' table: a grouped section header row per
    dimension (with its omnibus test p-value, where one was run), then
    one row per group. Funding stream and Provider keep the chart's
    own order; Remoteness keeps the fixed Urban/Regional/Remote order
    used in the chart; Industry and Delivery_Year keep the source
    table's own order (already alphabetical/chronological)."""
    stream_order = _stream_order(t06a)

    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header_html = "".join(f"<th style='text-align:{a};{th_style}'>{h}</th>" for h, a in zip(TABLE_HEADERS, TABLE_ALIGN))

    section_rows = []
    for dimension in TABLE_DIMENSION_ORDER:
        dim_label = TABLE_DIMENSION_LABELS[dimension]
        if dimension == "Delivery_Year":
            header_text = f"{dim_label} (context only, no test run)"
        else:
            p_row = t07_omnibus.loc[t07_omnibus["Dimension"] == dimension]
            if p_row.empty:
                raise TitleAssumptionError(f"Completion table: t07_omnibus has no row for {dimension}.")
            p = float(p_row["Omnibus_GEE_p_value"].iloc[0])
            header_text = f"{dim_label} (test for any difference: p = {p:.2f})"

        section_rows.append(
            f"<tr><td colspan='{len(TABLE_HEADERS)}' style='padding:8px 10px;background-color:{GREY_LIGHT};"
            f"color:{TEXT};font-weight:bold;'>{header_text}</td></tr>"
        )

        if dimension == "Funding_Source":
            group_order = stream_order
        elif dimension == "Remoteness":
            group_order = REGION_ORDER
        else:
            group_order = t07.loc[t07["Dimension"] == dimension, "Group"].tolist()

        for group in group_order:
            match = t07.loc[(t07["Dimension"] == dimension) & (t07["Group"] == group)]
            if match.empty:
                raise TitleAssumptionError(f"Completion table: t07 has no row for {dimension} = {group}.")
            r = match.iloc[0]
            cells = [
                _table_group_label(dimension, group),
                f"{int(r['Units']):,}",
                f"{int(r['Students']):,}",
                f"{float(r['Rate_%']):.1f}",
                f"{float(r['CI_Lower']):.1f} to {float(r['CI_Upper']):.1f}",
            ]
            tds = "".join(
                f"<td style='padding:6px 10px;text-align:{a};color:{TEXT};word-wrap:break-word;"
                f"white-space:normal;'>{c}</td>"
                for c, a in zip(cells, TABLE_ALIGN)
            )
            section_rows.append(f"<tr>{tds}</tr>")

    return (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header_html}</tr>{''.join(section_rows)}</table>"
    )

"""
Chart 7: Equity. A two-row dot plot comparing Aboriginal and Torres
Strait Islander (ATSI = Y) and other (ATSI = N) learners' completion
rates: "As recorded" (the unadjusted rate, with its 95% interval) and
"After allowing for provider, funding stream, region, industry and
year" (the adjusted model's predicted rate - the model gives an
interval only for the odds ratio, not the predicted rates themselves,
so this row has no interval lines).

Within each logical row, the two learner groups sit on their own,
adjacent category slots (Row_Y, Row_N) rather than sharing one y
position - this is what gives them the "small vertical offset" the
brief asks for, and it falls out of the same technique already used
elsewhere in this app for group headers and separator rows: a plain
Plotly categorical y-axis, with the row's own label and right-hand
text positioned at the fractional category value exactly between the
two (e.g. 0.5 between categories 0 and 1), not tied to either one.

Rounding: every figure in this module is formatted from a table's
*_exact column (or, for the subgroup table's Y/N rates, from t09a's
Rate_exact) via round_whole/round_dp (lib/numfmt.py), never from a
one-decimal display column - see that module's docstring for why a
one-decimal value cannot simply be re-rounded. This chart's own
writing-standard exception (CLAUDE.md) is why rates and gaps here are
shown to one decimal place, not as whole numbers: the gap is the point
of the chart, and 58.6 - 61.4 = -2.8 only "adds up" at one decimal.

Every number is pulled from app/data/ at call time. The app is
laptop-only: one fixed desktop layout.
"""

import math

import plotly.graph_objects as go

from .numfmt import round_dp, round_whole
from .theme import GREY_DARK, GREY_DOT, GREY_LIGHT, OCHRE, TEXT
from .titles import TitleAssumptionError
from .vocab import FUNDING_STREAM_NAMES

ROW1_LABEL = "Unadjusted<br>(as recorded)"
ROW2_LABEL = "Adjusted for provider,<br>funding stream, region,<br>industry and year"

DEFINITION_LINE = "Rates are for units counted in the completion rate (achieved, not achieved or withdrawn)."

# T09c (the adjusted model's table) holds no CI_Lower/CI_Upper for the two
# predicted rates themselves (Model-predicted completion rate, ATSI = Y/N) -
# only for the odds ratio (OR 95% CI lower/upper). This line explains why
# the adjusted row's dots have no interval lines, unlike row 1's.
ADJUSTED_ROW_NO_INTERVAL_NOTE = (
    "Lines show the range we are confident in. The adjusted rates are model estimates, so their range "
    "is shown as the odds ratio on the right instead."
)

# The 13px grey line above the first expander table (the one with the
# p-value column), explaining in plain words what the p-value means.
PVALUE_KEY_LINE = (
    "Each p-value asks whether the groups differ by more than chance would produce. Above 0.05 means "
    "the data is consistent with no difference; below 0.05 means a difference is unlikely to be chance."
)

AXIS_MIN_FLOOR = 50
AXIS_MAX_FLOOR = 70

PX_PER_UNIT = 62  # pixels per unit on the numeric y scale below
TOP_MARGIN = 32  # just enough for the 13px key text and its yshift, above the plot area
BOTTOM_MARGIN = 50  # x-axis tick labels and the "Axis shows..." note
LEFT_MARGIN = 230
RIGHT_MARGIN = 260

DOT_SIZE = 11
LABEL_FONT_SIZE = 13

SUBGROUP_ORDER = [
    ("Overall", "Overall"),
    ("Remoteness", "Urban"),
    ("Remoteness", "Regional"),
    ("Remoteness", "Remote"),
    ("Funding_Source", "11J"),
    ("Funding_Source", "11K"),
    ("Funding_Source", "11N"),
    ("Funding_Source", "11V"),
    ("Funding_Source", "FFT"),
]


def _stream_label(code):
    return f"{code} {FUNDING_STREAM_NAMES.get(code, code)}"


def _group_label(dimension, group):
    return _stream_label(group) if dimension == "Funding_Source" else group


def _t09c_value(t09c, metric):
    row = t09c.loc[t09c["Metric"] == metric]
    if row.empty:
        raise TitleAssumptionError(f"Equity chart: t09c has no row for '{metric}'.")
    return float(row["Value_exact"].iloc[0])


def _overall_unadjusted(t09a, t09b):
    """(y, n) dicts for the Overall row's unadjusted rates/intervals/
    units, plus the Overall gap/interval, all from *_exact columns."""
    rows = {}
    for level in ["Y", "N"]:
        match = t09a.loc[(t09a["Dimension"] == "Overall") & (t09a["ATSI"] == level)]
        if match.empty:
            raise TitleAssumptionError(f"Equity chart: t09a has no Overall/{level} row.")
        r = match.iloc[0]
        rows[level] = {
            "rate": float(r["Rate_exact"]),
            "low": float(r["Lower_exact"]),
            "high": float(r["Upper_exact"]),
            "units": int(r["Units"]),
            "achieved": int(r["Achieved_units"]),
        }

    gap_row = t09b.loc[t09b["Dimension"] == "Overall"]
    if gap_row.empty:
        raise TitleAssumptionError("Equity chart: t09b has no Overall row.")
    g = gap_row.iloc[0]
    gap = {"gap": float(g["Gap_exact"]), "low": float(g["Lower_exact"]), "high": float(g["Upper_exact"])}
    return rows["Y"], rows["N"], gap


def _adjusted(t09c):
    """Predicted Y/N rates and gap, plus the odds ratio with its own
    interval and p-value, all from Value_exact."""
    pred_y = _t09c_value(t09c, "Model-predicted completion rate, ATSI = Y (%)")
    pred_n = _t09c_value(t09c, "Model-predicted completion rate, ATSI = N (%)")
    pred_gap = _t09c_value(t09c, "Model-predicted gap, Y minus N (pp)")
    or_point = _t09c_value(t09c, "ATSI odds ratio (Y vs N)")
    or_lo = _t09c_value(t09c, "OR 95% CI lower")
    or_hi = _t09c_value(t09c, "OR 95% CI upper")
    or_p = _t09c_value(t09c, "OR p-value")
    return (
        {"rate": pred_y},
        {"rate": pred_n},
        {"gap": pred_gap, "or": or_point, "or_low": or_lo, "or_high": or_hi, "p": or_p},
    )


def _units_hover_line(units):
    """The hover's third line, '<br>{units:,} units', or '' when there
    is no unit count (the adjusted/model-predicted dot)."""
    return f"<br>{units:,} units" if units is not None else ""


def _axis_range(y, n):
    bounds = [y["low"], y["high"], n["low"], n["high"]]
    raw_min = 5 * math.floor(min(bounds) / 5)
    raw_max = 5 * math.ceil(max(bounds) / 5)
    return min(raw_min, AXIS_MIN_FLOOR), max(raw_max, AXIS_MAX_FLOOR)


# One numeric y scale for every element in the chart (dots, interval lines,
# value labels, connectors, row labels, right-hand text). Y increases
# downwards; the axis is reversed by its range below so row 1 is at the top.
# Row 1's two learner groups sit 1 unit apart; row 2 starts 1.3 units
# below row 1's second group (the old categorical layout had 2 units, so
# the space between rows is about 35% less).
ROW1_ATSI_Y = 0.0
ROW1_OTHER_Y = 1.0
ROW1_LABEL_Y = 0.5
ROW2_ATSI_Y = 2.3
ROW2_OTHER_Y = 3.3
ROW2_LABEL_Y = 2.8

Y_TOP_PAD = 0.6  # space above row 1, for its value label and clear of the key
Y_BOTTOM_PAD = 0.6  # space below row 2, for its value label
Y_RANGE = [ROW2_OTHER_Y + Y_BOTTOM_PAD, ROW1_ATSI_Y - Y_TOP_PAD]  # [bottom, top]

KEY_YSHIFT_PX = 10  # the key's offset above the plot area
VALUE_LABEL_YSHIFT_PX = 16  # a value label's offset from its dot
VALUE_LABEL_HEIGHT_PX = 16  # approximate line height of a 13px label


def build_figure(t09a, t09b, t09c):
    y1, n1, gap1 = _overall_unadjusted(t09a, t09b)
    y2, n2, gap2 = _adjusted(t09c)
    axis_min, axis_max = _axis_range(y1, n1)

    fig = go.Figure()

    # Step connector for each logical row, added first so the dots render
    # on top: a short vertical segment from each dot to the midpoint
    # between the row's two sub-positions, joined by one horizontal
    # segment at that midpoint - not a diagonal straight line between
    # the two dots.
    fig.add_trace(
        go.Scatter(
            x=[y1["rate"], y1["rate"], n1["rate"], n1["rate"]],
            y=[ROW1_ATSI_Y, ROW1_LABEL_Y, ROW1_LABEL_Y, ROW1_OTHER_Y],
            mode="lines", line=dict(color=GREY_LIGHT, width=1.5), hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[y2["rate"], y2["rate"], n2["rate"], n2["rate"]],
            y=[ROW2_ATSI_Y, ROW2_LABEL_Y, ROW2_LABEL_Y, ROW2_OTHER_Y],
            mode="lines", line=dict(color=GREY_LIGHT, width=1.5), hoverinfo="skip", showlegend=False,
        )
    )

    # Row 1's own 95% interval lines.
    fig.add_trace(
        go.Scatter(
            x=[y1["low"], y1["high"]], y=[ROW1_ATSI_Y, ROW1_ATSI_Y], mode="lines",
            line=dict(color=OCHRE, width=1.5), hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[n1["low"], n1["high"]], y=[ROW1_OTHER_Y, ROW1_OTHER_Y], mode="lines",
            line=dict(color=GREY_DOT, width=1.5), hoverinfo="skip", showlegend=False,
        )
    )

    # Dots: ochre for ATSI = Y, grey for ATSI = N. Hover is "{Group}" /
    # "{rate}%" / "{units} units" for the unadjusted (T09a) dot; the
    # adjusted dot has no unit count (it is a model-predicted rate, not
    # a table of units), so its third line is blank rather than shown
    # as a false zero.
    fig.add_trace(
        go.Scatter(
            x=[y1["rate"], y2["rate"]], y=[ROW1_ATSI_Y, ROW2_ATSI_Y], mode="markers",
            marker=dict(color=OCHRE, size=DOT_SIZE),
            customdata=[
                ["Aboriginal and Torres Strait Islander learners, unadjusted", y1["rate"], _units_hover_line(y1["units"])],
                ["Aboriginal and Torres Strait Islander learners, adjusted (predicted)", y2["rate"], ""],
            ],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:.1f}%%{customdata[2]}<extra></extra>",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[n1["rate"], n2["rate"]], y=[ROW1_OTHER_Y, ROW2_OTHER_Y], mode="markers",
            marker=dict(color=GREY_DOT, size=DOT_SIZE),
            customdata=[
                ["Other learners, unadjusted", n1["rate"], _units_hover_line(n1["units"])],
                ["Other learners, adjusted (predicted)", n2["rate"], ""],
            ],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:.1f}%%{customdata[2]}<extra></extra>",
            showlegend=False,
        )
    )

    # Direct rate labels beside each dot: ATSI = Y above, ATSI = N below,
    # clear of the interval lines (which sit at the dot's own y) and the
    # step connector.
    for label_y, rate in [(ROW1_ATSI_Y, y1["rate"]), (ROW2_ATSI_Y, y2["rate"])]:
        fig.add_annotation(
            x=rate, y=label_y, xref="x", yref="y", yshift=VALUE_LABEL_YSHIFT_PX, showarrow=False,
            text=f"{round_dp(rate, 1)}%", font=dict(size=LABEL_FONT_SIZE, color=TEXT),
        )
    for label_y, rate in [(ROW1_OTHER_Y, n1["rate"]), (ROW2_OTHER_Y, n2["rate"])]:
        fig.add_annotation(
            x=rate, y=label_y, xref="x", yref="y", yshift=-VALUE_LABEL_YSHIFT_PX, showarrow=False,
            text=f"{round_dp(rate, 1)}%", font=dict(size=LABEL_FONT_SIZE, color=TEXT),
        )

    # Left-margin row labels, centred between each row's two dots.
    for y_pos, text in [(ROW1_LABEL_Y, ROW1_LABEL), (ROW2_LABEL_Y, ROW2_LABEL)]:
        fig.add_annotation(
            x=axis_min, y=y_pos, xref="x", yref="y", xanchor="right", yanchor="middle",
            xshift=-10, align="right", showarrow=False, text=text,
            font=dict(size=LABEL_FONT_SIZE, color=TEXT),
        )

    # Right-hand two-line text, one block per row, also centred between
    # that row's two dots.
    gap1_whole = round_dp(gap1["gap"], 1)
    direction1 = "lower" if gap1["gap"] < 0 else "higher"
    fig.add_annotation(
        x=axis_max, y=ROW1_LABEL_Y, xref="x", yref="y", xanchor="left", yanchor="middle",
        xshift=14, align="left", showarrow=False,
        text=(
            f"<b>{abs(gap1_whole)} points {direction1}</b><br>"
            f"<span style='color:{GREY_DARK};font-size:11px'>95% interval {round_dp(gap1['low'], 1)} "
            f"to {round_dp(gap1['high'], 1)} points</span>"
        ),
        font=dict(size=LABEL_FONT_SIZE, color=TEXT),
    )
    gap2_whole = round_dp(gap2["gap"], 1)
    direction2 = "lower" if gap2["gap"] < 0 else "higher"
    fig.add_annotation(
        x=axis_max, y=ROW2_LABEL_Y, xref="x", yref="y", xanchor="left", yanchor="middle",
        xshift=14, align="left", showarrow=False,
        text=(
            f"<b>{abs(gap2_whole)} points {direction2}</b><br>"
            f"<span style='color:{GREY_DARK};font-size:11px'>odds ratio {round_dp(gap2['or'], 2):.2f} "
            f"(95% interval {round_dp(gap2['or_low'], 2):.2f} to {round_dp(gap2['or_high'], 2):.2f}), "
            f"p = {round_dp(gap2['p'], 2):.2f}</span>"
        ),
        font=dict(size=LABEL_FONT_SIZE, color=TEXT),
    )

    # Key, above the plot area. xref must be 'paper' here, not 'x': the
    # x-axis range is [50, 70], so x=0 under xref='x' would sit far to
    # the left of the visible figure (this was the earlier bug - the
    # key was being drawn, just entirely off-canvas).
    fig.add_annotation(
        x=0, y=1, xref="paper", yref="paper", xanchor="left", yanchor="bottom", yshift=KEY_YSHIFT_PX,
        showarrow=False, align="left",
        text=(
            f"<span style='color:{OCHRE}'>&#9679;</span> Aboriginal and Torres Strait Islander learners"
            f"&nbsp;&nbsp;&nbsp;&nbsp;<span style='color:{GREY_DOT}'>&#9679;</span> Other learners"
        ),
        font=dict(size=13, color=TEXT),
    )
    fig.add_annotation(
        x=(axis_min + axis_max) / 2, y=0, xref="x", yref="paper", xanchor="center", yanchor="top",
        yshift=-34, showarrow=False, text=f"Axis shows {axis_min}% to {axis_max}%, not zero.",
        font=dict(size=11, color=GREY_DOT),
    )

    fig.update_layout(
        height=TOP_MARGIN + math.ceil((Y_RANGE[0] - Y_RANGE[1]) * PX_PER_UNIT) + BOTTOM_MARGIN,
        margin=dict(l=LEFT_MARGIN, r=RIGHT_MARGIN, t=TOP_MARGIN, b=BOTTOM_MARGIN),
        showlegend=False,
        xaxis=dict(
            range=[axis_min, axis_max], dtick=5, ticksuffix="%", showgrid=True, gridcolor=GREY_LIGHT,
            zeroline=False, showline=False, ticks="", fixedrange=True, tickfont=dict(color=TEXT, size=12),
        ),
        yaxis=dict(visible=False, range=list(Y_RANGE), autorange=False, fixedrange=True),
    )
    return fig


def _caption_group_name(row):
    """The short name used for a subgroup in the headline caption (not
    the table label): 'Remote areas' for a region, the stream name on
    its own (no code) for a funding stream."""
    if row["dimension"] == "Remoteness":
        return f"{row['group']} areas"
    if row["dimension"] == "Funding_Source":
        return FUNDING_STREAM_NAMES.get(row["group"], row["group"])
    return row["label"]


def build_caption(t09a, t09b, t09c):
    """Build the caption. Every number is read from the tables.

    'The gap is widest in...' names whichever subgroup rows have an
    interval that excludes zero (computed fresh from t09a/t09b each
    call, via _subgroup_rows); if none do, that sentence is dropped
    rather than naming a group that is not actually clearer than the
    rest. 'and that adjusted result is the one that clears the usual
    threshold' is only added if the unadjusted gap's interval includes
    zero AND the adjusted p-value is below 0.05 - checked fresh each
    call, since the claim would otherwise not be true of the data."""
    y1, n1, gap1 = _overall_unadjusted(t09a, t09b)
    y2, n2, gap2 = _adjusted(t09c)

    includes_zero = bool(gap1["low"] <= 0 <= gap1["high"])

    rows = [r for r in _subgroup_rows(t09a, t09b) if r["dimension"] != "Overall"]
    excluding_rows = [r for r in rows if r["excludes_zero"]]
    excluding_labels = [r["label"] for r in excluding_rows]
    if excluding_rows:
        names = [f"{_caption_group_name(r)} ({round_dp(abs(r['gap']), 1)} points)" for r in excluding_rows]
        if len(names) == 1:
            widest_sentence = f" The gap is widest in {names[0]}."
        else:
            widest_sentence = f" The gap is widest in {', '.join(names[:-1])} and {names[-1]}."
    else:
        widest_sentence = ""

    threshold_cleared = bool(includes_zero and gap2["p"] < 0.05)
    if threshold_cleared:
        allowed_for_sentence = (
            f" It is similar in size once those factors are allowed for ({round_dp(abs(gap2['gap']), 1)} "
            f"points), and that adjusted result is the one that clears the usual threshold."
        )
    else:
        allowed_for_sentence = (
            f" It is similar in size once those factors are allowed for ({round_dp(abs(gap2['gap']), 1)} points)."
        )

    main = (
        f"**Aboriginal and Torres Strait Islander learners achieved {round_dp(y1['rate'], 1)}% of their "
        f"units against {round_dp(n1['rate'], 1)}% for other learners, a gap of {round_dp(abs(gap1['gap']), 1)} "
        f"points.**\n\nThe gap is small.{allowed_for_sentence}{widest_sentence}"
    )

    p = gap2["p"]
    n_subgroups = len(rows)
    k_excluding = len(excluding_labels)
    expected_chance = round_dp(0.05 * n_subgroups, 2)
    if includes_zero:
        zero_word = "includes zero"
        zero_bracket = " (the range crosses zero, so that gap alone could be chance)"
    else:
        zero_word = "excludes zero"
        direction = "above" if gap1["low"] > 0 else "below"
        zero_bracket = f" (clearly {direction} zero, so unlikely to be chance)"
    stats_line = (
        f"For readers who want the statistics: the adjusted result is p = {round_dp(p, 2):.2f}. If there "
        f"were no real gap, a difference this size would turn up about {round_whole(p * 100)} times in 100. "
        f"The unadjusted gap of {round_dp(abs(gap1['gap']), 1)} points has an interval of "
        f"{round_dp(gap1['low'], 1)} to {round_dp(gap1['high'], 1)} points, which {zero_word}{zero_bracket}. "
        f"{k_excluding} of {n_subgroups} regional and funding stream gaps exclude zero, where about "
        f"{expected_chance:.2f} would be expected by chance. Intervals allow for the same student "
        f"appearing in several units."
    )

    return main, {
        "y1_rate": round_dp(y1["rate"], 1),
        "n1_rate": round_dp(n1["rate"], 1),
        "gap1": round_dp(gap1["gap"], 1),
        "y2_rate": round_dp(y2["rate"], 1),
        "n2_rate": round_dp(n2["rate"], 1),
        "gap2": round_dp(gap2["gap"], 1),
        "includes_zero": includes_zero,
        "excluding_labels": excluding_labels,
        "threshold_cleared": threshold_cleared,
        "stats_line": stats_line,
    }


SUMMARY_TABLE_HEADERS = ["Group", "Aboriginal and Torres Strait Islander learners (%)", "Other learners (%)", "Gap (points)", "95% interval or odds ratio", "p-value"]
SUMMARY_TABLE_ALIGN = ["left", "right", "right", "right", "right", "right"]


def build_summary_table_html(t09a, t09b, t09c):
    """The first expander table: 'As recorded' vs 'After allowing for
    provider, funding stream, region, industry and year', one decimal
    throughout."""
    y1, n1, gap1 = _overall_unadjusted(t09a, t09b)
    y2, n2, gap2 = _adjusted(t09c)

    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header_html = "".join(
        f"<th style='text-align:{a};{th_style}'>{h}</th>" for h, a in zip(SUMMARY_TABLE_HEADERS, SUMMARY_TABLE_ALIGN)
    )

    row1_cells = [
        "Unadjusted (as recorded)",
        f"{round_dp(y1['rate'], 1):.1f}",
        f"{round_dp(n1['rate'], 1):.1f}",
        f"{round_dp(gap1['gap'], 1):+.1f}",
        f"{round_dp(gap1['low'], 1):.1f} to {round_dp(gap1['high'], 1):.1f}",
        "not tested",
    ]
    row2_cells = [
        "Adjusted for provider, funding stream, region, industry and year",
        f"{round_dp(y2['rate'], 1):.1f}",
        f"{round_dp(n2['rate'], 1):.1f}",
        f"{round_dp(gap2['gap'], 1):+.1f}",
        f"{round_dp(gap2['or'], 2):.2f} ({round_dp(gap2['or_low'], 2):.2f} to {round_dp(gap2['or_high'], 2):.2f})",
        f"{round_dp(gap2['p'], 2):.2f}",
    ]

    body_rows = []
    for cells in [row1_cells, row2_cells]:
        tds = "".join(
            f"<td style='padding:6px 10px;text-align:{a};color:{TEXT};'>{c}</td>"
            for c, a in zip(cells, SUMMARY_TABLE_ALIGN)
        )
        body_rows.append(f"<tr>{tds}</tr>")

    table_html = (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header_html}</tr>{''.join(body_rows)}</table>"
    )
    note = (
        f"Units counted: Aboriginal and Torres Strait Islander learners {y1['units']:,}, "
        f"other learners {n1['units']:,}."
    )
    interval_only_note = "The unadjusted gap is shown with its interval only."
    return table_html, note, interval_only_note


SUBGROUP_TABLE_HEADERS = ["Group", "Aboriginal and Torres Strait Islander (%)", "Other learners (%)", "Gap (points)", "95% interval", "Interval excludes zero"]
SUBGROUP_TABLE_ALIGN = ["left", "right", "right", "right", "right", "left"]


def _subgroup_rows(t09a, t09b):
    rows = []
    for dimension, group in SUBGROUP_ORDER:
        y_match = t09a.loc[(t09a["Dimension"] == dimension) & (t09a["Group"] == group) & (t09a["ATSI"] == "Y")]
        n_match = t09a.loc[(t09a["Dimension"] == dimension) & (t09a["Group"] == group) & (t09a["ATSI"] == "N")]
        gap_match = t09b.loc[(t09b["Dimension"] == dimension) & (t09b["Group"] == group)]
        if y_match.empty or n_match.empty or gap_match.empty:
            raise TitleAssumptionError(f"Equity table: missing a row for {dimension} = {group}.")
        y_rate = float(y_match.iloc[0]["Rate_exact"])
        n_rate = float(n_match.iloc[0]["Rate_exact"])
        g = gap_match.iloc[0]
        low, high = float(g["Lower_exact"]), float(g["Upper_exact"])
        excludes_zero = bool(high < 0 or low > 0)
        rows.append(
            {
                "dimension": dimension,
                "group": group,
                "label": _group_label(dimension, group),
                "y_rate": y_rate,
                "n_rate": n_rate,
                "gap": float(g["Gap_exact"]),
                "low": low,
                "high": high,
                "excludes_zero": excludes_zero,
            }
        )
    return rows


def subgroup_comparison_count(t09b):
    """Number of subgroup comparisons: every ATSI gap row except Overall
    (3 regions and 5 funding streams = 8). Overall is the headline
    comparison, not a subgroup, so it is never counted here."""
    count = int((t09b["Dimension"] != "Overall").sum())
    if count < 1:
        raise TitleAssumptionError("Equity: t09b has no subgroup rows besides Overall.")
    return count


def build_subgroup_lead_line(t09a, t09b):
    """The 13px grey line above the subgroup table: a plain-words
    explanation of 'interval excludes zero', then how many rows are
    shaded and how many would be expected to exclude zero by chance
    alone with this many comparisons - all computed fresh from the
    data, not typed in. The explanation says the range sits 'below
    zero' because every excluding row currently excludes zero on the
    low side (ATSI completing less often); this raises rather than
    print a false direction if that ever changes."""
    rows = [r for r in _subgroup_rows(t09a, t09b) if r["dimension"] != "Overall"]
    n_subgroups = subgroup_comparison_count(t09b)
    excluding = [r for r in rows if r["excludes_zero"]]
    if excluding and any(r["high"] >= 0 for r in excluding):
        raise TitleAssumptionError(
            "Equity subgroup lead line: at least one excluding row's range sits above zero, so the "
            "fixed 'below zero' wording no longer holds for every row."
        )
    expected = round_dp(n_subgroups * 0.05, 2)
    return (
        "Each gap comes with a range we are confident it falls within. 'Interval excludes zero' means "
        "the whole range sits below zero, so the gap is unlikely to be chance. Where the range crosses "
        f"zero, the gap could be chance. Shaded rows are the ones that exclude zero. With {n_subgroups} "
        f"comparisons, about {expected:.2f} would exclude zero by chance alone."
    )


def build_subgroup_table_html(t09a, t09b):
    """The second expander table: all 9 comparisons (overall, 3
    regions, 5 funding streams), with any row whose interval excludes
    zero tinted light ochre. Returns (table_html, rounding_note)."""
    from .theme import OCHRE_LIGHT_TINT

    rows = _subgroup_rows(t09a, t09b)

    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header_html = "".join(
        f"<th style='text-align:{a};{th_style}'>{h}</th>" for h, a in zip(SUBGROUP_TABLE_HEADERS, SUBGROUP_TABLE_ALIGN)
    )

    body_rows = []
    for row in rows:
        bg = f"background-color:{OCHRE_LIGHT_TINT};" if row["excludes_zero"] else ""
        cells = [
            row["label"],
            f"{round_dp(row['y_rate'], 1):.1f}",
            f"{round_dp(row['n_rate'], 1):.1f}",
            f"{round_dp(row['gap'], 1):+.1f}",
            f"{round_dp(row['low'], 1):.1f} to {round_dp(row['high'], 1):.1f}",
            "Yes" if row["excludes_zero"] else "No",
        ]
        tds = "".join(
            f"<td style='padding:6px 10px;text-align:{a};color:{TEXT};'>{c}</td>"
            for c, a in zip(cells, SUBGROUP_TABLE_ALIGN)
        )
        body_rows.append(f"<tr style='{bg}'>{tds}</tr>")

    table_html = (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header_html}</tr>{''.join(body_rows)}</table>"
    )

    rounding_note = (
        "Gaps are calculated before rounding, so they can differ by 0.1 from the difference of the "
        "two rates shown."
    )
    return table_html, rounding_note

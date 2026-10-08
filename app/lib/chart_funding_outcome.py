"""
Funding vs outcome: one Sankey chart, Funding stream -> Outcome (merged
to four groups).

Node order is fixed (arrangement='fixed' in go.Sankey): streams are
ordered by funded hours, largest at the top; the four outcome nodes
keep a fixed semantic order (Achieved, Continuing or learner support,
Not achieved, Withdrawn) regardless of their size, so the two "not
completed" outcomes always sit together at the bottom. "Not funded /
not started" is zero AHC in this data and is left out of the diagram
entirely; the expander table keeps all six groups.

Sankey node.y convention (verified from plotly.js source, not assumed):
in src/traces/sankey/render.js, the block that applies a trace's fixed
node.x/node.y (used whenever arrangement='fixed') does

    var pos = [trace.node.x[i] * width, trace.node.y[i] * height];
    ...
    var nodeHeight = graph.nodes[i].y1 - graph.nodes[i].y0;
    graph.nodes[i].y0 = pos[1] - nodeHeight / 2;
    graph.nodes[i].y1 = pos[1] + nodeHeight / 2;

node.y is multiplied directly by height with no inversion (the same
un-inverted scaling used for node.x, which is unambiguously 0 = left),
so node.y: 0 = top, 1 = bottom. The assignment also shows node.y sets
the node's CENTRE (y0/y1 are the centre minus/plus half the node's own
height), not its top edge. Plotly's own "paper" and axis-domain
coordinates run the opposite way (0 = bottom, 1 = top), so converting a
node position into either one means using (1 - node_y).

Plotly Sankey traces have no real x/y axes to anchor annotations to, so
node labels, drawn as annotations rather than the Sankey's own on-node
text (which cannot carry two different text sizes/colours), are
positioned against a hidden xaxis/yaxis added to the figure purely as
an anchor, with the same [0, 1] domain the Sankey itself uses. This is
the same "axis-domain-relative, not paper-relative" technique every
other chart in this app already uses to extend a label into a margin
regardless of the figure's rendered width - 'paper' coordinates span
the whole image including the margins, so they would put the label at
the wrong position whenever the figure isn't rendered at exactly the
width assumed when the numbers were chosen.

Every number is pulled from app/data/ at call time. The app is
laptop-only: one fixed desktop layout.
"""

import plotly.graph_objects as go

from .labels import stream_label
from .numfmt import round_dp, round_whole
from .theme import GREY_DARK, OCHRE, TEXT
from .titles import TitleAssumptionError
from .vocab import FUNDING_STREAM_NAMES

OUTCOME_NODE_ORDER = ["Achieved", "Continuing or learner support", "Not achieved", "Withdrawn"]
OCHRE_OUTCOME_NODES = {"Not achieved", "Withdrawn"}

# Outcome_Group (as stored) -> the merged outcome node it feeds, or None
# if it is left out of the diagram (always zero AHC in this data).
OUTCOME_GROUP_TO_NODE = {
    "Achieved": "Achieved",
    "Continuing": "Continuing or learner support",
    "Learner support": "Continuing or learner support",
    "Not achieved": "Not achieved",
    "Withdrawn": "Withdrawn",
    "Not funded / not started": None,
}

NODE_GREY = "#9AA0A6"
LINK_GREY_RGBA = "rgba(201,205,210,0.45)"
LINK_OCHRE_RGBA = "rgba(163,90,22,0.55)"
BRACKET_OCHRE = "#7A4210"

BASE_HEIGHT = 480  # the chart's height before any room is added for the stream-node gaps (see _figure_height)
LEFT_MARGIN = 210
RIGHT_MARGIN = 380
TOP_MARGIN = 20
BOTTOM_MARGIN = 20
# Extra headroom above the plot area, added to both the top margin and the
# overall figure height, so the two changes cancel out: the plot area's
# pixel height (and every node's position within it) is unchanged, the
# whole Sankey is simply shifted down by this many pixels inside a taller
# figure, leaving real empty space above the topmost node/link for its
# hover label to expand into without being clipped by the figure's edge.
HOVER_CLIP_FIX_PX = 50
# Fractional distance of the first/last outcome node's centre from the
# plot edge (BASE_HEIGHT-relative; the outcome column's height never
# changes - see module docstring on "keep the outcome nodes as they
# are"). Node rendered height is flow-proportional and not something
# this module controls directly, so this margin is a deliberately
# generous estimate of "at least 12px clear of the top/bottom edge,
# plus the node's own height" rather than a measured value - worth a
# visual check for a flow whose node ends up unusually tall.
NODE_Y_MARGIN = 0.06

# A visible gap between adjacent stream nodes, about 2.5% of BASE_HEIGHT
# (12px), inserted on top of the even spacing those nodes would
# otherwise get. Node height is flow-proportional, not fixed, so this
# guarantees *some* real separation between node rectangles regardless
# of how large any one flow is - unlike the outcome column, whose
# spacing is left exactly as it was.
STREAM_GAP_FRACTION = 0.025

LABEL_FONT_SIZE = 13
LABEL_WRAP_WIDTH = 170  # px: long outcome names wrap to two lines rather than running past the margin
NODE_X_LEFT = 0.01
NODE_X_RIGHT = 0.99

# The bracket is a shape, not an annotation, so it has no pixel xshift
# to lean on (see _add_not_completed_bracket) - its position has to be
# given directly in the hidden axis's 0-1 units. Converting "about
# 190px beyond the outcome nodes" into that unit needs an assumed
# total rendered figure width; 900px is used because that is the one
# actual fixed number in this app (app/lib/theme.py caps the content
# column at max-width: 900px) - the true rendered width can still come
# in narrower than that cap on an actual browser window, which is the
# most likely reason this offset needs a visual check.
_ASSUMED_FIGURE_WIDTH_PX = 900
_ASSUMED_DOMAIN_WIDTH_PX = _ASSUMED_FIGURE_WIDTH_PX - LEFT_MARGIN - RIGHT_MARGIN
BRACKET_OFFSET_PX = 190
BRACKET_X = NODE_X_RIGHT + BRACKET_OFFSET_PX / _ASSUMED_DOMAIN_WIDTH_PX

# Explicit <br> breaks for outcome names that would otherwise run
# wider than LABEL_WRAP_WIDTH on one line - annotation width does not
# auto-wrap text (see module docstring), so these are mandatory, not
# cosmetic.
OUTCOME_LABEL_LINE_BREAKS = {
    "Continuing or learner support": "Continuing or<br>learner support",
}

CLAUSE_FUNDED_IN_FULL_THRESHOLD = 95


def _share(ahc, total):
    # Both arguments are always exact AHC_Funded sums computed fresh here, never a
    # pre-rounded display column, so a single round_whole() call is exact.
    return round_whole(100 * float(ahc) / float(total))


def _node_y_positions(n):
    """Even spacing for the outcome column - unchanged by this task."""
    if n == 1:
        return [0.5]
    span = 1 - 2 * NODE_Y_MARGIN
    return [NODE_Y_MARGIN + i * span / (n - 1) for i in range(n)]


def _figure_height(n_streams):
    """BASE_HEIGHT, plus room for the (n_streams - 1) explicit gaps
    between stream nodes, so they can be added without encroaching on
    the top/bottom margin."""
    if n_streams <= 1:
        return BASE_HEIGHT
    gap_px = STREAM_GAP_FRACTION * BASE_HEIGHT
    return BASE_HEIGHT + (n_streams - 1) * gap_px


def _stream_y_positions(n, figure_height):
    """Stream-node centres: the same NODE_Y_MARGIN-from-the-edge and
    largest-first-at-the-top convention as _node_y_positions, but with
    STREAM_GAP_FRACTION of BASE_HEIGHT worth of extra, explicit gap
    folded into every step - a real gap between node rectangles, not
    just between their centres, regardless of how tall the flow makes
    any one of them. figure_height is taller than BASE_HEIGHT by
    exactly the amount _figure_height adds for this many streams, so
    the margin and step, held fixed in BASE_HEIGHT pixels, come out as
    smaller fractions of the taller figure without changing in
    absolute terms."""
    if n == 1:
        return [0.5]
    margin_px = NODE_Y_MARGIN * BASE_HEIGHT
    gap_px = STREAM_GAP_FRACTION * BASE_HEIGHT
    natural_step_px = (BASE_HEIGHT - 2 * margin_px) / (n - 1)
    step_px = natural_step_px + gap_px
    margin_fraction = margin_px / figure_height
    step_fraction = step_px / figure_height
    return [margin_fraction + i * step_fraction for i in range(n)]


def _ordered_totals(df, group_col):
    """Group totals, sorted largest first - the shared ordering rule for
    stream nodes."""
    totals = df.groupby(group_col)["AHC_Funded"].sum()
    return totals.sort_values(ascending=False)


def _merged_outcome_totals(df, group_col, group_key):
    """AHC for one stream, merged onto the four outcome nodes, as
    {node_name: ahc}. Groups mapping to None (zero-AHC in this data)
    are dropped, not merely zeroed, so a stray non-zero value there
    would surface as a visible link instead of silently vanishing."""
    sub = df.loc[df[group_col] == group_key]
    totals = {}
    for _, row in sub.iterrows():
        node = OUTCOME_GROUP_TO_NODE.get(row["Outcome_Group"])
        if node is None:
            if row["AHC_Funded"] != 0:
                raise TitleAssumptionError(
                    f"Funding vs outcome: '{row['Outcome_Group']}' is assumed to always be zero AHC and "
                    f"is left out of the Sankey diagram, but {group_key} has {row['AHC_Funded']} AHC in it."
                )
            continue
        totals[node] = totals.get(node, 0) + float(row["AHC_Funded"])
    return totals


def _stream_plain_name(code):
    return f"{code} {FUNDING_STREAM_NAMES.get(code, code)}"


def _stream_node_label(code, share_pct):
    return f"{_stream_plain_name(code)} {share_pct}%"


def _stream_not_completed_exact(t06a, stream):
    """Not-achieved plus withdrawn share of a stream's hours, from the
    4-decimal Share_within_Stream_exact companions (t06a)."""
    sub = t06a.loc[(t06a["Funding_Source"] == stream) & t06a["Outcome_Group"].isin(["Not achieved", "Withdrawn"])]
    if sub.empty or "Share_within_Stream_exact" not in sub.columns:
        raise TitleAssumptionError(f"Funding vs outcome caption: t06a has no exact shares for stream {stream}.")
    return float(sub["Share_within_Stream_exact"].sum())


def _industry_not_completed_exact(t17a, industry):
    """Not-completed share of an industry's hours, from the 4-decimal
    Not_Completed_Share_exact companion (t17a)."""
    rows = t17a.loc[t17a["Industry"] == industry]
    if rows.empty or "Not_Completed_Share_exact" not in rows.columns:
        raise TitleAssumptionError(f"Funding vs outcome caption: t17a has no exact share for {industry}.")
    return float(rows["Not_Completed_Share_exact"].iloc[0])


def _link_hover_template():
    return "<b>%{customdata[0]} to %{customdata[1]}</b><br>%{value:,.0f} hours (%{customdata[2]:.1f}% of this stream's hours)<extra></extra>"


def _node_hover_template():
    return "<b>%{customdata[0]}</b><br>%{customdata[1]:,.0f} hours (%{customdata[2]:.1f}% of all funded hours)<extra></extra>"


def _links(t06a):
    """The stream -> merged-outcome links, as a plain list of dicts (not
    a Figure), so totals and conservation can be checked directly
    against the source table in tests."""
    stream_totals = _ordered_totals(t06a, "Funding_Source")
    stream_order = stream_totals.index.tolist()

    result = []
    for stream in stream_order:
        merged = _merged_outcome_totals(t06a, "Funding_Source", stream)
        for outcome in OUTCOME_NODE_ORDER:
            value = merged.get(outcome, 0)
            if value <= 0:
                continue
            result.append({"source": stream, "target": outcome, "value": value})
    return result, stream_order, stream_totals


def build_figure(t06a):
    links, stream_order, stream_totals = _links(t06a)
    overall_total = float(stream_totals.sum())

    outcome_totals = {name: 0.0 for name in OUTCOME_NODE_ORDER}
    for link in links:
        outcome_totals[link["target"]] += link["value"]

    figure_height = _figure_height(len(stream_order))
    stream_y = dict(zip(stream_order, _stream_y_positions(len(stream_order), figure_height)))
    outcome_y = dict(zip(OUTCOME_NODE_ORDER, _node_y_positions(len(OUTCOME_NODE_ORDER))))

    node_keys = stream_order + OUTCOME_NODE_ORDER
    node_x = [NODE_X_LEFT] * len(stream_order) + [NODE_X_RIGHT] * len(OUTCOME_NODE_ORDER)
    node_y = [stream_y[s] for s in stream_order] + [outcome_y[o] for o in OUTCOME_NODE_ORDER]
    node_color = [NODE_GREY] * len(stream_order) + [
        OCHRE if o in OCHRE_OUTCOME_NODES else NODE_GREY for o in OUTCOME_NODE_ORDER
    ]
    key_to_index = {key: i for i, key in enumerate(node_keys)}

    link_source_totals = {}
    for link in links:
        link_source_totals[link["source"]] = link_source_totals.get(link["source"], 0) + link["value"]

    customdata = []
    link_colors = []
    for link in links:
        customdata.append(
            [_stream_plain_name(link["source"]), link["target"], 100 * link["value"] / link_source_totals[link["source"]]]
        )
        link_colors.append(LINK_OCHRE_RGBA if link["target"] in OCHRE_OUTCOME_NODES else LINK_GREY_RGBA)

    # Node hover: stream nodes show the full stream label; outcome nodes
    # show the outcome name as already displayed, never the raw
    # Outcome_Group/Source field names. Hours and share are exact (the
    # share is the node's exact fraction of all funded hours, formatted
    # to one decimal in the template, not the whole-number _share()
    # already used for the on-chart labels).
    node_customdata = [[_stream_plain_name(s), stream_totals[s], 100 * stream_totals[s] / overall_total] for s in stream_order]
    node_customdata += [[o, outcome_totals[o], 100 * outcome_totals[o] / overall_total] for o in OUTCOME_NODE_ORDER]

    fig = go.Figure(
        go.Sankey(
            arrangement="fixed",
            node=dict(
                label=["" for _ in node_keys],
                color=node_color,
                x=node_x,
                y=node_y,
                pad=18,
                thickness=14,
                line=dict(width=0),
                customdata=node_customdata,
                hovertemplate=_node_hover_template(),
            ),
            link=dict(
                source=[key_to_index[link["source"]] for link in links],
                target=[key_to_index[link["target"]] for link in links],
                value=[link["value"] for link in links],
                color=link_colors,
                customdata=customdata,
                hovertemplate=_link_hover_template(),
            ),
        )
    )

    # Hidden axes, anchored to the same [0, 1] domain the Sankey uses by
    # default, purely so label annotations and the outcome-gap bracket
    # can be positioned with xref='x'/yref='y' (axis-domain-relative,
    # correct at any rendered width) instead of xref='paper' (relative
    # to the whole image including the margins - see module docstring).
    fig.update_layout(
        xaxis=dict(visible=False, range=[0, 1], domain=[0, 1], fixedrange=True),
        yaxis=dict(visible=False, range=[0, 1], domain=[0, 1], fixedrange=True),
    )

    for stream in stream_order:
        fig.add_annotation(
            x=NODE_X_LEFT,
            y=1 - stream_y[stream],
            xref="x",
            yref="y",
            xanchor="right",
            yanchor="middle",
            xshift=-8,
            align="right",
            showarrow=False,
            text=_stream_node_label(stream, _share(stream_totals[stream], overall_total)),
            font=dict(size=LABEL_FONT_SIZE, color=GREY_DARK),
        )
    for outcome in OUTCOME_NODE_ORDER:
        display_name = OUTCOME_LABEL_LINE_BREAKS.get(outcome, outcome)
        fig.add_annotation(
            x=NODE_X_RIGHT,
            y=1 - outcome_y[outcome],
            xref="x",
            yref="y",
            xanchor="left",
            yanchor="middle",
            xshift=8,
            align="left",
            showarrow=False,
            text=f"{display_name} {_share(outcome_totals[outcome], overall_total)}%",
            font=dict(size=LABEL_FONT_SIZE, color=GREY_DARK),
            width=LABEL_WRAP_WIDTH,
        )

    _add_not_completed_bracket(fig, outcome_y, overall_total, outcome_totals)

    # figure_height (the plot area) is unchanged; HOVER_CLIP_FIX_PX is added
    # to both the overall height and the top margin, so the plot area's own
    # pixel height - and every node's position within it - stays exactly
    # the same, just shifted down inside a taller figure (see
    # HOVER_CLIP_FIX_PX's own comment above).
    fig.update_layout(
        height=figure_height + HOVER_CLIP_FIX_PX,
        margin=dict(l=LEFT_MARGIN, r=RIGHT_MARGIN, t=TOP_MARGIN + HOVER_CLIP_FIX_PX, b=BOTTOM_MARGIN),
        hoverlabel=dict(font=dict(size=LABEL_FONT_SIZE)),
    )
    return fig


def _add_not_completed_bracket(fig, outcome_y, overall_total, outcome_totals):
    """The ochre bracket and '{pct}% of funded hours' text beyond the
    outcome labels, spanning the 'Not achieved' and 'Withdrawn' nodes.
    Each node's own rendered height is flow-proportional, not a fixed
    value this module sets, so the bracket's span is approximated from
    the gap between the two nodes' centres (a third of that gap beyond
    each centre) rather than their true top/bottom edges - worth a
    visual check against where the flows actually land. BRACKET_X
    itself is also an approximation (see its definition) for the same
    reason: shapes, unlike annotations, have no pixel xshift, so its
    position has to be given directly in an assumed-width-dependent
    axis unit."""
    not_completed_ahc = outcome_totals.get("Not achieved", 0) + outcome_totals.get("Withdrawn", 0)
    pct = _share(not_completed_ahc, overall_total)

    gap = outcome_y["Withdrawn"] - outcome_y["Not achieved"]
    top_y = outcome_y["Not achieved"] - gap * 0.3
    bottom_y = outcome_y["Withdrawn"] + gap * 0.3

    tick = 0.015

    fig.add_shape(
        type="path",
        xref="x",
        yref="y",
        path=(
            f"M {BRACKET_X},{1 - top_y} L {BRACKET_X + tick},{1 - top_y} "
            f"M {BRACKET_X},{1 - top_y} L {BRACKET_X},{1 - bottom_y} "
            f"M {BRACKET_X},{1 - bottom_y} L {BRACKET_X + tick},{1 - bottom_y}"
        ),
        line=dict(color=BRACKET_OCHRE, width=2),
    )
    fig.add_annotation(
        x=BRACKET_X + tick,
        y=1 - (top_y + bottom_y) / 2,
        xref="x",
        yref="y",
        xanchor="left",
        yanchor="middle",
        xshift=6,
        align="left",
        showarrow=False,
        text=f"<b>{pct}% of<br>funded hours</b>",
        font=dict(size=12, color=BRACKET_OCHRE),
    )


def build_caption(t06a, t06c, t17a):
    """Build the caption. Every number is read from the tables, from the
    4-decimal exact shares (t06a and t17a), never a one-decimal column."""
    total = float(t06a["AHC_Funded"].sum())
    not_achieved = float(t06a.loc[t06a["Outcome_Group"] == "Not achieved", "AHC_Funded"].sum())
    withdrawn = float(t06a.loc[t06a["Outcome_Group"] == "Withdrawn", "AHC_Funded"].sum())
    not_completed = not_achieved + withdrawn

    stream_shares = {fs: _stream_not_completed_exact(t06a, fs) for fs in t06a["Funding_Source"].unique()}
    stream_low = min(stream_shares.values())
    stream_high = max(stream_shares.values())

    industry_shares = {ind: _industry_not_completed_exact(t17a, ind) for ind in t17a["Industry"].unique()}
    low_industry = min(industry_shares, key=industry_shares.get)
    high_industry = max(industry_shares, key=industry_shares.get)

    y_row = t06c.loc[t06c["Funded_Flag"] == "Y"]
    if y_row.empty:
        raise TitleAssumptionError("Funding vs outcome caption: t06c has no Funded_Flag = Y row.")
    # AHC_Funded is an exact integer, so the share is recomputed fresh from it rather
    # than reading the one-decimal Share_% column.
    p = 100 * float(y_row["AHC_Funded"].iloc[0]) / float(t06c["AHC_Funded"].sum())
    funded_in_full_included = bool(p >= CLAUSE_FUNDED_IN_FULL_THRESHOLD)

    paragraph1_bold = (
        f"**{round_whole(p)}% of the hours on units not achieved or withdrawn are recorded as fully "
        f"funded.**"
    )
    paragraph1_rest = (
        f"The share ranges from {round_whole(stream_low)}% to {round_whole(stream_high)}% across "
        f"funding streams and {round_whole(industry_shares[low_industry])}% to "
        f"{round_whole(industry_shares[high_industry])}% across industries."
    )
    paragraph2 = "To size the cost, payment records for these units are the next thing to obtain."

    caption = f"{paragraph1_bold}\n\n{paragraph1_rest}\n\n{paragraph2}"
    return caption, {
        "not_completed_pct": _share(not_completed, total),
        "stream_shares": stream_shares,
        "industry_shares": industry_shares,
        "low_industry": low_industry,
        "high_industry": high_industry,
        "funded_in_full_included": funded_in_full_included,
        "p": p,
    }


def build_continuing_share_note(t06a):
    """Replaces the old caveat's first sentence and its data-dictionary
    sentence (moved to the Method page): the share of hours still in
    units continuing or in learner support, stated as a fact."""
    total = float(t06a["AHC_Funded"].sum())
    continuing = float(
        t06a.loc[t06a["Outcome_Group"].isin(["Continuing", "Learner support"]), "AHC_Funded"].sum()
    )
    x = round_whole(100 * continuing / total)
    return (
        f"{x}% of hours are in units still continuing or in learner support, so the final share not "
        f"completed could still change. Industry is taken from each unit's program."
    )


OUTCOME_TABLE_VALUE_COLUMNS = ["Achieved", "Not achieved", "Withdrawn", "Continuing", "Learner support", "Not completed"]


def _outcome_wide_rows(df, group_col, group_order, overall_total):
    """One row per stream, with the five displayed outcome totals, a
    derived 'Not completed' total, that total's exact share of the
    stream's own hours, and the stream's share of all funded hours -
    the shape behind the 'show the numbers' table."""
    rows = []
    for key in group_order:
        sub = df.loc[df[group_col] == key]
        group_total = sub["AHC_Funded"].sum()
        outcome_sums = sub.groupby("Outcome_Group")["AHC_Funded"].sum()
        not_completed = outcome_sums.get("Not achieved", 0) + outcome_sums.get("Withdrawn", 0)
        rows.append(
            {
                "key": key,
                "Achieved": outcome_sums.get("Achieved", 0),
                "Not achieved": outcome_sums.get("Not achieved", 0),
                "Withdrawn": outcome_sums.get("Withdrawn", 0),
                "Continuing": outcome_sums.get("Continuing", 0),
                "Learner support": outcome_sums.get("Learner support", 0),
                "Not completed": not_completed,
                # Both group_total and not_completed are exact integer AHC sums,
                # so this share needs no *_exact companion to round once from.
                "Not_Completed_Share_exact": round_dp(100 * not_completed / group_total, 4) if group_total else 0.0,
                "Share_of_Total_%": round(100 * group_total / overall_total, 1),
            }
        )
    return rows


SHADED_OUTCOME_COLUMNS = {"Not achieved", "Withdrawn"}
SHADING_TAKEAWAY = "Shaded: hours on units not achieved or withdrawn."


def build_table_takeaway(t06a):
    """The lead line above the 'Show the numbers' table: the shading rule
    plus the share-not-completed range across streams, from the same
    exact per-stream shares the table's new column shows."""
    stream_totals = _ordered_totals(t06a, "Funding_Source")
    overall_total = float(stream_totals.sum())
    rows = _outcome_wide_rows(t06a, "Funding_Source", stream_totals.index.tolist(), overall_total)
    shares = {r["key"]: r["Not_Completed_Share_exact"] for r in rows}
    lo_key = min(shares, key=shares.get)
    hi_key = max(shares, key=shares.get)
    lo, hi = round_whole(shares[lo_key]), round_whole(shares[hi_key])
    return (
        f"{SHADING_TAKEAWAY} The share not completed is {lo}% to {hi}% "
        f"across streams, highest in {stream_label(hi_key)} and lowest in {stream_label(lo_key)}."
    )


def build_table_html(t06a):
    from .theme import GREY_LIGHT, OCHRE_LIGHT_TINT

    stream_totals = _ordered_totals(t06a, "Funding_Source")
    overall_total = float(stream_totals.sum())
    rows = _outcome_wide_rows(t06a, "Funding_Source", stream_totals.index.tolist(), overall_total)

    headers = (
        ["Funding stream"] + OUTCOME_TABLE_VALUE_COLUMNS + ["Share not completed (%)", "Share of all funded hours (%)"]
    )
    aligns = ["left"] + ["right"] * (len(OUTCOME_TABLE_VALUE_COLUMNS) + 2)
    th_style = f"padding:6px 10px;border-bottom:1px solid {GREY_LIGHT};color:{TEXT};"
    header_html = "".join(f"<th style='text-align:{a};{th_style}'>{h}</th>" for h, a in zip(headers, aligns))

    # Column labels, aligned with `cells` below: the stream name, then one
    # per OUTCOME_TABLE_VALUE_COLUMNS entry, then the two percentage columns.
    col_names = [None] + OUTCOME_TABLE_VALUE_COLUMNS + [None, None]

    body_rows = []
    for row in rows:
        cells = (
            [stream_label(row["key"])]
            + [f"{row[c]:,.0f}" for c in OUTCOME_TABLE_VALUE_COLUMNS]
            + [f"{round_dp(row['Not_Completed_Share_exact'], 1):.1f}", f"{row['Share_of_Total_%']:.1f}"]
        )
        tds = "".join(
            f"<td style='padding:6px 10px;text-align:{a};color:{TEXT};"
            f"{'background-color:' + OCHRE_LIGHT_TINT + ';' if name in SHADED_OUTCOME_COLUMNS else ''}"
            f"word-wrap:break-word;white-space:normal;'>{c}</td>"
            for c, a, name in zip(cells, aligns, col_names)
        )
        body_rows.append(f"<tr>{tds}</tr>")

    return (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr>{header_html}</tr>{''.join(body_rows)}</table>"
    )
